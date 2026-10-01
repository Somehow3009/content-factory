"""DB-backed FIFO queue with lease + idempotency (spec section 21-22). No Redis needed for MVP."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Job

RETRY_DELAYS_MIN = [1, 5, 15, 60]  # attempt -> delay; >=5 -> dead-letter


def enqueue(db: Session, job_type: str, entity_type: str = "", entity_id: str = "",
            priority: int = 0, idempotency_key: str = "", max_attempts: int = 5) -> Job:
    if idempotency_key:
        existing = db.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
        if existing:
            return existing
    job = Job(job_type=job_type, entity_type=entity_type, entity_id=entity_id,
              priority=priority, idempotency_key=idempotency_key or f"{job_type}:{entity_type}:{entity_id}:{datetime.utcnow().isoformat()}",
              max_attempts=max_attempts, status="QUEUED")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def recover_stuck(db: Session, lease_seconds: int = 300) -> int:
    """Worker chết giữa job (§49): PROCESSING quá lease -> QUEUED lại."""
    from datetime import datetime
    now = datetime.utcnow()
    rows = db.scalars(select(Job).where(
        Job.status == "PROCESSING",
        Job.locked_until.is_not(None),
        Job.locked_until < now)).all()
    for j in rows:
        j.status = "QUEUED"
        j.locked_until = None
    db.commit()
    return len(rows)


def claim(db: Session, worker_id: str = "worker-1", lease_seconds: int = 300) -> Job | None:
    now = datetime.utcnow()
    job = db.scalar(
        select(Job)
        .where(Job.status == "QUEUED")
        .where((Job.locked_until.is_(None)) | (Job.locked_until < now))
        .where(Job.scheduled_at <= now)
        .order_by(Job.priority.desc(), Job.created_at.asc())
        .limit(1)
    )
    if not job:
        return None
    job.status = "PROCESSING"
    job.locked_until = now + timedelta(seconds=lease_seconds)
    job.attempts += 1
    db.commit()
    db.refresh(job)
    return job


def complete(db: Session, job: Job) -> None:
    job.status = "COMPLETED"
    job.locked_until = None
    job.error_code = ""
    job.error_message = ""
    db.commit()


def defer(db: Session, job: Job, hours: int = 24) -> None:
    """Hoãn job (vd hết budget ngày) mà không tốn attempts (§45)."""
    from datetime import datetime, timedelta
    job.status = "QUEUED"
    job.locked_until = None
    job.scheduled_at = datetime.utcnow() + timedelta(hours=hours)
    db.commit()


def fail(db: Session, job: Job, error_code: str, error_message: str, retryable: bool = True) -> None:
    if retryable and job.attempts < job.max_attempts:
        delay = RETRY_DELAYS_MIN[min(job.attempts - 1, len(RETRY_DELAYS_MIN) - 1)]
        job.status = "QUEUED"
        job.scheduled_at = datetime.utcnow() + timedelta(minutes=delay)
        job.locked_until = None
    else:
        job.status = "DEAD_LETTER"
        job.locked_until = None
    job.error_code = error_code
    job.error_message = error_message
    db.commit()
