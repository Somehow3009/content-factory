"""Dashboard MVP §35: 5 màn hình tối giản (HTML, không cần đẹp)."""
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import AnalyticsSnapshot, Content, Job, Publish

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)):
    counts = {
        "candidates": db.scalar(select(func.count(Content.id))) or 0,
        "published": db.scalar(select(func.count(Publish.id)).where(Publish.status == "PUBLISHED")) or 0,
        "failed": db.scalar(select(func.count(Job.id)).where(Job.status == "DEAD_LETTER")) or 0,
        "queued": db.scalar(select(func.count(Job.id)).where(Job.status == "QUEUED")) or 0,
    }
    views = db.scalar(select(func.sum(AnalyticsSnapshot.views))) or 0
    return f"""<html><body><h1>Content Factory — Today</h1>
<ul><li>Candidates {counts['candidates']}</li><li>Published {counts['published']}</li>
<li>Failed {counts['failed']}</li><li>Queue {counts['queued']}</li><li>Views {views}</li></ul>
<p><a href='/api/v1/contents'>contents</a> <a href='/api/v1/publishes'>publishes</a>
<a href='/api/v1/analytics'>analytics</a></p></body></html>"""
