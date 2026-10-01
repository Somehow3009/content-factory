"""Chạy worker loop giới hạn vòng (dùng cho test E2E / chạy tay).
Usage: python scripts/drain.py [max_iters]
"""
from __future__ import annotations

import sys
import time

from app.database.db import SessionLocal, init_db
from app.jobs import queue as q
from app.jobs.dispatcher import PermanentError, RetryableError, dispatch


def main(max_iters: int = 50) -> int:
    init_db()
    db0 = SessionLocal()
    try:
        n = q.recover_stuck(db0)
        if n:
            print(f"recovered {n} stuck jobs")
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
