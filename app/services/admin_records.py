"""Admin view of stored reel records, and deleting one so the reel can be checked again from scratch.

Deleting a reel removes its document (current result, history, topic-check decision) and undoes what that
result added elsewhere, so a re-run starts clean and isn't double-counted:
- the creator's counters lose the current result's verdicts (the creator is removed if nothing is left);
- claims only this reel made are deleted; claims other reels share lose this reel and have their cached
  verdict expired, so the re-run verifies them again instead of reusing the old verdict.
Jobs, requests and disputes stay (they age out through `retention`), and so do the logs.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.cache import invalidate
from app.clients import CLAIMS, CREATORS, DISPUTES, JOBS, REELS, REQUESTS, mongo, queue_redis
from app.locks import owner
from app.services.history import creator_delta

LIST_PROJECTION = {
    "_id": 1, "creator_handle": 1, "permalink": 1, "request_count": 1, "first_seen": 1, "last_checked_at": 1,
    "gate": 1, "current.summary": 1, "current.checked_at": 1, "current.expires_at": 1,
    "current.claims.claim_id": 1, "history.checked_at": 1,
}


class ReelBusy(Exception):
    """A pipeline run holds the reel's lock."""


def _last_activity(doc: dict[str, Any]) -> datetime | None:
    times = [doc.get("last_checked_at"), (doc.get("gate") or {}).get("checked_at"), doc.get("first_seen")]
    present = [t for t in times if t]
    return max(present) if present else None


def row(doc: dict[str, Any], now: datetime) -> dict[str, Any]:
    current = doc.get("current") or {}
    gate = doc.get("gate") or {}
    expires_at = current.get("expires_at")
    if current:
        state = "stale" if expires_at and expires_at <= now else "checked"
    elif gate and not gate.get("relevant", True):
        state = "rejected"
    else:
        state = "empty"
    return {
        "reel_id": doc["_id"],
        "creator_handle": doc.get("creator_handle") or "",
        "permalink": doc.get("permalink"),
        "state": state,
        "summary": current.get("summary"),
        "claim_count": len(current.get("claims") or []),
        "history_count": len(doc.get("history") or []),
        "request_count": doc.get("request_count", 0),
        "checked_at": current.get("checked_at"),
        "expires_at": expires_at,
        "gate_reason": gate.get("reason") if state == "rejected" else None,
        "last_activity": _last_activity(doc),
    }


async def list_reels(q: str | None, limit: int) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if q and q.strip():
        pattern = {"$regex": re.escape(q.strip().lstrip("@")), "$options": "i"}
        query["$or"] = [{"_id": pattern}, {"creator_handle": pattern}]
    docs = await mongo()[REELS].find(query, LIST_PROJECTION).to_list(None)
    now = datetime.now(UTC)
    rows = [row(d, now) for d in docs]
    rows.sort(key=lambda r: r["last_activity"] or datetime.min.replace(tzinfo=UTC), reverse=True)
    return {"items": rows[:limit], "total": len(rows)}


def plan(reel: dict[str, Any], claims: list[dict[str, Any]]) -> dict[str, Any]:
    """What deleting `reel` changes. `claims` are the claim documents that list this reel."""
    reel_id = reel["_id"]
    current = reel.get("current")
    delete_claims = [c["_id"] for c in claims if set(c.get("reel_ids") or []) <= {reel_id}]
    shared_claims = [c["_id"] for c in claims if c["_id"] not in delete_claims]
    creator_inc = {k: -v for k, v in creator_delta(None, current).items()} if current else {}
    return {
        "reel_id": reel_id,
        "history_entries": len(reel.get("history") or []),
        "delete_claims": delete_claims,
        "expire_shared_claims": shared_claims,
        "creator": (reel.get("creator_handle") or None) if creator_inc else None,
        "creator_inc": creator_inc,
    }


async def _claims_for(reel_id: str) -> list[dict[str, Any]]:
    return await mongo()[CLAIMS].find({"reel_ids": reel_id}, {"_id": 1, "reel_ids": 1, "text": 1}).to_list(None)


async def detail(reel_id: str) -> dict[str, Any] | None:
    db = mongo()
    reel = await db[REELS].find_one({"_id": reel_id})
    if not reel:
        return None
    claims = await _claims_for(reel_id)
    jobs = await db[JOBS].find(
        {"reel_id": reel_id}, {"status": 1, "step": 1, "error": 1, "trace_id": 1, "created_at": 1, "finished_at": 1}
    ).to_list(None)
    jobs.sort(key=lambda j: j["created_at"], reverse=True)
    return {
        "record": reel,
        "jobs": [{"job_id": j.pop("_id"), **j} for j in jobs],
        "claims": [{"claim_id": c["_id"], "text": c.get("text", ""), "reels": len(c.get("reel_ids") or [])}
                   for c in claims],
        "requests": await db[REQUESTS].count_documents({"reel_id": reel_id}),
        "disputes": await db[DISPUTES].count_documents({"reel_id": reel_id}),
        "running_job": await owner(queue_redis(), reel_id),
        "plan": plan(reel, claims),
    }


async def delete_reel(reel_id: str) -> dict[str, Any] | None:
    db = mongo()
    if await owner(queue_redis(), reel_id):
        raise ReelBusy
    reel = await db[REELS].find_one({"_id": reel_id})
    if not reel:
        return None
    changes = plan(reel, await _claims_for(reel_id))

    await db[REELS].delete_one({"_id": reel_id})
    if changes["delete_claims"]:
        await db[CLAIMS].delete_many({"_id": {"$in": changes["delete_claims"]}})
    if changes["expire_shared_claims"]:
        await db[CLAIMS].update_many(
            {"_id": {"$in": changes["expire_shared_claims"]}},
            {"$pull": {"reel_ids": reel_id}, "$set": {"latest.expires_at": datetime.now(UTC)}},
        )
    creator = changes["creator"]
    if creator:
        await db[CREATORS].update_one({"_id": creator}, {"$inc": changes["creator_inc"]})
        await db[CREATORS].delete_one({"_id": creator, "claims_checked": {"$lte": 0}, "reels_checked": {"$lte": 0}})
    await invalidate()
    return changes
