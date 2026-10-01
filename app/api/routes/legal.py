"""Legal pages free (không cần mua domain): serve Terms/Privacy + file verify TikTok từ chính app."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.config.settings import settings

router = APIRouter()

_TERMS = """<html><body><h1>Terms of Service — Content Factory</h1>
<p>Content Factory posts short videos to your TikTok account only after your OAuth authorization.
You can revoke access anytime in TikTok Settings. Contact: khang31ty@gmail.com</p></body></html>"""

_PRIVACY = """<html><body><h1>Privacy Policy — Content Factory</h1>
<p>We store TikTok OAuth tokens encrypted (Fernet) and video metadata needed for posting and analytics.
We do not sell personal data. Contact: khang31ty@gmail.com</p></body></html>"""


@router.get("/legal/terms", response_class=HTMLResponse)
def terms():
    return _TERMS


@router.get("/legal/privacy", response_class=HTMLResponse)
def privacy():
    return _PRIVACY


@router.get("/tiktok-verify.txt", response_class=PlainTextResponse)
def tiktok_verify():
    return getattr(settings, "tiktok_site_verification", "") or "pending"


_VERIFY_TXT = "tiktok-developers-site-verification=dRmMFuRWQCG2kV7xA2D6koWS2GVIBoWB"


@router.get("/legal/terms/privacy", response_class=HTMLResponse)
def privacy_under_terms():
    return _PRIVACY


@router.get("/tiktokdRmMFuRWQCG2kV7xA2D6koWS2GVIBoWB.txt", response_class=PlainTextResponse)
def tiktok_verify_file():
    return _VERIFY_TXT


@router.get("/legal/terms/tiktokdRmMFuRWQCG2kV7xA2D6koWS2GVIBoWB.txt", response_class=PlainTextResponse)
def tiktok_verify_file_legal():
    return _VERIFY_TXT
