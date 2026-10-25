"""Read-through cache on the cache Redis (evicting). A version number in the queue Redis
(never evicted) is bumped whenever results change, which invalidates every cached read at once."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.clients import cache_redis, queue_redis
from app.log import log

VERSION_KEY = "cache:version"


async def cached(key: str, ttl: int, producer: Callable[[], Awaitable[Any]]) -> Any:
    if ttl <= 0:
        return jsonable_encoder(await producer())
    try:
        version = await queue_redis().get(VERSION_KEY) or "0"
        full_key = f"c:{version}:{key}"
        hit = await cache_redis().get(full_key)
        if hit is not None:
            return json.loads(hit)
    except Exception as exc:
        log.exception("cache read failed", exc, key=key)
        return jsonable_encoder(await producer())
    value = jsonable_encoder(await producer())
    try:
        await cache_redis().set(full_key, json.dumps(value), ex=ttl)
    except Exception as exc:
        log.exception("cache write failed", exc, key=key)
    return value


async def invalidate() -> None:
    try:
        await queue_redis().incr(VERSION_KEY)
    except Exception as exc:
        log.exception("cache invalidation failed", exc)
