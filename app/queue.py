"""Job queue on Redis Streams (queue Redis instance).

Producers XADD to a stream; workers read through a consumer group and ACK when done, so a job
that was being processed when a worker died is picked up again on restart (own pending entries)
or by another worker once it has been idle longer than the per-reel lock TTL. While a job runs, its
entry is re-claimed periodically so it never looks idle, however long the run takes. Retries go
through a sorted set of delayed jobs keyed by the time they become due.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ResponseError

from app.log import log

STREAM = "jobs:stream"
GROUP = "workers"
DELAYED = "jobs:delayed"

Handler = Callable[[dict[str, Any]], Awaitable[None]]


async def enqueue(redis: Redis, payload: dict[str, Any]) -> str:
    return await redis.xadd(STREAM, {"data": json.dumps(payload)})


async def schedule(redis: Redis, payload: dict[str, Any], delay_seconds: float) -> None:
    await redis.zadd(DELAYED, {json.dumps(payload): time.time() + delay_seconds})


def _entries(response: Any) -> list[tuple[str, dict[str, str]]]:
    """Normalise XREADGROUP output across RESP2 (list) and RESP3 (dict) replies."""
    if not response:
        return []
    if isinstance(response, dict):
        return list(response.get(STREAM, [[]])[0]) if response.get(STREAM) else []
    entries: list[tuple[str, dict[str, str]]] = []
    for _stream, messages in response:
        entries.extend(messages)
    return entries


class Consumer:
    def __init__(
        self,
        redis: Redis,
        name: str,
        handler: Handler,
        concurrency: int,
        reclaim_idle_ms: Callable[[], int],
    ) -> None:
        self.redis = redis
        self.name = name
        self.handler = handler
        self.concurrency = concurrency
        self.reclaim_idle_ms = reclaim_idle_ms
        self._slots = asyncio.Semaphore(concurrency)
        self._tasks: set[asyncio.Task[None]] = set()
        self._inflight: set[str] = set()  # message ids being processed right now
        self._stopping = asyncio.Event()

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def stop(self) -> None:
        self._stopping.set()

    async def _forget_old_consumers(self) -> None:
        """Drop consumer names left by previous containers that have nothing pending (housekeeping)."""
        try:
            for consumer in await self.redis.xinfo_consumers(STREAM, GROUP):
                if consumer.get("name") != self.name and int(consumer.get("pending", 0)) == 0:
                    await self.redis.xgroup_delconsumer(STREAM, GROUP, consumer["name"])
        except Exception as exc:
            log.exception("could not clean up old queue consumers", exc)

    async def run(self) -> None:
        await self.ensure_group()
        await self._forget_old_consumers()
        # Jobs this consumer had started before a restart.
        await self._dispatch(_entries(await self.redis.xreadgroup(GROUP, self.name, {STREAM: "0"}, count=100)))
        last_reclaim = 0.0
        while not self._stopping.is_set():
            try:
                await self._move_due_delayed()
                if time.monotonic() - last_reclaim > 60:
                    last_reclaim = time.monotonic()
                    await self._reclaim_stale()
                free = self._free_slots()
                if free == 0:
                    await asyncio.sleep(0.5)
                    continue
                response = await self.redis.xreadgroup(
                    GROUP, self.name, {STREAM: ">"}, count=free, block=2000
                )
                await self._dispatch(_entries(response))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("queue loop error", exc)
                await asyncio.sleep(2)
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    def _free_slots(self) -> int:
        return max(0, self.concurrency - len(self._tasks))

    async def _dispatch(self, entries: list[tuple[str, dict[str, str]]]) -> None:
        for message_id, fields in entries:
            if not fields:  # pending entry whose payload was already deleted
                await self.redis.xack(STREAM, GROUP, message_id)
                continue
            if message_id in self._inflight:  # already running here; never start a second copy
                continue
            self._inflight.add(message_id)
            await self._slots.acquire()
            task = asyncio.create_task(self._process(message_id, fields))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _keep_claimed(self, message_id: str) -> None:
        """Reset the entry's idle time now and then, so no reclaim takes it while it is still running."""
        while True:
            await asyncio.sleep(max(5.0, self.reclaim_idle_ms() / 3000))
            try:
                await self.redis.xclaim(STREAM, GROUP, self.name, 0, [message_id], justid=True)
            except Exception as exc:
                log.exception("could not refresh job claim", exc, message_id=message_id)

    async def _process(self, message_id: str, fields: dict[str, str]) -> None:
        keeper = asyncio.create_task(self._keep_claimed(message_id))
        try:
            payload = json.loads(fields.get("data", "{}"))
            await self.handler(payload)
        except Exception as exc:
            log.exception("job handler crashed", exc, message_id=message_id)
        finally:
            keeper.cancel()
            self._inflight.discard(message_id)
            self._slots.release()
            try:
                await self.redis.xack(STREAM, GROUP, message_id)
                await self.redis.xdel(STREAM, message_id)
            except Exception as exc:
                log.exception("could not ack job", exc, message_id=message_id)

    async def _move_due_delayed(self) -> None:
        due = await self.redis.zrangebyscore(DELAYED, "-inf", time.time(), start=0, num=20)
        for member in due:
            if await self.redis.zrem(DELAYED, member):
                await self.redis.xadd(STREAM, {"data": member})

    async def _reclaim_stale(self) -> None:
        result = await self.redis.xautoclaim(
            STREAM, GROUP, self.name, min_idle_time=self.reclaim_idle_ms(), start_id="0-0", count=10
        )
        messages = result[1] if len(result) > 1 else []
        messages = [(mid, fields) for mid, fields in messages if fields]
        if messages:
            log.info("reclaimed stale jobs", count=len(messages))
            await self._dispatch(messages)
