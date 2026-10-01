"""Analytics §28-29: snapshots append-only. CHỈ số liệu thật từ platform API.

- YouTube: videos.list(part=statistics) bằng token của channel -> views/likes/comments thật.
- TikTok inbox draft: chưa có metrics (phải bấm Post trong app trước) -> skip, không bịa số.
- Không bao giờ sinh số giả để dashboard đẹp.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Account, AnalyticsSnapshot, OAuthToken, Publish


def engagement_rate(views: int, likes: int, comments: int, shares: int) -> float:
    return (likes + comments + shares) / max(views, 1)


def performance_score(views: int, engagement: float, retention: float = 0.0) -> float:
    return views * 0.001 + engagement * 100 + retention * 50


async def fetch_youtube_stats(access_token: str, video_id: str) -> dict | None:
    import httpx
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://www.googleapis.com/youtube/v3/videos",
                        params={"part": "statistics,status", "id": video_id},
                        headers={"Authorization": f"Bearer {access_token}"})
        if r.status_code == 401:
            return {"unauthorized": True}
        r.raise_for_status()
        items = r.json().get("items", [])
        if not items:
            return None
        st = items[0].get("statistics", {})
        return {"views": int(st.get("viewCount", 0)),
                "likes": int(st.get("likeCount", 0)),
                "comments": int(st.get("commentCount", 0)),
                "shares": 0}


async def collect_for_publish(db: Session, publish_id: str) -> AnalyticsSnapshot | None:
    """Thu metrics thật. Trả None khi chưa có số liệu (draft) hoặc token hết hạn."""
    from app.security.encryption import decrypt_token
    from app.security.oauth import refresh_access_token
    from app.security.encryption import encrypt_token
    pub = db.scalar(select(Publish).where(Publish.id == publish_id))
    if not pub or not pub.external_post_id or pub.external_post_id.startswith("mock"):
        return None
    if pub.platform == "tiktok" and pub.status != "PUBLISHED":
        return None  # draft/inbox: TikTok chưa có metrics
    acc = db.scalar(select(Account).where(Account.id == pub.account_id))
    if not acc:
        return None
    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == acc.id))
    if not tok:
        return None
    access = decrypt_token(tok.access_token_encrypted)
    if pub.platform == "youtube":
        stats = await fetch_youtube_stats(access, pub.external_post_id)
        if not stats:
            return None
        if stats.get("unauthorized"):
            try:
                refresh = decrypt_token(tok.refresh_token_encrypted)
            except Exception:
                refresh = ""
            new = await refresh_access_token("youtube", refresh) if refresh else {}
            if not new.get("access_token"):
                acc.status = "REAUTH_REQUIRED"
                db.commit()
                return None
            tok.access_token_encrypted = encrypt_token(new["access_token"])
            db.commit()
            stats = await fetch_youtube_stats(new["access_token"], pub.external_post_id)
            if not stats or stats.get("unauthorized"):
                return None
        snap = AnalyticsSnapshot(publish_id=publish_id, views=stats["views"],
                                 likes=stats["likes"], comments=stats["comments"],
                                 shares=stats["shares"])
        db.add(snap)
        db.commit()
        db.refresh(snap)
        return snap
    return None  # platform khác: chưa có collector thật
