"""Custom async logger.

Events are buffered in-process and a background task ships them to the log service through a
Redis list (no RPC or REST). Logging never blocks the caller and never raises: if Redis is down,
events are printed to stdout and dropped. Safe to call from worker threads.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
from collections import deque
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis

from app.config import LoggingSection, get_config
from app.trace import trace_id_var

LEVELS = {"debug": 10, "info": 20, "error": 40}
FLUSH_INTERVAL_SECONDS = 0.5


class Logger:
    def __init__(self) -> None:
        self.source = "app"
        self._buffer: deque[dict[str, str]] = deque(maxlen=20_000)
        self._critical: deque[dict[str, str]] = deque(maxlen=5_000)
        self._redis: Redis | None = None
        self._task: asyncio.Task[None] | None = None

    def configure(self, source: str) -> None:
        self.source = source

    def debug(self, message: str, **fields: Any) -> None:
        self._emit("debug", message, fields)

    def info(self, message: str, **fields: Any) -> None:
        self._emit("info", message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("error", message, fields)

    def exception(self, message: str, exc: BaseException, **fields: Any) -> None:
        self._emit("error", f"{message}: {type(exc).__name__}: {exc}", fields)

    def business_critical(self, search_engine: str, event: str, detail: str = "") -> None:
        """A row for the business_critical table (e.g. a search engine started failing or recovered).
        Never filtered by log level; also written to the normal log as an error."""
        self._critical.append(
            {
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "trace_id": trace_id_var.get(),
                "search_engine": search_engine,
                "event": event,
                "detail": detail[:1000],
            }
        )
        self._emit("error", f"BUSINESS CRITICAL: search engine {search_engine} {event}", {"detail": detail[:300]})

    def _emit(self, level: str, message: str, fields: dict[str, Any]) -> None:
        if fields:
            message = message + " " + " ".join(f"{key}={value}" for key, value in fields.items())
        self._buffer.append(
            {
                "trace_id": trace_id_var.get(),
                "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "log_level": level,
                "message": f"[{self.source}] {message}",
            }
        )

    def start(self, redis: Redis) -> None:
        self._redis = redis
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="log-flusher")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self.flush()

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_SECONDS)
            await self.flush()

    async def flush(self) -> None:
        events, critical = _drain(self._buffer), _drain(self._critical)
        if not events and not critical:
            return
        try:
            settings = get_config().logging
        except Exception:
            settings = LoggingSection()
        threshold = LEVELS[settings.level]
        events = [e for e in events if LEVELS[e["log_level"]] >= threshold]
        if settings.stdout:
            _print(events)
        if self._redis is None or not (events or critical):
            return
        try:
            async with self._redis.pipeline(transaction=False) as pipe:
                if events:
                    pipe.rpush(settings.queue_key, *(json.dumps(e, ensure_ascii=False) for e in events))
                    pipe.ltrim(settings.queue_key, -settings.max_backlog, -1)
                if critical:
                    pipe.rpush(settings.business_critical_key, *(json.dumps(c, ensure_ascii=False) for c in critical))
                await pipe.execute()
        except Exception as exc:
            print(f"log service unreachable, dropped {len(events) + len(critical)} events: {exc}",
                  file=sys.stderr, flush=True)
            if not settings.stdout:
                _print(events)


def _drain(buffer: deque[dict[str, str]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    while True:
        try:
            items.append(buffer.popleft())
        except IndexError:
            return items


def _print(events: list[dict[str, str]]) -> None:
    for e in events:
        print(f"{e['timestamp']} {e['log_level'].upper():5} {e['trace_id']} {e['message']}", flush=True)


log = Logger()
