from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import accounts, analytics, contents, dashboard, health, internal, jobs, legal, publishes, videos
from app.config.logging import configure_logging
from app.database.db import init_db

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:  # scheduler nền: DISCOVER 30p / AUTO_PUBLISH 1h / ANALYTICS 6h / OPTIMIZE 24h
        from app.jobs.scheduler import start as start_scheduler
        start_scheduler()
    except Exception:
        pass
    yield


app = FastAPI(title="content-factory", lifespan=lifespan)

app.include_router(health.router)
app.include_router(legal.router)
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(contents.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(publishes.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")
app.include_router(internal.router)
