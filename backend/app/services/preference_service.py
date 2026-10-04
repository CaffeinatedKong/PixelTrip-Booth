"""Preference service: save a member's travel preferences and detect "everyone's in".

When the last member of a room saves preferences, the trip advances to
``preferences_collected`` (planning stage ``discover``), which is what lets the party
start destination discovery.
"""

from __future__ import annotations

from typing import Any

from app.agents.errors import UnresolvedMemberError
from app.exceptions import RoomNotFoundError
from app.repositories.member_repository import MemberRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.trip_repository import TripRepository
from app.schemas.planning import SavePreferencesRequest, SavePreferencesResponse
from app.schemas.room import TravelPreferencesSchema, TripSchema
from app.services.trip_progress import advance_trip, require_room_trip

#: Interim: the agent layer's flight search reads the departure origin from this
#: ``hard_constraints`` entry (spec 03, Backend Change Request Entry 1) until it reads the
#: ``travel_preferences.origin`` column. Mirroring keeps both in sync.
_ORIGIN_CONSTRAINT_TYPE = "departure_origin"


def _to_columns(request: SavePreferencesRequest) -> dict[str, Any]:
    """Map the request to ``travel_preferences`` columns, mirroring ``origin``."""
    fields = request.model_dump(mode="json")
    constraints = [
        item
        for item in fields["hard_constraints"]
        if not (isinstance(item, dict) and item.get("type") == _ORIGIN_CONSTRAINT_TYPE)
    ]
    if fields["origin"]:
        constraints.append({"type": _ORIGIN_CONSTRAINT_TYPE, "value": fields["origin"]})
    fields["hard_constraints"] = constraints
    return fields


class PreferenceService:
    """Saves preferences and advances the trip once every member has submitted."""

    def __init__(
        self,
        room_repo: RoomRepository,
        member_repo: MemberRepository,
        profile_repo: ProfileRepository,
        trip_repo: TripRepository,
    ) -> None:
        self._room_repo = room_repo
        self._member_repo = member_repo
        self._profile_repo = profile_repo
        self._trip_repo = trip_repo

    async def save(
        self, room_code: str, member_id: str, request: SavePreferencesRequest
    ) -> SavePreferencesResponse:
        """Replace the member's preferences and return them with the (maybe advanced) trip."""
        room = await self._room_repo.get_room_by_code(room_code)
        if room is None:
            raise RoomNotFoundError(f"Room '{room_code}' not found.")

        member = await self._member_repo.get_member_by_id(member_id)
        if member is None or member.get("room_id") != room["id"]:
            raise UnresolvedMemberError(member_id)

        saved = await self._profile_repo.save_preferences(member_id, _to_columns(request))

        trip = await require_room_trip(self._trip_repo, room["id"])
        if await self._everyone_submitted(room["id"]):
            trip = await advance_trip(self._trip_repo, trip, "preferences_collected")

        return SavePreferencesResponse(
            travel_preferences=TravelPreferencesSchema.model_validate(saved),
            trip=TripSchema.model_validate(trip),
        )

    async def _everyone_submitted(self, room_id: str) -> bool:
        members = await self._member_repo.list_by_room(room_id)
        if not members:
            return False
        member_ids = [m["id"] for m in members]
        prefs = await self._profile_repo.list_preferences_by_member_ids(member_ids)
        submitted = {p["member_id"] for p in prefs if p.get("submitted_at")}
        return submitted.issuperset(member_ids)
