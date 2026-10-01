"""Xóa jobs PROCESSING kẹt (DISCOVER/SCORE chạy lại sẽ đẻ việc mới, không cần cho E2E)."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Job

db = SessionLocal()
rows = db.scalars(select(Job).where(Job.status == "PROCESSING")).all()
for j in rows:
    print("purge:", j.job_type, j.status)
    db.delete(j)
db.commit()
db.close()
