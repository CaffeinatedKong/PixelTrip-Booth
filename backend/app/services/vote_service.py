"""Vote casting and resolution: the `Tiebreak_Flow` and its triggers.

A vote session resolves exactly one way, computed by plain code
(:func:`resolve_vote_session`) with no LLM or graph involvement
(Requirement 17.7) — resolution is a tally and a deterministic tiebreak, not a
decision the agent reasons about. Two independent triggers call into it:

* **Full participation** (:func:`on_vote_cast`, Requirement 17.11): every member
  still in the room has voted.
* **Owner-triggered early close** (:func:`close_session`, Requirement 17.12):
  the room's owner closes voting before everyone has responded, and resolution
  uses whatever is persisted at that moment.

Both funnel into the same :func:`resolve_vote_session`, so there is exactly one
place the winner-selection rule, the tie message, and the selection write live.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from app.agents.errors import UnresolvedMemberError, VoteSessionClosedError
from app.agents.messages import SummaryMessageContent, build_message_row
from app.services.trip_status_service import advance_trip_status

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import RepositoryBundle

#: ``selections.kind`` a resolved vote locks in, keyed by the recommendation
#: category the vote session's linked message carried.
_KIND_BY_CATEGORY: dict[str, str] = {"destination": "destination", "flight": "flight"}

#: Requirement 17.4-17.5: the trip status set when each kind of selection locks in.
_STATUS_BY_KIND: dict[str, str] = {
    "destination": "destination_selected",
    "flight": "flight_selected",
}


@dataclass(frozen=True)
class TieNote:
    """Describes a tie the `Tiebreak_Flow` broke.

    Attributes:
        tied_ids: Every option id that held the highest count.
        tied_count: That shared highest count.
        winner_id: The option the `Option_Index_Rule` selected.
    """

    tied_ids: list[str]
    tied_count: int
    winner_id: str


@dataclass(frozen=True)
class VoteResolution:
    """The result of resolving one vote session.

    Attributes:
        winning_option: The ``{id, ...}`` option payload that won.
        category: ``"destination"`` or ``"flight"``.
        tie: The tie detail, or ``None`` when one option led outright.
        selection: The written ``selections`` row.
        closed_session: The closed ``vote_sessions`` row.
    """

    winning_option: dict[str, Any]
    category: str
    tie: TieNote | None
    selection: dict[str, Any]
    closed_session: dict[str, Any]


def _resolve_category(vote_session: dict[str, Any], message: dict[str, Any] | None) -> str:
    """Resolve a session's category from its linked recommendation message.

    Category is not a column on ``vote_sessions``; it lives in the linked
    message's ``content.category``. Falls back to the session's own
    ``category`` key (set by callers that already know it, e.g. tests) so this
    does not hard-require a message round trip when the caller already has the
    answer.
    """
    content = (message or {}).get("content") or {}
    category = content.get("category") or vote_session.get("category")
    if category not in _KIND_BY_CATEGORY:
        raise ValueError(f"Could not resolve a vote session category from {vote_session!r}")
    return category


def pick_winner(
    counts: dict[str, int], options: list[dict[str, Any]]
) -> tuple[dict[str, Any], TieNote | None]:
    """Apply the `Option_Index_Rule` to a tally.

    Requirement 17.6-17.8: the winner is the option with the strictly highest
    count; a tie is broken by the lowest zero-based index in ``options``, using
    only the persisted array and the tally — no randomness, no clock, so
    re-running this over the same inputs always yields the same winner.

    Args:
        counts: ``{option_id: count}``, already restricted to eligible voters.
        options: The session's ``options`` array, in its persisted order.

    Returns:
        ``(winning_option, tie_note)``. ``tie_note`` is ``None`` unless two or
        more options shared the highest count.

    Raises:
        ValueError: If no option received any vote (an empty tally has no
            winner to pick).
    """
    if not counts:
        raise ValueError("cannot pick a winner from an empty tally")

    highest = max(counts.values())
    winners = [option_id for option_id, count in counts.items() if count == highest]
    ordered_ids = [opt["id"] for opt in options]
    winning_id = min(winners, key=ordered_ids.index)
    winning_option = next(opt for opt in options if opt["id"] == winning_id)

    tie = (
        TieNote(tied_ids=winners, tied_count=highest, winner_id=winning_id)
        if len(winners) > 1
        else None
    )
    return winning_option, tie


async def resolve_vote_session(
    repos: RepositoryBundle,
    vote_session: dict[str, Any],
) -> VoteResolution:
    """Resolve ``vote_session``: tally, tiebreak, write, close, and advance status.

    The tally restricts counts to members still present in the room
    (Requirement 17.6), so a member who left after voting cannot decide the
    outcome. The selection write and the session close are not expressed as a
    single database transaction here — both repositories issue independent
    calls — but both happen unconditionally in sequence with no intervening
    branch, so a failure between them is a `RepositoryError` the caller sees
    directly rather than a half-applied state this function hides.

    Args:
        repos: The repository bundle.
        vote_session: The session row to resolve. Must be ``status='open'``;
            callers are expected to have confirmed that before calling.

    Returns:
        A :class:`VoteResolution` describing the winner, the write, and any tie.
    """
    message = (
        await repos.message_repo.get_by_id(vote_session["message_id"])
        if vote_session.get("message_id")
        else None
    )
    category = _resolve_category(vote_session, message)

    members = await repos.member_repo.list_by_room(vote_session["room_id"])
    eligible_ids = [m["id"] for m in members]

    counts = await repos.vote_repo.count_by_option(vote_session["id"], eligible_ids)
    winning_option, tie = pick_winner(counts, vote_session["options"])

    kind = _KIND_BY_CATEGORY[category]
    selection = await repos.selection_repo.upsert(
        room_id=vote_session["room_id"],
        kind=kind,
        data=winning_option,
        vote_session_id=vote_session["id"],
    )
    closed_session = await repos.vote_session_repo.close(vote_session["id"])

    if tie is not None:
        content = SummaryMessageContent(
            title="A tie, broken",
            text=f"The vote was tied; {winning_option.get('title', winning_option['id'])} wins.",
            details={
                "tied_ids": tie.tied_ids,
                "tied_count": tie.tied_count,
                "winner": tie.winner_id,
                "category": category,
            },
        )
        await repos.message_repo.insert_turn(
            vote_session["room_id"], [build_message_row("summary", content)]
        )

    trip = await repos.trip_repo.get_by_room_id(vote_session["room_id"])
    if trip is not None:
        await advance_trip_status(
            repos, trip["id"], _STATUS_BY_KIND[kind], trip.get("status", "trip_created")
        )

    return VoteResolution(
        winning_option=winning_option,
        category=category,
        tie=tie,
        selection=selection,
        closed_session=closed_session,
    )


async def cast_vote(
    repos: RepositoryBundle,
    vote_session_id: str,
    member_id: str,
    option_id: str,
) -> dict[str, Any]:
    """Record one member's vote, then resolve the session if everyone has voted.

    Rejects before any write when the session is already closed
    (Requirement 17.13) or when ``member_id`` does not resolve to a real
    ``room_members`` row (Requirement 22.2-22.3) — a forged id must never reach
    ``votes``.

    Args:
        repos: The repository bundle.
        vote_session_id: The session being voted on.
        member_id: The voting member's id, as resolved by the caller against
            the triggering identity — not trusted here without a lookup.
        option_id: The chosen option's id.

    Returns:
        The inserted ``votes`` row.

    Raises:
        VoteSessionClosedError: If the session is not open.
        UnresolvedMemberError: If ``member_id`` is not a real room member.
    """
    session = await repos.vote_session_repo.get_by_id(vote_session_id)
    if session is None or session.get("status") != "open":
        raise VoteSessionClosedError(vote_session_id)

    member = await repos.member_repo.get_by_id(member_id)
    if member is None or member.get("room_id") != session.get("room_id"):
        raise UnresolvedMemberError(member_id)

    vote = await repos.vote_repo.upsert(vote_session_id, member_id, option_id)

    members = await repos.member_repo.list_by_room(session["room_id"])
    voter_count = await repos.vote_repo.count_distinct_voters(
        vote_session_id, [m["id"] for m in members]
    )
    if members and voter_count == len(members):
        await resolve_vote_session(repos, session)

    return vote


async def close_session(
    repos: RepositoryBundle,
    vote_session_id: str,
    requesting_member_id: str,
) -> VoteResolution:
    """Resolve ``vote_session_id`` early, at the room owner's request.

    Resolution uses only the votes persisted at the moment of the call
    (Requirement 17.12) — it does not wait for remaining members.

    Args:
        repos: The repository bundle.
        vote_session_id: The session to close.
        requesting_member_id: The member requesting closure. Must be the room's
            owner.

    Returns:
        The resolution.

    Raises:
        VoteSessionClosedError: If the session is not open.
        UnresolvedMemberError: If the requester is not the room's owner.
    """
    session = await repos.vote_session_repo.get_by_id(vote_session_id)
    if session is None or session.get("status") != "open":
        raise VoteSessionClosedError(vote_session_id)

    owner = await repos.member_repo.get_owner(session["room_id"])
    if owner is None or owner.get("id") != requesting_member_id:
        raise UnresolvedMemberError(requesting_member_id)

    return await resolve_vote_session(repos, session)
