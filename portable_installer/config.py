from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import __version__

APP_NAME = "Portable Developer Environment"
APP_VERSION = __version__

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
SOFTWARE_ROOT = PROJECT_ROOT / "software"
CACHE_ROOT = PROJECT_ROOT / ".cache"
LOG_ROOT = PROJECT_ROOT / "logs"
BOOTSTRAP_ROOT = PROJECT_ROOT / ".bootstrap"
LOG_FILE = LOG_ROOT / "installer.log"

HTTP_TIMEOUT = 90
HTTP_RETRIES = 3
DOWNLOAD_CHUNK = 1024 * 1024


@dataclass(frozen=True)
class Paths:
    project: Path = PROJECT_ROOT
    software: Path = SOFTWARE_ROOT
    cache: Path = CACHE_ROOT
    logs: Path = LOG_ROOT
    bootstrap: Path = BOOTSTRAP_ROOT

    def ensure(self) -> None:
        self.software.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
