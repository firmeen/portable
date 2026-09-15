from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..logging_utils import LOGGER


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not args:
        raise ValueError("Command cannot be empty")

    launch = list(args)
    executable = Path(launch[0])

    if executable.suffix.lower() in {".cmd", ".bat"}:
        launch = [
            os.environ.get("COMSPEC", "cmd.exe"),
            "/d",
            "/s",
            "/c",
            subprocess.list2cmdline(args),
        ]

    LOGGER.info("RUN | %s", subprocess.list2cmdline(args))

    return subprocess.run(
        launch,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=capture,
        check=True,
        shell=False,
    )


def verify(args: list[str], *, env: dict[str, str] | None = None) -> str:
    result = run(args, capture=True, env=env)
    output = (result.stdout or result.stderr or "OK").strip()
    return output.splitlines()[0] if output else "OK"
