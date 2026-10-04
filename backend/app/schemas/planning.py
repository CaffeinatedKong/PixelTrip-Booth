"""Request and response schemas for the week-1 planning endpoints.

Preferences, voting, agent runs, and itinerary versions. Same conventions as
``app/schemas/room.py``: snake_case in Python, camelCase on the wire, shapes from the
"HTTP API" section of ``api-contracts.md``.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.room import CharacterSchema, TravelPreferencesSchema, TripSchema, _Base

_MEMBER_ID_EXAMPLE = "3a9b8c7d-6e5f-4a3b-9c2d-1e0f9a8b7c6d"

# --- Preferences ----------------------------------------------------------------------


class DateRange(_Base):
    """An inclusive range of dates the member can travel."""

    start: date = Field(examples=["2026-12-20"])
    end: date = Field(examples=["2026-12-27"])

    @model_validator(mode="after")
    def _end_not_before_start(self) -> DateRange:
        if self.end < self.start:
            raise ValueError("'end' must not be before 'start'")
        return self


class CharacterInput(_Base):
    """The member's pixel character. Replaces the saved character when sent."""

    appearance: dict[str, Any] = Field(
        default_factory=dict,
        max_length=50,
        description="Free-form choices from the character creator.",
        examples=[{"outfit": "explorer", "palette": "forest", "accessory": "backpack"}],
    )
    sprite_key: str | None = Field(
        default=None,
        max_length=100,
        description="Which sprite to draw; null means the default sprite.",
        examples=["explorer-01"],
    )

    @field_validator("sprite_key")
    @classmethod
    def _blank_sprite_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class SavePreferencesRequest(_Base):
    """A member's full set of travel preferences. Replaces whatever was saved before.

    ``character`` is optional: when sent it replaces the member's character; when
    omitted the character is left unchanged.
    """

    available_dates: list[DateRange] = Field(
        default_factory=list,
        max_length=20,
        description="Date ranges the member can travel; the AI uses the overlap across the party.",
        examples=[[{"start": "2026-12-20", "end": "2026-12-27"}]],
    )
    destinations: list[Any] = Field(default_factory=list, max_length=20, examples=[["Tokyo"]])
    travel_style: str | None = Field(default=None, max_length=50, examples=["relaxed"])
    budget: float | None = Field(default=None, ge=0, le=10_000_000, examples=[1500])
    interests: list[Any] = Field(
        default_factory=list, max_length=30, examples=[["food", "museums"]]
    )
    activities: list[Any] = Field(
        default_factory=list,
        max_length=30,
        examples=[
            [{"name": "hiking", "priority": "must_have"}, {"name": "spa", "priority": "optional"}]
        ],
    )
    hard_constraints: list[Any] = Field(
        default_factory=list, max_length=30, examples=[["no red-eye flights"]]
    )
    origin: str | None = Field(
        default=None,
        max_length=100,
        description="Departure city or IATA code, used for flight search.",
        examples=["SIN"],
    )

    character: CharacterInput | None = Field(
        default=None,
        description="Optional. Saves the member's pixel character in the same call.",
    )

    @field_validator("travel_style", "origin")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SavePreferencesResponse(_Base):
    """The saved preferences and character, plus the trip (its status may have advanced)."""

    travel_preferences: TravelPreferencesSchema
    character: CharacterSchema | None = Field(
        default=None, description="The member's character; null only if none exists."
    )
    trip: TripSchema


# --- Voting ---------------------------------------------------------------------------


class CastVoteRequest(_Base):
    member_id: UUID = Field(examples=[_MEMBER_ID_EXAMPLE])
    option_id: str = Field(min_length=1, max_length=200, examples=["opt-tokyo"])


class CastVoteResponse(_Base):
    vote_session_id: str
    member_id: str
    option_id: str
    session_status: Literal["open", "closed"] = Field(
        description="'closed' when this vote was the last one needed and the session resolved."
    )


class CloseVoteRequest(_Base):
    member_id: UUID = Field(
        description="Must be the room owner's member id.", examples=[_MEMBER_ID_EXAMPLE]
    )


class TieInfo(_Base):
    tied_option_ids: list[str]
    tied_count: int


class VoteResolutionResponse(_Base):
    vote_session_id: str
    category: Literal["destination", "flight"]
    winning_option: dict[str, Any] = Field(
        description="The winning option exactly as it appeared in the vote session."
    )
    tie: TieInfo | None = Field(
        default=None, description="Set when a tie was broken by option order."
    )
    selection_id: str


# --- Agent runs -----------------------------------------------------------------------


class StartRunRequest(_Base):
    run_type: Literal["discovery", "logistics", "itinerary", "refinement"] = Field(
        examples=["discovery"]
    )
    member_id: UUID = Field(examples=[_MEMBER_ID_EXAMPLE])
    idempotency_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Send the same key on a retry to get the same run back instead of a new one.",
        examples=["discover-1"],
    )


# --- Itinerary versions ---------------------------------------------------------------


class ItineraryVersionSchema(_Base):
    id: str
    trip_id: str
    version: int
    source: Literal["build", "refine"]
    status: Literal["proposed", "approved", "rejected", "superseded"]
    itinerary: dict[str, Any]
    change_summary: str | None = None
