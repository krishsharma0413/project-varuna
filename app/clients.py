"""Shared Redis and MongoDB clients, opened lazily from config.yaml.

Two Redis instances: `queue_redis` (job queue, locks, rate limits, budget, log events; never
evicts) and `cache_redis` (read cache; 200 MB with least-recently-used eviction).
"""

from __future__ import annotations

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.config import get_config

_queue: Redis | None = None
_cache: Redis | None = None
_mongo: AsyncMongoClient | None = None


def _redis(url: str) -> Redis:
    return Redis.from_url(
        url,
        decode_responses=True,
        socket_timeout=10,
        socket_connect_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
    )


def queue_redis() -> Redis:
    global _queue
    if _queue is None:
        _queue = _redis(get_config().redis.queue_url)
    return _queue


def cache_redis() -> Redis:
    global _cache
    if _cache is None:
        _cache = _redis(get_config().redis.cache_url)
    return _cache


def mongo() -> AsyncDatabase:
    global _mongo
    config = get_config()
    if _mongo is None:
        _mongo = AsyncMongoClient(
            config.mongo.uri,
            tz_aware=True,
            serverSelectionTimeoutMS=10_000,
            appname="varuna",
        )
    return _mongo[config.mongo.database]


async def close_clients() -> None:
    global _queue, _cache, _mongo
    for client in (_queue, _cache):
        if client is not None:
            await client.aclose()
    if _mongo is not None:
        await _mongo.close()
    _queue = _cache = _mongo = None


# Collection names. No secondary indexes are created (free-tier storage); lookups by `_id`
# use MongoDB's built-in _id index, everything else scans and is cached in Redis.
REELS = "reels"            # _id = reel shortcode
CREATORS = "creators"      # _id = instagram handle (lowercase)
CLAIMS = "claims"          # _id = claim hash
JOBS = "jobs"              # _id = job id
REQUESTS = "requests"      # one row per submission, for unique-requester counts
DISPUTES = "disputes"
