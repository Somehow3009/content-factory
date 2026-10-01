"""E2E trim: chỉ giữ 1 content (mới nhất), còn lại SKIPPED + xóa jobs rác của chúng."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Content, Job

db = SessionLocal()
rows = db.scalars(select(Content).where(Content.status == "SELECTED")
                  .order_by(Content.created_at.desc())).all()
keep = rows[0] if rows else None
drop_ids = {c.id for c in rows[1:]}
for c in rows[1:]:
    c.status = "SKIPPED"
jobs = db.scalars(select(Job).where(Job.status == "QUEUED")).all()
n_del = 0
for j in jobs:
    if j.job_type in ("INGEST", "PROCESS", "PUBLISH") and j.entity_id in drop_ids:
        db.delete(j)
        n_del += 1
db.commit()
print("keep:", keep.id[:8] if keep else None)
print("skipped:", len(drop_ids), "deleted jobs:", n_del)
print("remaining queued:", [(j.job_type, j.entity_id[:8]) for j in
      db.scalars(select(Job).where(Job.status == "QUEUED")).all()][:10])
db.close()
