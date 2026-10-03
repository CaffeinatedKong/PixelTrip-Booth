"""Guest, character, and travel-preference data access.

These three tables are always read together as a unit by the agent layer: the
Discovery node needs every party member's ``characters`` and
``travel_preferences`` rows to compute the ``Group_Profile`` (Requirement 7.1),
and ``guests`` supplies the display name that ``room_members`` does not carry.
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository

_GUESTS = "guests"
_CHARACTERS = "characters"
_PREFERENCES = "travel_preferences"


class ProfileRepository(BaseRepository):
    """Reads and writes ``guests``, ``characters``, and ``travel_preferences``."""

    # --- guests ------------------------------------------------------------

    async def get_guest_by_id(self, guest_id: str) -> dict[str, Any] | None:
        """Return the guest row for ``guest_id``, or ``None`` if absent."""
        try:
            response = (
                await self._client.table(_GUESTS).select("*").eq("id", guest_id).limit(1).execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_guest_by_id", table=_GUESTS)
        return self._first_row(response)

    # --- characters --------------------------------------------------------

    async def get_character_by_member_id(self, member_id: str) -> dict[str, Any] | None:
        """Return the character row for ``member_id``, or ``None`` if absent."""
        try:
            response = (
                await self._client.table(_CHARACTERS)
                .select("*")
                .eq("member_id", member_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_character_by_member_id", table=_CHARACTERS)
        return self._first_row(response)

    async def list_characters_by_member_ids(self, member_ids: list[str]) -> list[dict[str, Any]]:
        """Return character rows for every id in ``member_ids``.

        Returns an empty list for empty input without issuing a query, so the
        Discovery node's roster load does not fire a pointless ``in ()``.
        """
        if not member_ids:
            return []
        try:
            response = (
                await self._client.table(_CHARACTERS)
                .select("*")
                .in_("member_id", member_ids)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_characters_by_member_ids", table=_CHARACTERS)
        return self._rows(response)

    # --- travel_preferences ------------------------------------------------

    async def get_preferences_by_member_id(self, member_id: str) -> dict[str, Any] | None:
        """Return the preferences row for ``member_id``, or ``None`` if absent."""
        try:
            response = (
                await self._client.table(_PREFERENCES)
                .select("*")
                .eq("member_id", member_id)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="get_preferences_by_member_id", table=_PREFERENCES)
        return self._first_row(response)

    async def list_preferences_by_member_ids(self, member_ids: list[str]) -> list[dict[str, Any]]:
        """Return preference rows for every id in ``member_ids``.

        The Discovery and Logistics nodes derive ``Availability_Overlap`` and
        ``Budget_Ceiling`` from exactly these rows.
        """
        if not member_ids:
            return []
        try:
            response = (
                await self._client.table(_PREFERENCES)
                .select("*")
                .in_("member_id", member_ids)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_preferences_by_member_ids", table=_PREFERENCES)
        return self._rows(response)
