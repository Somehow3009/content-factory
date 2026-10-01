"""Đổi YouTube code -> token -> lưu Neon. Code paste vào biến CODE."""
from __future__ import annotations

import asyncio

CODE = "4/0AXlqoi68vUsdKdf_OawLfh-EbaDc2MFOH3r939H277HTQRnhOYev9QjuLxOSSg4y1ZyB6Q"

from sqlalchemy import select

from app.database.db import SessionLocal
from app.database.models import Account, OAuthToken
from app.security.encryption import encrypt_token
from app.security.oauth import exchange_code


def main() -> None:
    res = asyncio.run(exchange_code("youtube", CODE))
    if not res.get("access_token"):
        print("EXCHANGE FAILED:", str(res)[:300])
        return
    db = SessionLocal()
    acc = db.scalar(select(Account).where(Account.platform == "youtube",
                                          Account.status == "ACTIVE"))
    if not acc:
        acc = Account(platform="youtube", username="main-channel",
                      status="ACTIVE", daily_publish_limit=5)
        db.add(acc)
        db.commit()
        db.refresh(acc)
    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == acc.id))
    if not tok:
        tok = OAuthToken(account_id=acc.id, provider="youtube",
                         access_token_encrypted="", refresh_token_encrypted="")
        db.add(tok)
    tok.access_token_encrypted = encrypt_token(res["access_token"])
    if res.get("refresh_token"):  # Google chỉ trả refresh khi prompt=consent; giữ cũ nếu thiếu
        tok.refresh_token_encrypted = encrypt_token(res["refresh_token"])
    tok.scope = res.get("scope", "")
    if acc.status != "ACTIVE":
        acc.status = "ACTIVE"
    db.commit()
    print("STORED youtube account:", acc.id[:8])
    print("scope:", res.get("scope"))
    db.close()


if __name__ == "__main__":
    main()
