from dataclasses import dataclass
from typing import Protocol


@dataclass
class PublishMetadata:
    title: str
    description: str
    privacy: str = "private"  # audited apps can use public
    tags: list[str] | None = None


@dataclass
class PublishResult:
    publish_id: str
    external_post_id: str = ""
    status: str = "REMOTE_PROCESSING"
    error_code: str = ""
    log_id: str = ""


class Publisher(Protocol):
    async def publish(self, account_id: str, video_storage_key: str,
                      metadata: PublishMetadata) -> PublishResult:
        ...
