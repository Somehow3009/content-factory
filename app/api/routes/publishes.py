from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import Publish

router = APIRouter()


@router.get("/publishes")
def list_publishes(db: Session = Depends(get_db)):
    return [{"id": p.id, "platform": p.platform, "status": p.status,
             "publish_id": p.publish_id} for p in db.scalars(select(Publish).limit(50)).all()]


class PublishReq(BaseModel):
    content_id: str
    account_ids: list[str]
    platform: str = "tiktok"


@router.post("/publishes/queue")
def queue_publish(req: PublishReq, db: Session = Depends(get_db)):
    from app.jobs.pipeline import queue_publishes
    n = queue_publishes(db, req.content_id, req.account_ids, req.platform)
    return {"queued": n}
