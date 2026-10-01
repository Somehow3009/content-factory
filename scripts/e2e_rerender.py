"""E2E re-render: dựng lại 3 variants thành mp4 thật (slideshow+voice+sub) rồi up S3."""
from __future__ import annotations

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import ContentVariant, MediaAsset
from app.media import renderer, storage

CID = "0cf8465f"

db = SessionLocal()
c_full = None
for v in db.scalars(select(ContentVariant)).all():
    if v.content_id.startswith(CID):
        c_full = v.content_id
        break
print("content:", c_full)
voice_key = f"content/{c_full}/voice/voice.wav"
srt_key = f"content/{c_full}/subtitle/vi.srt"
for code, secs in (("a", 60), ("b", 45), ("c", 30)):
    key = f"content/{c_full}/render/variant-{code}.mp4"
    out = storage.local_path(key)
    renderer.render("", storage.local_path(voice_key), storage.local_path(srt_key),
                    out, max_seconds=secs)
    import os
    size = os.path.getsize(out)
    storage.put_bytes(key, open(out, "rb").read(), content_type="video/mp4")
    m = db.scalar(select(MediaAsset).where(MediaAsset.storage_key == key))
    if m:
        m.size_bytes = size
    print("rendered", code, size, "bytes")
db.commit()
db.close()
