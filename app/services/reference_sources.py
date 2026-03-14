from __future__ import annotations

from pathlib import Path

from app.services.substack import normalize_source_url, source_name_from_url


DEFAULT_REFERENCE_SOURCES_FILE = "data/reference_sources.txt"


def load_reference_sources(path: str = DEFAULT_REFERENCE_SOURCES_FILE) -> list[str]:
    source_file = Path(path)
    if not source_file.exists():
        return []

    urls: list[str] = []
    for raw in source_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(normalize_source_url(line))

    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def reference_source_name(url: str) -> str:
    return source_name_from_url(url)
