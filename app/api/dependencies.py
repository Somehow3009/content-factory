from fastapi import Header, HTTPException

from app.config.settings import settings


def require_worker(x_worker_token: str = Header(default="")):
    if x_worker_token != settings.api_worker_token:
        raise HTTPException(401, "bad worker token")
