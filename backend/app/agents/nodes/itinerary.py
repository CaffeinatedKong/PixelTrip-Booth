"""Itinerary persistence and the Itinerary_Node (BUILD stage).

Two things live here:

1. :func:`persist_itinerary_version` — the optimistic-lock insert loop shared by
   this node and, later, Negotiation_Node. Appending a version can race another
   run inserting the same ``(trip_id, version)`` pair; this function is the one
   place that race is handled, so a specialist node never has to re-derive the
   retry/escalate policy.

2. :func:`itinerary_node` — the BUILD-stage specialist. It loads both locked
   selections and the party's preferences, derives a day count, generates a
   simple day-by-day itinerary, and persists it as the trip's first version.

**Why "evaluate applicability" is trivial here but not forever.** A lost race
during a *build* (``version == 1``) always means another run already built the
trip's first version — there is no ``Affected_Scope`` to re-check, because a
first build changes nothing relative to a prior version; there is no prior
version. So :func:`persist_itinerary_version`'s ``is_still_applicable`` callback
is one line here (``return False``: the attempt is never still applicable once
beaten). Negotiation_Node, which generates version 2+ from a real
``Affected_Scope``, is where that callback does real work — this function takes
the callback as a parameter precisely so that case can plug in without a second
copy of the retry loop.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig

from app.agents.errors import (
    DestinationNotSelectedError,
    FlightNotSelectedError,
    InvalidTripDurationError,
    ItineraryPersistenceError,
    PreferencesNotCollectedError,
    RepeatedVersionContentionError,
)
from app.agents.group_profile import compute_group_profile
from app.agents.messages import SummaryMessageContent, emit_npc_message
from app.agents.proposals import (
    DateRange,
    DestinationRef,
    ItineraryDayModel,
    ItineraryItemModel,
    ItineraryModel,
    ItineraryProposal,
)
from app.exceptions import RepositoryError
from app.repositories.itinerary_version_repository import UniqueVersionViolation
from app.services.trip_status_service import advance_trip_status

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Awaitable, Callable

    from app.agents.state import AgentState, RepositoryBundle

logger = logging.getLogger(__name__)

#: Requirement 5.11-5.12: at most 2 lost-race retries, failing on a 3rd collision.
MAX_LOST_RACE_CYCLES = 2

#: Requirement 9.3: 1-10 items per day.
MIN_ITEMS_PER_DAY = 1
MAX_ITEMS_PER_DAY = 10

#: Requirement 9.5: a derived trip duration outside this range fails the run.
MIN_TRIP_DAYS = 1
MAX_TRIP_DAYS = 30

STAGE = "BUILD"


async def persist_itinerary_version(
    state: AgentState,
    repos: RepositoryBundle,
    itinerary_dict: dict[str, Any],
    source: str,
    change_summary: str | None,
    is_still_applicable: Callable[[dict[str, Any]], Awaitable[bool]],
) -> tuple[dict[str, Any] | None, AgentState]:
    """Insert one itinerary version, retrying through at most 2 lost races.

    Args:
        state: The run's state. ``state.base_version`` is read for the
            candidate version number and updated on each lost race
            (Requirement 5.5).
        repos: The repository bundle.
        itinerary_dict: The itinerary payload to persist (already stripped of
            any agent-internal bookkeeping — see
            :meth:`~app.agents.proposals.ItineraryProposal.to_persistable`).
        source: The caller's intended source for its *first* attempt —
            ``"build"`` for a first version, ``"refine"`` for every later one.
            A retry after a lost race always re-derives the actual source from
            the new candidate version instead of reusing this value: a build
            whose first attempt collided is, by definition, no longer trying
            to write version 1, so continuing to call it ``"build"`` would
            violate ``CHECK ((version = 1) = (source = 'build'))`` on retry
            (Requirement 5.7). This parameter exists so a mismatched intent is
            still caught on the very first attempt, before any lost race could
            paper over a caller bug.
        change_summary: 1-500 characters for a refine version, or ``None`` for
            a build (Requirement 9.7's "no changeSummary"). A caller retrying
            a build after a lost race has no change summary to offer either,
            since nothing in a first build's content is scoped to an
            ``Affected_Scope`` — this is fine because a build's own
            ``is_still_applicable`` always returns ``False`` (see module
            docstring), so a build is never actually retried with a derived
            ``"refine"`` source in practice; only Negotiation_Node's own calls,
            which already pass a real summary, retry past version 1.
        is_still_applicable: Called with the re-fetched highest-version row
            after a lost race. ``True`` retries the insert at the new
            ``base_version + 1``; ``False`` ends the attempt with nothing
            written (Requirement 5.6).

    Returns:
        ``(row, state)`` on a successful insert, or ``(None, state)`` when a
        lost race made the proposal no longer applicable
        (Requirement 5.6) — the caller must emit exactly one
        ``kind='text'`` message for that outcome and persist nothing further.

    Raises:
        ValueError: If ``source`` does not match the first attempt's candidate
            version — a caller bug, not a race.
        RepeatedVersionContentionError: After a 3rd lost race
            (Requirement 5.12).
        ItineraryPersistenceError: If the insert fails for any reason other
            than ``UNIQUE(trip_id, version)`` (Requirement 5.13). Never
            retried.
    """
    lost_race_count = 0

    while lost_race_count <= MAX_LOST_RACE_CYCLES:
        candidate_version = state.base_version + 1
        candidate_source = "build" if candidate_version == 1 else "refine"
        if lost_race_count == 0 and source != candidate_source:
            # A caller bug, not a race: Requirement 5.7's CHECK constraint pairs
            # version 1 with 'build' and every later version with 'refine'.
            raise ValueError(
                f"source {source!r} is invalid for version {candidate_version}; "
                f"expected {candidate_source!r}"
            )

        try:
            row = await repos.itinerary_version_repo.insert_version(
                trip_id=state.trip_id,
                version=candidate_version,
                source=candidate_source,
                itinerary=itinerary_dict,
                change_summary=change_summary,
            )
        except UniqueVersionViolation:
            lost_race_count += 1
            latest = await repos.itinerary_version_repo.get_latest(state.trip_id)
            if latest is None:  # pragma: no cover - defensive: a 23505 implies a row exists
                raise
            state = state.with_base_version(int(latest["version"]))

            if lost_race_count > MAX_LOST_RACE_CYCLES:
                break
            if not await is_still_applicable(latest):
                # Requirement 5.6: completed, nothing written, one message.
                return None, state
            continue
        except RepositoryError as exc:
            # Requirement 5.13: anything other than the version UNIQUE
            # violation is a fatal, non-retried failure.
            raise ItineraryPersistenceError("the version could not be inserted") from exc

        # Success: supersede older proposed rows, never touch approved/rejected
        # (Requirement 5.9).
        await repos.itinerary_version_repo.supersede_lower_versions(
            state.trip_id, below_version=row["version"]
        )
        return row, state

    # Requirement 5.12: a 3rd lost race within the same run.
    raise RepeatedVersionContentionError(lost_race_count)


# ---------------------------------------------------------------------------
# Day-count derivation (Requirement 9.3-9.4)
# ---------------------------------------------------------------------------


def _parse_date(value: Any) -> date | None:
    """Parse an ISO date (or date-time) string, returning ``None`` if unusable."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _derive_day_count(
    flight_selection: dict[str, Any],
    group_profile: dict[str, Any],
) -> int:
    """Derive the itinerary's day count (Requirement 9.3-9.5).

    Prefers the locked flight's outbound/return dates; falls back to the
    availability overlap's first range when either flight date is absent.
    Raises before any write when the result falls outside 1-30 days.
    """
    flight_data = flight_selection.get("data") or {}
    outbound = _parse_date(flight_data.get("depart_at") or flight_data.get("departAt"))
    returning = _parse_date(flight_data.get("return_at") or flight_data.get("returnAt"))

    if outbound is None or returning is None:
        overlap = group_profile.get("availability_overlap") or []
        if overlap:
            outbound = _parse_date(overlap[0]["start"])
            returning = _parse_date(overlap[0]["end"])

    if outbound is None or returning is None:
        raise InvalidTripDurationError(0)

    day_count = (returning - outbound).days + 1
    if not MIN_TRIP_DAYS <= day_count <= MAX_TRIP_DAYS:
        raise InvalidTripDurationError(day_count)
    return day_count


# ---------------------------------------------------------------------------
# Itinerary generation
# ---------------------------------------------------------------------------


def _generate_items(day_index: int) -> list[ItineraryItemModel]:
    """Generate a simple, deterministic set of items for one day.

    No LLM client exists yet under ``app/agents/`` (the same documented
    interim choice discovery_node made for candidate destinations). A real day
    plan needs the model's judgment about what to see and in what order; until
    that lands, each day gets a single well-formed placeholder activity so the
    itinerary object is structurally complete and immediately improvable once
    generation is wired in. Ordering (Requirement 9.6) and unique ids
    (Requirement 9.9) hold regardless of what fills each slot.
    """
    return [
        ItineraryItemModel(
            id=f"d{day_index}-i1",
            title="Free time to explore",
            description="The guide has not yet filled in this day's plan.",
        )
    ]


def _build_itinerary(
    trip_id: str,
    room_id: str,
    destination_selection: dict[str, Any],
    outbound: date,
    day_count: int,
) -> ItineraryModel:
    """Build the itinerary object for a fresh BUILD-stage version."""
    destination_data = destination_selection.get("data") or {}
    destination_title = destination_data.get("title", "the destination")

    days = [
        ItineraryDayModel(
            day=day_number,
            date=(outbound + timedelta(days=day_number - 1)).isoformat(),
            items=_generate_items(day_number),
        )
        for day_number in range(1, day_count + 1)
    ]

    return ItineraryModel(
        trip_id=trip_id,
        room_id=room_id,
        title=f"The {destination_title} Quest",
        summary=f"A {day_count}-day adventure to {destination_title}.",
        destination=DestinationRef(name=destination_title),
        dates=DateRange(
            start=outbound.isoformat(),
            end=(outbound + timedelta(days=day_count - 1)).isoformat(),
        ),
        days=days,
    )


async def _never_still_applicable(_latest: dict[str, Any]) -> bool:
    """A build's lost-race callback: there is no scope to re-check (see module docstring)."""
    return False


async def itinerary_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Draft the trip's first itinerary version for the BUILD stage.

    Raises:
        DestinationNotSelectedError: If no destination is locked
            (Requirement 9.11).
        FlightNotSelectedError: If no flight is locked (Requirement 9.11).
        PreferencesNotCollectedError: If no party member has submitted
            preferences (Requirement 9.12).
        InvalidTripDurationError: If the derived day count falls outside 1-30
            (Requirement 9.5).
        RepeatedVersionContentionError: After a 3rd lost-race collision
            (Requirement 5.12).
        ItineraryPersistenceError: If the insert fails for a non-contention
            reason (Requirement 5.13).
        TripNotFoundError: If the trip does not exist.
        StagePreconditionNotMetError: If the room is closed or past this stage.
    """
    repos: RepositoryBundle = config["configurable"]["repos"]

    context = await _load_context(state, repos)
    state = state.with_trip_context(context)

    destination_selection = context["selections"].get("destination")
    if destination_selection is None:
        raise DestinationNotSelectedError()
    flight_selection = context["selections"].get("flight")
    if flight_selection is None:
        raise FlightNotSelectedError()
    if not context["preferences"]:
        raise PreferencesNotCollectedError()

    profile = compute_group_profile(
        context["members"], context["preferences"], context["characters"]
    )
    state = state.with_group_profile(profile)

    day_count = _derive_day_count(flight_selection, profile)

    flight_data = flight_selection.get("data") or {}
    outbound = _parse_date(flight_data.get("depart_at") or flight_data.get("departAt"))
    if outbound is None:
        overlap = profile.get("availability_overlap") or []
        outbound = _parse_date(overlap[0]["start"]) if overlap else date.today()

    itinerary = _build_itinerary(
        state.trip_id, context["room_id"], destination_selection, outbound, day_count
    )
    proposal = ItineraryProposal(itinerary=itinerary, affected_scope={})
    state = state.with_proposal(proposal.model_dump(mode="json"))

    row, state = await persist_itinerary_version(
        state,
        repos,
        proposal.to_persistable(),
        source="build",
        change_summary=None,
        is_still_applicable=_never_still_applicable,
    )

    if row is None:
        # Requirement 5.6: another run already built this trip's first
        # version. The party's plan already moved on; say so and stop.
        await emit_npc_message(repos, state.trip_id, "text", _already_moved_on_text())
        return state

    await emit_npc_message(
        repos,
        state.trip_id,
        "summary",
        SummaryMessageContent(
            title=itinerary.title,
            text=itinerary.summary,
            stage=STAGE,
            itinerary_version_id=row["id"],
        ),
    )
    await advance_trip_status(
        repos, state.trip_id, "itinerary_generated", context["trip"]["status"]
    )

    return state


def _already_moved_on_text() -> Any:
    """Build the Requirement 5.6 ``kind='text'`` content for a lost first build."""
    from app.agents.messages import TextMessageContent

    return TextMessageContent(
        text="The party's plan already moved on, so this attempt made no changes.",
        stage=STAGE,
    )


async def _load_context(state: AgentState, repos: RepositoryBundle) -> dict[str, Any]:
    """Re-fetch the trip context fresh (Requirement 6.1-6.3)."""
    from app.agents.state import load_trip_context

    return await load_trip_context(repos, state.trip_id, state.run_type)
