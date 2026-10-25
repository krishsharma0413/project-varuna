"""Log service: moves events from Redis lists into SQLite.

Run with `python -m app.logsvc.main`. Other services never talk to this one directly; they push
events onto Redis lists and carry on, so this service being down never disrupts them.

Tables:
- website_logs       every log line (trace_id, timestamp, log_level, message)
- business_critical  moments a search engine started failing or recovered
                     (timestamp, trace_id, search_engine, event, detail)
"""

from __future__ import annotations

import json
import signal
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import redis

from app.config import LoggingSection, get_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS website_logs (
    trace_id  TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    log_level TEXT NOT NULL,
    message   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS business_critical (
    timestamp     TEXT NOT NULL,
    trace_id      TEXT NOT NULL,
    search_engine TEXT NOT NULL,
    event         TEXT NOT NULL,
    detail        TEXT NOT NULL
);
-- For the admin log viewer (lookups by time range and by trace ID). Local disk, not Atlas.
CREATE INDEX IF NOT EXISTS website_logs_timestamp ON website_logs (timestamp);
CREATE INDEX IF NOT EXISTS website_logs_trace_id ON website_logs (trace_id);
CREATE INDEX IF NOT EXISTS business_critical_timestamp ON business_critical (timestamp);
"""

_running = True


def _stop(*_: object) -> None:
    global _running
    _running = False


@dataclass(frozen=True)
class Stream:
    key: Callable[[LoggingSection], str]
    table: str
    columns: tuple[str, ...]


STREAMS = (
    Stream(lambda s: s.queue_key, "website_logs", ("trace_id", "timestamp", "log_level", "message")),
    Stream(lambda s: s.business_critical_key, "business_critical",
           ("timestamp", "trace_id", "search_engine", "event", "detail")),
)


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.executescript(SCHEMA)
    db.commit()
    return db


def rows(raw_events: list[str], columns: tuple[str, ...]) -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    for raw in raw_events:
        try:
            event = json.loads(raw)
            out.append(tuple(str(event.get(c, "")) for c in columns))
        except (ValueError, TypeError, AttributeError):
            fallback = {"trace_id": "-", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "log_level": "error",
                        "message": f"[logsvc] unreadable event: {raw[:500]}", "search_engine": "-",
                        "event": "unreadable", "detail": raw[:500]}
            out.append(tuple(fallback[c] for c in columns))
    return out


def move(client: redis.Redis, db: sqlite3.Connection, stream: Stream, settings: LoggingSection) -> int:
    key = stream.key(settings)
    batch = client.lpop(key, settings.batch_size)
    if not batch:
        return 0
    placeholders = ", ".join("?" for _ in stream.columns)
    try:
        db.executemany(
            f"INSERT INTO {stream.table} ({', '.join(stream.columns)}) VALUES ({placeholders})",
            rows(batch, stream.columns),
        )
        db.commit()
    except sqlite3.Error as exc:
        print(f"sqlite write to {stream.table} failed, returning {len(batch)} events: {exc}", flush=True)
        try:
            client.lpush(key, *reversed(batch))
        except redis.RedisError:
            pass
        time.sleep(2)
        return 0
    return len(batch)


def main() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    config = get_config()
    client = redis.Redis.from_url(config.redis.queue_url, decode_responses=True, socket_timeout=10)
    db = connect(config.logging.sqlite_path)
    print(f"log service writing to {config.logging.sqlite_path}", flush=True)
    while _running:
        settings = get_config().logging
        try:
            moved = sum(move(client, db, stream, settings) for stream in STREAMS)
        except redis.RedisError as exc:
            print(f"redis unavailable: {exc}", flush=True)
            time.sleep(2)
            continue
        if not moved:
            time.sleep(0.5)
    db.close()


if __name__ == "__main__":
    main()
