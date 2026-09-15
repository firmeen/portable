from __future__ import annotations

import json
import platform
import time
import urllib.request
from pathlib import Path

from ..config import APP_VERSION, DOWNLOAD_CHUNK, HTTP_RETRIES, HTTP_TIMEOUT
from ..logging_utils import log

try:
    import truststore  # type: ignore

    truststore.inject_into_ssl()
except Exception:
    pass

USER_AGENT = (
    f"firmeen-portable-installer/{APP_VERSION} "
    f"Python/{platform.python_version()} Windows/{platform.release()}"
)


def request_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if extra:
        headers.update(extra)
    return headers


def request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> bytes:
    last_error: Exception | None = None

    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers=request_headers(headers))
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                return response.read()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= HTTP_RETRIES:
                break
            time.sleep(min(attempt * 2, 5))

    raise RuntimeError(f"HTTP request failed: {url}: {last_error}")


def request_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> str:
    return request_bytes(url, headers=headers).decode("utf-8", errors="replace")


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
):
    return json.loads(request_text(url, headers=headers))


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = Path(str(destination) + ".part")
    partial.unlink(missing_ok=True)
    log("DOWNLOAD", url)
    last_error: Exception | None = None

    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            request = urllib.request.Request(url, headers=request_headers())
            with urllib.request.urlopen(
                request, timeout=HTTP_TIMEOUT
            ) as response, partial.open("wb") as output:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                last_draw = 0.0

                while True:
                    chunk = response.read(DOWNLOAD_CHUNK)
                    if not chunk:
                        break
                    output.write(chunk)
                    downloaded += len(chunk)
                    now = time.monotonic()
                    if now - last_draw < 0.15:
                        continue

                    if total:
                        percentage = downloaded / total * 100
                        print(
                            "\r           "
                            f"{downloaded / 1048576:8.1f} MB / "
                            f"{total / 1048576:8.1f} MB   {percentage:6.2f}%",
                            end="",
                            flush=True,
                        )
                    else:
                        print(
                            f"\r           {downloaded / 1048576:8.1f} MB",
                            end="",
                            flush=True,
                        )
                    last_draw = now
                print()

            partial.replace(destination)
            return destination
        except KeyboardInterrupt:
            partial.unlink(missing_ok=True)
            raise
        except Exception as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt >= HTTP_RETRIES:
                break
            log("RETRY", f"Attempt {attempt}/{HTTP_RETRIES} failed: {exc}")
            time.sleep(min(attempt * 2, 5))

    raise RuntimeError(f"Download failed: {url}: {last_error}")
