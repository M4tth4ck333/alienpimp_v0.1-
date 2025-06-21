from typing import Optional, List
from pathlib import Path
from logger import get_logger
from orm import PackageORM, PackageStorage
from datetime import datetime

class BasePackage(PackageORM):
    def __init__(self, name: str, version: str, source: str, filepath: Optional[Path] = None):
        super().__init__(name, version, source)
        self.logger = get_logger(f"Package:{self.name}")
        self.filepath = filepath
        self.timestamp = None
        self.sha256 = None
        if filepath:
            try:
                self.sha256 = self.compute_sha256(filepath)
                self.timestamp = datetime.utcnow().isoformat()
            except Exception as e:
                self.logger.error(f"Fehler beim Hashen von {filepath}: {e}")

    def compute_sha256(self, filepath: Path) -> str:
        import hashlib
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def build(self):
        self.logger.info(f"Baue Paket {self.name} Version {self.version}")

    def update(self):
        self.logger.info(f"Aktualisiere Paket {self.name}")

    def morph(self, target_format: str):
        self.logger.info(f"Transformiere {self.name} in {target_format}")

class AlienManager:
    def __init__(self, storage_csv="packages.csv", storage_json="packages.json"):
        self.logger = get_logger("AlienManager")
        self.packages = {}
        self.storage = PackageStorage(storage_csv, storage_json)
        self.load_packages()

    def add_package(self, pkg: BasePackage):
        self.packages[pkg.name] = pkg
        self.logger.info(f"Paket hinzugefügt: {pkg.name}")
        self.save_packages()

    def get_package(self, name: str) -> Optional[BasePackage]:
        return self.packages.get(name)

    def list_packages(self) -> List[str]:
        return list(self.packages.keys())

    def build_all(self):
        self.logger.info("Starte Build aller Pakete")
        for pkg in self.packages.values():
            pkg.build()

    def save_packages(self):
        pkgs = list(self.packages.values())
        self.storage.save_csv(pkgs)
        self.storage.save_json(pkgs)

    def load_packages(self):
        pkgs = self.storage.load_json()
        if not pkgs:
            pkgs = self.storage.load_csv()
        for pkg_orm in pkgs:
            pkg = BasePackage(pkg_orm.name, pkg_orm.version, pkg_orm.source)
            pkg.timestamp = getattr(pkg_orm, "timestamp", None)
            pkg.sha256 = getattr(pkg_orm, "sha256", None)
            self.packages[pkg.name] = pkg
        self.logger.info(f"{len(self.packages)} Pakete geladen")
