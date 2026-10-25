"""Per-reel lock so many requests for one reel start a single pipeline run.

The lock value is the job id that owns it; release and extend only act if that is still the owner.
"""

from __future__ import annotations

from redis.asyncio import Redis

RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end
return 0
"""
EXTEND = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) end
return 0
"""


def lock_key(reel_id: str) -> str:
    return f"lock:reel:{reel_id}"


async def acquire(redis: Redis, reel_id: str, job_id: str, ttl: int) -> bool:
    return bool(await redis.set(lock_key(reel_id), job_id, nx=True, ex=ttl))


async def owner(redis: Redis, reel_id: str) -> str | None:
    return await redis.get(lock_key(reel_id))


async def release(redis: Redis, reel_id: str, job_id: str) -> None:
    await redis.eval(RELEASE, 1, lock_key(reel_id), job_id)


async def extend(redis: Redis, reel_id: str, job_id: str, ttl: int) -> None:
    await redis.eval(EXTEND, 1, lock_key(reel_id), job_id, ttl)
