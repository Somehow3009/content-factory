"""Dispatcher full: job_type -> handler thật (DB session riêng)."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Content, Job, Publish, Source


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


def dispatch(job_type: str, entity_id: str) -> None:
    db = SessionLocal()
    try:
        if job_type == "DISCOVER":
            import asyncio
            from app.discovery.collector import discover_source
            from app.jobs import queue as qq
            srcs = db.scalars(select(Source).where(Source.enabled == 1)).all()
            target = [s for s in srcs if (not entity_id or s.id == entity_id)] or srcs
            for s in target:
                asyncio.run(discover_source(db, s.id))
                # auto-score candidates mới
                for c in db.scalars(select(Content).where(Content.status == "DISCOVERED")).all():
                    qq.enqueue(db, "SCORE", "content", c.id, idempotency_key=f"score:{c.id}")
            return
        if job_type == "SCORE":
            from app.jobs.pipeline import score_and_select
            score_and_select(db, entity_id)
            return
        if job_type == "INGEST":
            import asyncio
            from app.ingestion.ingest import ingest_content
            from app.jobs import queue as qq
            asyncio.run(ingest_content(db, entity_id))
            c = db.scalar(select(Content).where(Content.id == entity_id))
            if c and c.status == "INGESTED":
                qq.enqueue(db, "PROCESS", "content", entity_id, idempotency_key=f"process:{entity_id}")
            return
        if job_type in ("PROCESS", "TRANSCRIBE", "WRITE_SCRIPT", "GENERATE_VOICE", "RENDER", "QC"):
            import os as _os
            from app.jobs import guards, pipeline
            from app.jobs import queue as _qq
            max_renders = int(_os.getenv("MAX_RENDER_JOBS_PER_DAY", "20"))
            if not guards.render_budget_ok(db, max_renders):
                cur = db.scalars(select(Job).where(
                    Job.job_type == job_type, Job.entity_id == entity_id,
                    Job.status == "PROCESSING")).first()
                if cur is not None:
                    _qq.defer(db, cur, hours=24)
                return
            pipeline.process_content(db, entity_id)
            return
            pipeline.process_content(db, entity_id)
            return
        if job_type == "PUBLISH":
            import asyncio
            from app.jobs import queue as qq
            from app.publishers.manager import run_publish
            # entity_id ở đây là variant_id (enqueue từ queue_publishes); tìm publish CREATED tương ứng
            pubs = db.scalars(select(Publish).where(Publish.variant_id == entity_id,
                                                    Publish.status == "CREATED")).all()
            for p in pubs:
                asyncio.run(run_publish(db, p.id))
                if p.status == "PUBLISHED":
                    qq.enqueue(db, "COLLECT_ANALYTICS", "publish", p.id,
                               idempotency_key=f"analytics:{p.id}:0")
            return
        if job_type == "CHECK_PUBLISH_STATUS":
            import asyncio
            from app.publishers import tiktok as _tk
            from app.security.encryption import decrypt_token
            from app.database.models import OAuthToken
            pubs = db.scalars(select(Publish).where(
                Publish.status == "REMOTE_PROCESSING")).all()
            for p in pubs:
                try:
                    from app.database.models import Account as _Acc
                    acc = db.scalar(select(_Acc).where(_Acc.id == p.account_id))
                    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == p.account_id)) if acc else None
                    if not tok or tok.access_token_encrypted.startswith("mock"):
                        continue
                    access = decrypt_token(tok.access_token_encrypted)
                    st = asyncio.run(_tk.check_status(access, p.publish_id))
                    if st in ("PUBLISHED", "SUCCESS", "SEND_TO_USER_INBOX"):
                        p.status = "PUBLISHED" if st != "SEND_TO_USER_INBOX" else "INBOX"
                    elif st in ("FAILED",):
                        p.status = "FAILED"
                    db.commit()
                except Exception:
                    db.rollback()
            return
        if job_type == "AUTO_PUBLISH":
            from app.jobs.pipeline import auto_queue_ready
            auto_queue_ready(db)
            return
        if job_type == "COLLECT_ANALYTICS":
            import asyncio
            from app.analytics.collector import collect_for_publish
            if entity_id:
                asyncio.run(collect_for_publish(db, entity_id))
            else:  # tick định kỳ: thu cho publishes mới nhất (tối đa 5)
                for p in db.scalars(select(Publish).where(
                        Publish.status.in_(["PUBLISHED", "INBOX"]))
                        .order_by(Publish.created_at.desc()).limit(5)).all():
                    try:
                        asyncio.run(collect_for_publish(db, p.id))
                    except Exception:
                        db.rollback()
            return
        if job_type == "OPTIMIZE":
            from app.analytics.optimizer import run_rules
            run_rules(db)
            return
        raise PermanentError(f"unknown job_type: {job_type}")
    except (RetryableError, PermanentError):
        raise
    except Exception as e:
        raise RetryableError(str(e)) from e
    finally:
        db.close()
