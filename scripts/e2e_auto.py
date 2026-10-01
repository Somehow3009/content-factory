"""E2E step: enqueue AUTO_PUBLISH."""
from __future__ import annotations

from app.database.db import SessionLocal
from app.jobs import queue as q

db = SessionLocal()
job = q.enqueue(db, "AUTO_PUBLISH", "scheduler", "", idempotency_key="e2e-auto-1")
print("auto job:", job.id[:8], job.status)
db.close()
