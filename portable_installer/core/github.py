from __future__ import annotations

import functools
import os
from typing import Callable

from .http import request_json


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@functools.lru_cache(maxsize=32)
def latest_release(repository: str) -> dict:
    return request_json(
        f"https://api.github.com/repos/{repository}/releases/latest",
        headers=_headers(),
    )


def asset(
    repository: str,
    matcher: Callable[[str], bool],
) -> tuple[str, str]:
    release = latest_release(repository)
    for item in release.get("assets", []):
        name = item.get("name", "")
        if matcher(name):
            return name, item["browser_download_url"]
    raise RuntimeError(f"No matching release asset for {repository}")


def best_asset(
    repository: str,
    scorer: Callable[[str], int],
) -> tuple[str, str]:
    candidates: list[tuple[int, str, str]] = []
    for item in latest_release(repository).get("assets", []):
        name = item.get("name", "")
        score = scorer(name)
        if score > 0:
            candidates.append((score, name, item["browser_download_url"]))

    if not candidates:
        raise RuntimeError(f"No suitable release asset for {repository}")

    candidates.sort(reverse=True)
    _, name, url = candidates[0]
    return name, url
