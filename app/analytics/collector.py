"""Analytics §28-29: snapshots append-only (T+1h/6h/24h/48h/7d) + metrics."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AnalyticsSnapshot, Publish


def engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    return (likes + comments + shares) / max(views, 1)


def performance_score(views: int, engagement: float, retention: float = 0.0) -> float:
    return views * 0.001 + engagement * 100 + retention * 50


async def collect_for_publish(db: Session, publish_id: str) -> AnalyticsSnapshot:
    pub = db.scalar(select(Publish).where(Publish.id == publish_id))
    if not pub:
        raise ValueError("publish not found")
    # MVP: mock metrics (prod: gọi TikTok/YouTube analytics API theo publish.publish_id).
    # Tăng dần theo số snapshot đã có để giả lập growth T+1h -> T+7d.
    n = len(db.scalars(select(AnalyticsSnapshot).where(
        AnalyticsSnapshot.publish_id == publish_id)).all())
    views = 100 * (n + 1)
    snap = AnalyticsSnapshot(publish_id=publish_id, views=views,
                             likes=int(views * 0.06), comments=int(views * 0.01),
                             shares=int(views * 0.005))
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap
