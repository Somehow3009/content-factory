"""Pipeline orchestration: score->select->ingest->process->variants->publish_queue."""
from __future__ import annotations

import json
import os

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Content, ContentVariant, MediaAsset, Publish, Script
from app.discovery.scorer import score
from app.intelligence import scriptwriter
from app.intelligence.transcription import Transcriber
from app.jobs import queue as q
from app.media import qc as qcmod
from app.media import renderer, storage, subtitle, tts


def score_and_select(db: Session, content_id: str, weights: dict | None = None) -> float:
    """Chấm điểm + chọn top-N mỗi source mỗi ngày (§6, §45). Vượt quota -> SKIPPED, không tốn render."""
    from app.database.models import Content as _C
    c = db.scalar(select(Content).where(Content.id == content_id))
    s = score(0.5, 0.05, 0.9, 0.7, 0.8, weights)
    c.trend_score = s
    if s <= 1.0:
        c.status = "SCORING"
        db.commit()
        return s
    cap = int(os.getenv("MAX_SELECTED_PER_SOURCE_PER_DAY", "3"))
    today = func.date(_C.created_at) == func.date(func.now())
    n = db.scalar(select(func.count(_C.id)).where(
        _C.source_id == c.source_id, _C.status == "SELECTED", today)) or 0
    if n >= cap:
        c.status = "SKIPPED"
    else:
        c.status = "SELECTED"
        q.enqueue(db, "INGEST", "content", c.id, idempotency_key=f"ingest:{c.id}")
    db.commit()
    return s


def process_content(db: Session, content_id: str) -> str:
    """INGESTED -> TRANSCRIBE -> script VI -> voice -> subtitle -> render variants."""
    from app.media.storage import local_path
    c = db.scalar(select(Content).where(Content.id == content_id))
    c.status = "PROCESSING"
    db.commit()

    src_asset = db.scalar(select(MediaAsset).where(
        MediaAsset.content_id == content_id, MediaAsset.asset_type == "SOURCE_VIDEO"))
    src_path = local_path(src_asset.storage_key) if src_asset else ""
    transcript = Transcriber().transcribe_file(src_path)
    tkey = f"content/{content_id}/transcript/source.json"
    storage.put_bytes(tkey, json.dumps(transcript, ensure_ascii=False).encode(),
                      content_type="application/json")
    db.add(MediaAsset(content_id=content_id, asset_type="TRANSCRIPT", storage_key=tkey,
                       mime_type="application/json"))

    summary = scriptwriter.summarize(transcript)
    script = scriptwriter.localize_to_vi(summary)
    caption = scriptwriter.build_caption(script)
    sc = Script(content_id=content_id, hook=script["hook"],
                body=json.dumps(script["body"], ensure_ascii=False),
                ending=script["ending"], cta=script["cta"])
    db.add(sc)
    db.commit()
    db.refresh(sc)
    scriptwriter.save_script_files(content_id, {**script, **caption})

    # voice + subtitle (dùng chung cho mọi variant MVP)
    voice_local = local_path(f"content/{content_id}/voice/voice.wav")
    tts.synthesize(script, voice_local)
    voice_key = f"content/{content_id}/voice/voice.wav"
    storage.put_bytes(voice_key, open(voice_local, "rb").read(), content_type="audio/wav")
    db.add(MediaAsset(content_id=content_id, asset_type="VOICE", storage_key=voice_key))

    srt_text = subtitle.script_to_srt(script)
    srt_key = f"content/{content_id}/subtitle/vi.srt"
    storage.put_bytes(srt_key, srt_text.encode("utf-8"), content_type="text/plain")
    db.add(MediaAsset(content_id=content_id, asset_type="SUBTITLE", storage_key=srt_key))
    srt_local = local_path(srt_key)
    db.commit()

    # variants A/B/C (§14)
    for v in renderer.VARIANTS:
        var = ContentVariant(content_id=content_id, variant_code=v["code"],
                             script_id=sc.id, status="RENDERING")
        db.add(var)
        db.commit()
        db.refresh(var)
        out_local = local_path(f"content/{content_id}/render/variant-{v['code'].lower()}.mp4")
        renderer.render(src_path, voice_local, srt_local, out_local, max_seconds=v["max_seconds"])
        rkey = f"content/{content_id}/render/variant-{v['code'].lower()}.mp4"
        storage.put_bytes(rkey, open(out_local, "rb").read(), content_type="video/mp4")
        db.add(MediaAsset(content_id=content_id, asset_type="RENDERED_VIDEO", storage_key=rkey,
                           mime_type="video/mp4", size_bytes=len(open(out_local, 'rb').read())))
        res = qcmod.check(out_local, require_subtitle=True, subtitle_path=srt_local)
        var.status = "READY" if res["passed"] else "QC_FAILED"
        db.commit()

    c.status = "READY"
    db.commit()
    return c.status


def queue_publishes(db: Session, content_id: str, account_ids: list[str], platform: str) -> int:
    n = 0
    for var in db.scalars(select(ContentVariant).where(
            ContentVariant.content_id == content_id, ContentVariant.status == "READY")).all():
        for acc_id in account_ids:
            key = f"publish:{platform}:{acc_id}:{var.id}"
            exists = db.scalar(select(Publish).where(
                Publish.platform == platform, Publish.account_id == acc_id,
                Publish.variant_id == var.id))
            if exists:
                continue
            db.add(Publish(variant_id=var.id, account_id=acc_id, platform=platform, status="CREATED"))
            q.enqueue(db, "PUBLISH", "publish", var.id, idempotency_key=key)
            n += 1
    db.commit()
    return n


def auto_queue_ready(db: Session) -> int:
    """AUTO_PUBLISH: mọi content READY chưa có publish -> tạo publish cho mọi ACTIVE account.

    Tôn trọng daily limit ở manager.run_publish. Idempotent qua UNIQUE(platform,account,variant).
    """
    from app.database.models import Account
    total = 0
    accounts = db.scalars(select(Account).where(Account.status == "ACTIVE")).all()
    by_platform: dict[str, list[str]] = {}
    for a in accounts:
        by_platform.setdefault(a.platform, []).append(a.id)
    if not by_platform:
        return 0
    for c in db.scalars(select(Content).where(Content.status == "READY")).all():
        for platform, acc_ids in by_platform.items():
            total += queue_publishes(db, c.id, acc_ids, platform)
    return total
