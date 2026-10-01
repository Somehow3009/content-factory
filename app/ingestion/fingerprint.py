"""Fingerprint: sha256 để dedupe content (§7 content_hash, §15 duplicate check)."""
from __future__ import annotations

import hashlib


def fingerprint_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint_text(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
    return h.hexdigest()
