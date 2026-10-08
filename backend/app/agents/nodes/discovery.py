"""Discovery_Node — DISCOVER stage destination recommendation.

The flow is five steps, each with exactly one way to fail without reaching the
next:

1. **Load fresh context, compute the Group_Profile.** Zero ``travel_preferences``
   rows is a hard failure (``PreferencesNotCollectedError``) — there is nothing
   to reason over, so no profile is even computed (Requirement 7.12).
2. **Escalate if the party shares no dates.** An empty availability overlap
   means no plan can be scheduled at all; escalating here, before any candidate
   work, avoids proposing a destination the party could never actually visit
   (Requirement 7.11).
3. **Seed and filter candidates.** ``travel_preferences.destinations`` seeds the
   set before anything model-generated (Requirement 7.5); hard constraints and
   the budget ceiling then exclude candidates (Requirement 7.9). An empty result
   escalates, naming whichever constraint did the eliminating (Requirement 7.10).
4. **Validate through the guardrail loop.** The same three-layer pipeline every
   proposal goes through, with the party's own repair/escalate budget
   (``Iteration_Cap``). An escalation from *this* step is handled identically to
   steps 2-3 from the node's point of view: nothing further is written.
5. **On success, emit the recommendation and open its vote.** One message, one
   paired ``vote_sessions`` row, with any prior open destination session closed
   first so at most one stays open per room (Requirement 7.6-7.8).

**On LLM-sourced candidates.** Requirement 7.5 only requires that
``travel_preferences.destinations`` entries are seeded *before* any
model-generated or tool-sourced candidate. The candidate set is therefore built
in three layers, in this order: the party's own destinations, then names the
LLM suggests for the remaining slots, then a small fixed fallback list
(``FALLBACK_CANDIDATES``) for whatever is still missing.

The LLM augments candidate generation; it is never a single point of failure
for the DISCOVER stage. If the call fails for any reason — no API key, a
timeout, a provider outage, a malformed answer — :func:`_generate_llm_candidates`
returns nothing, the node logs at ``info`` (a routine, expected path, not an
incident) and carries on with exactly the deterministic behaviour it had before
an LLM existed. Whatever the model suggests then goes through the same hard
constraint and budget filter as every other candidate, so a model that ignores
a stated constraint is caught here rather than reaching the party.

**Scope of the LLM call.** Only the *first* attempt gets LLM-sourced candidates.
The guardrail loop's repair iterations (``_producer`` below) re-gather candidates
deterministically: a repair must be fast and repeatable, and must not depend on
a second model call that might return something different from the proposal it
is trying to fix.

**Card copy (CR-1).** After filtering, one more LLM call scores and describes
the survivors, filling each item's ``description`` and ``meta`` (``score``,
``whyThisFits``, ``tags``, ``tradeOff``, ``details``). It fails soft the same
way: any destination the model skips, or whose copy mentions a hard-constraint
subject, gets plain deterministic copy instead. Repairs reuse that copy.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from app.agents.errors import LLMGenerationError, PreferencesNotCollectedError
from app.agents.group_profile import compute_group_profile
from app.agents.guardrails import perform_human_escalation, run_guardrail_loop
from app.agents.llm import UNTRUSTED_INPUT_GUARD, clip_for_prompt, clip_text
from app.agents.messages import RecommendationMessageContent, emit_npc_message
from app.agents.proposals import DestinationRecommendationProposal
from app.core.config import get_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import AgentState, RepositoryBundle

logger = logging.getLogger(__name__)

#: Requirement 7.6: a recommendation carries 3-5 items.
MIN_RECOMMENDATION_ITEMS = 3
MAX_RECOMMENDATION_ITEMS = 5

#: Used to top up the candidate set when neither the party's own
#: ``travel_preferences.destinations`` entries nor the LLM's suggestions reach the
#: minimum — the safety net that keeps DISCOVER working with no model available.
FALLBACK_CANDIDATES: tuple[str, ...] = ("Kyoto, Japan", "Lisbon, Portugal", "Reykjavik, Iceland")

#: A suggestion longer than this is not a destination name; treat it as junk.
MAX_DESTINATION_NAME_LENGTH = 80

#: Requirement 7.7: the vote question's length bound.
MAX_QUESTION_LENGTH = 200

STAGE = "DISCOVER"

#: Card copy limits (CR-1): the frontend renders these on a small pixel card.
MAX_TAGS = 5
MAX_TAG_LENGTH = 24
MAX_DESCRIPTION_TEXT = 300
MAX_REASONING_TEXT = 600
MAX_DETAILS_TEXT = 1500

#: Fallback fit scores when no model is available: a destination someone in the
#: party wish-listed is a stronger signal than a guide suggestion.
WISHLIST_SCORE = 85
SUGGESTED_SCORE = 70


def _slugify(name: str) -> str:
    """Turn a destination name into a short, stable item id."""
    return "".join(ch if ch.isalnum() else "-" for ch in name.lower()).strip("-") or "option"


def _gather_candidates(group_profile: dict[str, Any]) -> list[str]:
    """Seed candidates from the party's own destinations, then top up.

    Requirement 7.5: every ``travel_preferences.destinations`` entry comes
    first, in the order ``compute_group_profile`` already de-duplicated them in.
    """
    seeded = list(group_profile.get("destinations") or [])
    candidates = list(seeded)
    for fallback in FALLBACK_CANDIDATES:
        if len(candidates) >= MAX_RECOMMENDATION_ITEMS:
            break
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


class _CandidateList(BaseModel):
    """The LLM's answer: destination names only (everything else is built here).

    The upper bound is the recommendation maximum rather than the number asked
    for: a model that over-delivers is truncated by the caller, not failed.
    """

    model_config = ConfigDict(extra="forbid")

    destinations: list[str] = Field(min_length=1, max_length=MAX_RECOMMENDATION_ITEMS)


def _clean_destination_name(raw: Any) -> str | None:
    """Return a usable destination name, or ``None`` if the model's entry is junk."""
    name = " ".join(str(raw).split()).strip(" .,-")
    if not 2 <= len(name) <= MAX_DESTINATION_NAME_LENGTH:
        return None
    return name


async def _generate_llm_candidates(
    group_profile: dict[str, Any],
    llm: Any,
    exclude: list[str],
    needed: int,
) -> list[str]:
    """Ask the LLM for up to ``needed`` additional destination names.

    Returns an empty list — never raises — on any failure, so the caller's
    fallback to ``FALLBACK_CANDIDATES`` is the only error-handling path
    ``discovery_node`` needs.
    """
    if llm is None or needed <= 0:
        return []

    overlap = group_profile.get("availability_overlap") or []
    window = f"{overlap[0].get('start')} to {overlap[0].get('end')}" if overlap else "unspecified"
    ceiling = group_profile.get("budget_ceiling")
    system_prompt = (
        f"{UNTRUSTED_INPUT_GUARD}\n\n"
        "You are an in-world NPC travel guide for a group trip-planning game. "
        "Suggest real-world travel destinations, each written as 'City, Country', that fit "
        "the party's combined interests, activities and travel styles, and are sensible for "
        "their travel window and budget. Never suggest a destination that violates a stated "
        "hard constraint. Return destination names only."
    )
    user_prompt = (
        f"Party size: {group_profile.get('member_count') or 'unknown'}\n"
        f"Travel window: {window}\n"
        f"Budget ceiling per person: {ceiling if ceiling is not None else 'none stated'}\n"
        f"Interests: {clip_for_prompt(group_profile.get('interests'))}\n"
        f"Activities: {clip_for_prompt(group_profile.get('activities'))}\n"
        f"Travel styles: {clip_for_prompt(group_profile.get('travel_styles'))}\n"
        f"Hard constraints: {clip_for_prompt(group_profile.get('hard_constraints'))}\n"
        f"Already suggested (do not repeat): {clip_for_prompt(exclude)}\n"
        f"Suggest exactly {needed} new destination(s)."
    )
    try:
        result = await llm.generate_structured(
            operation="destination_candidates",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=_CandidateList,
        )
        raw_names = result.destinations
    except LLMGenerationError:
        logger.info("LLM candidate generation unavailable; using fallback list")
        return []
    except Exception:  # a malformed double or SDK surprise must not break DISCOVER
        logger.info("LLM candidate generation returned an unusable result; using fallback list")
        return []

    names: list[str] = []
    seen = {name.lower() for name in exclude}
    for raw in raw_names:
        name = _clean_destination_name(raw)
        if name is not None and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name)
    return names[:needed]


def _negated_subject(constraint: str) -> str | None:
    """Extract the forbidden subject from a negative constraint.

    Mirrors ``app.agents.guardrails.business._negated_constraint``: a
    constraint phrased as a prohibition (``"no "``, ``"not "``, ``"avoid "``,
    ``"without "``, ``"never "``) yields the subject it forbids; anything else
    is a preference, not something a candidate name can be checked against.
    """
    lowered = constraint.strip().lower()
    for prefix in ("no ", "not ", "avoid ", "without ", "never "):
        if lowered.startswith(prefix):
            return lowered[len(prefix) :].strip() or None
    return None


def _violates_hard_constraints(name: str, hard_constraints: list[str]) -> str | None:
    """Return the violated constraint's text, or ``None`` if the candidate is clear.

    A blunt case-insensitive substring scan against the constraint's forbidden
    subject — matching the same bluntness the business guardrail itself uses —
    so a false positive here only costs a repair iteration, while a false
    negative would hand the party something they explicitly ruled out.
    """
    lowered = name.lower()
    for constraint in hard_constraints:
        subject = _negated_subject(str(constraint))
        if subject and subject in lowered:
            return str(constraint)
    return None


def _estimate_cost(name: str, group_profile: dict[str, Any]) -> float | None:
    """Estimate a candidate's per-member cost.

    No pricing tool is wired yet, so this returns ``None`` (unestimated) for
    every candidate rather than inventing a figure — an unestimated candidate is
    never excluded by the budget filter below, exactly like an unconstrained
    ceiling never excludes anything. When a pricing tool lands, this is the one
    function that needs to change.
    """
    return None


def _filter_candidates(
    candidates: list[str], group_profile: dict[str, Any]
) -> tuple[list[str], str | None]:
    """Apply hard constraints and the budget ceiling (Requirement 7.9).

    Returns:
        ``(surviving_candidates, eliminating_reason)``. ``eliminating_reason`` is
        set only when filtering emptied the set, naming the constraint or the
        ceiling for the escalation message (Requirement 7.10).
    """
    hard_constraints = [str(c) for c in (group_profile.get("hard_constraints") or [])]
    ceiling = group_profile.get("budget_ceiling")

    survivors: list[str] = []
    last_violated_constraint: str | None = None
    for name in candidates:
        violated = _violates_hard_constraints(name, hard_constraints)
        if violated is not None:
            last_violated_constraint = violated
            continue
        cost = _estimate_cost(name, group_profile)
        if ceiling is not None and cost is not None and cost > float(ceiling):
            continue
        survivors.append(name)

    if survivors:
        return survivors, None

    if last_violated_constraint is not None:
        return [], f"the hard constraint {last_violated_constraint!r}"
    if ceiling is not None:
        return [], f"the party's budget ceiling of {ceiling}"
    return [], "the party's current constraints"


class _DestinationInsight(BaseModel):
    """The LLM's card copy for one destination (CR-1)."""

    model_config = ConfigDict(extra="ignore")

    name: str
    score: int
    description: str = ""
    why_this_fits: str = ""
    tags: list[str] = Field(default_factory=list)
    trade_off: str = ""
    details: str = ""


class _DestinationInsights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    insights: list[_DestinationInsight] = Field(min_length=1)


def _forbidden_subjects(group_profile: dict[str, Any]) -> list[str]:
    subjects = (_negated_subject(str(c)) for c in group_profile.get("hard_constraints") or [])
    return [s for s in subjects if s]


def _clean_tags(raw: Any) -> list[str]:
    tags: list[str] = []
    for value in raw or []:
        tag = clip_text(str(value), MAX_TAG_LENGTH)
        if tag and tag.lower() not in {t.lower() for t in tags}:
            tags.append(tag)
    return tags[:MAX_TAGS]


def _fallback_card(name: str, group_profile: dict[str, Any]) -> dict[str, Any]:
    """Deterministic card copy used when the LLM is unavailable or unusable."""
    wished = name.lower() in {str(d).lower() for d in group_profile.get("destinations") or []}
    overlap = group_profile.get("availability_overlap") or []
    ceiling = group_profile.get("budget_ceiling")
    window = f"{overlap[0].get('start')} to {overlap[0].get('end')}" if overlap else None
    details = " ".join(
        part
        for part in (
            f"Shared travel window: {window}." if window else "",
            f"Budget up to {ceiling} per person." if ceiling is not None else "",
        )
        if part
    )
    why = (
        "Someone in the party put this on their wish list."
        if wished
        else "Suggested by the guide to round out the party's options."
    )
    return {
        "description": why,
        "meta": {
            "score": WISHLIST_SCORE if wished else SUGGESTED_SCORE,
            "whyThisFits": why,
            "tags": ["Party wish list"] if wished else ["Guide's pick"],
            "tradeOff": "No cost estimate yet; check prices before you vote.",
            "details": details or why,
        },
    }


def _card_from_insight(insight: _DestinationInsight, forbidden: list[str]) -> dict[str, Any] | None:
    """Turn one model insight into card copy, or ``None`` if it is unusable.

    Copy that mentions a hard-constraint subject is dropped: the business
    guardrail scans item text, so it would reject the whole proposal.
    """
    why = clip_text(insight.why_this_fits, MAX_REASONING_TEXT)
    description = clip_text(insight.description, MAX_DESCRIPTION_TEXT) or why
    if why is None or description is None:
        return None
    card = {
        "description": description,
        "meta": {
            "score": max(0, min(100, int(insight.score))),
            "whyThisFits": why,
            "tags": _clean_tags(insight.tags),
            "tradeOff": clip_text(insight.trade_off, MAX_REASONING_TEXT) or "",
            "details": clip_text(insight.details, MAX_DETAILS_TEXT) or description,
        },
    }
    text = " ".join(
        [card["description"], why, card["meta"]["tradeOff"], card["meta"]["details"]]
        + card["meta"]["tags"]
    ).lower()
    if any(subject in text for subject in forbidden):
        return None
    return card


async def _generate_insights(
    candidates: list[str], group_profile: dict[str, Any], llm: Any
) -> dict[str, dict[str, Any]]:
    """Ask the LLM to score and describe each candidate (CR-1).

    Returns card copy keyed by lower-cased name. Never raises: a failure, or a
    candidate the model skipped, simply gets :func:`_fallback_card` later.
    """
    if llm is None or not candidates:
        return {}

    overlap = group_profile.get("availability_overlap") or []
    window = f"{overlap[0].get('start')} to {overlap[0].get('end')}" if overlap else "unspecified"
    ceiling = group_profile.get("budget_ceiling")
    system_prompt = (
        f"{UNTRUSTED_INPUT_GUARD}\n\n"
        "You are an in-world NPC travel guide for a group trip-planning game. For each "
        "destination given, judge how well it fits the whole party and write card copy that "
        "helps them decide. Be specific and concrete; avoid generic praise.\n"
        "- score: 0-100 fit for the party (interests, activities, styles, budget, dates). "
        "Spread the scores so the best fit clearly stands out.\n"
        "- description: 1-2 sentences capturing the place's character.\n"
        "- why_this_fits: 2-3 sentences naming the party's own interests, activities and "
        "travel styles it matches, with real examples (a district, dish, beach or "
        "activity), and how it suits their budget and travel window.\n"
        "- tags: 3-5 short labels (1-3 words each), e.g. Budget, Low crowds, Nightlife.\n"
        "- trade_off: 1-2 sentences on the most important downside for this party and how "
        "they could work around it.\n"
        "- details: 4-6 sentences covering the weather in their travel window, the top "
        "things to do for this party, the food scene, a rough daily cost per person "
        "compared with their budget, and where to stay or how to get around.\n"
        "Use the destination name exactly as given. Never mention or recommend anything a "
        "hard constraint rules out."
    )
    user_prompt = (
        f"Party size: {group_profile.get('member_count') or 'unknown'}\n"
        f"Travel window: {window}\n"
        f"Budget ceiling per person: {ceiling if ceiling is not None else 'none stated'}\n"
        f"Interests: {clip_for_prompt(group_profile.get('interests'))}\n"
        f"Activities: {clip_for_prompt(group_profile.get('activities'))}\n"
        f"Travel styles: {clip_for_prompt(group_profile.get('travel_styles'))}\n"
        f"Hard constraints: {clip_for_prompt(group_profile.get('hard_constraints'))}\n"
        f"Party wish list: {clip_for_prompt(group_profile.get('destinations'))}\n"
        f"Destinations to describe: {clip_for_prompt(candidates)}"
    )
    try:
        result = await llm.generate_structured(
            operation="destination_insights",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=_DestinationInsights,
        )
        insights = list(result.insights)
    except LLMGenerationError:
        logger.info("LLM destination insights unavailable; using fallback card copy")
        return {}
    except Exception:  # a malformed double or SDK surprise must not break DISCOVER
        logger.info("LLM destination insights were unusable; using fallback card copy")
        return {}

    wanted = {name.lower() for name in candidates}
    forbidden = _forbidden_subjects(group_profile)
    cards: dict[str, dict[str, Any]] = {}
    for insight in insights:
        key = " ".join(str(insight.name).split()).strip(" .,-").lower()
        if key in wanted and key not in cards:
            card = _card_from_insight(insight, forbidden)
            if card is not None:
                cards[key] = card
    return cards


def _build_proposal(
    candidates: list[str],
    group_profile: dict[str, Any] | None = None,
    insights: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a raw destination recommendation payload from candidate names.

    Each item carries CR-1 card copy: ``description`` plus ``meta`` with
    ``score``, ``whyThisFits``, ``tags``, ``tradeOff`` and ``details``.
    """
    profile = group_profile or {}
    items = []
    for name in candidates[:MAX_RECOMMENDATION_ITEMS]:
        card = (insights or {}).get(name.lower()) or _fallback_card(name, profile)
        items.append(
            {
                "id": _slugify(name),
                "title": name,
                "description": card["description"],
                "meta": dict(card["meta"]),
            }
        )
    return {
        "title": "Where shall our journey begin?",
        "items": items,
        "question": "Which destination calls to the party?"[:MAX_QUESTION_LENGTH],
    }


async def _gather_candidates_with_llm(group_profile: dict[str, Any], llm: Any) -> list[str]:
    """Seed from the party, fill from the LLM, then top up from the fixed list.

    Equivalent to :func:`_gather_candidates` when ``llm`` is ``None`` or fails.
    """
    candidates = list(group_profile.get("destinations") or [])
    needed = MAX_RECOMMENDATION_ITEMS - len(candidates)
    for name in await _generate_llm_candidates(group_profile, llm, candidates, needed):
        if len(candidates) < MAX_RECOMMENDATION_ITEMS:
            candidates.append(name)
    for fallback in FALLBACK_CANDIDATES:
        if len(candidates) >= MAX_RECOMMENDATION_ITEMS:
            break
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


async def discovery_node(state: AgentState, config: RunnableConfig) -> AgentState:
    """Produce a destination recommendation for the DISCOVER stage.

    Raises:
        PreferencesNotCollectedError: If the room has no travel preferences at
            all (Requirement 7.12). No profile is computed, nothing is written.
        TripNotFoundError: If the trip does not exist.
        StagePreconditionNotMetError: If the room is closed or past this stage.
    """
    repos: RepositoryBundle = config["configurable"]["repos"]

    context = await _load_context(state, repos)
    state = state.with_trip_context(context)

    if not context["preferences"]:
        raise PreferencesNotCollectedError()

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

    candidates = await _gather_candidates_with_llm(profile, repos.llm)
    survivors, eliminating_reason = _filter_candidates(candidates, profile)
    if not survivors:
        await perform_human_escalation(
            state,
            repos,
            constraint=f"every candidate destination was eliminated by {eliminating_reason}",
            question="Would the party like to relax that constraint?",
            options=[
                ("relax_constraint", "Relax that constraint"),
                ("raise_budget", "Raise our budget"),
            ],
        )
        return state

    cap = get_settings().iteration_cap

    async def _producer(repair_state: AgentState) -> dict[str, Any]:
        """Re-load context and recompute candidates, honoring Requirement 6.3."""
        fresh_context = await _load_context(repair_state, repos)
        fresh_profile = compute_group_profile(
            fresh_context["members"], fresh_context["preferences"], fresh_context["characters"]
        )
        fresh_candidates = _gather_candidates(fresh_profile)
        fresh_survivors, _reason = _filter_candidates(fresh_candidates, fresh_profile)
        # Reuse the first attempt's card copy: a repair must not call the model again.
        return _build_proposal(fresh_survivors or survivors, fresh_profile, insights)

    insights = await _generate_insights(survivors[:MAX_RECOMMENDATION_ITEMS], profile, repos.llm)
    loop_outcome = await run_guardrail_loop(
        state,
        repos,
        _build_proposal(survivors, profile, insights),
        "destination_recommendation",
        _producer,
        cap,
    )
    state = loop_outcome.state

    if loop_outcome.escalated:
        return state

    proposal: DestinationRecommendationProposal = loop_outcome.proposal
    state = state.with_proposal(proposal.model_dump(mode="json"))

    await _close_prior_vote_session(repos, context["room_id"])
    message = await emit_npc_message(
        repos,
        state.trip_id,
        "recommendation",
        RecommendationMessageContent(
            title=proposal.title,
            category="destination",
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
    """Close any open destination vote session before opening a new one.

    Requirement 7.8: at most one open destination session per room.
    """
    existing = await repos.vote_session_repo.get_open_by_room_and_category(room_id, "destination")
    if existing is not None:
        await repos.vote_session_repo.close(existing["id"])
