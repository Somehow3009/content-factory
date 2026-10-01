"""Xóa snapshots bịa + backfill stats YouTube thật."""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.analytics.collector import collect_for_publish
from app.database.db import SessionLocal
from app.database.models import AnalyticsSnapshot, Publish

db = SessionLocal()
fakes = db.scalars(select(AnalyticsSnapshot)).all()
print("xoa snapshots cu (bia):", len(fakes))
for s in fakes:
    db.delete(s)
db.commit()
for p in db.scalars(select(Publish).where(Publish.platform == "youtube")).all():
    snap = asyncio.run(collect_for_publish(db, p.id))
    if snap:
        print("that:", p.external_post_id, snap.views, "views", snap.likes, "likes")
    else:
        print("chua co so lieu:", p.external_post_id)
db.close()
