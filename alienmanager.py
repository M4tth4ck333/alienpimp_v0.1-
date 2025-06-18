# orm.py
import csv
import json
from typing import List, Dict, Optional
from pathlib import Path
import hashlib
from datetime import datetime

class PackageORM:
    def __init__(self, name: str, version: str, source: str, timestamp: Optional[str] = None, sha256: Optional[str] = None):
        self.name = name
        self.version = version
        self.source = source
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.sha256 = sha256 or ""

    def compute_sha256(self, filepath: Path):
        if not filepath.exists() or not filepath.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")
        hasher = hashlib.sha256()
        with filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        self.sha256 = hasher.hexdigest()

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "timestamp": self.timestamp,
            "sha256": self.sha256
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]):
        return cls(
            name=data.get("name", ""),
            version=data.get("version", ""),
            source=data.get("source", ""),
            timestamp=data.get("timestamp", ""),
            sha256=data.get("sha256", "")
        )

class PackageStorage:
    def __init__(self, filepath_csv: str, filepath_json: str):
        self.filepath_csv = Path(filepath_csv)
        self.filepath_json = Path(filepath_json)

    def save_csv(self, packages: List[PackageORM]):
        with self.filepath_csv.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["name", "version", "source", "timestamp", "sha256"])
            writer.writeheader()
            for pkg in packages:
                writer.writerow(pkg.to_dict())

    def load_csv(self) -> List[PackageORM]:
        if not self.filepath_csv.exists():
            return []
        with self.filepath_csv.open("r", newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            return [PackageORM.from_dict(row) for row in reader]

    def save_json(self, packages: List[PackageORM]):
        with self.filepath_json.open("w", encoding="utf-8") as jsonfile:
            json.dump([pkg.to_dict() for pkg in packages], jsonfile, indent=4)

    def load_json(self) -> List[PackageORM]:
        if not self.filepath_json.exists():
            return []
        with self.filepath_json.open("r", encoding="utf-8") as jsonfile:
            data = json.load(jsonfile)
            return [PackageORM.from_dict(d) for d in data]
