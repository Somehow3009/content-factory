from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import Content

router = APIRouter()


@router.get("/contents")
def list_contents(db: Session = Depends(get_db)):
    rows = db.scalars(select(Content).limit(50)).all()
    return [{"id": c.id, "title": c.title, "status": c.status, "trend_score": c.trend_score} for c in rows]
