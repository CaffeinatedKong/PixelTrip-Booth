"""Member repository: room membership and case-insensitive identity lookup.

Identity rule: ``room_id + normalized display name`` -> room member, so "Gerald",
"gerald", "GERald", and "  Gerald  " are the same member. The database enforces this with
the generated ``room_members.normalized_name`` column and
``UNIQUE(room_id, normalized_name)``; ``normalize_display_name`` applies the same rule in
Python for lookups.
"""

from __future__ import annotations

from typing import Literal

from app.exceptions import MemberAlreadyExistsError, ValidationError
from app.repositories.base import BaseRepository, require_text, require_uuid

TABLE = "room_members"
UNIQUE_VIOLATION = "23505"
ROLES = ("owner", "member")


def normalize_display_name(name: str) -> str:
    """Trim, collapse internal whitespace to one space, and lower-case.

    Must match the database column:
    ``lower(btrim(regexp_replace(display_name, '\\s+', ' ', 'g')))``.
    """
    return " ".join(name.split()).lower()


def _is_unique_violation(exc: Exception) -> bool:
    return getattr(exc, "code", None) == UNIQUE_VIOLATION or UNIQUE_VIOLATION in str(exc)


class MemberRepository(BaseRepository):
    """Owns ``room_members`` operations."""

    async def create_member(
        self,
        room_id: str,
        guest_id: str,
        display_name: str,
        role: Literal["owner", "member"],
    ) -> dict:
        """Insert a membership row and return it.

        Raises ``MemberAlreadyExistsError`` if a member with the same normalized name
        already exists in the room (e.g. two concurrent joins).
        """
        require_uuid(room_id, "room_id")
        require_uuid(guest_id, "guest_id")
        require_text(display_name, "display_name", 50)
        if role not in ROLES:
            raise ValidationError("'role' must be 'owner' or 'member'.")

        data = {
            "room_id": room_id,
            "guest_id": guest_id,
            "display_name": display_name,
            "role": role,
        }
        try:
            response = await self._client.table(TABLE).insert(data).execute()
        except Exception as exc:
            if _is_unique_violation(exc):
                raise MemberAlreadyExistsError(
                    "A member with that name already exists in this room."
                ) from exc
            self._handle_error(exc, operation="create_member", table=TABLE)
        if not response.data:
            self._handle_error(
                ValueError("No data returned"), operation="create_member", table=TABLE
            )
        return response.data[0]

    async def get_member_by_display_name(self, room_id: str, display_name: str) -> dict | None:
        """Case-insensitive match on ``normalized_name`` within the given room."""
        require_uuid(room_id, "room_id")
        require_text(display_name, "display_name", 50)
        return await self._select_one(
            TABLE, room_id=room_id, normalized_name=normalize_display_name(display_name)
        )

    async def get_member_by_id(self, member_id: str) -> dict | None:
        """Return the member with this id, or ``None``."""
        require_uuid(member_id, "member_id")
        return await self._select_one(TABLE, id=member_id)

    async def list_members_by_room(self, room_id: str) -> list[dict]:
        """Return all members of the room (possibly empty)."""
        require_uuid(room_id, "room_id")
        try:
            response = await self._client.table(TABLE).select("*").eq("room_id", room_id).execute()
        except Exception as exc:
            self._handle_error(exc, operation="list_members_by_room", table=TABLE)
        return response.data or []
