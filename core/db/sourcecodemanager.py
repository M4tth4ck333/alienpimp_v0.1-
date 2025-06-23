import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("sourcecode_manager")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

class SourceCodeManager:
    
    def install_deb_package(self, deb_path: Path) -> bool:
        if not deb_path.exists():
            logger.error(f"DEB-Paket nicht gefunden: {deb_path}")
            return False
        try:
            logger.info(f"Installiere DEB-Paket {deb_path}")
            result = subprocess.run(
                ["sudo", "dpkg", "-i", str(deb_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Installation abgeschlossen:\n{result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler bei Installation:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei Installation: {e}")
            return False
    
    def build_src_tarball(self, src_dir: Path, output_tarball: Path) -> bool:
        if not src_dir.exists() or not src_dir.is_dir():
            logger.error(f"Quellverzeichnis nicht gefunden: {src_dir}")
            return False
        try:
            logger.info(f"Erstelle Source-Tarball {output_tarball} aus {src_dir}")
            result = subprocess.run(
                ["tar", "-czf", str(output_tarball), "-C", str(src_dir.parent), src_dir.name],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Tarball erfolgreich erstellt:\n{result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler beim Erstellen des Tarballs:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Erstellen des Tarballs: {e}")
            return False
    
    def compile_c_source(self, source_file: Path, output_binary: Path, extra_flags=None) -> bool:
        if not source_file.exists():
            logger.error(f"C-Quellcode nicht gefunden: {source_file}")
            return False
        cmd = ["gcc", "-o", str(output_binary), str(source_file)]
        if extra_flags:
            cmd.extend(extra_flags)
        try:
            logger.info(f"Kompiliere {source_file} zu {output_binary}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Kompilierung erfolgreich:\n{result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Kompilierungsfehler:\n{e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei Kompilierung: {e}")
            return False
            
    def convert_package(
        self,
        src_pkg: Path,
        target_format: str,
        output_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Konvertiert ein Paket mittels `alien` von deb zu rpm oder umgekehrt.

        :param src_pkg: Pfad zur Quelldatei (.deb oder .rpm)
        :param target_format: Ziel-Format 'deb' oder 'rpm'
        :param output_dir: Optionales Ausgabe-Verzeichnis, default: Verzeichnis der Quelldatei
        :return: Pfad zur konvertierten Datei oder None bei Fehler
        """
        if not src_pkg.exists():
            logger.error(f"Quelldatei nicht gefunden: {src_pkg}")
            return None

        target_format = target_format.lower()
        if target_format not in {"deb", "rpm"}:
            logger.error(f"Ungültiges Ziel-Format: {target_format}")
            return None

        output_dir = output_dir or src_pkg.parent

        alien_target_flag = f"--to-{target_format}"

        cmd = ["alien", alien_target_flag, str(src_pkg), "--scripts", "-v", "-d", str(output_dir)]

        logger.info(f"Starte Paket-Konvertierung mit alien: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Alien Konvertierung erfolgreich:\n{result.stdout}")

            # Suche nach Dateien mit Ziel-Extension, die nach src_pkg erstellt wurden
            src_mtime = src_pkg.stat().st_mtime
            converted_files = [
                f for f in output_dir.glob(f"*.{target_format}")
                if f.stat().st_mtime >= src_mtime
            ]

            if not converted_files:
                logger.error("Keine konvertierte Datei gefunden.")
                return None

            # Neuste Datei wählen
            converted_file = max(converted_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Konvertierte Datei: {converted_file}")
            return converted_file

        except subprocess.CalledProcessError as e:
            logger.error(f"Alien Fehler:\n{e.stderr}")
            return None

        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei alien Konvertierung: {e}")
            return None
