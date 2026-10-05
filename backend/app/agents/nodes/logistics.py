"""Logistics_Node — LOGISTICS stage flight recommendation.

Mirrors discovery_node's shape (load context, compute profile, escalate on an
unworkable precondition, otherwise filter/rank candidates, validate through the
guardrail loop, emit + vote), with one real addition: this node calls an
``External_Tool`` for its factual data instead of relying only on preferences.

1. **Load context, require a locked destination.** Flights are arranged
   *for* a destination, so a missing ``kind='destination'`` selection fails
   the run outright, before any tool call (Requirement 8.1-8.2).
2. **Escalate before touching the flight tool, not after.** Both pre-tool
   escalation paths — an empty availability overlap and an unresolved
   departure origin — are checked first (Requirement 8.10-8.11); the whole
   point of checking first is that ``FlightSearchTool`` is never invoked for
   a request that cannot be formed, which also means it never spends the
   run's ``Tool_Call_Cap`` on a call that was going to be escalated anyway.
3. **Call the tool once, then filter and rank.** Exclusions are over budget
   or outside the overlap, never both inputs required at once — an
   unconstrained budget excludes nothing (Requirement 8.6). An empty result
   escalates, naming whichever bound did the eliminating (Requirement 8.7).
   Survivors are sorted ``(price, duration, stops)`` ascending before ever
   reaching the guardrail (Requirement 8.8), since ranking is this node's job,
   not the model's.
4. **Validate through the guardrail loop**, exactly like discovery.
5. **On success, emit the recommendation and open its vote**, closing any
   prior open *flight*-category session first (Requirement 8.4-8.5, 8.9).

**On the departure origin (Backend Change Request Entry 1).** No typed column
holds a party's departure origin yet. Per the filed change request, this node
reads a conventioned ``travel_preferences.hard_constraints`` entry shaped
``{"type": "departure_origin", "value": "<IATA or city>"}``. Absence is an
escalation, never a guess from model output or from the destination
(Requirement 8.11) — guessing an origin would mean searching flights from a
place no one in the party may be starting from.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig

from app.agents.errors import DestinationNotSelectedError
from app.agents.group_profile import compute_group_profile
from app.agents.guardrails import perform_human_escalation, run_guardrail_loop
from app.agents.messages import RecommendationMessageContent, emit_npc_message
from app.agents.proposals import FlightRecommendationProposal
from app.agents.tools.base import FlightOption
from app.agents.tools.flights import FlightSearchTool
from app.core.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import AgentState, RepositoryBundle

logger = logging.getLogger(__name__)

#: Requirement 8.4: a recommendation carries 3-5 items.
MIN_RECOMMENDATION_ITEMS = 3
MAX_RECOMMENDATION_ITEMS = 5

#: Requirement 8.5: the vote question's length bound.
MAX_QUESTION_LENGTH = 200

STAGE = "LOGISTICS"

#: Backend Change Request Entry 1: the conventioned ``hard_constraints`` entry
#: naming a departure origin, pending a typed ``travel_preferences.origin``
#: column.
_DEPARTURE_ORIGIN_TYPE = "departure_origin"


def _resolve_departure_origin(preferences: list[dict[str, Any]]) -> str | None:
    """Read the party's departure origin from a conventioned hard constraint.

    Reads the *raw* ``travel_preferences`` rows rather than
    ``Group_Profile.hard_constraints``: ``compute_group_profile`` flattens that
    column to display strings via ``_string_entries`` (it only recognises
    ``name``/``label``/``title``/``activity`` keys), which silently drops a
    ``{"type": "departure_origin", "value": ...}`` entry. Reading the raw rows
    here avoids depending on a lossy derivation for data this convention needs
    intact.

    Returns ``None`` when absent — the caller escalates rather than guessing
    (Requirement 8.11). Never inferred from model output or from the
    destination.
    """
    for preference in preferences:
        constraints = preference.get("hard_constraints")
        if not isinstance(constraints, list):
            continue
        for constraint in constraints:
            if isinstance(constraint, dict) and constraint.get("type") == _DEPARTURE_ORIGIN_TYPE:
                value = constraint.get("value")
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


def _option_cost(option: FlightOption) -> float:
    """The per-member price this node ranks and filters on."""
    return option.price


def _within_overlap(option: FlightOption, overlap: list[dict[str, str]]) -> bool:
    """Return ``True`` when the option's departure falls within the overlap.

    An empty ``overlap`` means no shared dates exist at all, which the caller
    has already escalated on before this function is ever reached — so this
    only decides membership for a non-empty overlap.
    """
    depart_date = option.depart_at.split("T", 1)[0]
    return any(entry["start"] <= depart_date <= entry["end"] for entry in overlap)


def _filter_and_rank(
    options: list[FlightOption], group_profile: dict[str, Any]
) -> tuple[list[FlightOption], str | None]:
    """Apply Requirement 8.6's exclusions, then Requirement 8.8's ordering.

    Returns:
        ``(survivors_sorted, eliminating_reason)``. ``eliminating_reason`` is
        set only when filtering emptied the set (Requirement 8.7).
    """
    ceiling = group_profile.get("budget_ceiling")
    overlap = group_profile.get("availability_overlap") or []

    survivors: list[FlightOption] = []
    excluded_by_budget = False
    excluded_by_dates = False
    for option in options:
        if ceiling is not None and _option_cost(option) > float(ceiling):
            excluded_by_budget = True
            continue
        if not _within_overlap(option, overlap):
            excluded_by_dates = True
            continue
        survivors.append(option)

    if survivors:
        ranked = sorted(survivors, key=lambda o: (o.price, o.duration_minutes, o.stops))
        return ranked, None

    if excluded_by_budget:
        return [], f"the party's budget ceiling of {ceiling}"
    if excluded_by_dates:
        return [], "the party's available travel dates"
    return [], "the party's current constraints"


def _build_proposal(options: list[FlightOption]) -> dict[str, Any]:
    """Build a raw flight recommendation payload from ranked options."""
    items = [
        {
            "id": option.id,
            "title": f"{option.carrier} {option.flight_number}",
            "meta": {
                "flight_id": option.id,
                "carrier": option.carrier,
                "flight_number": option.flight_number,
                "origin": option.origin,
                "destination": option.destination,
                "depart_at": option.depart_at,
                "arrive_at": option.arrive_at,
                "price": option.price,
                "duration_minutes": option.duration_minutes,
                "stops": option.stops,
                # The itinerary sizes the trip from depart_at / return_at.
                "return_at": option.return_depart_at,
                "return_arrive_at": option.return_arrive_at,
            },
        }
        for option in options[:MAX_RECOMMENDATION_ITEMS]
    ]
    return {
        "title": "How shall the party travel?",
        "items": items,
        "question": "Which flight suits the party best?"[:MAX_QUESTION_LENGTH],
    }


async def logistics_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Produce a flight recommendation for the LOGISTICS stage.

    Raises:
        DestinationNotSelectedError: If no destination is locked in yet
            (Requirement 8.2). No flight-tool call, no write.
        TripNotFoundError: If the trip does not exist.
        StagePreconditionNotMetError: If the room is closed or past this stage.
    """
    repos: RepositoryBundle = config["configurable"]["repos"]

    context = await _load_context(state, repos)
    state = state.with_trip_context(context)

    destination_selection = context["selections"].get("destination")
    if destination_selection is None:
        raise DestinationNotSelectedError()

    profile = compute_group_profile(
        context["members"], context["preferences"], context["characters"]
    )
    state = state.with_group_profile(profile)

    if not profile["availability_overlap"]:
        await perform_human_escalation(
            state,
            repos,
            constraint="no shared travel dates exist across the party",
            question="Would the party like to widen their available dates?",
            options=[("widen_dates", "Widen our available dates")],
        )
        return state

    origin = _resolve_departure_origin(context["preferences"])
    if origin is None:
        await perform_human_escalation(
            state,
            repos,
            constraint="no departure origin has been given for the party",
            question="Where shall the party's journey begin?",
            options=[("set_origin", "Tell the guide where we're departing from")],
        )
        return state

    destination_data = destination_selection.get("data") or {}
    # Vote options (and so the locked selection) carry "label"; accept "title" too.
    destination_name = destination_data.get("title") or destination_data.get("label") or ""
    search_params = {
        "origin": origin,
        "destination": destination_name,
        "depart_after": (profile["availability_overlap"][0]["start"]),
        "depart_before": (profile["availability_overlap"][-1]["end"]),
    }

    tool = FlightSearchTool()
    response, state = await tool.invoke(state, **search_params)

    survivors, eliminating_reason = _filter_and_rank(response.options, profile)
    if not survivors:
        await perform_human_escalation(
            state,
            repos,
            constraint=f"every flight option was eliminated by {eliminating_reason}",
            question="Would the party like to relax that constraint?",
            options=[
                ("relax_budget", "Raise our budget"),
                ("widen_dates", "Widen our available dates"),
            ],
        )
        return state

    cap = get_settings().iteration_cap

    async def _producer(repair_state: AgentState) -> dict[str, Any]:
        """Re-load context and re-rank from the already-recorded tool response.

        The flight tool is not called again on a repair iteration: its
        response was already recorded in state by the initial call above, and
        Requirement 19.9 treats an identical call as a cache hit anyway — this
        just skips the round trip entirely by reusing the already-filtered
        ``survivors`` rather than re-deriving them from a fresh profile that,
        for flights already in hand, would not change their price or dates.
        """
        await _load_context(repair_state, repos)
        return _build_proposal(survivors)

    loop_outcome = await run_guardrail_loop(
        state,
        repos,
        _build_proposal(survivors),
        "flight_recommendation",
        _producer,
        cap,
    )
    state = loop_outcome.state

    if loop_outcome.escalated:
        return state

    proposal: FlightRecommendationProposal = loop_outcome.proposal
    state = state.with_proposal(proposal.model_dump(mode="json"))

    await _close_prior_vote_session(repos, context["room_id"])
    message = await emit_npc_message(
        repos,
        state.trip_id,
        "recommendation",
        RecommendationMessageContent(
            title=proposal.title,
            category="flight",
            items=[item.model_dump(mode="json") for item in proposal.items],
            prompt=proposal.prompt,
            stage=STAGE,
        ),
    )
    await repos.vote_session_repo.create(
        room_id=context["room_id"],
        message_id=message["id"],
        question=proposal.question,
        options=[{"id": item.id, "label": item.title} for item in proposal.items],
    )

    return state


async def _load_context(state: AgentState, repos: RepositoryBundle) -> dict[str, Any]:
    """Re-fetch the trip context fresh (Requirement 6.1-6.3)."""
    from app.agents.state import load_trip_context

    return await load_trip_context(repos, state.trip_id, state.run_type)


async def _close_prior_vote_session(repos: RepositoryBundle, room_id: str) -> None:
    """Close any open flight vote session before opening a new one.

    Requirement 8.9: at most one open flight session per room.
    """
    existing = await repos.vote_session_repo.get_open_by_room_and_category(room_id, "flight")
    if existing is not None:
        await repos.vote_session_repo.close(existing["id"])
