import json
import csv
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

class BasePackage:
    """
    Universelle Basis-Klasse für Pakete aller Systeme (deb, rpm, pacman, pypi, github, etc.)
    Unterstützt Metadaten, Source-Verzeichnis, Build-Infos, und flexible Getter/Setter.
    """

    SUPPORTED_BUILD_SYSTEMS = {
        'make', 'cmake', 'ninja', 'meson', 'autotools', 'scons', 'waf', 'setuptools',
        'poetry', 'pip', 'distutils', 'bazel', 'qmake', 'gradle', 'maven', 'ant',
        'cargo', 'go', 'npm', 'yarn', 'pnpm', 'gulp', 'webpack', 'rollup', 'vite',
        'conan', 'vcpkg', 'dub', 'stack', 'cabal', 'swiftpm', 'dotnet', 'msbuild'
    }

    def __init__(
        self,
        name: str,
        version: str,
        source: str,
        filepath: Optional[Path] = None,
        build_system: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialisiert ein neues Paket.
        """
        self._name: str = name
        self._version: str = version
        self._source: str = source  # z.B. 'deb', 'rpm', 'pypi', 'github', 'local'
        self._filepath: Optional[Path] = filepath if isinstance(filepath, Path) or filepath is None else Path(filepath)
        self._build_system: Optional[str] = build_system.lower() if build_system else None

        self._metadata: Dict[str, Any] = {}
        self._timestamp: datetime = timestamp if timestamp else datetime.utcnow()
        self._sha256: Optional[str] = None
        self._sha1: Optional[str] = None
        self._md5: Optional[str] = None

        if self._build_system and self._build_system not in self.SUPPORTED_BUILD_SYSTEMS:
            raise ValueError(f"Build-System '{self._build_system}' nicht unterstützt.")

    # Property Getter/Setter
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, val: str):
        self._name = val

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, val: str):
        self._version = val

    @property
    def source(self) -> str:
        return self._source

    @source.setter
    def source(self, val: str):
        self._source = val

    @property
    def filepath(self) -> Optional[Path]:
        return self._filepath

    @filepath.setter
    def filepath(self, val: Optional[Any]):
        if isinstance(val, Path) or val is None:
            self._filepath = val
        else:
            self._filepath = Path(val)

    @property
    def build_system(self) -> Optional[str]:
        return self._build_system

    @build_system.setter
    def build_system(self, val: Optional[str]):
        val = val.lower() if val else None
        if val and val not in self.SUPPORTED_BUILD_SYSTEMS:
            raise ValueError(f"Build-System '{val}' nicht unterstützt.")
        self._build_system = val

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, val: datetime):
        self._timestamp = val

    @property
    def sha256(self) -> Optional[str]:
        return self._sha256

    @sha256.setter
    def sha256(self, val: Optional[str]):
        self._sha256 = val

    @property
    def sha1(self) -> Optional[str]:
        return self._sha1

    @sha1.setter
    def sha1(self, val: Optional[str]):
        self._sha1 = val

    @property
    def md5(self) -> Optional[str]:
        return self._md5

    @md5.setter
    def md5(self, val: Optional[str]):
        self._md5 = val

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    def set_metadata(self, key: str, value: Any):
        self._metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self._metadata.get(key, default)

    def calculate_hash(self, algorithm: str = "sha256") -> Optional[str]:
        """
        Berechnet den Datei-Hash mit dem gewünschten Algorithmus.
        Unterstützt: 'sha256', 'sha1', 'md5'.
        """
        if self._filepath and self._filepath.is_file():
            algo = algorithm.lower()
            if algo not in {"sha256", "sha1", "md5"}:
                raise ValueError("Nur 'sha256', 'sha1' und 'md5' werden unterstützt.")
            h = getattr(hashlib, algo)()
            with open(self._filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    h.update(chunk)
            return h.hexdigest()
        return None

    def calculate_sha256(self):
        """Berechnet und speichert den SHA256-Hash der Datei."""
        self._sha256 = self.calculate_hash("sha256")

    def calculate_sha1(self):
        """Berechnet und speichert den SHA1-Hash der Datei."""
        self._sha1 = self.calculate_hash("sha1")

    def calculate_md5(self):
        """Berechnet und speichert den MD5-Hash der Datei."""
        self._md5 = self.calculate_hash("md5")

    def calculate_all_hashes(self):
        """Berechnet und speichert SHA256, SHA1 und MD5."""
        self.calculate_sha256()
        self.calculate_sha1()
        self.calculate_md5()

    def to_json(self) -> str:
        data = {
            "name": self._name,
            "version": self._version,
            "source": self._source,
            "filepath": str(self._filepath) if self._filepath else None,
            "build_system": self._build_system,
            "timestamp": self._timestamp.isoformat(),
            "sha256": self._sha256,
            "sha1": self._sha1,
            "md5": self._md5,
            "metadata": self._metadata
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def to_csv_dict(self) -> Dict[str, Any]:
        base = {
            "name": self._name,
            "version": self._version,
            "source": self._source,
            "filepath": str(self._filepath) if self._filepath else '',
            "build_system": self._build_system or '',
            "timestamp": self._timestamp.isoformat(),
            "sha256": self._sha256 or '',
            "sha1": self._sha1 or '',
            "md5": self._md5 or '',
        }
        meta = {f"meta_{k}": v for k, v in self._metadata.items()}
        base.update(meta)
        return base

    @staticmethod
    def export_to_csv(packages: List["BasePackage"], filepath: Path):
        if not packages:
            return
        keys = set()
        for p in packages:
            keys.update(p.to_csv_dict().keys())
        keys = sorted(keys)
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            for p in packages:
                writer.writerow(p.to_csv_dict())

    @staticmethod
    def export_to_json(packages: List["BasePackage"], filepath: Path):
        data = [json.loads(p.to_json()) for p in packages]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def build(self):
        if not self._build_system:
            raise RuntimeError("Kein Build-System definiert.")
        print(f"Baue Paket {self._name} mit Build-System {self._build_system}")

    def __repr__(self) -> str:
        return f"<BasePackage {self._name} v{self._version} ({self._source})>"
