import asyncio

from app.queue import Consumer


class FakeRedis:
    def __init__(self):
        self.claims = 0

    async def xack(self, *_args):
        return 1

    async def xdel(self, *_args):
        return 1

    async def xclaim(self, *_args, **_kwargs):
        self.claims += 1
        return []


async def test_a_running_job_is_not_dispatched_twice():
    """Regression: a job running longer than the reclaim idle time was reclaimed and started again
    while the first run was still going, so the whole pipeline ran twice."""
    calls, started, release = [], asyncio.Event(), asyncio.Event()

    async def handler(payload):
        calls.append(payload)
        started.set()
        await release.wait()

    consumer = Consumer(FakeRedis(), "worker", handler, concurrency=2, reclaim_idle_ms=lambda: 60_000)
    entry = [("1-0", {"data": '{"job_id": "j1"}'})]
    await consumer._dispatch(entry)
    await started.wait()
    await consumer._dispatch(entry)  # e.g. picked up by the stale-job reclaim
    release.set()
    await asyncio.gather(*consumer._tasks)
    assert len(calls) == 1

    await consumer._dispatch(entry)  # once finished, the same id may run again (e.g. a retry)
    await asyncio.gather(*consumer._tasks)
    assert len(calls) == 2
