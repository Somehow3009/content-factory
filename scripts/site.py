"""Render dashboard tĩnh từ DB -> dist/index.html (đẩy lên GitHub Pages).
Không secret nào lộ: chỉ thống kê + id rút gọn, không token.
Usage: python scripts/site.py [out_dir]
"""
from __future__ import annotations

import html
import sys
from datetime import datetime

from sqlalchemy import func, select

from app.database.db import SessionLocal, init_db
from app.database.models import AnalyticsSnapshot, Content, Job, Publish


def _row(*cells: str) -> str:
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def main(out_dir: str = "dist") -> None:
    import os
    init_db()
    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    n_content = db.scalar(select(func.count(Content.id))) or 0
    n_pub = db.scalar(select(func.count(Publish.id)).where(Publish.status == "PUBLISHED")) or 0
    n_inbox = db.scalar(select(func.count(Publish.id)).where(Publish.status == "INBOX")) or 0
    n_fail = db.scalar(select(func.count(Job.id)).where(Job.status == "DEAD_LETTER")) or 0
    n_queue = db.scalar(select(func.count(Job.id)).where(Job.status == "QUEUED")) or 0
    views = db.scalar(select(func.sum(AnalyticsSnapshot.views))) or 0

    contents = db.scalars(select(Content).order_by(Content.created_at.desc()).limit(30)).all()
    pubs = db.scalars(select(Publish).order_by(Publish.created_at.desc()).limit(30)).all()
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(30)).all()

    def esc(v) -> str:
        return html.escape(str(v if v is not None else ""))

    body = f"""<h1>Content Factory — Dashboard</h1><p>Updated {now} (auto hourly)</p>
<h2>Today</h2><ul>
<li>Candidates/Contents: {n_content}</li><li>Published: {n_pub}</li>
<li>Inbox drafts: {n_inbox}</li><li>Failed jobs: {n_fail}</li>
<li>Queued: {n_queue}</li><li>Total views: {views}</li></ul>
<h2>Contents</h2><table border=1><tr><th>ID</th><th>Title</th><th>Status</th><th>Score</th></tr>
{"".join(_row(esc(c.id[:8]), esc((c.title or "")[:60]), esc(c.status), esc(round(c.trend_score or 0, 2))) for c in contents)}
</table><h2>Publishes</h2><table border=1><tr><th>ID</th><th>Platform</th><th>Status</th><th>External</th></tr>
{"".join(_row(esc(p.id[:8]), esc(p.platform), esc(p.status), esc((p.publish_id or "")[:40])) for p in pubs)}
</table><h2>Jobs</h2><table border=1><tr><th>Type</th><th>Status</th><th>Attempts</th><th>Error</th></tr>
{"".join(_row(esc(j.job_type), esc(j.status), esc(j.attempts), esc((j.error_code or "")[:40])) for j in jobs)}
</table>"""
    page = ("<html><head><meta charset=utf-8><meta name=viewport content='width=device-width'>"
            "<meta http-equiv=refresh content='3600'><title>Content Factory</title></head>"
            f"<body>{body}</body></html>")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(page)
    print("wrote", os.path.join(out_dir, "index.html"))
    db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
