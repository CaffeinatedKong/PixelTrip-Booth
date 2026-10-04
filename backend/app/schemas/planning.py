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

from app.schemas.room import TravelPreferencesSchema, TripSchema, _Base

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


class SavePreferencesRequest(_Base):
    """A member's full set of travel preferences. Replaces whatever was saved before."""

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

    @field_validator("travel_style", "origin")
    @classmethod
    def _blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class SavePreferencesResponse(_Base):
    """The saved preferences plus the trip, whose status may have advanced."""

    travel_preferences: TravelPreferencesSchema
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
