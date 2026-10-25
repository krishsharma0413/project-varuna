"""Health of each search provider/engine, shared by all workers through the queue Redis.

- A failure starts a cooldown (`search.failure_cooldown_seconds`) during which the engine is skipped.
- The first failure after a healthy period is a business-critical event ("failing"); the first success
  after failing is another ("recovered"). Repeated failures in between are not re-recorded.
"""

from __future__ import annotations

from typing import Protocol

from app.log import log

ALL_PROVIDERS = "all-search-providers"


class KeyValue(Protocol):
    async def exists(self, *names: str) -> int: ...
    async def set(self, name: str, value: str, ex: int | None = None, get: bool = False) -> object: ...
    async def delete(self, *names: str) -> int: ...


class SearchHealth:
    def __init__(self, store: KeyValue, cooldown_seconds: int) -> None:
        self.store = store
        self.cooldown = cooldown_seconds

    @staticmethod
    def _state_key(name: str) -> str:
        return f"search:health:{name}"

    @staticmethod
    def _cooldown_key(name: str) -> str:
        return f"search:cooldown:{name}"

    async def cooling_down(self, name: str) -> bool:
        try:
            return bool(await self.store.exists(self._cooldown_key(name)))
        except Exception as exc:
            log.exception("search health unavailable", exc)
            return False

    async def failed(self, name: str, reason: str) -> None:
        log.info("search engine failed", engine=name, reason=reason[:300])
        try:
            if self.cooldown > 0 and name != ALL_PROVIDERS:
                await self.store.set(self._cooldown_key(name), "1", ex=self.cooldown)
            previous = await self.store.set(self._state_key(name), "failing", get=True)
        except Exception as exc:
            log.exception("search health unavailable", exc)
            previous = None
        if previous != "failing":
            log.business_critical(name, "failing", reason)

    async def succeeded(self, name: str) -> None:
        try:
            was_failing = await self.store.delete(self._state_key(name))
        except Exception as exc:
            log.exception("search health unavailable", exc)
            return
        if was_failing:
            log.business_critical(name, "recovered")
