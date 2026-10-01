"""Publish manager §20/§27/§33/§46: state machine + daily limit + idempotency + circuit breaker.

Tự động: resolve video thật -> publish -> 401 thì refresh token 1 lần -> retry.
"""
from __future__ import annotations

import os as _os
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.models import Account, OAuthToken, Publish
from app.publishers import meta as meta_pub
from app.publishers import tiktok as tk
from app.publishers import youtube as yt
from app.publishers.base import PublishMetadata, PublishResult

FAIL_THRESHOLD = 5  # error gần nhất -> PAUSED


def _get_token(db: Session, account_id: str) -> tuple[str, str]:
    """(access, refresh). 'mock' khi chưa có OAuth thật (test offline)."""
    from app.security.encryption import decrypt_token
    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == account_id))
    if not tok or tok.access_token_encrypted.startswith("mock"):
        return "mock", ""
    try:
        refresh = decrypt_token(tok.refresh_token_encrypted) if tok.refresh_token_encrypted else ""
    except Exception:
        refresh = ""
    return decrypt_token(tok.access_token_encrypted), refresh


async def _refresh_and_save(db: Session, account_id: str, provider: str, refresh: str) -> str:
    from app.security.encryption import encrypt_token
    from app.security.oauth import refresh_access_token
    new = await refresh_access_token(provider, refresh)
    if not new.get("access_token"):
        return ""
    tok = db.scalar(select(OAuthToken).where(OAuthToken.account_id == account_id))
    tok.access_token_encrypted = encrypt_token(new["access_token"])
    if new.get("refresh_token"):
        tok.refresh_token_encrypted = encrypt_token(new["refresh_token"])
    db.commit()
    return new["access_token"]


def _resolve_video(db: Session, variant_id: str) -> tuple[str, str]:
    """(public_url, local_path) của RENDERED_VIDEO mới nhất. local_path phục vụ FILE_UPLOAD."""
    from app.database.models import ContentVariant, MediaAsset
    from app.media.storage import local_path, presigned_publish_url
    url = f"https://storage.local/{variant_id}.mp4"
    video_path = ""
    try:
        var = db.scalar(select(ContentVariant).where(ContentVariant.id == variant_id))
        if var:
            asset = db.scalar(select(MediaAsset).where(
                MediaAsset.content_id == var.content_id,
                MediaAsset.asset_type == "RENDERED_VIDEO").order_by(MediaAsset.created_at.desc()))
            if asset:
                url = presigned_publish_url(asset.storage_key)
                lp = local_path(asset.storage_key)
                if _os.path.exists(lp) and _os.path.getsize(lp) > 1024:
                    video_path = lp
    except Exception:
        pass
    return url, video_path


async def run_publish(db: Session, publish_id: str) -> str:
    pub = db.scalar(select(Publish).where(Publish.id == publish_id))
    if not pub:
        raise ValueError("publish not found")
    if pub.status == "PUBLISHED":  # idempotency §22
        return pub.status
    acc = db.scalar(select(Account).where(Account.id == pub.account_id))
    if not acc or acc.status != "ACTIVE":
        pub.status = "PERMANENT_ERROR"
        db.commit()
        return pub.status
    # daily limit
    today = datetime.utcnow().date()
    count = db.scalar(select(func.count(Publish.id)).where(
        Publish.account_id == acc.id, func.date(Publish.created_at) == today)) or 0
    if count > acc.daily_publish_limit:
        pub.status = "RETRYABLE_ERROR"
        db.commit()
        return pub.status

    pub.status = "UPLOADING"
    db.commit()
    meta = PublishMetadata(title=f"video-{pub.variant_id[:8]}", description="auto by content-factory")

    async def _do(access: str) -> PublishResult:
        if pub.platform == "tiktok":
            url, video_path = _resolve_video(db, pub.variant_id)
            return await tk.publish_tiktok(access, url, meta, video_path=video_path, mode="draft")
        if pub.platform == "youtube":
            _, video_path = _resolve_video(db, pub.variant_id)
            return await yt.publish_youtube(access, video_path or f".storage/{pub.variant_id}.mp4", meta)
        return await meta_pub.publish_meta(pub.platform, access, "", meta)

    try:
        access, refresh = _get_token(db, acc.id)
        res = await _do(access)
        # 401/access hết hạn -> refresh 1 lần rồi retry (TikTok 24h, YouTube 1h)
        if res.error_code in ("http_401", "401", "access_token_invalid") and refresh and access != "mock":
            new_access = await _refresh_and_save(db, acc.id, pub.platform, refresh)
            if new_access:
                res = await _do(new_access)
            else:
                acc.status = "REAUTH_REQUIRED"
        pub.publish_id = res.publish_id
        pub.external_post_id = res.external_post_id
        pub.error_code = res.error_code
        pub.status = res.status
        # circuit breaker: lỗi nhiều -> PAUSED
        fails = db.scalar(select(func.count(Publish.id)).where(
            Publish.account_id == acc.id, Publish.status.in_(["RETRYABLE_ERROR", "PERMANENT_ERROR"]))) or 0
        if fails >= FAIL_THRESHOLD:
            acc.status = "PAUSED"
        db.commit()
        return pub.status
    except Exception as e:
        pub.status = "RETRYABLE_ERROR"
        pub.error_code = type(e).__name__
        db.commit()
        return pub.status
