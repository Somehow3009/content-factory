from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import MediaAsset

router = APIRouter()


@router.get("/videos")
def list_videos(db: Session = Depends(get_db)):
    rows = db.scalars(select(MediaAsset).where(
        MediaAsset.asset_type == "RENDERED_VIDEO").limit(50)).all()
    return [{"content_id": m.content_id, "storage_key": m.storage_key,
             "size_bytes": m.size_bytes} for m in rows]
