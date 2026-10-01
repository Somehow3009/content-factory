"""YouTube publisher §18: videos.insert resumable upload. Mock khi thiếu creds."""
from __future__ import annotations

import time

from app.config.settings import settings
from app.publishers.base import PublishMetadata, PublishResult


def _mock() -> bool:
    return not settings.google_client_id


async def publish_youtube(access_token: str, video_path: str, meta: PublishMetadata) -> PublishResult:
    if _mock():
        return PublishResult(publish_id=f"mock-yt-{int(time.time())}",
                             external_post_id=f"yt-{int(time.time())}", status="PUBLISHED")
    import httpx
    async with httpx.AsyncClient(timeout=120) as c:
        # resumable session init
        r = await c.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"snippet": {"title": meta.title[:100], "description": meta.description[:5000],
                              "tags": meta.tags or []},
                  "status": {"privacyStatus": "private"}})
        r.raise_for_status()
        session_url = r.headers.get("location", "")
        # upload bytes (MVP: 1 PUT; prod chunked)
        data = open(video_path, "rb").read()
        r2 = await c.put(session_url, content=data,
                         headers={"Content-Length": str(len(data))})
        r2.raise_for_status()
        vid = r2.json().get("id", "")
        return PublishResult(publish_id=vid, external_post_id=vid, status="PUBLISHED")
