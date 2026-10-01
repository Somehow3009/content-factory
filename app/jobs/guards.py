"""Budget guard §45 + retention §47: giới hạn job/ngày, xóa intermediate cũ."""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Job


def render_budget_ok(db: Session, max_per_day: int = 20) -> bool:
    today = datetime.utcnow().date()
    n = db.scalar(select(func.count(Job.id)).where(
        Job.job_type.in_(["RENDER", "PROCESS"]), Job.status == "COMPLETED",
        func.date(Job.created_at) == today)) or 0
    return n < max_per_day


def cleanup_local_storage(root: str = "./.storage", intermediate_days: int = 3,
                          rendered_days: int = 30) -> int:
    removed = 0
    now = time.time()
    for base, days in (("transcript", 99), ("voice", intermediate_days),
                       ("subtitle", intermediate_days), ("render", rendered_days),
                       ("source", 7)):
        pass
    # MVP: xóa file render/source quá hạn theo mtime
    import pathlib
    for p in pathlib.Path(root).rglob("*"):
        if not p.is_file():
            continue
        age_days = (now - p.stat().st_mtime) / 86400
        limit = rendered_days if "/render/" in p.as_posix() else (7 if "/source/" in p.as_posix() else intermediate_days)
        if age_days > limit and p.suffix in (".mp4", ".wav", ".bin"):
            try:
                p.unlink()
                removed += 1
            except Exception:
                pass
    return removed
