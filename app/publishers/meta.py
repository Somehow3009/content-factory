"""Meta publisher §19: FB + IG chung interface, tách module meta/*."""
from __future__ import annotations

import time

from app.publishers.base import PublishMetadata, PublishResult


async def publish_meta(account_platform: str, access_token: str,
                       video_url: str, meta: PublishMetadata) -> PublishResult:
    # MVP mock (cần Page token + app review thật mới post được). Giữ interface để swap.
    return PublishResult(publish_id=f"mock-{account_platform}-{int(time.time())}", status="PUBLISHED")
