"""TikTok publisher §17: Upload-draft (video.upload) + Direct Post (video.publish).

- Draft:  POST /v2/post/publish/inbox/video/init/ (scope video.upload, body chỉ source_info)
- Direct: POST /v2/post/publish/video/init/      (scope video.publish, cần creator_info trước)
FILE_UPLOAD cho cả 2 -> không cần domain verify. Mock khi thiếu TIKTOK_CLIENT_KEY.
Rate limit init: 6 req/phút/token.
"""
from __future__ import annotations

import os
import time

import httpx

from app.config.settings import settings
from app.publishers.base import PublishMetadata, PublishResult

_TIKTOK_BASE = "https://open.tiktokapis.com/v2"
_last_init: list[float] = []  # process-local guard (DB guard thêm ở manager)


def _mock() -> bool:
    return not settings.tiktok_client_key


def _rate_ok() -> bool:
    now = time.time()
    _last_init[:] = [t for t in _last_init if now - t < 60]
    if len(_last_init) >= 6:
        return False
    _last_init.append(now)
    return True


def _err_code(status: int) -> str:
    return "429" if status == 429 else f"http_{status}"


async def upload_draft(access_token: str, video_path: str) -> PublishResult:
    """Upload draft (inbox) — chỉ cần scope video.upload. User vào TikTok inbox để edit/post."""
    if _mock():
        return PublishResult(publish_id=f"mock-tk-{int(time.time())}", status="PUBLISHED")
    if not _rate_ok():
        return PublishResult(publish_id="", status="RETRYABLE_ERROR", error_code="429")
    size = os.path.getsize(video_path)
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{_TIKTOK_BASE}/post/publish/inbox/video/init/", headers=headers,
                         json={"source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                               "chunk_size": size, "total_chunk_count": 1}})
        if r.status_code != 200:
            return PublishResult(publish_id="", status="RETRYABLE_ERROR" if r.status_code in (429, 500, 502, 503, 504) else "PERMANENT_ERROR",
                                 error_code=_err_code(r.status_code))
        data = r.json().get("data", {})
        upload_url = data.get("upload_url", "")
        with open(video_path, "rb") as f:
            blob = f.read()
        up = await c.put(upload_url, content=blob,
                         headers={"Content-Type": "video/mp4", "Content-Length": str(size),
                                  "Content-Range": f"bytes 0-{size-1}/{size}"})
        if up.status_code not in (200, 201, 206):
            return PublishResult(publish_id=data.get("publish_id", ""), status="RETRYABLE_ERROR",
                                 error_code=_err_code(up.status_code))
        return PublishResult(publish_id=data.get("publish_id", ""), status="REMOTE_PROCESSING")


async def direct_post(access_token: str, video_path: str, meta: PublishMetadata,
                      privacy: str = "SELF_ONLY") -> PublishResult:
    """Direct Post — cần scope video.publish + creator_info trước."""
    if _mock():
        return PublishResult(publish_id=f"mock-tk-{int(time.time())}", status="PUBLISHED")
    if not _rate_ok():
        return PublishResult(publish_id="", status="RETRYABLE_ERROR", error_code="429")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}
    async with httpx.AsyncClient(timeout=60) as c:
        ci = await c.post(f"{_TIKTOK_BASE}/post/publish/creator_info/query/", headers=headers, json={})
        if ci.status_code != 200:
            return PublishResult(publish_id="", status="PERMANENT_ERROR" if ci.status_code == 401 else "RETRYABLE_ERROR",
                                 error_code=_err_code(ci.status_code))
        size = os.path.getsize(video_path)
        title = f"{meta.title} {meta.description}"[:2200][:150]
        r = await c.post(f"{_TIKTOK_BASE}/post/publish/video/init/", headers=headers,
                         json={"post_info": {"title": title, "privacy_level": privacy},
                               "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                                               "chunk_size": size, "total_chunk_count": 1}})
        if r.status_code != 200:
            return PublishResult(publish_id="", status="RETRYABLE_ERROR" if r.status_code in (429, 500, 502, 503, 504) else "PERMANENT_ERROR",
                                 error_code=_err_code(r.status_code))
        data = r.json().get("data", {})
        with open(video_path, "rb") as f:
            blob = f.read()
        up = await c.put(data.get("upload_url", ""), content=blob,
                         headers={"Content-Type": "video/mp4", "Content-Length": str(size),
                                  "Content-Range": f"bytes 0-{size-1}/{size}"})
        if up.status_code not in (200, 201, 206):
            return PublishResult(publish_id=data.get("publish_id", ""), status="RETRYABLE_ERROR",
                                 error_code=_err_code(up.status_code))
        return PublishResult(publish_id=data.get("publish_id", ""), status="REMOTE_PROCESSING")


async def publish_tiktok(access_token: str, video_url: str = "", meta: PublishMetadata | None = None,
                         privacy: str = "SELF_ONLY", video_path: str = "",
                         mode: str = "draft") -> PublishResult:
    """Mặc định mode='draft' (video.upload). Direct khi có token video.publish."""
    meta = meta or PublishMetadata(title="video", description="auto")
    if mode == "direct" and video_path:
        return await direct_post(access_token, video_path, meta, privacy)
    if video_path:
        return await upload_draft(access_token, video_path)
    # PULL_FROM_URL draft (cần domain verify) — giữ cho production sau
    if _mock():
        return PublishResult(publish_id=f"mock-tk-{int(time.time())}", status="PUBLISHED")
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=UTF-8"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{_TIKTOK_BASE}/post/publish/inbox/video/init/", headers=headers,
                         json={"source_info": {"source": "PULL_FROM_URL", "video_url": video_url}})
        if r.status_code != 200:
            return PublishResult(publish_id="", status="RETRYABLE_ERROR", error_code=_err_code(r.status_code))
        return PublishResult(publish_id=r.json().get("data", {}).get("publish_id", ""), status="REMOTE_PROCESSING")


async def check_status(access_token: str, publish_id: str) -> str:
    if _mock() or not access_token or publish_id.startswith("mock-"):
        return "PUBLISHED"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{_TIKTOK_BASE}/post/publish/status/fetch/",
                         headers=headers, json={"publish_id": publish_id})
        r.raise_for_status()
        return r.json().get("data", {}).get("status", "REMOTE_PROCESSING")
