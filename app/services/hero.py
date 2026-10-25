"""Hero section: the claim checked by the most unique people, across distinct reels, recently.

Ranks by unique requesters, then distinct reels, so repeated requests from one person can't push a
claim to the top. Falls back to the latest checked reel when nothing was requested in the window.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.clients import REELS, REQUESTS, mongo
from app.config import Config


async def compute_hero(config: Config) -> dict[str, Any] | None:
    db = mongo()
    window_hours = config.hero.window_hours
    since = datetime.now(UTC) - timedelta(hours=window_hours)
    requests = await db[REQUESTS].find({"created_at": {"$gte": since}}, {"_id": 0}).to_list(length=None)

    by_reel: dict[str, dict[str, Any]] = {}
    for r in requests:
        entry = by_reel.setdefault(r["reel_id"], {"requesters": set(), "count": 0, "last": r["created_at"]})
        entry["requesters"].add(r["requester"])
        entry["count"] += 1
        entry["last"] = max(entry["last"], r["created_at"])

    reels = []
    if by_reel:
        reels = await db[REELS].find(
            {"_id": {"$in": list(by_reel)}, "current": {"$ne": None}},
            {"current.claims": 1, "current.checked_at": 1},
        ).to_list(length=None)

    claims: dict[str, dict[str, Any]] = {}
    for reel in reels:
        stats = by_reel[reel["_id"]]
        for claim in reel["current"]["claims"]:
            agg = claims.setdefault(
                claim["claim_id"],
                {"claim": claim, "reel_id": reel["_id"], "requesters": set(), "reels": set(), "checks": 0},
            )
            agg["requesters"] |= stats["requesters"]
            agg["reels"].add(reel["_id"])
            agg["checks"] += stats["count"]
            if claim["checked_at"] > agg["claim"]["checked_at"]:
                agg["claim"], agg["reel_id"] = claim, reel["_id"]

    if claims:
        best = max(claims.values(), key=lambda a: (len(a["requesters"]), len(a["reels"]), a["checks"]))
        return {
            "claim": best["claim"],
            "reel_id": best["reel_id"],
            "checks": best["checks"],
            "unique_people": len(best["requesters"]),
            "distinct_reels": len(best["reels"]),
            "last_checked_at": best["claim"]["checked_at"],
            "window_hours": window_hours,
            "fallback": False,
        }

    latest = await db[REELS].find_one(
        {"current": {"$ne": None}}, {"current": 1, "request_count": 1}, sort=[("last_checked_at", -1)]
    )
    if not latest or not latest["current"].get("claims"):
        return None
    summary = latest["current"].get("summary") or {}
    claim = next(
        (c for c in latest["current"]["claims"] if c["text"] == summary.get("claim_text")),
        latest["current"]["claims"][0],
    )
    return {
        "claim": claim,
        "reel_id": latest["_id"],
        "checks": latest.get("request_count", 0),
        "unique_people": None,
        "distinct_reels": 1,
        "last_checked_at": latest["current"]["checked_at"],
        "window_hours": None,
        "fallback": True,
    }
