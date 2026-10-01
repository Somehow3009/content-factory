"""OAuth §26-27: build URL + exchange code. Token mã hóa Fernet trước khi lưu DB."""
from __future__ import annotations

import urllib.parse

from app.config.settings import settings


def authorize_url(provider: str) -> str:
    if provider == "tiktok":
        q = urllib.parse.urlencode({"client_key": settings.tiktok_client_key, "response_type": "code",
                                    "scope": "user.info.basic,video.upload,video.publish",
                                    "redirect_uri": settings.tiktok_redirect_uri, "state": "xyz"})
        return f"https://www.tiktok.com/v2/auth/authorize/?{q}"
    if provider in ("youtube", "google"):
        q = urllib.parse.urlencode({"client_id": settings.google_client_id, "response_type": "code",
                                    "scope": ("https://www.googleapis.com/auth/youtube.upload "
                                              "https://www.googleapis.com/auth/youtube.readonly"),
                                    "redirect_uri": settings.google_redirect_uri, "access_type": "offline",
                                    "prompt": "consent", "state": "xyz"})
        return f"https://accounts.google.com/o/oauth2/v2/auth?{q}"
    if provider in ("meta", "facebook", "instagram"):
        q = urllib.parse.urlencode({"client_id": settings.meta_app_id,
                                    "redirect_uri": settings.google_redirect_uri,
                                    "scope": "pages_manage_posts,instagram_basic,instagram_content_publish",
                                    "response_type": "code", "state": "xyz"})
        return f"https://www.facebook.com/v19.0/dialog/oauth?{q}"
    raise ValueError(provider)


async def refresh_access_token(provider: str, refresh_token: str) -> dict:
    """Tự refresh khi access hết hạn (TikTok 24h, YouTube 1h). Trả dict token mới hoặc {}."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            if provider == "tiktok" and settings.tiktok_client_key:
                r = await c.post("https://open.tiktokapis.com/v2/oauth/token/",
                                 data={"client_key": settings.tiktok_client_key,
                                       "client_secret": settings.tiktok_client_secret,
                                       "grant_type": "refresh_token",
                                       "refresh_token": refresh_token})
                r.raise_for_status()
                return r.json()
            if provider in ("youtube", "google") and settings.google_client_id:
                r = await c.post("https://oauth2.googleapis.com/token",
                                 data={"client_id": settings.google_client_id,
                                       "client_secret": settings.google_client_secret,
                                       "grant_type": "refresh_token",
                                       "refresh_token": refresh_token})
                r.raise_for_status()
                return r.json()
    except Exception:
        return {}
    return {}


async def exchange_code(provider: str, code: str) -> dict:
    """Đổi code -> token. MVP trả mock khi thiếu creds để test pipeline."""
    import httpx
    try:
        if provider == "tiktok" and settings.tiktok_client_key:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post("https://open.tiktokapis.com/v2/oauth/token/",
                                 data={"client_key": settings.tiktok_client_key,
                                       "client_secret": settings.tiktok_client_secret,
                                       "code": code, "grant_type": "authorization_code",
                                       "redirect_uri": settings.tiktok_redirect_uri})
                r.raise_for_status()
                return r.json()
        if provider in ("youtube", "google") and settings.google_client_id:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.post("https://oauth2.googleapis.com/token",
                                 data={"client_id": settings.google_client_id,
                                       "client_secret": settings.google_client_secret,
                                       "code": code, "grant_type": "authorization_code",
                                       "redirect_uri": settings.google_redirect_uri})
                r.raise_for_status()
                return r.json()
    except Exception as e:
        return {"mock": True, "error": str(e)}
    return {"mock": True, "access_token": f"mock-{provider}-token", "expires_in": 86400}
