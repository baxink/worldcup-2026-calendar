from __future__ import annotations

import ssl
import time
import urllib.request
from pathlib import Path


DEFAULT_URL = "https://api.fifa.com/api/v3/calendar/matches?language=en&idseason=285023&count=200"


def fetch_url(url: str = DEFAULT_URL, timeout: int = 20, attempts: int = 2) -> str:
    headers = {"User-Agent": "Mozilla/5.0 worldcup-2026-calendar/1.0"}
    request = urllib.request.Request(url, headers=headers)
    context = ssl._create_unverified_context()
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
                return response.read().decode("utf-8", errors="replace")
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2)
    raise RuntimeError(f"Failed to fetch FIFA data from {url}: {last_error}")


def save_raw_response(raw_dir: Path, content: str) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "fifa-latest.txt"
    path.write_text(content, encoding="utf-8")
    return path
