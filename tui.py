from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime
import json
import csv
import hashlib

@dataclass
class BasePackage:
    name: str
    version: str
    source: str
    filepath: Optional[Union[Path, str]] = None
    build_system: Optional[str] = None
    sha256: Optional[str] = None
    sha1: Optional[str] = None
    md5: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    SUPPORTED_BUILD_SYSTEMS = {
        'make', 'cmake', 'ninja', 'meson', 'autotools', 'scons', 'waf', 'setuptools',
        'poetry', 'pip', 'distutils', 'bazel', 'qmake', 'gradle', 'maven', 'ant',
        'cargo', 'go', 'npm', 'yarn', 'pnpm', 'gulp', 'webpack', 'rollup', 'vite',
        'conan', 'vcpkg', 'dub', 'stack', 'cabal', 'swiftpm', 'dotnet', 'msbuild'
    }

    def __post_init__(self):
        # Normalize filepath to Path or None
        if self.filepath:
            if not isinstance(self.filepath, Path):
                self.filepath = Path(self.filepath)

        # Validate build_system
        if self.build_system:
            bs = self.build_system.lower()
            if bs not in self.SUPPORTED_BUILD_SYSTEMS:
                raise ValueError(f"Build system '{bs}' not supported.")
            self.build_system = bs

        # Validate metadata type
        if not isinstance(self.metadata, dict):
            raise TypeError("metadata must be a dict")

        # Validate timestamp
        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be a datetime object")

        # Validate basic string fields
        for attr in ['name', 'version', 'source']:
            val = getattr(self, attr)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{attr} must be a non-empty string")

    def set_metadata(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError("Metadata key must be a string")
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def calculate_hash(self, algorithm: str = "sha256") -> Optional[str]:
        if not self.filepath or not self.filepath.is_file():
            return None
        algo = algorithm.lower()
        if algo not in {"sha256", "sha1", "md5"}:
            raise ValueError("Supported hash algorithms: sha256, sha1, md5")
        h = hashlib.new(algo)
        with self.filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b''):
                h.update(chunk)
        return h.hexdigest()

    def calculate_all_hashes(self) -> None:
        self.sha256 = self.calculate_hash("sha256")
        self.sha1 = self.calculate_hash("sha1")
        self.md5 = self.calculate_hash("md5")

    def to_json(self) -> str:
        def serializer(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(asdict(self), default=serializer, indent=2, ensure_ascii=False)

    def to_csv_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['filepath'] = str(self.filepath) if self.filepath else ''
        d['timestamp'] = self.timestamp.isoformat()
        d['build_system'] = self.build_system or ''
        d['sha256'] = self.sha256 or ''
        d['sha1'] = self.sha1 or ''
        d['md5'] = self.md5 or ''
        # Flatten metadata keys with prefix to avoid collisions
        for k, v in self.metadata.items():
            d[f"meta_{k}"] = v
        d.pop('metadata', None)
        return d

    @staticmethod
    def export_to_csv(packages: List["BasePackage"], filepath: Path) -> None:
        if not packages:
            return
        keys = set()
        rows = [p.to_csv_dict() for p in packages]
        for row in rows:
            keys.update(row.keys())
        keys = sorted(keys)
        with filepath.open("w", newline='', encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    @staticmethod
    def export_to_json(packages: List["BasePackage"], filepath: Path) -> None:
        data = [json.loads(p.to_json()) for p in packages]
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def build(self) -> None:
        if not self.build_system:
            raise RuntimeError("No build system defined.")
        # TODO: Implement actual build logic here
        print(f"Building package {self.name} with build system {self.build_system}")

    def __repr__(self) -> str:
        return f"<BasePackage name={self.name} version={self.version} source={self.source}>"
