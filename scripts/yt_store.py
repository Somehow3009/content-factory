"""Đổi YouTube code -> token -> lưu Neon. Code paste vào biến CODE."""
from __future__ import annotations

import asyncio

CODE = "4/0AXlqoi60IU0Qy2ibbRudDZuagHzZguHVTUPdarDraJd3t6vWWZ2XNiXc3iUKcwVyBS65_w"

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
    acc = Account(platform="youtube", username="main-channel",
                  status="ACTIVE", daily_publish_limit=5)
    db.add(acc)
    db.commit()
    db.refresh(acc)
    db.add(OAuthToken(account_id=acc.id, provider="youtube",
                      access_token_encrypted=encrypt_token(res["access_token"]),
                      refresh_token_encrypted=encrypt_token(res.get("refresh_token", "")),
                      scope=res.get("scope", "")))
    db.commit()
    print("STORED youtube account:", acc.id[:8])
    print("scope:", res.get("scope"))
    db.close()


if __name__ == "__main__":
    main()
