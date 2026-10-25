"""Pure helpers for results, history and counters (no I/O, unit-tested)."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.models import SEVERITY, VERDICTS, ClaimResult, Summary


def summarize(claims: list[ClaimResult]) -> Summary | None:
    if not claims:
        return None
    counts = Counter(c.verdict for c in claims)
    top = next(v for v in SEVERITY if counts.get(v))
    headline = next(c for c in claims if c.verdict == top)
    return Summary(
        verdict=top,
        claim_text=headline.text,
        counts={v: counts.get(v, 0) for v in VERDICTS},
        claim_count=len(claims),
    )


def verdict_counts(result: dict[str, Any] | None) -> Counter[str]:
    if not result:
        return Counter()
    return Counter(c["verdict"] for c in result.get("claims", []))


def archive_entry(result: dict[str, Any], keep_raw_text: bool) -> dict[str, Any]:
    """The copy of an expired/replaced result that goes into the reel's history array."""
    entry = dict(result)
    if not keep_raw_text and isinstance(entry.get("extraction"), dict):
        extraction = dict(entry["extraction"])
        for key in ("transcript", "ocr_text", "caption"):
            extraction.pop(key, None)
        entry["extraction"] = extraction
    return entry


def history_push(entry: dict[str, Any], max_entries: int) -> dict[str, Any]:
    """$push spec that appends to history, keeping only the newest `max_entries` (0 = unlimited)."""
    spec: dict[str, Any] = {"$each": [entry]}
    if max_entries > 0:
        spec["$slice"] = -max_entries
    return spec


def creator_delta(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, int]:
    """$inc document for a creator when `new` replaces `old` as a reel's current result."""
    before, after = verdict_counts(old), verdict_counts(new)
    inc = {f"counts.{v}": after.get(v, 0) - before.get(v, 0) for v in VERDICTS}
    inc["claims_checked"] = sum(after.values()) - sum(before.values())
    inc["reels_checked"] = 0 if old else 1
    return {k: v for k, v in inc.items() if v}
