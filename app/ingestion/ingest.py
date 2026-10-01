"""Ingestion: download media_url -> storage /content/{id}/source/original -> media_assets."""
from __future__ import annotations

import hashlib

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Content, MediaAsset
from app.ingestion.fingerprint import fingerprint_bytes
from app.media.storage import put_bytes


async def ingest_content(db: Session, content_id: str) -> str:
    c = db.scalar(select(Content).where(Content.id == content_id))
    if not c:
        raise ValueError("content not found")
    c.status = "INGESTING"
    db.commit()

    data = b""
    if c.source_url:
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as cli:
                r = await cli.get(c.source_url)
                if r.status_code == 200 and len(r.content) > 1024:
                    data = r.content
        except Exception:
            data = b""
    if not data:  # RSS text-only hoặc download fail -> placeholder để pipeline vẫn chạy MVP
        data = f"placeholder:{c.id}:{c.title}".encode()

    digest = fingerprint_bytes(data)
    # duplicate check
    dup = db.scalar(select(Content).where(Content.content_hash == digest, Content.id != c.id))
    if dup:
        c.status = "BLOCKED"
        db.commit()
        return c.status

    key = f"content/{c.id}/source/original.bin"
    put_bytes(key, data, content_type="application/octet-stream")
    c.content_hash = digest
    db.add(MediaAsset(content_id=c.id, asset_type="SOURCE_VIDEO", storage_key=key,
                       mime_type="application/octet-stream", size_bytes=len(data), sha256=digest))
    c.status = "INGESTED"
    db.commit()
    return c.status
