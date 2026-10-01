"""Discovery collector: chạy adapter -> lưu Content DISCOVERED (dedupe theo source+external)."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Content, Source
from app.discovery.adapters.rss import RSSAdapter
from app.discovery.base import SourceConfig

_ADAPTERS = {"rss": RSSAdapter}


def get_adapter(name: str):
    cls = _ADAPTERS.get(name)
    if not cls:
        raise ValueError(f"unknown adapter: {name}")
    return cls()


async def discover_source(db: Session, source_id: str) -> int:
    src = db.scalar(select(Source).where(Source.id == source_id))
    if not src or not src.enabled:
        return 0
    cfg = SourceConfig(source_id=src.id, adapter=src.adapter,
                       config=json.loads(src.config or "{}"))
    adapter = get_adapter(src.adapter)
    candidates = await adapter.discover(cfg)
    n = 0
    for c in candidates:
        exists = db.scalar(select(Content).where(
            Content.source_id == src.id, Content.external_id == c.external_id))
        if exists:
            continue
        db.add(Content(source_id=src.id, external_id=c.external_id,
                       source_url=c.source_url, title=c.title or "",
                       description=c.description or "", language=c.language or "unknown",
                       status="DISCOVERED"))
        n += 1
    db.commit()
    return n
