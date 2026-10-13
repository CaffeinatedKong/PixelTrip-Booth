"""Per-version itinerary review decisions.

One row per (itinerary version, member): ``approve`` or ``refine``. This, not the
shared ``room_members.stage_ready`` flag, is what decides whether the party has
approved a version. A new version starts with no rows, so each review round is fresh.
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository

_TABLE = "itinerary_reviews"


class ReviewRepository(BaseRepository):
    """Stores and reads members' decisions on an itinerary version."""

    async def upsert(
        self, trip_id: str, itinerary_version_id: str, member_id: str, decision: str
    ) -> dict[str, Any]:
        """Record (or change) a member's decision on a version and return the row."""
        try:
            response = (
                await self._client.table(_TABLE)
                .upsert(
                    {
                        "trip_id": trip_id,
                        "itinerary_version_id": itinerary_version_id,
                        "member_id": member_id,
                        "decision": decision,
                    },
                    on_conflict="itinerary_version_id,member_id",
                )
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="upsert", table=_TABLE)

        row = self._first_row(response)
        if row is None:
            self._handle_error(
                ValueError("upsert returned no row"), operation="upsert", table=_TABLE
            )
        return row

    async def list_by_version(self, itinerary_version_id: str) -> list[dict[str, Any]]:
        """Return every member's decision on ``itinerary_version_id``."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("itinerary_version_id", itinerary_version_id)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_by_version", table=_TABLE)
        return self._rows(response)
