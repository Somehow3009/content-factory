"""Stateless worker loop (spec section 23). Safe to kill anytime; state lives in DB."""

import time

import structlog

from app.database.db import SessionLocal, init_db
from app.jobs import queue as q
from app.jobs.dispatcher import dispatch

log = structlog.get_logger()


def main() -> None:
    init_db()
    log.info("worker.start")
    while True:
        db = SessionLocal()
        try:
            job = q.claim(db)
            if not job:
                db.close()
                time.sleep(5)
                continue
            job_id, job_type = job.id, job.job_type
            try:
                dispatch(job_type, job.entity_id)
                q.complete(db, job)
                log.info("job.completed", job_id=job_id, job_type=job_type)
            except Exception as exc:  # dispatcher raises RetryableError/PermanentError
                from app.jobs.dispatcher import PermanentError
                retryable = not isinstance(exc, PermanentError)
                q.fail(db, job, type(exc).__name__, str(exc), retryable=retryable)
                log.error("job.failed", job_id=job_id, error=str(exc))
            finally:
                db.close()
        except Exception as exc:
            log.error("worker.loop_error", error=str(exc))
            db.close()
            time.sleep(5)


if __name__ == "__main__":
    main()
