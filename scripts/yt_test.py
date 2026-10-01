"""Test upload YouTube private bằng variant-a mp4 thật."""
from __future__ import annotations

import asyncio
import glob
import os

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Account, OAuthToken
from app.publishers import youtube as yt
from app.publishers.base import PublishMetadata
from app.security.encryption import decrypt_token


def main() -> None:
    db = SessionLocal()
    acc = db.scalar(select(Account).where(Account.platform == "youtube",
                                          Account.status == "ACTIVE"))
    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == acc.id))
    access = decrypt_token(tok.access_token_encrypted)
    cand = glob.glob(os.path.join(".storage", "content", "0cf8465f*",
                                  "render", "variant-a.mp4"))
    print("file:", cand[0], os.path.getsize(cand[0]))
    res = asyncio.run(yt.publish_youtube(
        access, cand[0],
        PublishMetadata(title="Content Factory MVP test (private)",
                        description="upload test tu pipeline",
                        tags=["shorts", "test"])))
    print("status:", res.status)
    print("video_id:", res.publish_id)
    print("error:", res.error_code)
    db.close()


if __name__ == "__main__":
    main()
