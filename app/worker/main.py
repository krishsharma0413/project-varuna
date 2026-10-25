"""Pipeline worker: consumes the Redis job stream and runs periodic housekeeping.

Run with `python -m app.worker.main`.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import socket
from datetime import UTC, datetime, timedelta

from app.clients import JOBS, REQUESTS, close_clients, mongo, queue_redis
from app.config import get_config
from app.log import log
from app.pipeline.orchestrator import handle_job
from app.queue import Consumer


async def housekeeping(stop: asyncio.Event) -> None:
    """Deletes old finished jobs and old request rows (no TTL indexes on the free tier)."""
    while not stop.is_set():
        config = get_config()
        try:
            now = datetime.now(UTC)
            jobs = await mongo()[JOBS].delete_many(
                {"status": {"$in": ["done", "failed", "rejected"]},
                 "created_at": {"$lt": now - timedelta(days=config.retention.jobs_days)}}
            )
            requests = await mongo()[REQUESTS].delete_many(
                {"created_at": {"$lt": now - timedelta(days=config.retention.requests_days)}}
            )
            if jobs.deleted_count or requests.deleted_count:
                log.info("housekeeping", jobs_deleted=jobs.deleted_count, requests_deleted=requests.deleted_count)
        except Exception as exc:
            log.exception("housekeeping failed", exc)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=config.retention.sweep_minutes * 60)


async def main() -> None:
    config = get_config()
    log.configure("worker")
    log.start(queue_redis())
    consumer = Consumer(
        queue_redis(),
        name=socket.gethostname(),
        handler=handle_job,
        concurrency=config.worker.concurrency,
        reclaim_idle_ms=lambda: get_config().pipeline.lock_ttl_seconds * 1000,
    )
    stop = asyncio.Event()

    def request_stop() -> None:
        log.info("worker stopping")
        stop.set()
        consumer.stop()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, request_stop)

    log.info("worker started", concurrency=config.worker.concurrency)
    try:
        await asyncio.gather(consumer.run(), housekeeping(stop))
    finally:
        await log.stop()
        await close_clients()


if __name__ == "__main__":
    asyncio.run(main())
