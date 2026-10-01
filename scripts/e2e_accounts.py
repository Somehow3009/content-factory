"""E2E step: pause account trùng + báo trạng thái queue."""
from __future__ import annotations

from sqlalchemy import func, select

from app.database.db import SessionLocal
from app.database.models import Account, Content, Job

db = SessionLocal()
accs = db.scalars(select(Account).where(Account.platform == "tiktok")).all()
for a in accs[1:]:
    a.status = "PAUSED"
db.commit()
print("accounts:", [(a.id[:8], a.username, a.status) for a in
                    db.scalars(select(Account)).all()])
print("jobs by status:", db.execute(
    select(Job.status, func.count(Job.id)).group_by(Job.status)).all())
print("contents:", db.scalar(select(func.count(Content.id))))
db.close()
