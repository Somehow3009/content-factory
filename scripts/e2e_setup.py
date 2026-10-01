"""Setup E2E: tạo RSS source + enqueue DISCOVER. Chạy 1 lần."""
from __future__ import annotations

import json

from app.database.db import SessionLocal, init_db
from app.database.models import Account, Source
from app.jobs import queue as q

FEED = "https://vnexpress.net/rss/so-hoa.rss"


def main() -> None:
    init_db()
    db = SessionLocal()
    src = db.query(Source).filter(Source.name == "vnexpress-so-hoa").first()
    if not src:
        src = Source(name="vnexpress-so-hoa", adapter="rss",
                     config=json.dumps({"feed_url": FEED}))
        db.add(src)
        db.commit()
        db.refresh(src)
    print("source:", src.id)
    job = q.enqueue(db, "DISCOVER", "source", src.id, idempotency_key="e2e-discover-1")
    print("job:", job.id, job.job_type, job.status)
    accs = db.query(Account).filter(Account.platform == "tiktok",
                                    Account.status == "ACTIVE").all()
    print("tiktok accounts:", [(a.id[:8], a.username) for a in accs])
    db.close()


if __name__ == "__main__":
    main()
