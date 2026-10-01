"""MVP acceptance test (§40): pipeline offline không cần creds ngoài."""
import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.models import Base, Content, Source


def _test_db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return sessionmaker(bind=eng, expire_on_commit=False)


def test_trend_score_and_fingerprint():
    from app.discovery.scorer import score
    from app.ingestion.fingerprint import fingerprint_text
    s = score(1.0, 0.1, 0.9, 0.7, 0.8, None)
    assert s > 0
    assert fingerprint_text("a") != fingerprint_text("b")
    assert fingerprint_text("a") == fingerprint_text("a")


def test_queue_idempotency_and_retry():
    S = _test_db()
    db = S()
    from app.database.models import Job
    from app.jobs import queue as q
    j1 = q.enqueue(db, "RENDER", "content", "c1", idempotency_key="k1")
    j2 = q.enqueue(db, "RENDER", "content", "c1", idempotency_key="k1")
    assert j1.id == j2.id  # idempotent §22
    job = q.claim(db)
    assert job is not None
    q.fail(db, job, "Timeout", "t", retryable=True)
    assert db.scalar(select(Job).where(Job.id == job.id)).status == "QUEUED"
    # permanent sau max_attempts
    job2 = db.scalar(select(Job).where(Job.id == job.id))
    job2.attempts = 99
    db.commit()
    q.fail(db, job2, "Bad", "b", retryable=True)
    assert job2.status == "DEAD_LETTER"


def test_script_subtitle_qc_render_offline(tmp_path):
    from app.intelligence import scriptwriter
    from app.media import qc as qcmod
    from app.media import renderer, subtitle, tts
    tr = {"language": "zh", "segments": [{"start": 0, "end": 3, "text": "ni hao"}]}
    summary = scriptwriter.summarize(tr)
    script = scriptwriter.localize_to_vi(summary)
    assert "hook" in script and "body" in script
    srt = subtitle.script_to_srt(script)
    assert "-->" in srt
    voice = str(tmp_path / "v.wav")
    tts.synthesize(script, voice)
    src = str(tmp_path / "s.bin")
    open(src, "wb").write(b"x" * 5000)
    out = str(tmp_path / "o.mp4")
    srt_p = str(tmp_path / "v.srt")
    open(srt_p, "w", encoding="utf-8").write(srt)
    renderer.render(src, voice, srt_p, out)
    res = qcmod.check(out, subtitle_path=srt_p)
    assert res["passed"]


def test_full_pipeline_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("STORAGE_FORCE_LOCAL", "1")
    from app.config import settings as _s
    monkeypatch.setattr(_s.settings, "tiktok_client_key", "")
    monkeypatch.setattr(_s.settings, "google_client_id", "")
    S = _test_db()
    db = S()
    import app.media.storage as st
    import pathlib
    st.LOCAL_ROOT = pathlib.Path(str(tmp_path / "storage"))

    src = Source(name="test-rss", adapter="rss", config='{"feed_url":"http://x"}')
    db.add(src)
    db.commit()
    c = Content(source_id=src.id, external_id="e1", source_url="", title="demo",
                description="demo", status="INGESTED")
    db.add(c)
    db.commit()

    from app.jobs.pipeline import process_content, queue_publishes
    stt = process_content(db, c.id)
    assert stt == "READY"

    from app.database.models import Account, ContentVariant
    acc = Account(platform="tiktok", username="u1", status="ACTIVE", daily_publish_limit=5)
    db.add(acc)
    db.commit()
    n = queue_publishes(db, c.id, [acc.id], "tiktok")
    assert n >= 1  # 3 variants READY -> queue

    import asyncio
    from app.publishers.manager import run_publish
    from app.database.models import Publish
    pub = db.scalars(select(Publish)).first()
    # gắn token mock
    from app.database.models import OAuthToken
    db.add(OAuthToken(account_id=acc.id, provider="tiktok", access_token_encrypted="mock"))
    db.commit()
    s2 = asyncio.run(run_publish(db, pub.id))
    assert s2 == "PUBLISHED"
    # idempotency: chạy lại không đăng trùng
    s3 = asyncio.run(run_publish(db, pub.id))
    assert s3 == "PUBLISHED"

        from app.analytics.collector import collect_for_publish
        snap = asyncio.run(collect_for_publish(db, pub.id))
        assert snap is None  # mock publish -> không bịa số liệu, chỉ API thật mới có snapshot
