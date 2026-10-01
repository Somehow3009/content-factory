"""Render dashboard tĩnh từ DB -> dist/index.html (GitHub Pages).
Dark UI + cards + biểu đồ (Chart.js CDN). Không lộ secret: chỉ id rút gọn.
Usage: python scripts/site.py [out_dir]
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime

from sqlalchemy import func, select

from app.database.db import SessionLocal, init_db
from app.database.models import AnalyticsSnapshot, Content, Job, Publish


def esc(v) -> str:
    return html.escape(str(v if v is not None else ""))


STATUS_COLORS = {
    "READY": "#22c55e", "PUBLISHED": "#22c55e", "SELECTED": "#38bdf8",
    "INGESTED": "#38bdf8", "PROCESSING": "#f59e0b", "UPLOADING": "#f59e0b",
    "REMOTE_PROCESSING": "#f59e0b", "INBOX": "#a78bfa", "QUEUED": "#64748b",
    "FAILED": "#ef4444", "DEAD_LETTER": "#ef4444", "PERMANENT_ERROR": "#ef4444",
    "RETRYABLE_ERROR": "#f59e0b", "SKIPPED": "#475569", "DISCOVERED": "#475569",
    "COMPLETED": "#22c55e", "ACTIVE": "#22c55e", "PAUSED": "#f59e0b",
}


def badge(s: str) -> str:
    c = STATUS_COLORS.get(str(s), "#94a3b8")
    return (f"<span style='display:inline-block;padding:2px 10px;border-radius:999px;"
            f"font-size:12px;background:{c}22;color:{c};border:1px solid {c}55'>{esc(s)}</span>")


def card(label: str, value, accent: str = "#38bdf8") -> str:
    return (f"<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;"
            f"padding:16px 20px;min-width:140px;flex:1'><div style='color:#64748b;"
            f"font-size:13px'>{label}</div><div style='font-size:28px;font-weight:700;"
            f"color:{accent}'>{value}</div></div>")


def main(out_dir: str = "dist") -> None:
    import os
    init_db()
    db = SessionLocal()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    def cnt(model, *conds) -> int:
        q = select(func.count(model.id))
        for cnd in conds:
            q = q.where(cnd)
        return db.scalar(q) or 0

    s_ready = cnt(Content, Content.status == "READY")
    s_pub = cnt(Publish, Publish.status == "PUBLISHED")
    s_inbox = cnt(Publish, Publish.status == "INBOX")
    s_queue = cnt(Job, Job.status == "QUEUED")
    s_dead = cnt(Job, Job.status == "DEAD_LETTER")
    s_contents = cnt(Content)
    views = db.scalar(select(func.sum(AnalyticsSnapshot.views))) or 0

    funnel = [
        ("Discovered", cnt(Content, Content.status == "DISCOVERED")),
        ("Selected", cnt(Content, Content.status == "SELECTED")),
        ("Ready", s_ready),
        ("Inbox drafts", s_inbox),
        ("Published", s_pub),
    ]
    funnel_html = "".join(
        f"<div style='flex:1;text-align:center'><div style='font-size:24px;font-weight:700'>{v}</div>"
        f"<div style='color:#64748b;font-size:13px'>{k}</div></div>" + ("<div style='align-self:center;color:#334155'>→</div>" if i < len(funnel) - 1 else "")
        for i, (k, v) in enumerate(funnel))

    snaps = db.scalars(select(AnalyticsSnapshot).order_by(
        AnalyticsSnapshot.captured_at.asc()).limit(200)).all()
    by_day: dict[str, int] = {}
    for s in snaps:
        d = s.captured_at.strftime("%m-%d") if s.captured_at else "?"
        by_day[d] = max(by_day.get(d, 0), s.views or 0)
    chart_labels = list(by_day.keys())[-14:]
    chart_values = [by_day[k] for k in chart_labels]

    contents = db.scalars(select(Content).order_by(Content.created_at.desc()).limit(25)).all()
    pubs = db.scalars(select(Publish).order_by(Publish.created_at.desc()).limit(25)).all()
    jobs = db.scalars(select(Job).order_by(Job.created_at.desc()).limit(25)).all()

    def trow_contents(cs) -> str:
        return "".join(
            f"<tr><td style='font-family:monospace'>{esc(c.id[:8])}</td>"
            f"<td>{esc((c.title or '')[:60])}</td><td>{badge(c.status)}</td>"
            f"<td style='text-align:right'>{esc(round(c.trend_score or 0, 2))}</td></tr>" for c in cs)

    def trow_pubs(ps) -> str:
        return "".join(
            f"<tr><td style='font-family:monospace'>{esc(p.id[:8])}</td>"
            f"<td>{esc(p.platform)}</td><td>{badge(p.status)}</td>"
            f"<td style='font-family:monospace;font-size:12px'>{esc((p.publish_id or '')[:36])}</td></tr>" for p in ps)

    def trow_jobs(js) -> str:
        return "".join(
            f"<tr><td>{esc(j.job_type)}</td><td>{badge(j.status)}</td>"
            f"<td style='text-align:right'>{esc(j.attempts)}/{esc(j.max_attempts)}</td>"
            f"<td style='font-size:12px;color:#f59e0b'>{esc((j.error_code or '')[:30])}</td></tr>" for j in js)

    th = ("background:#0f172a;position:sticky;top:0;text-align:left;padding:10px 12px;"
          "color:#94a3b8;font-size:13px;font-weight:600")
    td = "padding:9px 12px;border-top:1px solid #1e293b;font-size:14px"
    table = ("width:100%;border-collapse:collapse;background:#020617;"
             "border:1px solid #1e293b;border-radius:12px;overflow:hidden")

    page = f"""<!DOCTYPE html><html lang=vi><head><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<meta http-equiv=refresh content='3600'><title>Content Factory 🏭</title>
<script src='https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'></script>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#020617;color:#e2e8f0;
font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-size:26px;margin:6px 0}}h2{{font-size:18px;margin:28px 0 12px;color:#cbd5e1}}
.sub{{color:#64748b;font-size:13px}}td{{{td}}}th{{{th}}}</style></head><body><div class=wrap>
<h1>🏭 Content Factory</h1><div class=sub>Cập nhật {now} · tự động mỗi giờ</div>
<h2>Tổng quan</h2>
<div style='display:flex;gap:12px;flex-wrap:wrap'>
{card("Contents", s_contents)}{card("Ready", s_ready, "#22c55e")}
{card("Published", s_pub, "#22c55e")}{card("Inbox drafts", s_inbox, "#a78bfa")}
{card("Views", f"{{:,}}".format(views), "#f59e0b")}{card("Queue", s_queue)}{card("Dead jobs", s_dead, "#ef4444" if s_dead else "#22c55e")}
</div>
<h2>Pipeline</h2>
<div style='display:flex;gap:6px;background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:18px 12px'>{funnel_html}</div>
<h2>Views theo ngày</h2>
<div style='background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:16px'><canvas id=v height=90></canvas></div>
<h2>Contents mới nhất</h2><table style='{table}'><tr><th>ID</th><th>Tiêu đề</th><th>Trạng thái</th><th>Score</th></tr>{trow_contents(contents)}</table>
<h2>Publishes mới nhất</h2><table style='{table}'><tr><th>ID</th><th>Nền tảng</th><th>Trạng thái</th><th>External ID</th></tr>{trow_pubs(pubs)}</table>
<h2>Jobs mới nhất</h2><table style='{table}'><tr><th>Loại</th><th>Trạng thái</th><th>Thử</th><th>Lỗi</th></tr>{trow_jobs(jobs)}</table>
<div class=sub style='margin-top:32px'>Content Factory MVP · worker GitHub Actions · DB Neon · Storage Supabase</div>
</div><script>try{{new Chart(document.getElementById('v'),{{type:'line',
data:{{labels:{json.dumps(chart_labels)},datasets:[{{label:'views',data:{json.dumps(chart_values)},
borderColor:'#38bdf8',backgroundColor:'#38bdf822',fill:true,tension:.3}}]}},
options:{{plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true}}}}}})}}catch(e){{}}</script>
</body></html>"""
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8").write(page)
    print("wrote", os.path.join(out_dir, "index.html"))
    db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "dist")
