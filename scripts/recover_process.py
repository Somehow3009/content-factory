"""Hồi sinh contents kẹt PROCESSING (job chết mà content không về trạng thái retry được).

Với mỗi content PROCESSING không còn PROCESS job live (QUEUED/PROCESSING):
  - xóa PROCESS jobs DEAD của nó
  - trả content về INGESTED
  - enqueue PROCESS mới
Chạy 1 lần sau khi fix nguyên nhân (vd thiếu ffmpeg).
Usage: python scripts/recover_process.py [--yes]
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Content, Job
from app.jobs import queue as q

LIVE = ("QUEUED", "PROCESSING")


def main(apply: bool = False, limit: int = 3) -> None:
    db = SessionLocal()
    stuck = db.scalars(select(Content).where(Content.status == "PROCESSING")
                       .order_by(Content.created_at.desc())).all()
    revived = 0
    skipped = 0
    for c in stuck:
        live = db.scalars(select(Job).where(
            Job.job_type == "PROCESS", Job.entity_id == c.id,
            Job.status.in_(LIVE))).first()
        if live:
            continue
        print("stuck:", c.id[:8], (c.title or "")[:40])
        if not apply:
            continue
        for j in db.scalars(select(Job).where(
                Job.job_type == "PROCESS", Job.entity_id == c.id)).all():
            db.delete(j)
        if revived < limit:
            c.status = "INGESTED"
            db.commit()
            q.enqueue(db, "PROCESS", "content", c.id,
                      idempotency_key=f"process:{c.id}")
            revived += 1
        else:  # tin cũ: cho qua để khỏi spam kênh bằng news hết hạn
            c.status = "SKIPPED"
            db.commit()
            skipped += 1
    if apply:
        print(f"revived: {revived}, skipped stale: {skipped}")
    else:
        print("dry-run. Thêm --yes để hồi sinh.")
    db.close()


if __name__ == "__main__":
    import os
    main("--yes" in sys.argv, int(os.getenv("RECOVER_LIMIT", "3")))
