"""Submitting a reel: fresh-result check, per-reel lock, daily budget, enqueue."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from app.clients import JOBS, REQUESTS, mongo, queue_redis
from app.config import Config
from app.locks import acquire, owner, release
from app.log import log
from app.pipeline.topic_gate import is_remembered_rejection
from app.queue import enqueue
from app.services import reels
from app.trace import trace_id_var

REEL_URL = re.compile(
    r"^(?:https?://)?(?:www\.|m\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:reels?|p|tv)/([A-Za-z0-9_-]{5,40})",
    re.IGNORECASE,
)


class BudgetExceeded(Exception):
    pass


def parse_reel_url(value: str) -> str | None:
    match = REEL_URL.match(value.strip())
    return match.group(1) if match else None


def permalink(reel_id: str) -> str:
    return f"https://www.instagram.com/reel/{reel_id}/"


def requester_key(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


async def _record_request(reel_id: str, email: str) -> None:
    await mongo()[REQUESTS].insert_one(
        {"reel_id": reel_id, "requester": requester_key(email), "source": "web", "created_at": datetime.now(UTC)}
    )
    await reels.count_request(reel_id, permalink(reel_id))


async def _take_budget(config: Config) -> str:
    key = f"budget:checks:{datetime.now(UTC):%Y-%m-%d}"
    redis = queue_redis()
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, 2 * 86400)
    if used > config.budget.daily_check_cap:
        await redis.decr(key)
        raise BudgetExceeded
    return key


async def refund_budget(key: str | None) -> None:
    """Give a daily-budget slot back (used when the topic check rejects a reel)."""
    if not key:
        return
    try:
        if int(await queue_redis().get(key) or 0) > 0:
            await queue_redis().decr(key)
    except Exception as exc:
        log.exception("budget refund failed", exc)


async def submit(reel_id: str, email: str, config: Config) -> dict[str, Any]:
    db, redis = mongo(), queue_redis()
    existing = await reels.get_reel(reel_id)
    if reels.is_fresh(existing):
        await _record_request(reel_id, email)
        return {"status": "done", "reel_id": reel_id, "job_id": None}
    gate = (existing or {}).get("gate")
    if is_remembered_rejection(gate, config, datetime.now(UTC)):
        log.info("reel already rejected by the topic check", reel_id=reel_id)
        return {"status": "rejected", "reel_id": reel_id, "job_id": None, "reason": gate.get("reason", "")}

    job_id = uuid.uuid4().hex
    if not await acquire(redis, reel_id, job_id, config.pipeline.lock_ttl_seconds):
        running = await owner(redis, reel_id)
        if running:
            await db[JOBS].update_one({"_id": running}, {"$addToSet": {"requesters": email.lower()}})
            await _record_request(reel_id, email)
            job = await db[JOBS].find_one({"_id": running}, {"status": 1})
            log.info("joined running job", reel_id=reel_id, job_id=running)
            return {"status": (job or {}).get("status", "queued"), "reel_id": reel_id, "job_id": running}
        # The lock expired between our two calls; take it now.
        if not await acquire(redis, reel_id, job_id, config.pipeline.lock_ttl_seconds):
            raise RuntimeError("Could not lock the reel, please retry.")

    try:
        budget_key = await _take_budget(config)
    except BudgetExceeded:
        await release(redis, reel_id, job_id)
        raise

    now = datetime.now(UTC)
    trace_id = trace_id_var.get()
    await db[JOBS].insert_one(
        {
            "_id": job_id,
            "reel_id": reel_id,
            "url": permalink(reel_id),
            "status": "queued",
            "step": "queued",
            "error": None,
            "requesters": [email.lower()],
            "trace_id": trace_id,
            "attempts": 0,
            "created_at": now,
            "updated_at": now,
            "finished_at": None,
        }
    )
    await _record_request(reel_id, email)
    await enqueue(redis, {"job_id": job_id, "reel_id": reel_id, "trace_id": trace_id, "attempt": 0,
                          "budget_key": budget_key})
    log.info("job queued", reel_id=reel_id, job_id=job_id)
    return {"status": "queued", "reel_id": reel_id, "job_id": job_id}


async def get_job(job_id: str) -> dict[str, Any] | None:
    job = await mongo()[JOBS].find_one({"_id": job_id}, {"requesters": 0, "trace_id": 0})
    if not job:
        return None
    return {
        "job_id": job["_id"],
        "reel_id": job["reel_id"],
        "status": job["status"],
        "step": job.get("step"),
        "error": job.get("error"),
        "attempts": job.get("attempts", 0),
        "created_at": job["created_at"],
        "updated_at": job.get("updated_at"),
        "finished_at": job.get("finished_at"),
    }
