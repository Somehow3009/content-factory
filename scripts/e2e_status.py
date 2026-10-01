"""E2E status: content top-1 + variants + assets + publishes."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Content, ContentVariant, MediaAsset, Publish

KEEP = "0cf8465f"
db = SessionLocal()
c = db.scalar(select(Content).where(Content.id.like(KEEP + "%")))
print("content:", c.id[:8], c.status, "score:", round(c.trend_score or 0, 2))
for v in db.scalars(select(ContentVariant).where(ContentVariant.content_id == c.id)).all():
    print(" variant:", v.variant_code, v.status)
for m in db.scalars(select(MediaAsset).where(MediaAsset.content_id == c.id)).all():
    print(" asset:", m.asset_type, m.storage_key, m.size_bytes)
for p in db.scalars(select(Publish)).all():
    print(" publish:", p.platform, p.status, p.publish_id[:30] if p.publish_id else "")
db.close()
