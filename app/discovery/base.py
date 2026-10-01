from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class EngagementSnapshot:
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0


@dataclass
class ContentCandidate:
    external_id: str
    source_id: str
    source_url: str
    title: str | None = None
    description: str | None = None
    language: str | None = None
    published_at: datetime | None = None
    engagement: EngagementSnapshot | None = None
    media_url: str | None = None


@dataclass
class SourceConfig:
    source_id: str
    adapter: str
    config: dict


class SourceAdapter(Protocol):
    async def discover(self, source_config: SourceConfig) -> list[ContentCandidate]:
        ...


def trend_velocity(current: float, previous: float) -> float:
    return (current - previous) / max(previous, 1)


def trend_score(velocity: float, engagement_rate: float, freshness: float,
                topic_relevance: float, novelty: float, weights: dict) -> float:
    return (velocity * weights.get("w1", 1.0)
            + engagement_rate * weights.get("w2", 1.0)
            + freshness * weights.get("w3", 1.0)
            + topic_relevance * weights.get("w4", 1.0)
            + novelty * weights.get("w5", 1.0))
