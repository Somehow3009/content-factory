from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import Account, OAuthToken, Source

router = APIRouter()


@router.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    return [{"id": s.id, "name": s.name, "adapter": s.adapter} for s in db.scalars(select(Source)).all()]


class SourceReq(BaseModel):
    name: str
    adapter: str = "rss"
    config: str = "{}"


@router.post("/sources")
def create_source(req: SourceReq, db: Session = Depends(get_db)):
    s = Source(name=req.name, adapter=req.adapter, config=req.config)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"id": s.id}


@router.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    return [{"id": a.id, "platform": a.platform, "username": a.username, "status": a.status}
            for a in db.scalars(select(Account)).all()]


class AccountReq(BaseModel):
    platform: str
    username: str = ""
    daily_publish_limit: int = 5


@router.post("/accounts")
def create_account(req: AccountReq, db: Session = Depends(get_db)):
    a = Account(platform=req.platform, username=req.username,
                daily_publish_limit=req.daily_publish_limit)
    db.add(a)
    db.commit()
    db.refresh(a)
    # mock token mã hóa để pipeline chạy offline (§26)
    from app.security.encryption import encrypt_token
    try:
        db.add(OAuthToken(account_id=a.id, provider=req.platform,
                          access_token_encrypted=encrypt_token("mock-token")))
        db.commit()
    except Exception:
        pass
    return {"id": a.id, "oauth_url": f"/api/v1/accounts/oauth/{req.platform}"}


@router.get("/accounts/oauth/callback", response_class=HTMLResponse)
def oauth_callback(code: str = Query(default=""), error: str = Query(default="")):
    if error:
        return f"<html><body><h1>OAuth lỗi: {error}</h1></body></html>"
    return (f"<html><body><h1>Copy code này gửi cho Muse:</h1>"
            f"<p style='font-size:20px;background:#eee;padding:12px'>{code}</p>"
            f"<p>Code dùng 1 lần, hết hạn sau vài phút.</p></body></html>")
