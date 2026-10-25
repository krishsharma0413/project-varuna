"""Private admin API: the log viewer and the reel records page. Only accounts in `auth.admins`
(config.yaml) get past `admin_user`; everyone else gets a plain 404, so the endpoints don't advertise
themselves."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.api.deps import config_dep, limit_ip, session_email
from app.clients import JOBS, mongo
from app.config import Config, resolve_path
from app.log import log
from app.services import admin_records, logs_query
from app.services.admin_records import ReelBusy
from app.services.logs_query import LogFilter
from app.services.submissions import parse_reel_url

PRESETS = {"15m": 15, "30m": 30, "1h": 60, "6h": 360, "24h": 1440, "7d": 10080, "30d": 43200}
LEVELS = {"debug", "info", "error"}


async def admin_user(request: Request, config: Config = Depends(config_dep)) -> str:
    email = session_email(request, config)
    if not email or not config.is_admin(email):
        raise HTTPException(status_code=404, detail="Not Found")
    return email


router = APIRouter(prefix="/api/v1/admin", dependencies=[Depends(limit_ip("read")), Depends(admin_user)])


def _csv(value: str | None, allowed: set[str] | None = None) -> list[str]:
    items = [v.strip().lower() for v in (value or "").split(",") if v.strip()]
    return [v for v in items if allowed is None or v in allowed]


def _range(preset: str | None, since: datetime | None, until: datetime | None) -> tuple[datetime, datetime | None]:
    if since:
        return since, until
    minutes = PRESETS.get(preset or "30m", 30)
    return datetime.now(UTC) - timedelta(minutes=minutes), None


@router.get("/logs")
async def logs(
    trace_id: str | None = Query(None, max_length=64),
    reel: str | None = Query(None, max_length=300),
    preset: str | None = Query(None, max_length=8),
    since: datetime | None = None,
    until: datetime | None = None,
    levels: str | None = Query(None, max_length=40),
    sources: str | None = Query(None, max_length=80),
    q: str | None = Query(None, max_length=200),
    limit: int = Query(300, ge=1, le=1000),
    before: str | None = Query(None, max_length=40),
    config: Config = Depends(config_dep),
) -> Any:
    path = resolve_path(config.logging.sqlite_path)
    base = LogFilter(levels=_csv(levels, LEVELS), sources=_csv(sources), text=(q or "").strip())

    if trace_id and trace_id.strip():
        items = await asyncio.to_thread(logs_query.by_traces, path, [trace_id.strip()], base)
        return {"mode": "trace", "items": items, "trace_ids": [trace_id.strip()], "next_before": None}

    if reel and reel.strip():
        reel_id = parse_reel_url(reel) or reel.strip()
        jobs = await mongo()[JOBS].find({"reel_id": reel_id}, {"trace_id": 1, "created_at": 1}).to_list(None)
        jobs.sort(key=lambda j: j["created_at"], reverse=True)
        from_jobs = [j["trace_id"] for j in jobs if j.get("trace_id")]
        from_logs = await asyncio.to_thread(logs_query.traces_mentioning, path, reel_id)
        trace_ids = list(dict.fromkeys([*from_jobs, *from_logs]))
        items = await asyncio.to_thread(logs_query.by_traces, path, trace_ids, base)
        return {"mode": "reel", "reel_id": reel_id, "items": items, "trace_ids": trace_ids, "next_before": None}

    start, end = _range(preset, since, until)
    window = LogFilter(levels=base.levels, sources=base.sources, text=base.text, since=start, until=end)
    page = await asyncio.to_thread(logs_query.by_range, path, window, limit, before)
    return {"mode": "range", **page, "trace_ids": [], "since": start, "until": end}


@router.get("/business-critical")
async def business_critical(
    preset: str | None = Query(None, max_length=8),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(300, ge=1, le=1000),
    config: Config = Depends(config_dep),
) -> Any:
    start, end = _range(preset, since, until)
    items = await asyncio.to_thread(
        logs_query.business_critical, resolve_path(config.logging.sqlite_path), start, end, limit
    )
    return {"items": items, "since": start, "until": end}


@router.get("/reels")
async def reel_records(
    q: str | None = Query(None, max_length=300),
    limit: int = Query(100, ge=1, le=500),
) -> Any:
    reel_id = parse_reel_url(q) if q else None
    return await admin_records.list_reels(reel_id or q, limit)


@router.get("/reels/{reel_id}")
async def reel_record(reel_id: str = Path(max_length=40)) -> Any:
    found = await admin_records.detail(reel_id)
    if found is None:
        raise HTTPException(status_code=404, detail="No record for this reel.")
    return found


@router.delete("/reels/{reel_id}")
async def delete_reel_record(reel_id: str = Path(max_length=40)) -> Any:
    try:
        changes = await admin_records.delete_reel(reel_id)
    except ReelBusy:
        detail = "A check is running for this reel. Try again when it ends."
        raise HTTPException(status_code=409, detail=detail) from None
    if changes is None:
        raise HTTPException(status_code=404, detail="No record for this reel.")
    log.info("admin deleted reel record", reel_id=reel_id, claims_deleted=len(changes["delete_claims"]),
             claims_expired=len(changes["expire_shared_claims"]), creator=changes["creator"] or "-")
    return changes
