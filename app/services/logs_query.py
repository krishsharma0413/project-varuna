"""Read-only queries over the logs SQLite file (written by the log service, shared through a volume).

Three ways in:
- by trace ID: one journey, oldest first
- by reel ID: every journey that touched the reel (trace IDs from its jobs plus log lines naming it)
- by time range: newest first, paged with a `before` cursor
Level, source and text filters apply to all of them.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_JOURNEY_ROWS = 2000


def ts(value: datetime) -> str:
    """Same text format the logger writes, so string comparison matches time order."""
    return value.astimezone(UTC).isoformat(timespec="milliseconds")


@dataclass
class LogFilter:
    levels: list[str] = field(default_factory=list)   # empty = all
    sources: list[str] = field(default_factory=list)  # e.g. ["api", "worker"]; empty = all
    text: str = ""
    since: datetime | None = None
    until: datetime | None = None


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _where(f: LogFilter) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if f.levels:
        clauses.append(f"log_level IN ({', '.join('?' for _ in f.levels)})")
        params += f.levels
    if f.sources:
        clauses.append("(" + " OR ".join("message LIKE ? ESCAPE '\\'" for _ in f.sources) + ")")
        params += [f"[{_escape_like(s)}]%" for s in f.sources]
    if f.text:
        clauses.append("message LIKE ? ESCAPE '\\'")
        params.append(f"%{_escape_like(f.text)}%")
    if f.since:
        clauses.append("timestamp >= ?")
        params.append(ts(f.since))
    if f.until:
        clauses.append("timestamp <= ?")
        params.append(ts(f.until))
    return clauses, params


def _connect(path: Path) -> sqlite3.Connection | None:
    if not path.is_file():
        return None
    db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(r) for r in cursor.fetchall()]


def by_traces(path: Path, trace_ids: list[str], f: LogFilter) -> list[dict[str, Any]]:
    trace_ids = [t for t in dict.fromkeys(trace_ids) if t and t != "-"]
    db = _connect(path)
    if db is None or not trace_ids:
        return []
    clauses, params = _where(f)
    clauses.insert(0, f"trace_id IN ({', '.join('?' for _ in trace_ids)})")
    params = [*trace_ids, *params]
    try:
        sql = (f"SELECT trace_id, timestamp, log_level, message FROM website_logs WHERE {' AND '.join(clauses)} "
               f"ORDER BY timestamp ASC LIMIT {MAX_JOURNEY_ROWS}")
        return _rows(db.execute(sql, params))
    finally:
        db.close()


def traces_mentioning(path: Path, needle: str, limit: int = 200) -> list[str]:
    """Trace IDs of log lines that mention `needle` (e.g. a reel ID), most recent first."""
    db = _connect(path)
    if db is None or not needle:
        return []
    try:
        cursor = db.execute(
            "SELECT trace_id, MAX(timestamp) AS last FROM website_logs WHERE message LIKE ? ESCAPE '\\' "
            "AND trace_id != '-' GROUP BY trace_id ORDER BY last DESC LIMIT ?",
            (f"%{_escape_like(needle)}%", limit),
        )
        return [r["trace_id"] for r in cursor.fetchall()]
    finally:
        db.close()


def by_range(path: Path, f: LogFilter, limit: int, before: str | None) -> dict[str, Any]:
    db = _connect(path)
    if db is None:
        return {"items": [], "next_before": None}
    clauses, params = _where(f)
    if before:
        clauses.append("timestamp < ?")
        params.append(before)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        sql = (f"SELECT trace_id, timestamp, log_level, message FROM website_logs {where} "
               "ORDER BY timestamp DESC LIMIT ?")
        items = _rows(db.execute(sql, [*params, limit + 1]))
    finally:
        db.close()
    has_more = len(items) > limit
    items = items[:limit]
    return {"items": items, "next_before": items[-1]["timestamp"] if has_more and items else None}


def business_critical(path: Path, since: datetime | None, until: datetime | None, limit: int) -> list[dict[str, Any]]:
    db = _connect(path)
    if db is None:
        return []
    clauses: list[str] = []
    params: list[Any] = []
    if since:
        clauses.append("timestamp >= ?")
        params.append(ts(since))
    if until:
        clauses.append("timestamp <= ?")
        params.append(ts(until))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        sql = (f"SELECT timestamp, trace_id, search_engine, event, detail FROM business_critical {where} "
               "ORDER BY timestamp DESC LIMIT ?")
        return _rows(db.execute(sql, [*params, limit]))
    except sqlite3.OperationalError:
        return []  # table not created yet
    finally:
        db.close()
