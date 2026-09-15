from __future__ import annotations

import logging

from .config import LOG_FILE, LOG_ROOT

LOGGER = logging.getLogger("portable-installer")
LOGGER.setLevel(logging.INFO)

if not LOGGER.handlers:
    try:
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        LOGGER.addHandler(handler)
    except Exception:
        pass


def log(tag: str, message: str) -> None:
    print(f"[{tag:<9}] {message}")
    LOGGER.info("%s | %s", tag, message)
