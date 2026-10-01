"""MVP tables (spec section 39). Enums stored as strings for portability."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    adapter: Mapped[str] = mapped_column(String(64))  # rss | api | creator_feed | douyin
    config: Mapped[str] = mapped_column(Text, default="{}")
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Content(Base):
    __tablename__ = "contents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    external_id: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="unknown")
    license_status: Mapped[str] = mapped_column(String(32), default="unknown")
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="DISCOVERED")
    trend_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_content_source_external"),)


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    content_id: Mapped[str] = mapped_column(ForeignKey("contents.id"))
    asset_type: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Script(Base):
    __tablename__ = "scripts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    content_id: Mapped[str] = mapped_column(ForeignKey("contents.id"))
    hook: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="[]")
    ending: Mapped[str] = mapped_column(Text, default="")
    cta: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(16), default="vi")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ContentVariant(Base):
    __tablename__ = "content_variants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    content_id: Mapped[str] = mapped_column(ForeignKey("contents.id"))
    variant_code: Mapped[str] = mapped_column(String(32), default="A")
    script_id: Mapped[str] = mapped_column(String(36), default="")
    template_id: Mapped[str] = mapped_column(String(64), default="9x16-default")
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    platform: Mapped[str] = mapped_column(String(32))  # tiktok | youtube | facebook | instagram
    external_account_id: Mapped[str] = mapped_column(String(255), default="")
    username: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    daily_publish_limit: Mapped[int] = mapped_column(Integer, default=5)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    provider: Mapped[str] = mapped_column(String(32))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text, default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scope: Mapped[str] = mapped_column(Text, default="")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_type: Mapped[str] = mapped_column(String(32))  # DISCOVER | INGEST | ... | PUBLISH
    entity_type: Mapped[str] = mapped_column(String(32), default="")
    entity_id: Mapped[str] = mapped_column(String(36), default="")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    idempotency_key: Mapped[str] = mapped_column(String(255), default="")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str] = mapped_column(String(64), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_jobs_idempotency"),)


class Publish(Base):
    __tablename__ = "publishes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    variant_id: Mapped[str] = mapped_column(ForeignKey("content_variants.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    platform: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="CREATED")
    publish_id: Mapped[str] = mapped_column(String(255), default="")  # platform-side id
    external_post_id: Mapped[str] = mapped_column(String(255), default="")
    error_code: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("platform", "account_id", "variant_id", name="uq_publish_platform_account_variant"),
    )


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    publish_id: Mapped[str] = mapped_column(ForeignKey("publishes.id"))
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
