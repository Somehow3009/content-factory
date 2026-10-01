"""Worker loop giới hạn vòng + tự tạo ticks định kỳ (§32) để chạy standalone.

Dùng cho: test E2E, chạy tay, và GitHub Actions cron (không cần API process).
Usage: python scripts/drain.py [max_iters]
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.database.db import SessionLocal, init_db
from app.database.models import Job
from app.jobs import queue as q
from app.jobs.dispatcher import PermanentError, RetryableError, dispatch

# job_type -> chu kỳ phút. Drain tự enqueue nếu quá hạn chưa có job nào được tạo.
TICKS = {
    "DISCOVER": 30,
    "AUTO_PUBLISH": 60,
    "CHECK_PUBLISH_STATUS": 60,
    "COLLECT_ANALYTICS": 360,
    "OPTIMIZE": 1440,
}


def ensure_ticks(db) -> int:
    n = 0
    now = datetime.utcnow()
    for jtype, minutes in TICKS.items():
        pending = db.scalar(select(func.count(Job.id)).where(
            Job.job_type == jtype, Job.status == "QUEUED")) or 0
        if pending:
            continue
        last = db.scalar(select(func.max(Job.created_at)).where(Job.job_type == jtype))
        if last and now - last < timedelta(minutes=minutes):
            continue
        try:
            q.enqueue(db, jtype, "scheduler", "",
                      idempotency_key=f"tick:{jtype}:{now.strftime('%Y%m%d%H%M')}")
            n += 1
        except Exception:
            db.rollback()
    return n


def main(max_iters: int = 50) -> int:
    init_db()
    db0 = SessionLocal()
    try:
        n = q.recover_stuck(db0)
        if n:
            print(f"recovered {n} stuck jobs")
        t = ensure_ticks(db0)
        if t:
            print(f"scheduled {t} periodic ticks")
    finally:
        db0.close()
    done = 0
    for _ in range(max_iters):
        db = SessionLocal()
        try:
            job = q.claim(db)
            if not job:
                print("queue empty")
                return done
            jid, jtype, ent = job.id, job.job_type, job.entity_id
            try:
                dispatch(jtype, ent)
                q.complete(db, job)
                print(f"OK {jtype} {ent[:8]}")
                done += 1
            except PermanentError as e:
                q.fail(db, job, "Permanent", str(e), retryable=False)
                print(f"DEAD {jtype}: {e}")
            except RetryableError as e:
                q.fail(db, job, "Retryable", str(e)[:200], retryable=True)
                print(f"RETRY {jtype}: {str(e)[:200]}")
        finally:
            db.close()
        time.sleep(1)
    print(f"reached max_iters, done={done}")
    return done


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 50)
