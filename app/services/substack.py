from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def normalize_source_url(url: str) -> str:
    clean = url.strip()
    if not clean:
        return clean
    if not clean.startswith(("http://", "https://")):
        clean = f"https://{clean}"
    return clean.rstrip("/") + "/"


def source_to_rss_url(url: str) -> str:
    base = normalize_source_url(url)
    parsed = urlparse(base)

    # Handle substack profile URLs like https://substack.com/@handle
    if parsed.netloc in {"substack.com", "www.substack.com"} and parsed.path.startswith("/@"):
        handle = parsed.path.replace("/@", "").strip("/")
        return f"https://{handle}.substack.com/feed"

    return f"{base}feed"


def source_name_from_url(url: str) -> str:
    parsed = urlparse(normalize_source_url(url))
    host = parsed.netloc.replace("www.", "")
    if host == "substack.com" and parsed.path.startswith("/@"):
        return parsed.path.replace("/@", "").strip("/")
    return host.split(".")[0]


def load_default_substack_sources(path: str = "data/substack_sources.txt") -> list[str]:
    source_file = Path(path)
    if not source_file.exists():
        return []

    entries: list[str] = []
    for raw in source_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(normalize_source_url(line))

    # preserve order while deduplicating
    seen: set[str] = set()
    uniq: list[str] = []
    for src in entries:
        if src in seen:
            continue
        seen.add(src)
        uniq.append(src)
    return uniq
