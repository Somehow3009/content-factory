from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import AnalyticsSnapshot

router = APIRouter()


@router.get("/analytics")
def list_analytics(db: Session = Depends(get_db)):
    rows = db.scalars(select(AnalyticsSnapshot).limit(100)).all()
    return [{"publish_id": s.publish_id, "views": s.views, "likes": s.likes,
             "comments": s.comments, "shares": s.shares,
             "captured_at": s.captured_at.isoformat()} for s in rows]
