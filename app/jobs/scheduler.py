"""Scheduler §32: chỉ CREATE JOB (discover/15m queue/process/hourly publish/6h analytics/daily optimize)."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.database.db import SessionLocal
from app.jobs import queue as q

_sched: BackgroundScheduler | None = None


def _tick(job_type: str, entity: str = ""):
    db = SessionLocal()
    try:
        q.enqueue(db, job_type, "scheduler", entity,
                  idempotency_key=f"sched:{job_type}:{entity}")
    except Exception:
        db.rollback()
    finally:
        db.close()


def start() -> BackgroundScheduler:
    """Chạy nền trong API process. Idempotent: gọi 2 lần chỉ chạy 1 scheduler."""
    global _sched
    if _sched and _sched.running:
        return _sched
    s = BackgroundScheduler()
    s.add_job(lambda: _tick("DISCOVER"), "interval", minutes=30, id="discover")
    s.add_job(lambda: _tick("AUTO_PUBLISH"), "interval", minutes=60, id="auto_publish")
    s.add_job(lambda: _tick("COLLECT_ANALYTICS"), "interval", hours=6, id="analytics")
    s.add_job(lambda: _tick("OPTIMIZE"), "interval", hours=24, id="optimize")
    s.start()
    _sched = s
    return s
