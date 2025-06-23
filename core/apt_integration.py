import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("apt_integration")

# Logging konfigurieren (einmal beim Start)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def install_deb_package(deb_path: Path):
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

def build_src_tarball(src_dir: Path, output_tarball: Path):
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

def compile_c_source(source_file: Path, output_binary: Path, extra_flags=None):
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
