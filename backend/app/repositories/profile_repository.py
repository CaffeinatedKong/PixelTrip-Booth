"""Profile repository: guests, characters, and travel preferences as one domain."""

from __future__ import annotations

from app.repositories.base import BaseRepository, require_text, require_uuid

GUESTS = "guests"
CHARACTERS = "characters"
PREFERENCES = "travel_preferences"


class ProfileRepository(BaseRepository):
    """Owns ``guests``, ``characters``, and ``travel_preferences`` operations."""

    async def create_guest(self, display_name: str, avatar_url: str | None = None) -> dict:
        """Insert a guest profile and return it."""
        require_text(display_name, "display_name", 50)
        data: dict = {"display_name": display_name}
        if avatar_url is not None:
            data["avatar_url"] = avatar_url
        return await self._insert_one(GUESTS, data)

    async def get_guest_by_id(self, guest_id: str) -> dict | None:
        """Return the guest with this id, or ``None``."""
        require_uuid(guest_id, "guest_id")
        return await self._select_one(GUESTS, id=guest_id)

    async def create_character(self, member_id: str, appearance: dict | None = None) -> dict:
        """Insert a character for the member and return it."""
        require_uuid(member_id, "member_id")
        return await self._insert_one(
            CHARACTERS, {"member_id": member_id, "appearance": appearance or {}}
        )

    async def get_character_by_member_id(self, member_id: str) -> dict | None:
        """Return the member's character, or ``None``."""
        require_uuid(member_id, "member_id")
        return await self._select_one(CHARACTERS, member_id=member_id)

    async def create_preferences(
        self,
        member_id: str,
        available_dates: list | None = None,
        destinations: list | None = None,
        interests: list | None = None,
        activities: list | None = None,
        hard_constraints: list | None = None,
    ) -> dict:
        """Insert the member's travel preferences (list fields default to ``[]``)."""
        require_uuid(member_id, "member_id")
        data = {
            "member_id": member_id,
            "available_dates": available_dates or [],
            "destinations": destinations or [],
            "interests": interests or [],
            "activities": activities or [],
            "hard_constraints": hard_constraints or [],
        }
        return await self._insert_one(PREFERENCES, data)

    async def get_preferences_by_member_id(self, member_id: str) -> dict | None:
        """Return the member's travel preferences, or ``None``."""
        require_uuid(member_id, "member_id")
        return await self._select_one(PREFERENCES, member_id=member_id)
