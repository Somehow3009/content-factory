from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.jobs import queue as q

router = APIRouter()


class EnqueueReq(BaseModel):
    job_type: str
    entity_type: str = ""
    entity_id: str = ""
    priority: int = 0
    idempotency_key: str = ""


@router.post("/jobs")
def enqueue_job(req: EnqueueReq, db: Session = Depends(get_db)):
    job = q.enqueue(db, req.job_type, req.entity_type, req.entity_id, req.priority, req.idempotency_key)
    return {"id": job.id, "status": job.status}
