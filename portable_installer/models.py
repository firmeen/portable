from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Priority(Enum):
    CORE = "CORE"
    RECOMMENDED = "REC"
    OPTIONAL = "OPT"


@dataclass(frozen=True)
class Program:
    id: str
    name: str
    description: str
    ecosystem: str
    priority: Priority
    installer: Callable[[], str]
    installed: Callable[[], bool]
    dependencies: tuple[str, ...] = ()
    path_entries: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstallResult:
    id: str
    name: str
    success: bool
    status: str
    detail: str
    requested: bool
