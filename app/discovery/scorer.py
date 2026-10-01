"""Trend scoring §6. Weights nằm trong config, không hard-code lõi."""
from __future__ import annotations

DEFAULT_WEIGHTS = {"w1": 1.0, "w2": 2.0, "w3": 1.5, "w4": 1.0, "w5": 0.5}


def velocity(current: float, previous: float) -> float:
    return (current - previous) / max(previous, 1)


def score(velocity_: float, engagement_rate: float, freshness: float,
          topic_relevance: float, novelty: float, weights: dict | None = None) -> float:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    return (velocity_ * w["w1"] + engagement_rate * w["w2"] + freshness * w["w3"]
            + topic_relevance * w["w4"] + novelty * w["w5"])
