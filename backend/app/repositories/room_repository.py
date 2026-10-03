"""Party room data access.

The agent layer reads two fields from here that live nowhere else:
``party_rooms.status`` (is the room still open to planning?) and
``party_rooms.planning_stage`` (has the party already moved past this run's
stage?). Both gate whether a run may proceed at all — see Requirement 6.7-6.8.
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository

_TABLE = "party_rooms"


class RoomRepository(BaseRepository):
    """Reads ``party_rooms`` rows."""

    async def get_by_id(self, room_id: str) -> dict[str, Any] | None:
        """Return the room row for ``room_id``, or ``None`` if absent."""
        try:
            response = (
                await self._client.table(_TABLE).select("*").eq("id", room_id).limit(1).execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_by_id", table=_TABLE)
        return self._first_row(response)

    async def get_by_code(self, room_code: str) -> dict[str, Any] | None:
        """Return the room row for ``room_code``, or ``None`` if absent."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("room_code", room_code)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_by_code", table=_TABLE)
        return self._first_row(response)
