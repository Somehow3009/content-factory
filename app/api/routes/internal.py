"""Internal worker API §36: claim/complete/fail, auth bằng worker token."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_worker
from app.database.db import get_db
from app.database.models import Job
from app.jobs import queue as q

router = APIRouter()


@router.post("/internal/jobs/claim")
def claim_job(db: Session = Depends(get_db), _: None = Depends(require_worker)):
    job = q.claim(db)
    return {"job": {"id": job.id, "job_type": job.job_type, "entity_id": job.entity_id} if job else None}


class FailReq(BaseModel):
    error_code: str = ""
    error_message: str = ""
    retryable: bool = True


@router.post("/internal/jobs/{job_id}/complete")
def complete_job(job_id: str, db: Session = Depends(get_db), _: None = Depends(require_worker)):
    job = db.scalar(select(Job).where(Job.id == job_id))
    q.complete(db, job)
    return {"ok": True}


@router.post("/internal/jobs/{job_id}/fail")
def fail_job(job_id: str, req: FailReq, db: Session = Depends(get_db), _: None = Depends(require_worker)):
    job = db.scalar(select(Job).where(Job.id == job_id))
    q.fail(db, job, req.error_code, req.error_message, req.retryable)
    return {"ok": True}
