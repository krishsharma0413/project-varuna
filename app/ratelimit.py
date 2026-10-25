"""Fixed-window rate limits stored in the queue Redis (keys expire with their window).

Rules come from config.yaml on every request ("5/hour", "120/minute"), so editing the file changes
limits immediately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from redis.asyncio import Redis

UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


@dataclass(frozen=True)
class Rule:
    limit: int
    window: int


def parse_rule(rule: str) -> Rule:
    count, _, unit = rule.strip().partition("/")
    unit = unit.strip().lower().rstrip("s")
    if unit not in UNITS or not count.strip().isdigit():
        raise ValueError(f"invalid rate limit rule {rule!r}; use e.g. '5/hour'")
    return Rule(limit=int(count), window=UNITS[unit])


async def hit(redis: Redis, bucket: str, identity: str, rules: list[str]) -> int:
    """Count one request. Returns 0 if allowed, otherwise the seconds until the client may retry."""
    parsed = [parse_rule(r) for r in rules]
    if not parsed:
        return 0
    now = time.time()
    async with redis.pipeline(transaction=False) as pipe:
        for rule in parsed:
            key = f"rl:{bucket}:{rule.window}:{identity}:{int(now // rule.window)}"
            pipe.incr(key)
            pipe.expire(key, rule.window + 1)
        results = await pipe.execute()
    retry_after = 0
    for index, rule in enumerate(parsed):
        if results[index * 2] > rule.limit:
            retry_after = max(retry_after, int(rule.window - (now % rule.window)) + 1)
    return retry_after
