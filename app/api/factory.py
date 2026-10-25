"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import routes_admin, routes_auth, routes_public, routes_submit
from app.api.middleware import TraceMiddleware
from app.clients import close_clients, queue_redis
from app.config import get_config
from app.log import log


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    get_config()  # fail fast on a missing or invalid config.yaml
    log.configure("api")
    log.start(queue_redis())
    log.info("api started")
    yield
    log.info("api stopping")
    await log.stop()
    await close_clients()


def create_app() -> FastAPI:
    app = FastAPI(
        title="varuna fact checker API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(TraceMiddleware)
    app.include_router(routes_public.router)
    app.include_router(routes_auth.router)
    app.include_router(routes_submit.router)
    app.include_router(routes_admin.router)
    return app
