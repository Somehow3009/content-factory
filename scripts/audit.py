"""Audit dashboard: publishes/analytics/jobs-error thực tế."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import AnalyticsSnapshot, Job, Publish

db = SessionLocal()
for p in db.scalars(select(Publish)).all():
    print("PUB", p.platform, p.status, (p.publish_id or "")[:40],
          (p.external_post_id or "")[:20], (p.error_code or ""))
for s in db.scalars(select(AnalyticsSnapshot)).all():
    print("SNAP", s.publish_id[:8], s.views, s.likes, s.comments, s.shares,
          str(s.captured_at)[:16])
for j in db.scalars(select(Job).where(Job.status.in_(["QUEUED", "DEAD_LETTER"]))).all():
    print("JOB", j.job_type, j.status, j.attempts, (j.error_code or "")[:30],
          (j.error_message or "")[:200])
db.close()
