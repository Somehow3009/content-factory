"""Dọn rác Neon: contents bỏ (SKIPPED/DISCOVERED/SCORING/BLOCKED) + cascade,
publishes FAILED, jobs DEAD/QUEUED-tồn. Giữ: READY/SELECTED/INGESTED/PROCESSING,
PUBLISHED/INBOX/REMOTE_PROCESSING, accounts, tokens, sources.
Chạy: python scripts/clean.py [--yes]
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import (AnalyticsSnapshot, Content, ContentVariant, Job,
                                 MediaAsset, Publish, Script)

JUNK_CONTENT = {"SKIPPED", "DISCOVERED", "SCORING", "BLOCKED"}


def main(apply: bool = False) -> None:
    db = SessionLocal()
    junk = db.scalars(select(Content).where(Content.status.in_(JUNK_CONTENT))).all()
    jids = [c.id for c in junk]
    n_var = n_pub = n_snap = n_script = n_asset = 0
    if jids:
        vars_ = db.scalars(select(ContentVariant).where(ContentVariant.content_id.in_(jids))).all()
        vids = [v.id for v in vars_]
        n_var = len(vids)
        if vids:
            pubs = db.scalars(select(Publish).where(Publish.variant_id.in_(vids))).all()
            pids = [p.id for p in pubs]
            n_pub = len(pids)
            if pids:
                snaps = db.scalars(select(AnalyticsSnapshot).where(
                    AnalyticsSnapshot.publish_id.in_(pids))).all()
                n_snap = len(snaps)
                if apply:
                    for s in snaps:
                        db.delete(s)
            if apply:
                for p in pubs:
                    db.delete(p)
            for v in vars_:
                if apply:
                    db.delete(v)
        scripts = db.scalars(select(Script).where(Script.content_id.in_(jids))).all()
        n_script = len(scripts)
        assets = db.scalars(select(MediaAsset).where(MediaAsset.content_id.in_(jids))).all()
        n_asset = len(assets)
        if apply:
            for s in scripts:
                db.delete(s)
            for m in assets:
                db.delete(m)
            for c in junk:
                db.delete(c)
    failed_pubs = db.scalars(select(Publish).where(Publish.status == "FAILED")).all()
    dead_jobs = db.scalars(select(Job).where(Job.status == "DEAD_LETTER")).all()
    stale = db.scalars(select(Job).where(
        Job.status == "QUEUED",
        Job.job_type.in_(["SCORE", "INGEST", "PROCESS", "PUBLISH", "DISCOVER"]))).all()
    print(f"junk contents: {len(jids)} (variants {n_var}, publishes {n_pub}, "
          f"snapshots {n_snap}, scripts {n_script}, assets {n_asset})")
    print(f"failed publishes: {len(failed_pubs)}, dead jobs: {len(dead_jobs)}, "
          f"stale queued: {len(stale)}")
    if apply:
        for p in failed_pubs:
            for s in db.scalars(select(AnalyticsSnapshot).where(
                    AnalyticsSnapshot.publish_id == p.id)).all():
                db.delete(s)
            db.delete(p)
        for j in dead_jobs + stale:
            db.delete(j)
        db.commit()
        print("cleaned.")
    else:
        print("dry-run. Chạy lại với --yes để xóa.")
    db.close()


if __name__ == "__main__":
    main("--yes" in sys.argv)
