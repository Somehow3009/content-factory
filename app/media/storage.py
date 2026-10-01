"""Storage abstraction: R2/S3 khi có creds, fallback filesystem local cho MVP/dev."""
from __future__ import annotations

import os
from pathlib import Path

LOCAL_ROOT = Path(os.getenv("STORAGE_LOCAL_ROOT", "./.storage"))

try:
    from app.config.settings import settings
except Exception:  # pragma: no cover
    settings = None  # type: ignore


def _use_s3() -> bool:
    return bool(settings and settings.storage_access_key and settings.storage_secret_key)


def _client():
    import boto3
    from botocore.client import Config
    kwargs: dict = {
        "aws_access_key_id": settings.storage_access_key,
        "aws_secret_access_key": settings.storage_secret_key,
        "region_name": settings.storage_region or "auto",
    }
    if settings.storage_endpoint:
        kwargs["endpoint_url"] = settings.storage_endpoint
        kwargs["config"] = Config(signature_version="s3v4")
    return boto3.client("s3", **kwargs)


def put_bytes(storage_key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    import os as _os
    # luôn cache local để FFmpeg/QC đọc được ngay
    try:
        p = LOCAL_ROOT / storage_key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    except Exception:
        pass
    if _os.getenv("STORAGE_FORCE_LOCAL") != "1" and _use_s3():
        _client().put_object(Bucket=settings.storage_bucket, Key=storage_key,
                             Body=data, ContentType=content_type)
    return storage_key


def get_bytes(storage_key: str) -> bytes:
    if _use_s3():
        r = _client().get_object(Bucket=settings.storage_bucket, Key=storage_key)
        return r["Body"].read()
    return (LOCAL_ROOT / storage_key).read_bytes()


def local_path(storage_key: str) -> str:
    """Đường dẫn file local cho FFmpeg. File output chưa tồn tại -> chỉ trả path, không tải."""
    import os as _os
    if _os.getenv("STORAGE_FORCE_LOCAL") == "1":
        p = LOCAL_ROOT / storage_key
        return str(p)
    if _use_s3():
        p = LOCAL_ROOT / storage_key
        if p.exists():
            return str(p)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(get_bytes(storage_key))
        except Exception:
            pass  # key chưa có trên S3 (file output) -> trả path để ghi mới
        return str(p)
    p = LOCAL_ROOT / storage_key
    return str(p)


def presigned_publish_url(storage_key: str, expires_in: int = 3600) -> str:
    """Private object -> signed URL cho TikTok PULL_FROM_URL (§17/§25). Local trả file://."""
    if _use_s3():
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.storage_bucket, "Key": storage_key},
            ExpiresIn=expires_in,
        )
    return f"file://{LOCAL_ROOT.resolve()}/{storage_key}"
