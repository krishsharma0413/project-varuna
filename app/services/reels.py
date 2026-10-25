"""Reads and writes for reels, creators and claims.

One document per reel (`_id` = shortcode) holds the current result plus a `history` array.
When a result expires, the next check moves it into history and the new result takes its place;
nothing is deleted.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.clients import CLAIMS, CREATORS, REELS, mongo
from app.config import Config
from app.models import CheckResult
from app.services.history import archive_entry, creator_delta, history_push

CARD_PROJECTION = {
    "_id": 1,
    "permalink": 1,
    "creator_handle": 1,
    "duration_s": 1,
    "topic_tags": 1,
    "request_count": 1,
    "last_checked_at": 1,
    "current.summary": 1,
    "current.checked_at": 1,
    "current.expires_at": 1,
}


def _now() -> datetime:
    return datetime.now(UTC)


def card(doc: dict[str, Any]) -> dict[str, Any]:
    current = doc.get("current") or {}
    expires_at = current.get("expires_at")
    return {
        "reel_id": doc["_id"],
        "permalink": doc.get("permalink"),
        "creator_handle": doc.get("creator_handle"),
        "duration_s": doc.get("duration_s"),
        "topic_tags": doc.get("topic_tags", []),
        "request_count": doc.get("request_count", 0),
        "checked_at": current.get("checked_at"),
        "expires_at": expires_at,
        "stale": bool(expires_at and expires_at <= _now()),
        "summary": current.get("summary"),
    }


async def list_reels(
    *, topic: str | None, q: str | None, creator: str | None, before: datetime | None, limit: int
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"current": {"$ne": None}}
    if topic:
        query["topic_tags"] = topic
    if creator:
        query["creator_handle"] = creator.lower().lstrip("@")
    if before:
        query["last_checked_at"] = {"$lt": before}
    if q:
        pattern = {"$regex": re.escape(q.strip().lstrip("@")), "$options": "i"}
        query["$or"] = [{"_id": pattern}, {"creator_handle": pattern}, {"current.claims.text": pattern}]
    cursor = mongo()[REELS].find(query, CARD_PROJECTION).sort("last_checked_at", -1).limit(limit)
    return [card(d) for d in await cursor.to_list(length=None)]


async def get_reel(reel_id: str) -> dict[str, Any] | None:
    return await mongo()[REELS].find_one({"_id": reel_id})


def is_fresh(doc: dict[str, Any] | None) -> bool:
    current = (doc or {}).get("current")
    return bool(current and current.get("expires_at") and current["expires_at"] > _now())


async def count_request(reel_id: str, permalink: str) -> None:
    await mongo()[REELS].update_one(
        {"_id": reel_id},
        {
            "$inc": {"request_count": 1},
            "$setOnInsert": {"permalink": permalink, "first_seen": _now(), "current": None, "history": []},
        },
        upsert=True,
    )


async def store_result(
    reel_id: str,
    *,
    permalink: str,
    creator_handle: str,
    caption: str,
    duration_s: float | None,
    result: CheckResult,
    config: Config,
) -> None:
    db = mongo()
    new = result.model_dump(mode="python")
    existing = await db[REELS].find_one({"_id": reel_id}, {"current": 1, "creator_handle": 1})
    old = (existing or {}).get("current")
    topic_tags = sorted({t for c in result.claims for t in c.topic_tags})
    update: dict[str, Any] = {
        "$set": {
            "permalink": permalink,
            "creator_handle": creator_handle,
            "caption": caption,
            "duration_s": duration_s,
            "topic_tags": topic_tags,
            "current": new,
            "last_checked_at": result.checked_at,
        },
        "$setOnInsert": {"first_seen": result.checked_at, "request_count": 0},
    }
    if old:
        update["$push"] = {
            "history": history_push(archive_entry(old, config.history.keep_raw_text), config.history.max_entries)
        }
    await db[REELS].update_one({"_id": reel_id}, update, upsert=True)

    if creator_handle:
        same_creator = (existing or {}).get("creator_handle") == creator_handle
        delta = creator_delta(old if same_creator else None, new)
        await db[CREATORS].update_one(
            {"_id": creator_handle},
            {"$inc": delta, "$set": {"last_updated": result.checked_at}} if delta
            else {"$set": {"last_updated": result.checked_at}},
            upsert=True,
        )

    for claim in result.claims:
        await db[CLAIMS].update_one(
            {"_id": claim.claim_id},
            {
                "$set": {
                    "text": claim.text,
                    "type": claim.type,
                    "topic_tags": claim.topic_tags,
                    "latest": claim.model_dump(mode="python"),
                    "latest_checked_at": claim.checked_at,
                },
                "$addToSet": {"reel_ids": reel_id},
                "$setOnInsert": {"first_seen": claim.checked_at},
            },
            upsert=True,
        )


async def save_gate(reel_id: str, decision: dict[str, Any], topics_hash: str, *, caption: str,
                    creator_handle: str) -> None:
    """Remember the topic-check decision on the reel, so a rejected reel isn't re-checked for a while."""
    now = _now()
    await mongo()[REELS].update_one(
        {"_id": reel_id},
        {
            "$set": {"gate": {**decision, "topics_hash": topics_hash, "checked_at": now},
                     "caption": caption, "creator_handle": creator_handle},
            "$setOnInsert": {"first_seen": now, "current": None, "history": [], "request_count": 0},
        },
        upsert=True,
    )


async def fresh_claim(claim_id: str) -> dict[str, Any] | None:
    doc = await mongo()[CLAIMS].find_one({"_id": claim_id}, {"latest": 1})
    latest = (doc or {}).get("latest")
    if latest and latest.get("expires_at") and latest["expires_at"] > _now():
        return latest
    return None


async def save_embedding(claim_id: str, embedding: list[float]) -> None:
    await mongo()[CLAIMS].update_one({"_id": claim_id}, {"$set": {"embedding": embedding}})


async def get_claim(claim_id: str) -> dict[str, Any] | None:
    return await mongo()[CLAIMS].find_one({"_id": claim_id}, {"embedding": 0})


async def leaderboard(limit: int, config: Config) -> list[dict[str, Any]]:
    cursor = mongo()[CREATORS].find({}).sort("claims_checked", -1).limit(limit)
    return [creator_view(d, config) for d in await cursor.to_list(length=None)]


async def get_creator(handle: str, config: Config) -> dict[str, Any] | None:
    doc = await mongo()[CREATORS].find_one({"_id": handle.lower().lstrip("@")})
    return creator_view(doc, config) if doc else None


def creator_view(doc: dict[str, Any], config: Config) -> dict[str, Any]:
    claims_checked = doc.get("claims_checked", 0)
    return {
        "handle": doc["_id"],
        "reels_checked": doc.get("reels_checked", 0),
        "claims_checked": claims_checked,
        "counts": doc.get("counts", {}),
        "record_visible": claims_checked >= config.creators.min_sample,
        "min_sample": config.creators.min_sample,
        "last_updated": doc.get("last_updated"),
    }


async def topic_counts() -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    cursor = mongo()[REELS].find({"current": {"$ne": None}}, {"topic_tags": 1})
    for doc in await cursor.to_list(length=None):
        for tag in doc.get("topic_tags", []):
            counts[tag] = counts.get(tag, 0) + 1
    return [{"topic": t, "reels": n} for t, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]


async def search_creators(prefix: str, limit: int) -> list[dict[str, Any]]:
    pattern = {"$regex": "^" + re.escape(prefix.lower().lstrip("@"))}
    cursor = mongo()[CREATORS].find({"_id": pattern}, {"_id": 1, "claims_checked": 1}).limit(limit)
    return [{"handle": d["_id"], "claims_checked": d.get("claims_checked", 0)} for d in await cursor.to_list(None)]
