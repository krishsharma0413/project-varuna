"""Public read endpoints. Everything here is open to anyone; results are cached in Redis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import config_dep, limit_ip
from app.cache import cached
from app.clients import mongo, queue_redis
from app.config import Config
from app.log import log
from app.pipeline.ranking import load_rankings
from app.services import reels
from app.services import transparency as transparency_service
from app.services.hero import compute_hero
from app.services.submissions import parse_reel_url

router = APIRouter(prefix="/api/v1")
read_limit = Depends(limit_ip("read"))


@router.get("/health")
async def health() -> dict[str, Any]:
    # Public endpoint: error details (hostnames, connection strings) go to the log, not the response.
    checks: dict[str, str] = {}
    try:
        await queue_redis().ping()
        checks["redis_queue"] = "ok"
    except Exception as exc:
        log.exception("health check: redis queue unavailable", exc)
        checks["redis_queue"] = "error"
    try:
        await mongo().client.admin.command("ping")
        checks["mongo"] = "ok"
    except Exception as exc:
        log.exception("health check: mongo unavailable", exc)
        checks["mongo"] = "error"
    return {"status": "ok" if all(v == "ok" for v in checks.values()) else "degraded", "checks": checks}


@router.get("/config/public", dependencies=[read_limit])
async def public_config(config: Config = Depends(config_dep)) -> dict[str, Any]:
    return {
        "google_client_id": config.auth.google.client_id,
        "hero_window_hours": config.hero.window_hours,
        "min_creator_sample": config.creators.min_sample,
        "max_video_seconds": config.pipeline.max_video_seconds,
        "submit_limits": config.rate_limits.submit,
        "min_independent_sources": config.verification.min_independent_sources,
        "topics": config.topics if config.topic_gate.enabled else [],
    }


@router.get("/hero", dependencies=[read_limit])
async def hero(config: Config = Depends(config_dep)) -> Any:
    return await cached("hero", config.cache.hero_ttl_seconds, lambda: compute_hero(config))


@router.get("/reels", dependencies=[read_limit])
async def list_reels(
    topic: str | None = Query(None, max_length=80),
    q: str | None = Query(None, max_length=200),
    creator: str | None = Query(None, max_length=60),
    before: datetime | None = None,
    limit: int = Query(24, ge=1, le=48),
    config: Config = Depends(config_dep),
) -> Any:
    key = f"reels:{topic}:{q}:{creator}:{before.isoformat() if before else ''}:{limit}"

    async def produce() -> dict[str, Any]:
        items = await reels.list_reels(topic=topic, q=q, creator=creator, before=before, limit=limit)
        next_before = items[-1]["checked_at"] if len(items) == limit else None
        return {"items": items, "next_before": next_before}

    return await cached(key, config.cache.ttl_seconds, produce)


@router.get("/reels/{reel_id}", dependencies=[read_limit])
async def get_reel(reel_id: str, config: Config = Depends(config_dep)) -> Any:
    async def produce() -> dict[str, Any] | None:
        doc = await reels.get_reel(reel_id)
        if not doc or not doc.get("current"):
            return None
        current = doc["current"]
        return {
            "reel_id": doc["_id"],
            "permalink": doc.get("permalink"),
            "creator_handle": doc.get("creator_handle"),
            "caption": doc.get("caption", ""),
            "duration_s": doc.get("duration_s"),
            "topic_tags": doc.get("topic_tags", []),
            "request_count": doc.get("request_count", 0),
            "first_seen": doc.get("first_seen"),
            "stale": current["expires_at"] <= datetime.now(UTC),
            "current": current,
            "history": list(reversed(doc.get("history", []))),
        }

    result = await cached(f"reel:{reel_id}", config.cache.ttl_seconds, produce)
    if result is None:
        raise HTTPException(status_code=404, detail="No check exists for this reel yet.")
    return result


@router.get("/claims/{claim_id}", dependencies=[read_limit])
async def get_claim(claim_id: str, config: Config = Depends(config_dep)) -> Any:
    async def produce() -> dict[str, Any] | None:
        doc = await reels.get_claim(claim_id)
        if not doc:
            return None
        doc["claim_id"] = doc.pop("_id")
        return doc

    result = await cached(f"claim:{claim_id}", config.cache.ttl_seconds, produce)
    if result is None:
        raise HTTPException(status_code=404, detail="Claim not found.")
    return result


@router.get("/creators", dependencies=[read_limit])
async def creators(limit: int = Query(50, ge=1, le=100), config: Config = Depends(config_dep)) -> Any:
    return await cached(
        f"creators:{limit}", config.cache.ttl_seconds, lambda: _leaderboard(limit, config)
    )


async def _leaderboard(limit: int, config: Config) -> dict[str, Any]:
    return {"items": await reels.leaderboard(limit, config), "min_sample": config.creators.min_sample}


@router.get("/creators/{handle}", dependencies=[read_limit])
async def creator(handle: str, config: Config = Depends(config_dep)) -> Any:
    async def produce() -> dict[str, Any] | None:
        profile = await reels.get_creator(handle, config)
        if not profile:
            return None
        items = await reels.list_reels(topic=None, q=None, creator=handle, before=None, limit=48)
        return {"creator": profile, "reels": items}

    result = await cached(f"creator:{handle.lower()}", config.cache.ttl_seconds, produce)
    if result is None:
        raise HTTPException(status_code=404, detail="No checked reels from this creator yet.")
    return result


@router.get("/topics", dependencies=[read_limit])
async def topics(config: Config = Depends(config_dep)) -> Any:
    return await cached("topics", config.cache.ttl_seconds, _topics)


async def _topics() -> dict[str, Any]:
    return {"items": await reels.topic_counts()}


@router.get("/search", dependencies=[Depends(limit_ip("search"))])
async def search(q: str = Query(..., min_length=1, max_length=200), config: Config = Depends(config_dep)) -> Any:
    reel_id = parse_reel_url(q)
    if reel_id:
        doc = await reels.get_reel(reel_id)
        found = doc is not None and bool(doc.get("current"))
        return {"reel_id": reel_id if found else None, "unchecked_reel_id": None if found else reel_id,
                "reels": [], "creators": []}
    creators = await reels.search_creators(q, 10) if q.startswith("@") else []
    items = await reels.list_reels(topic=None, q=q, creator=None, before=None, limit=24)
    return {"reel_id": None, "unchecked_reel_id": None, "reels": items, "creators": creators}


@router.get("/sources", dependencies=[read_limit])
async def sources() -> Any:
    return load_rankings()


@router.get("/transparency", dependencies=[read_limit])
async def transparency(config: Config = Depends(config_dep)) -> Any:
    """Models, settings and prompts in use right now, straight from config.yaml (not cached)."""
    return transparency_service.build(config)
