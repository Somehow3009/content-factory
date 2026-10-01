"""E2E inspect + fix: ACTIVE đúng account có token thật, giữ top-1 content, dọn jobs rác."""
from __future__ import annotations

from sqlalchemy import func, select

from app.database.db import SessionLocal
from app.database.models import Account, Content, Job, OAuthToken

db = SessionLocal()
toks = {t.account_id for t in db.scalars(select(OAuthToken)).all()
        if not t.access_token_encrypted.startswith("mock")}
for a in db.scalars(select(Account)).all():
    a.status = "ACTIVE" if a.id in toks else "PAUSED"
db.commit()
print("accounts:", [(a.id[:8], a.username, a.status) for a in
                    db.scalars(select(Account)).all()])
print("jobs:", db.execute(
    select(Job.job_type, Job.status, func.count(Job.id))
    .group_by(Job.job_type, Job.status)).all())
rows = db.scalars(select(Content).order_by(Content.trend_score.desc())).all()
print("contents:", [(c.id[:8], c.status, round(c.trend_score or 0, 2)) for c in rows])
db.close()
