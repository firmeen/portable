from __future__ import annotations

import os
import re
from pathlib import Path

from ..config import SOFTWARE_ROOT
from ..core.environment import add_user_path, set_user_environment
from ..core.process import run, verify
from ..logging_utils import log


def software_path(name: str) -> Path:
    SOFTWARE_ROOT.mkdir(parents=True, exist_ok=True)
    return SOFTWARE_ROOT / name


def exists(relative: str) -> bool:
    return (SOFTWARE_ROOT / relative).exists()


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(number) for number in re.findall(r"\d+", value))


def npm_global_install(package: str, target: Path, command: str) -> str:
    from .javascript import ensure_node, npm_path

    ensure_node()
    target.mkdir(parents=True, exist_ok=True)
    npm = npm_path()
    log("NPM", f"Installing {package}")
    run(
        [
            str(npm),
            "install",
            "--global",
            "--prefix",
            str(target),
            "--no-audit",
            "--no-fund",
            package,
        ]
    )
    add_user_path(target)

    for executable in (target / f"{command}.cmd", target / f"{command}.exe"):
        if executable.exists():
            return verify([str(executable), "--version"])

    raise RuntimeError(f"{command} executable was not created")


def command_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if extra:
        env.update(extra)
    return env


__all__ = [
    "add_user_path",
    "command_env",
    "exists",
    "log",
    "npm_global_install",
    "run",
    "set_user_environment",
    "software_path",
    "verify",
    "version_tuple",
]
