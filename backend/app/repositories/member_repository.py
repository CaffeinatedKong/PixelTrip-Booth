"""Room-member data access.

Spec 03's agent layer uses this repository read-only: the Discovery node loads the
party roster, ``AgentRunService`` resolves a triggering member's identity against
it before trusting a client-supplied id (Requirement 22.2), and vote tallying
restricts counts to members still present in the room (Requirement 17.6).
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository

_TABLE = "room_members"


class MemberRepository(BaseRepository):
    """Reads and writes ``room_members`` rows."""

    async def get_by_id(self, member_id: str) -> dict[str, Any] | None:
        """Return the member row for ``member_id``, or ``None`` if absent.

        This is the resolution step Requirement 22.2 requires before any
        client-supplied identity is persisted as authoritative.
        """
        try:
            response = (
                await self._client.table(_TABLE).select("*").eq("id", member_id).limit(1).execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_by_id", table=_TABLE)
        return self._first_row(response)

    async def list_by_room(self, room_id: str) -> list[dict[str, Any]]:
        """Return every member row for ``room_id``, oldest first."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("room_id", room_id)
                .order("created_at")
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_by_room", table=_TABLE)
        return self._rows(response)

    async def count_by_room(self, room_id: str) -> int:
        """Return the number of members in ``room_id``."""
        return len(await self.list_by_room(room_id))

    async def get_owner(self, room_id: str) -> dict[str, Any] | None:
        """Return the room's ``role = 'owner'`` member row, or ``None``.

        Used to authorize owner-triggered vote-session closure
        (Requirement 17.12).
        """
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("room_id", room_id)
                .eq("role", "owner")
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_owner", table=_TABLE)
        return self._first_row(response)
