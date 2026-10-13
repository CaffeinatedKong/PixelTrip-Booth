"""A small in-process cache with a short lifetime and one load per key at a time.

Built for endpoints every party member polls (run progress): with 20-40 people in a
room, a request per person every couple of seconds is mostly the same question. Caching
the answer for a moment turns "one database read per request" into "one per key per
interval", and :meth:`TTLCache.get_or_load` makes concurrent requests for a key that is
being loaded wait for that one load rather than each starting their own.

Per process: with several workers each keeps its own copy, which is fine for a lifetime
of a few seconds. Failures are never cached.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Hashable
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class TTLCache(Generic[K, V]):
    def __init__(
        self,
        ttl_seconds: float,
        *,
        max_entries: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max = max_entries
        self._clock = clock
        self._values: dict[K, tuple[float, V]] = {}
        self._loading: dict[K, asyncio.Task[V]] = {}

    def get(self, key: K) -> V | None:
        """The cached value, or ``None`` if absent or expired."""
        entry = self._values.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if self._clock() - stored_at >= self._ttl:
            del self._values[key]
            return None
        return value

    def set(self, key: K, value: V) -> None:
        if len(self._values) >= self._max and key not in self._values:
            # Drop the oldest entry; entries live seconds, so this is a backstop only.
            oldest = min(self._values, key=lambda k: self._values[k][0])
            del self._values[oldest]
        self._values[key] = (self._clock(), value)

    async def get_or_load(self, key: K, loader: Callable[[], Awaitable[V]]) -> V:
        """The cached value, else the result of ``loader`` (shared by concurrent callers)."""
        if self._ttl <= 0:
            return await loader()
        cached = self.get(key)
        if cached is not None:
            return cached
        task = self._loading.get(key)
        if task is None:
            task = asyncio.ensure_future(loader())
            self._loading[key] = task
            task.add_done_callback(lambda _t, k=key: self._loading.pop(k, None))
        value = await asyncio.shield(task)
        self.set(key, value)
        return value

    def invalidate(self, predicate: Callable[[K], bool]) -> None:
        """Forget every entry whose key matches ``predicate``."""
        for key in [k for k in self._values if predicate(k)]:
            del self._values[key]

    def clear(self) -> None:
        self._values.clear()
