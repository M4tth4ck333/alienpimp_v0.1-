import asyncio
import logging
import json
import csv
import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict
import sys
import shutil # Für cleanup in main()

# --- Konfiguration ---
LOG_FILE = "package_manager.log"
DEFAULT_LOG_LEVEL = logging.INFO

# --- Enums für Typ-Sicherheit und Klarheit ---
class SourceType(str, Enum):
    DEB = "deb"
    RPM = "rpm"
    PACMAN = "pacman"
    PYPI = "pypi"
    GITHUB = "github"
    LOCAL = "local"
    GIT = "git" # Hinzugefügt für generische Git-Quellen
    HTTP = "http" # Hinzugefügt für direkte Downloads

class BuildSystem(str, Enum):
    MAKE = "make"
    CMAKE = "cmake"
    NINJA = "ninja"
    MESON = "meson"
    AUTOTOOLS = "autotools"
    SCONS = "scons"
    WAF = "waf"
    SETUPTOOLS = "setuptools"
    POETRY = "poetry"
    PIP = "pip" # NEU: Für Python-Pakete wie theHarvester
    GO = "go"
    CARGO = "cargo"
    TCC_BUILD = "tcc_build" 

# --- Basis-Klasse für Pakete (Zellbaustein) ---
@dataclass
class BasePackage:
    name: str
    version: str
    source: Union[str, SourceType]
    filepath: Optional[Path] = None  # Pfad zur lokalen Datei des Pakets
    build_system: Optional[Union[str, BuildSystem]] = None
    sha256: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict) # Für JPEGs, etc.

    def __post_init__(self):
        self._validate_fields()
        self._convert_enums()

    def _validate_fields(self):
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Package name must be a non-empty string.")
        if not self.version or not isinstance(self.version, str):
            raise ValueError("Version must be a non-empty string.")
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict.")
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime object.")
        if self.filepath and not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

    def _convert_enums(self):
        if isinstance(self.source, str):
            try:
                self.source = SourceType(self.source.lower())
            except ValueError:
                raise ValueError(f"Invalid source type '{self.source}'. Allowed: {[s.value for s in SourceType]}")
        elif not isinstance(self.source, SourceType):
            raise TypeError("source must be a string or SourceType Enum.")

        if self.build_system:
            if isinstance(self.build_system, str):
                try:
                    self.build_system = BuildSystem(self.build_system.lower())
                except ValueError:
                    raise ValueError(f"Unsupported build system '{self.build_system}'. Allowed: {[b.value for b in BuildSystem]}")
            elif not isinstance(self.build_system, BuildSystem):
                raise TypeError("build_system must be a string or BuildSystem Enum.")

    def set_metadata(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError("Metadata key must be a string.")
        self.metadata[key] = value
        logging.debug(f"Metadata '{key}' set for package '{self.name}'.")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    async def calculate_sha256(self, force: bool = False) -> Optional[str]:
        if self.sha256 is not None and not force:
            logging.debug(f"Using cached SHA256 for '{self.name}'.")
            return self.sha256
        if not self.filepath or not self.filepath.is_file():
            # Wenn es ein Verzeichnis ist, sollte man einen Verzeichnis-Hash machen,
            # aber hier fokussieren wir auf eine einzelne Datei für SHA256
            logging.warning(f"Cannot calculate SHA256 for '{self.name}': filepath not set or not a single file.")
            return None

        logging.info(f"Calculating SHA256 for '{self.name}' at '{self.filepath}'...")
        h = hashlib.sha256()
        try:
            with open(self.filepath, "rb") as f:
                while chunk := await asyncio.to_thread(f.read, 4096): # non-blocking file read
                    h.update(chunk)
            self.sha256 = h.hexdigest()
            logging.info(f"SHA256 calculated for '{self.name}': {self.sha256}")
            return self.sha256
        except Exception as e:
            logging.error(f"Error calculating SHA256 for '{self.name}': {e}")
            return None

    def to_json_dict(self) -> Dict[str, Any]:
        """Konvertiert BasePackage-Objekt in ein JSON-serialisierbares Dictionary."""
        d = asdict(self)
        d['filepath'] = str(self.filepath) if self.filepath else None
        d['timestamp'] = self.timestamp.isoformat()
        if isinstance(d['source'], Enum): d['source'] = d['source'].value
        if isinstance(d['build_system'], Enum): d['build_system'] = d['build_system'].value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_json_dict(), indent=2, ensure_ascii=False)

    def to_csv_dict(self, meta_prefix="meta_") -> Dict[str, Any]:
        d = self.to_json_dict() # Nutze die JSON-Grundstruktur
        d['filepath'] = d['filepath'] or '' # CSV braucht leere Strings statt None
        d['build_system'] = d['build_system'] or ''
        d['sha256'] = d['sha256'] or ''
        # Flatten metadata keys with prefix
        meta = d.pop("metadata", {})
        for k, v in meta.items():
            d[f"{meta_prefix}{k}"] = v
        return d

    @staticmethod
    def _export_to_file(packages: List["BasePackage"], filepath: Path, exporter_func, mode: str, **kwargs) -> None:
        if not packages:
            logging.warning(f"No packages to export to {filepath}.")
            return
        try:
            with open(filepath, mode, encoding='utf-8', **kwargs) as f:
                exporter_func(packages, f)
            logging.info(f"Packages successfully exported to {filepath}.")
        except Exception as e:
            logging.error(f"Failed to export packages to {filepath}: {e}")
            raise RuntimeError(f"Export failed: {e}")

    @staticmethod
    def export_to_csv(packages: List["BasePackage"], filepath: Path) -> None:
        def _write_csv(pkgs: List["BasePackage"], f):
            keys = set()
            rows = [p.to_csv_dict() for p in pkgs]
            for row in rows:
                keys.update(row.keys())
            # Stellen Sie sicher, dass wichtige Felder zuerst kommen
            ordered_keys = ['name', 'version', 'source', 'build_system', 'filepath', 'sha256', 'timestamp']
            remaining_keys = sorted([k for k in keys if k not in ordered_keys])
            final_keys = ordered_keys + remaining_keys

            writer = csv.DictWriter(f, fieldnames=final_keys)
            writer.writeheader()
            writer.writerows(rows)
        
        BasePackage._export_to_file(packages, filepath, _write_csv, 'w', newline='')

    @staticmethod
    def export_to_json(packages: List["BasePackage"], filepath: Path) -> None:
        def _write_json(pkgs: List["BasePackage"], f):
            data = [p.to_json_dict() for p in pkgs]
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        BasePackage._export_to_file(packages, filepath, _write_json, 'w')

    async def build(self) -> None:
        if not self.build_system:
            logging.error(f"Cannot build package '{self.name}': No build system defined.")
            raise RuntimeError("No build system defined.")
        
        logging.info(f"Attempting to build package '{self.name}' using build system '{self.build_system.value}'...")
        
        # Vor dem Bauen prüfen, ob Klonen erforderlich ist
        if self.source in [SourceType.GITHUB, SourceType.GIT]:
            if not self.filepath or not self.filepath.is_dir():
                logging.info(f"Source is '{self.source}', and filepath is not a valid directory. Attempting to clone.")
                try:
                    await self._clone_repository()
                    # Nach dem Klonen den Hash neu berechnen, da die Datei jetzt lokal ist
                    # SHA256 von Verzeichnissen ist komplexer; hier vereinfacht für eine Hauptdatei
                    # oder der Hash wird nach Installation des Pakets auf die Binary/Hauptdatei angewendet.
                    # await self.calculate_sha256(force=True) # Deaktiviert, da filepath jetzt ein Dir ist
                except RuntimeError as e:
                    logging.error(f"Failed to clone repository for {self.name}: {e}")
                    raise # Build kann nicht fortgesetzt werden ohne Quellcode
            else:
                logging.info(f"Source is '{self.source}', and filepath '{self.filepath}' already exists. Skipping clone.")

        # NEU: Spezielle Logik für theHarvester
        if self.name == "theHarvester" and self.build_system == BuildSystem.PIP:
            logging.info(f"Special build path detected for {self.name} using pip.")
            await self._build_pip_install() # Neue Methode für pip
        elif self.name == "social-engineer-toolkit" and self.build_system == BuildSystem.PIP:
            logging.info(f"Special build path detected for {self.name} using pip.")
            await self._build_pip_install() # Auch SET wird mit pip installiert
        elif self.name == "Tiny-C-Compiler" and self.build_system == BuildSystem.TCC_BUILD:
            logging.info(f"Special build path detected for {self.name}.")
            await self._build_tcc()
        else:
            # Dispatch an spezialisierte, asynchrone Methoden oder an ein externes Build-System-Modul
            build_func_name = f"_build_{self.build_system.value.replace('-', '_')}" # make-like names python-friendly
            build_func = getattr(self, build_func_name, None)

            if build_func and asyncio.iscoroutinefunction(build_func):
                await build_func()
            else:
                logging.warning(f"No specific async build method found for {self.build_system.value}. Using generic build logic.")
                # Hier könnte die Schnittstelle zu Ihrem C++ Build-System oder externen Tools sein
                print(f"Executing generic build for {self.name}...")
                # Beispiel: await asyncio.sleep(2) # Simuliere Arbeit
                logging.info(f"Generic build for {self.name} completed.")

    async def _clone_repository(self) -> None:
        """
        Klont das Repository, wenn SourceType GITHUB oder GIT ist.
        Der Klon-Pfad wird aus dem Paketnamen und dem aktuellen Arbeitsverzeichnis abgeleitet,
        oder kann optional in metadata['clone_path'] hinterlegt werden.
        """
        repo_url = self.metadata.get('repo_url')
        if not repo_url and self.source == SourceType.GITHUB:
            # Annahme für GitHub: URL kann aus name abgeleitet werden, wenn keine explizite URL gegeben
            repo_url = f"https://github.com/{self.source_from_name()}/{self.name}.git"
        elif not repo_url and self.source == SourceType.GIT:
             raise ValueError(f"Repository URL not found in metadata['repo_url'] for GIT source type.")

        if not repo_url:
            logging.error(f"Cannot clone '{self.name}': No repository URL found in metadata or derivable from source.")
            raise RuntimeError(f"No repository URL specified for {self.name}.")

        # Zielpfad für das Klonen
        clone_dir = self.metadata.get('clone_path', Path.cwd() / self.name)
        if not isinstance(clone_dir, Path):
            clone_dir = Path(clone_dir)

        if clone_dir.exists() and any(clone_dir.iterdir()):
            logging.warning(f"Clone directory '{clone_dir}' for '{self.name}' already exists and is not empty. Skipping clone.")
            self.filepath = clone_dir # Setze filepath, auch wenn nicht geklont
            return

        logging.info(f"Cloning repository '{repo_url}' for package '{self.name}' to '{clone_dir}'...")
        try:
            proc = await asyncio.create_subprocess_exec(
                'git', 'clone', repo_url, str(clone_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logging.info(f"Successfully cloned '{repo_url}' for '{self.name}'.")
                self.filepath = clone_dir
            else:
                logging.error(f"Failed to clone '{repo_url}' for '{self.name}' (Return Code: {proc.returncode}):\n{stderr.decode().strip()}")
                raise RuntimeError(f"Git clone failed for {self.name}.")
        except FileNotFoundError:
            logging.error("Git command not found. Is Git installed and in PATH?")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred during cloning {self.name}: {e}")
            raise

    # Hilfsfunktion, um den GitHub-Benutzernamen aus dem Paketnamen abzuleiten (Beispiel)
    def source_from_name(self) -> str:
        # Für M4tth4ck333 Repositories
        if self.name in ["theHarvester", "Tiny-C-Compiler", "weirdolib-ng", "hashcat", "social-engineer-toolkit"]:
            return "M4tth4ck333"
        return self.metadata.get('github_user', 'default_github_user') 

    # --- Beispiel-Spezialmethoden für Build-Systeme (asynchron) ---
    async def _build_make(self):
        logging.info(f"Starting async Make build for {self.name}...")
        if not self.filepath or not self.filepath.is_dir():
            raise RuntimeError(f"Cannot build {self.name}: filepath not set or not a directory after cloning.")
        try:
            proc = await asyncio.create_subprocess_exec(
                'make', '-C', str(self.filepath), 
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                logging.info(f"Make build for {self.name} successful:\n{stdout.decode().strip()}")
            else:
                logging.error(f"Make build for {self.name} failed (Return Code: {proc.returncode}):\n{stderr.decode().strip()}")
                raise RuntimeError(f"Make build failed for {self.name}")
        except FileNotFoundError:
            logging.error("Make command not found. Is Make installed and in PATH?")
            raise
        except Exception as e:
            logging.error(f"An error occurred during Make build for {self.name}: {e}")
            raise
        
    async def _build_cmake(self):
        logging.info(f"Starting async CMake build for {self.name}...")
        if not self.filepath or not self.filepath.is_dir():
            raise RuntimeError(f"Cannot build {self.name}: filepath not set or not a directory after cloning.")
        
        build_dir = self.filepath / "build" 
        build_dir.mkdir(parents=True, exist_ok=True)
        try:
            logging.debug(f"Running CMake configure in {build_dir} for {self.name}...")
            proc_config = await asyncio.create_subprocess_exec(
                'cmake', str(self.filepath), '-B', str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_config, stderr_config = await proc_config.communicate()
            if proc_config.returncode != 0:
                logging.error(f"CMake configure for {self.name} failed:\n{stderr_config.decode().strip()}")
                raise RuntimeError(f"CMake configure failed for {self.name}")
            logging.debug(f"CMake configure output:\n{stdout_config.decode().strip()}")

            logging.debug(f"Running CMake build in {build_dir} for {self.name}...")
            proc_build = await asyncio.create_subprocess_exec(
                'cmake', '--build', str(build_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_build, stderr_build = await proc_build.communicate()
            if proc_build.returncode == 0:
                logging.info(f"CMake build for {self.name} successful:\n{stdout_build.decode().strip()}")
            else:
                logging.error(f"CMake build for {self.name} failed (Return Code: {proc_build.returncode}):\n{stderr_build.decode().strip()}")
                raise RuntimeError(f"CMake build failed for {self.name}")
        except FileNotFoundError:
            logging.error("CMake command not found. Is CMake installed and in PATH?")
            raise
        except Exception as e:
            logging.error(f"An error occurred during CMake build for {self.name}: {e}")
            raise

    async def _build_tcc(self):
        logging.info(f"Starting special TCC build for {self.name} with 2>&1 | gcc...")
        if not self.filepath or not self.filepath.is_dir():
            raise RuntimeError(f"Cannot build {self.name}: filepath not set or not a directory after cloning.")
        
        # Annahme: 'tcc' Executable ist im geklonten Repo-Root von Tiny-C-Compiler vorhanden
        tcc_compiler_path = self.filepath / "tcc" 
        if not tcc_compiler_path.is_file():
            # Wenn tcc nicht direkt ausführbar ist, müsste es erst gebaut werden (z.B. mit Make)
            # bevor es als Compiler genutzt werden kann. Das wäre ein vorgelagerter Schritt.
            # Für dieses Beispiel nehmen wir an, es ist da oder wird gefunden.
            logging.warning(f"TCC compiler not found at expected path: {tcc_compiler_path}. Attempting to use system TCC if available.")
            tcc_compiler_path = "tcc" # Fallback to system TCC

        test_c_file = self.filepath / "temp_test.c"
        test_out_file = self.filepath / "temp_test_output"
        test_c_file.write_text('int main() { printf("Hello from TCC build test!\\n"); return 0; }')

        try:
            logging.debug(f"Compiling a dummy C file with TCC using '{tcc_compiler_path}' at {self.filepath}")
            tcc_proc = await asyncio.create_subprocess_exec(
                str(tcc_compiler_path),
                str(test_c_file),
                '-o', str(test_out_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.filepath) # Wichtig: CWD setzen, falls TCC relative Pfade erwartet
            )
            tcc_stdout, tcc_stderr = await tcc_proc.communicate()

            logging.info(f"TCC output (stdout):\n{tcc_stdout.decode().strip()}")
            logging.info(f"TCC errors (stderr):\n{tcc_stderr.decode().strip()}")

            if tcc_proc.returncode != 0:
                logging.error(f"TCC compilation failed for {self.name} (Return Code: {tcc_proc.returncode})")
                raise RuntimeError(f"TCC compilation failed for {self.name}")
            
            # Hier der Part für "2>&1 | gcc" - Analyse der TCC-Ausgabe
            combined_output = tcc_stdout + tcc_stderr
            if combined_output:
                logging.debug(f"Piping combined TCC output to GCC for analysis...")
                gcc_proc = await asyncio.create_subprocess_exec(
                    'gcc', '-x', 'c', '-', 
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE 
                )
                gcc_stdout, gcc_stderr = await gcc_proc.communicate(input=combined_output)
                logging.info(f"GCC analysis output (stdout):\n{gcc_stdout.decode().strip()}")
                logging.info(f"GCC analysis errors (stderr):\n{gcc_stderr.decode().strip()}")
                if gcc_proc.returncode != 0:
                    logging.warning(f"GCC analysis returned non-zero exit code {gcc_proc.returncode}. Might indicate issues.")
            else:
                logging.info("No TCC output to pipe to GCC for analysis.")

            logging.info(f"Special TCC build for {self.name} completed successfully.")

        except FileNotFoundError as e:
            logging.error(f"Required command (TCC or GCC) not found for TCC build: {e}")
            raise RuntimeError(f"Required command not found: {e}")
        except Exception as e:
            logging.error(f"An error occurred during special TCC build for {self.name}: {e}")
            raise

    # NEU: Spezielle Build-Methode für PIP
    async def _build_pip_install(self):
        logging.info(f"Starting pip installation for {self.name}...")
        if not self.filepath or not self.filepath.is_dir():
            raise RuntimeError(f"Cannot install {self.name}: filepath not set or not a directory after cloning.")
        
        try:
            # Installiere im "editable" Modus (-e) oder direkt aus dem Quellcode-Verzeichnis
            # Dies simuliert `pip install .` im Repository-Root
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', str(self.filepath), # Installiere aus dem Verzeichnis
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                logging.info(f"Successfully installed {self.name} via pip:\n{stdout.decode().strip()}")
                # Optional: Nach erfolgreicher Installation den Pfad zur Haupt-Executable/Modul ermitteln
                # und in filepath oder metadata speichern.
                # Für theHarvester könnte das der Pfad zum theHarvester Skript sein.
                installed_script = shutil.which(self.name) # Versuche, den installierten Pfad zu finden (z.B. 'theHarvester' oder 'setoolkit')
                if installed_script:
                    self.set_metadata("installed_executable", str(installed_script))
                    logging.info(f"Executable for {self.name} found at: {installed_script}")
                else:
                    logging.warning(f"Could not determine installed executable path for {self.name}.")
            else:
                logging.error(f"Pip installation failed for {self.name} (Return Code: {proc.returncode}):\n{stderr.decode().strip()}")
                raise RuntimeError(f"Pip installation failed for {self.name}")
        except FileNotFoundError:
            logging.error("Python or Pip command not found. Is Python installed and in PATH?")
            raise
        except Exception as e:
            logging.error(f"An error occurred during pip installation for {self.name}: {e}")
            raise


    def __repr__(self) -> str:
        return f"<BasePackage {self.name} v{self.version} ({self.source.value if isinstance(self.source, Enum) else self.source})>"

# --- Initialisierung des Loggers (für das gesamte System) ---
def setup_system_logging(log_level=DEFAULT_LOG_LEVEL):
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Auch auf Konsole ausgeben
        ]
    )
    logging.getLogger(__name__).info("System logging initialized.")

# --- Beispiel für die Nutzung (Asynchrone Event-Loop) ---
async def main():
    setup_system_logging(logging.DEBUG) # Setze Level auf DEBUG für detaillierte Ausgabe
    
    # Beispiel für Tiny-C-Compiler
    tcc_package = BasePackage(
        name="Tiny-C-Compiler",
        version="0.9.27", # Annahme
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/M4tth4ck333/Tiny-C-Compiler.git"},
        build_system=BuildSystem.TCC_BUILD, 
        filepath=Path("Tiny-C-Compiler") 
    )

    # Beispiel für theHarvester
    theharvester_package = BasePackage(
        name="theHarvester",
        version="4.3.0", # Annahme
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/M4tth4ck333/theHarvester.git"},
        build_system=BuildSystem.PIP, # Wird via PIP installiert
        filepath=Path("theHarvester") # Standard-Klonpfad im CWD
    )

    # NEUE PAKETE
    weirdolib_ng_package = BasePackage(
        name="weirdolib-ng",
        version="1.0.0", # Annahme
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/M4tth4ck333/weirdolib-ng.git"},
        build_system=BuildSystem.MAKE, # Vermutung basierend auf C/C++ Bibliothek
        filepath=Path("weirdolib-ng")
    )

    hashcat_package = BasePackage(
        name="hashcat",
        version="6.2.6", # Annahme
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/M4tth4ck333/hashcat.git"},
        build_system=BuildSystem.MAKE, # Typischer Build für Hashcat
        filepath=Path("hashcat")
    )

    social_engineer_toolkit_package = BasePackage(
        name="social-engineer-toolkit",
        version="10.0", # Annahme
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/M4tth4ck333/social-engineer-toolkit.git"},
        build_system=BuildSystem.PIP, # Python-Tool, wahrscheinlich pip install
        filepath=Path("social-engineer-toolkit")
    )
    
    packages_to_manage = [
        tcc_package, 
        theharvester_package,
        weirdolib_ng_package,
        hashcat_package,
        social_engineer_toolkit_package
    ]

    for pkg in packages_to_manage:
        try:
            await pkg.build()
            # SHA256 auf die Haupt-Executable/Installationsdateien anwenden, falls relevant
            # Dies müsste spezifischer sein, z.B. Hash der installierten theHarvester Binary
            # oder des TCC Compilers nach dem Build.
            # Für Verzeichnisse ist ein rekursiver Hash nötig, hier übersprungen.
            if pkg.name in ["theHarvester", "social-engineer-toolkit"] and pkg.get_metadata("installed_executable"):
                 # Versuche, den Hash der installierten Binärdatei zu berechnen
                 pkg.filepath = Path(pkg.get_metadata("installed_executable"))
                 await pkg.calculate_sha256(force=True)
            elif pkg.name == "Tiny-C-Compiler" and (pkg.filepath / "tcc").is_file():
                 pkg.filepath = pkg.filepath / "tcc" # Hash des TCC-Compilers
                 await pkg.calculate_sha256(force=True)
            elif pkg.name == "hashcat" and (pkg.filepath / "hashcat").is_file(): # Annahme für hashcat binary
                 pkg.filepath = pkg.filepath / "hashcat"
                 await pkg.calculate_sha256(force=True)
            elif pkg.name == "weirdolib-ng" and (pkg.filepath / "libweirdo.so").is_file(): # Annahme für eine lib
                 pkg.filepath = pkg.filepath / "libweirdo.so" # Beispiel, muss überprüft werden
                 await pkg.calculate_sha256(force=True)
            else:
                 logging.info(f"Skipping SHA256 calculation for {pkg.name} as no specific file to hash after build.")
        except RuntimeError as e:
            logging.error(f"Build process failed for {pkg.name}: {e}")
        except FileNotFoundError as e:
             logging.error(f"Required tool for {pkg.name} not found: {e}")


    # Pakete exportieren
    exported_packages = packages_to_manage
    try:
        await asyncio.to_thread(BasePackage.export_to_json, exported_packages, Path("packages_export.json"))
        await asyncio.to_thread(BasePackage.export_to_csv, exported_packages, Path("packages_export.csv"))
    except RuntimeError as e:
        logging.error(f"Error during export: {e}")

    logging.info("Alien Package Manager 2.0 operations completed.")


if __name__ == "__main__":
    async def cleanup_dummy_repos(paths: List[Path]):
        for path in paths:
            if path.exists() and path.is_dir():
                logging.info(f"Cleaning up dummy repository at {path}...")
                try:
                    await asyncio.to_thread(shutil.rmtree, path, ignore_errors=True) 
                    logging.info(f"Cleaned up {path}")
                except Exception as e:
                    logging.error(f"Error during cleanup of {path}: {e}")

    async def prepare_and_run():
        repos_to_clean = [
            Path("Tiny-C-Compiler"), 
            Path("theHarvester"), 
            Path("weirdolib-ng"),
            Path("hashcat"),
            Path("social-engineer-toolkit")
        ]
        await cleanup_dummy_repos(repos_to_clean) 
        
        # Erstellen eines Dummy-Verzeichnisses für den lokalen Test (falls es nicht vom Klonen kommt)
        # Für den Tiny-C-Compiler Test, der eine C-Datei braucht
        dummy_tcc_path = Path("Tiny-C-Compiler")
        if not dummy_tcc_path.exists():
            dummy_tcc_path.mkdir(parents=True, exist_ok=True)
            # Eine Dummy-tcc binary für den Test, da ein kompletter TCC-Build komplex ist
            # In einem echten Szenario müsste TCC entweder bereits im PATH sein oder erst gebaut werden.
            (dummy_tcc_path / "tcc").write_text("#!/bin/bash\necho 'Simulating TCC compilation...'\nexit 0", encoding='utf-8')
            (dummy_tcc_path / "tcc").chmod(0o755) # Ausführbar machen
            (dummy_tcc_path / "temp_test.c").write_text('int main() { return 0; }', encoding='utf-8')
            logging.info(f"Dummy TCC environment created at {dummy_tcc_path}")

        # Erstellen von Dummy Makefiles für weirdolib-ng und hashcat, falls die Klone leer bleiben
        dummy_weirdolib_path = Path("weirdolib-ng")
        if not dummy_weirdolib_path.exists():
            dummy_weirdolib_path.mkdir(parents=True, exist_ok=True)
            (dummy_weirdolib_path / "Makefile").write_text("all:\n\techo 'Building weirdolib-ng'", encoding='utf-8')
            logging.info(f"Dummy weirdolib-ng environment created at {dummy_weirdolib_path}")
            
        dummy_hashcat_path = Path("hashcat")
        if not dummy_hashcat_path.exists():
            dummy_hashcat_path.mkdir(parents=True, exist_ok=True)
            (dummy_hashcat_path / "Makefile").write_text("all:\n\techo 'Building hashcat'", encoding='utf-8')
            # Füge eine Dummy-hashcat Binary hinzu, damit SHA256 berechnet werden kann
            (dummy_hashcat_path / "hashcat").write_text("#!/bin/bash\necho 'Simulating hashcat executable...'\nexit 0", encoding='utf-8')
            (dummy_hashcat_path / "hashcat").chmod(0o755)
            logging.info(f"Dummy hashcat environment created at {dummy_hashcat_path}")


        # Für TheHarvester und SET Test: Nichts Besonderes außer dem Klonen. pip install . reicht.
        await main()

    asyncio.run(prepare_and_run())