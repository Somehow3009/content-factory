"""Optimization §30: rule-based V1. Không ML."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.collector import engagement_rate
from app.database.models import Account, AnalyticsSnapshot, Publish


def run_rules(db: Session) -> list[str]:
    actions: list[str] = []
    snaps = db.scalars(select(AnalyticsSnapshot)).all()
    for s in snaps:
        er = engagement_rate(s.views, s.likes, s.comments, s.shares)
        if s.views > 50 and er < 0.01:
            actions.append(f"low_engagement:{s.publish_id}")
    # pause account nếu lỗi publish cao
    pubs = db.scalars(select(Publish)).all()
    errs = [p for p in pubs if p.status in ("RETRYABLE_ERROR", "PERMANENT_ERROR")]
    if pubs and len(errs) / max(len(pubs), 1) > 0.5:
        for a in db.scalars(select(Account)).all():
            if a.status == "ACTIVE":
                a.status = "PAUSED"
                actions.append(f"pause_account:{a.id}")
        db.commit()
    return actions
