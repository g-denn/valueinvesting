from __future__ import annotations

import hashlib


def canonicalize(text: str) -> str:
    return " ".join(text.lower().split())


def fingerprint(text: str) -> str:
    return hashlib.sha256(canonicalize(text).encode("utf-8")).hexdigest()
