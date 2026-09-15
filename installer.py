#!/usr/bin/env python3
"""Stable entry point for the Portable Developer Environment."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from portable_installer.app import main
except ModuleNotFoundError as exc:
    if exc.name != "portable_installer":
        raise

    print()
    print("Portable Developer Environment cannot start.")
    print()
    print('The required folder "portable_installer" is missing.')
    print("Keep installer.py, Install.cmd, and portable_installer/ together")
    print("from the same complete repository checkout or ZIP download.")
    print()
    print("If you are testing PR #1, run:")
    print("  git fetch origin")
    print("  git switch feat/modular-installer-v4")
    print("  git pull origin feat/modular-installer-v4")
    print()
    raise SystemExit(2) from None


if __name__ == "__main__":
    raise SystemExit(main())
