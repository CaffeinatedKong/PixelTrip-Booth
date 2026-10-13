"""The last successful flight search per route and dates (``flight_search_cache``).

Only real provider results are stored, never estimates. A recent entry saves a paid
search; when every provider fails the last entry is shown with its age (see
``logistics_node``). The key is built here so the lookup and the write always agree.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.repositories.base import BaseRepository

_TABLE = "flight_search_cache"


@dataclass(frozen=True)
class CachedSearch:
    """A stored search result and how old it is."""

    options: list[dict[str, Any]]
    currency: str
    fetched_at: datetime

    @property
    def age_seconds(self) -> float:
        return max(0.0, (datetime.now(UTC) - self.fetched_at).total_seconds())


def cache_key(origin: str, destination: str, depart_after: str, depart_before: str | None) -> str:
    """A stable key: the same route and dates always map to the same row."""
    parts = (origin, destination, depart_after, depart_before or "")
    return "|".join(" ".join(str(p).split()).lower() for p in parts)


def _parse(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


class FlightCacheRepository(BaseRepository):
    """Reads and writes the flight search cache."""

    async def get(self, key: str) -> CachedSearch | None:
        """The stored search for ``key`` however old, or ``None``. Callers judge the age."""
        try:
            response = await self._client.table(_TABLE).select("*").eq("cache_key", key).execute()
        except Exception as exc:
            self._handle_error(exc, operation="get", table=_TABLE)
        row = self._first_row(response)
        if row is None or not isinstance(row.get("options"), list):
            return None
        fetched_at = _parse(row.get("fetched_at"))
        if fetched_at is None:
            return None
        return CachedSearch(row["options"], str(row.get("currency") or ""), fetched_at)

    async def put(self, key: str, options: list[dict[str, Any]], currency: str) -> None:
        """Store (or replace) the search for ``key``, stamped now."""
        try:
            await (
                self._client.table(_TABLE)
                .upsert(
                    {
                        "cache_key": key,
                        "options": options,
                        "currency": currency,
                        "fetched_at": datetime.now(UTC).isoformat(),
                    },
                    on_conflict="cache_key",
                )
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="put", table=_TABLE)
