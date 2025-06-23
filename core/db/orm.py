from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
from datetime import datetime
import json
import csv
from enum import Enum
import threading

# Optional: Enum für Source und Build-System
class SourceType(str, Enum):
    DEB = "deb"
    RPM = "rpm"
    PACMAN = "pacman"
    PYPI = "pypi"
    GITHUB = "github"
    LOCAL = "local"

class BuildSystem(str, Enum):
    MAKE = "make"
    CMAKE = "cmake"
    NINJA = "ninja"
    MESON = "meson"
    AUTOTOOLS = "autotools"
    SCONS = "scons"
    WAF = "waf"
    SETUPTOOLS = "setuptools"

@dataclass
class BasePackage:
    name: str
    version: str
    source: Union[str, SourceType]
    filepath: Optional[Path] = None
    build_system: Optional[Union[str, BuildSystem]] = None
    sha256: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Interner Lock für Thread-Safety (optional)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self):
        # Validierung und Typkonvertierung
        if not self.name or not isinstance(self.name, str):
            raise ValueError("Package name must be a non-empty string.")
        if not self.version or not isinstance(self.version, str):
            raise ValueError("Version must be a non-empty string.")
        # Enum-Konvertierung (optional)
        if isinstance(self.source, str):
            try:
                self.source = SourceType(self.source.lower())
            except ValueError:
                raise ValueError(f"Invalid source type '{self.source}'. Allowed: {[s.value for s in SourceType]}")
        elif not isinstance(self.source, SourceType):
            raise TypeError("source must be a string or SourceType Enum.")

        if self.filepath and not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

        if self.build_system:
            if isinstance(self.build_system, str):
                try:
                    self.build_system = BuildSystem(self.build_system.lower())
                except ValueError:
                    raise ValueError(f"Unsupported build system '{self.build_system}'. Allowed: {[b.value for b in BuildSystem]}")
            elif not isinstance(self.build_system, BuildSystem):
                raise TypeError("build_system must be a string or BuildSystem Enum.")

        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary.")

        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object.")

    # Metadaten-Methoden mit Lock für Thread-Safety
    def set_metadata(self, key: str, value: Any) -> None:
        if not isinstance(key, str):
            raise TypeError("Metadata key must be a string.")
        with self._lock:
            self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.metadata.get(key, default)

    # Hash-Berechnung mit einfachem Cache
    def calculate_sha256(self, force: bool = False) -> str:
        with self._lock:
            if self.sha256 is not None and not force:
                return self.sha256
            if not self.filepath or not self.filepath.is_file():
                raise FileNotFoundError("Filepath is not set or file does not exist.")
            import hashlib
            h = hashlib.sha256()
            with open(self.filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            self.sha256 = h.hexdigest()
            return self.sha256

    def to_json(self) -> str:
        def serializer(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, Enum):
                return obj.value
            raise TypeError(f"Type {type(obj)} not serializable")
        return json.dumps(asdict(self), default=serializer, indent=2, ensure_ascii=False)

    def to_csv_dict(self, meta_prefix="meta_") -> Dict[str, Any]:
        d = asdict(self)
        d['filepath'] = str(self.filepath) if self.filepath else ''
        d['timestamp'] = self.timestamp.isoformat()
        d['sha256'] = self.sha256 or ''
        # Enum-Werte als Strings
        if isinstance(d['source'], Enum):
            d['source'] = d['source'].value
        if isinstance(d['build_system'], Enum):
            d['build_system'] = d['build_system'].value if d['build_system'] else ''
        # Metadaten mit Präfix
        meta = d.pop("metadata", {})
        for k, v in meta.items():
            d[f"{meta_prefix}{k}"] = v
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
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=keys)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        except Exception as e:
            raise RuntimeError(f"Failed to export CSV: {e}")

    @staticmethod
    def export_to_json(packages: List["BasePackage"], filepath: Path) -> None:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([json.loads(p.to_json()) for p in packages], f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise RuntimeError(f"Failed to export JSON: {e}")

    # Build-Hook als Template-Methode / Strategy-Pattern Basis
    def build(self) -> None:
        if not self.build_system:
            raise RuntimeError("No build system defined.")
        # Beispiel: Dispatch an spezialisierte Methoden
        build_func = getattr(self, f"_build_{self.build_system.value}", None)
        if callable(build_func):
            build_func()
        else:
            # Default-Implementierung
            print(f"Building package {self.name} using generic build system '{self.build_system.value}'...")

    # Beispiel-Spezialmethoden für Build-Systeme (kann erweitert werden)
    def _build_make(self):
        print(f"Building {self.name} using Make...")

    def _build_cmake(self):
        print(f"Building {self.name} using CMake...")

    def __repr__(self) -> str:
        return f"<BasePackage {self.name} v{self.version} ({self.source.value if isinstance(self.source, Enum) else self.source})>"

