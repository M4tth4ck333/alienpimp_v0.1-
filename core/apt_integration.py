import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("apt_integration")

def install_deb_package(deb_path: Path):
    if not deb_path.exists():
        logger.error(f"DEB-Paket nicht gefunden: {deb_path}")
        return False
    try:
        logger.info(f"Installiere DEB-Paket {deb_path}")
        subprocess.run(["sudo", "dpkg", "-i", str(deb_path)], check=True)
        logger.info("Installation abgeschlossen")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler bei Installation: {e}")
        return False

def build_src_tarball(src_dir: Path, output_tarball: Path):
    if not src_dir.exists() or not src_dir.is_dir():
        logger.error(f"Quellverzeichnis nicht gefunden: {src_dir}")
        return False
    try:
        logger.info(f"Erstelle Source-Tarball {output_tarball} aus {src_dir}")
        subprocess.run(["tar", "-czf", str(output_tarball), "-C", str(src_dir.parent), src_dir.name], check=True)
        logger.info("Tarball erfolgreich erstellt")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Erstellen des Tarballs: {e}")
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
        subprocess.run(cmd, check=True)
        logger.info("Kompilierung erfolgreich")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Kompilierungsfehler: {e}")
        return False
