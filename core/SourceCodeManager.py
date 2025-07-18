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
    PIP = "pip"
    GO = "go"
    CARGO = "cargo"

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
            logging.warning(f"Cannot calculate SHA256 for '{self.name}': filepath not set or file does not exist.")
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
        
        # Dispatch an spezialisierte, asynchrone Methoden oder an ein externes Build-System-Modul
        build_func_name = f"_build_{self.build_system.value.replace('-', '_')}" # make-like names python-friendly
        build_func = getattr(self, build_func_name, None)

        if build_func and asyncio.iscoroutinefunction(build_func):
            await build_func()
        else:
            logging.warning(f"No specific async build method found for {self.build_system.value}. Using generic build logic.")
            # Hier könnte die Schnittstelle zu Ihrem C++ Build-System oder externen Tools sein
            # asyncio.create_subprocess_exec ist ideal für externe Prozesse
            print(f"Executing generic build for {self.name}...")
            # Beispiel: await asyncio.sleep(2) # Simuliere Arbeit
            logging.info(f"Generic build for {self.name} completed.")


    # --- Beispiel-Spezialmethoden für Build-Systeme (asynchron) ---
    async def _build_make(self):
        logging.info(f"Starting async Make build for {self.name}...")
        # Hier würden Sie 'make' als Subprozess aufrufen
        try:
            proc = await asyncio.create_subprocess_exec(
                'make', '-C', str(self.filepath.parent), # Annahme: Makefile ist im Elternverzeichnis
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
        # Beispiel: cmake konfigurieren und bauen
        build_dir = self.filepath.parent / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        try:
            logging.debug(f"Running CMake configure in {build_dir} for {self.name}...")
            proc_config = await asyncio.create_subprocess_exec(
                'cmake', str(self.filepath.parent), '-B', str(build_dir),
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
    
    # Beispiel für ein lokales Paket
    local_pkg = BasePackage(
        name="my_local_app",
        version="1.0.0",
        source=SourceType.LOCAL,
        filepath=Path("path/to/my_local_app/source_code"), # Diesen Pfad anpassen!
        build_system=BuildSystem.CMAKE
    )
    
    # Beispiel für ein GitHub-Paket (ohne tatsächlichen Download hier)
    github_pkg = BasePackage(
        name="external_lib",
        version="2.1.0",
        source=SourceType.GITHUB,
        metadata={"repo_url": "https://github.com/someuser/externallib"},
        build_system=BuildSystem.MAKE
    )

    packages_to_manage = [local_pkg, github_pkg]

    # Hashes berechnen
    for pkg in packages_to_manage:
        if pkg.filepath and pkg.filepath.is_dir(): # Nur für existierende lokale Verzeichnisse
            await pkg.calculate_sha256() # Asynchron aufrufen
        
    # Paket Metadaten setzen (z.B. das "JPEG" für GitHub-Paket)
    github_pkg.set_metadata("pictogram_binary_rep", "base64encoded_jpeg_data_here")
    
    # Pakete bauen (asynchron)
    for pkg in packages_to_manage:
        try:
            # Für das Beispiel muss der filepath existieren und der Build-System-Befehl installiert sein.
            # Im realen System würden Sie hier vorher den Code klonen/herunterladen.
            if pkg.filepath and pkg.filepath.is_dir() and pkg.build_system:
                await pkg.build()
            else:
                logging.info(f"Skipping build for {pkg.name}: Filepath not valid or no build system specified.")
        except RuntimeError as e:
            logging.error(f"Build process failed for {pkg.name}: {e}")
        except FileNotFoundError as e:
             logging.error(f"Required build tool for {pkg.name} not found: {e}")


    # Pakete exportieren
    exported_packages = packages_to_manage
    try:
        await asyncio.to_thread(BasePackage.export_to_json, exported_packages, Path("packages_export.json"))
        await asyncio.to_thread(BasePackage.export_to_csv, exported_packages, Path("packages_export.csv"))
    except RuntimeError as e:
        logging.error(f"Error during export: {e}")

    logging.info("Alien Package Manager 2.0 operations completed.")


if __name__ == "__main__":
    # Erstellen Sie ein Dummy-Verzeichnis für den Test, wenn es nicht existiert
    # und simulieren Sie eine CMakeLists.txt für den Build-Test
    dummy_source_path = Path("path/to/my_local_app/source_code")
    if not dummy_source_path.exists():
        dummy_source_path.mkdir(parents=True, exist_ok=True)
        # Dummy CMakeLists.txt
        (dummy_source_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)\nproject(DummyProject)\nadd_executable(dummy_app main.cpp)")
        (dummy_source_path / "main.cpp").write_text("#include <iostream>\nint main() { std::cout << \"Hello from DummyApp!\" << std::endl; return 0; }")
        logging.info(f"Dummy source directory created at {dummy_source_path}")


    asyncio.run(main())
