"""Room repository: room lookup and atomic room creation."""

from __future__ import annotations

from app.exceptions import ValidationError
from app.repositories.base import ROOM_CODE_PATTERN, BaseRepository, require_text, require_uuid

TABLE = "party_rooms"
RPC_CREATE_ROOM = "create_room_with_owner"
RESULT_KEYS = ("room", "guest", "member", "character", "travel_preferences")


class RoomRepository(BaseRepository):
    """Owns ``party_rooms`` operations and the ``create_room_with_owner`` RPC."""

    async def create_room_with_owner(
        self,
        name: str,
        room_code: str,
        owner_display_name: str,
        appearance: dict | None = None,
    ) -> dict:
        """Create the room, owner guest, owner membership, character, and preferences.

        Runs as one database transaction via the RPC: all five records or none. Returns a
        dict with keys ``room``, ``guest``, ``member``, ``character``,
        ``travel_preferences``.
        """
        require_text(name, "name", 100)
        require_text(owner_display_name, "owner_display_name", 50)
        if not isinstance(room_code, str) or not ROOM_CODE_PATTERN.fullmatch(room_code):
            raise ValidationError("'room_code' must match ^[A-Z0-9]{4,12}$.")

        params = {
            "p_room_name": name,
            "p_room_code": room_code,
            "p_owner_display_name": owner_display_name,
            "p_appearance": appearance or {},
        }
        try:
            response = await self._client.rpc(RPC_CREATE_ROOM, params).execute()
        except Exception as exc:
            self._handle_error(exc, operation=RPC_CREATE_ROOM, table=TABLE)

        result = response.data
        if not isinstance(result, dict) or any(key not in result for key in RESULT_KEYS):
            self._handle_error(
                ValueError("Unexpected RPC result"), operation=RPC_CREATE_ROOM, table=TABLE
            )
        return result

    async def get_room_by_code(self, room_code: str) -> dict | None:
        """Return the room with this code, or ``None``."""
        return await self._select_one(TABLE, room_code=room_code)

    async def get_room_by_id(self, room_id: str) -> dict | None:
        """Return the room with this id, or ``None``."""
        require_uuid(room_id, "room_id")
        return await self._select_one(TABLE, id=room_id)
