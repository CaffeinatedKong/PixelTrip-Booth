"""HTTP-facing voting service.

Thin wrapper over the agent layer's ``vote_service`` (``cast_vote`` / ``close_session``),
which owns tallying, tie-breaking, the selection write, and the trip status advance.
This class adds what an HTTP caller needs on top: a 404 for an unknown session, a check
that the chosen option belongs to the session, and response shapes for the API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.exceptions import ValidationError, VoteSessionNotFoundError
from app.schemas.planning import CastVoteResponse, TieInfo, VoteResolutionResponse
from app.services.vote_service import cast_vote, close_session

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import RepositoryBundle


class VotingEndpointService:
    """Casts and closes votes for the vote endpoints."""

    def __init__(self, repos: RepositoryBundle) -> None:
        self._repos = repos

    async def cast(self, vote_session_id: str, member_id: str, option_id: str) -> CastVoteResponse:
        """Record (or replace) the member's vote; resolves the session if everyone voted."""
        session = await self._require_session(vote_session_id)
        option_ids = [str(option.get("id")) for option in session.get("options") or []]
        if option_id not in option_ids:
            raise ValidationError("'optionId' is not one of this vote's options.")

        await cast_vote(self._repos, vote_session_id, member_id, option_id)

        after = await self._repos.vote_session_repo.get_by_id(vote_session_id)
        status = (after or session).get("status", "open")
        if status == "open":
            # Voting is this member's part of the current stage. When the vote instead
            # closed (this was the last vote), the party has moved to the next stage and
            # readiness was reset for it, so the member is not marked ready there.
            await self._repos.member_repo.set_stage_ready(member_id, True)
        return CastVoteResponse(
            vote_session_id=vote_session_id,
            member_id=member_id,
            option_id=option_id,
            session_status=status,
        )

    async def close(self, vote_session_id: str, member_id: str) -> VoteResolutionResponse:
        """Close the vote early (room owner only) and lock in the winner."""
        await self._require_session(vote_session_id)
        resolution = await close_session(self._repos, vote_session_id, member_id)
        tie = resolution.tie
        return VoteResolutionResponse(
            vote_session_id=vote_session_id,
            category=resolution.category,
            winning_option=resolution.winning_option,
            tie=TieInfo(tied_option_ids=tie.tied_ids, tied_count=tie.tied_count) if tie else None,
            selection_id=resolution.selection["id"],
        )

    async def _require_session(self, vote_session_id: str) -> dict:
        session = await self._repos.vote_session_repo.get_by_id(vote_session_id)
        if session is None:
            raise VoteSessionNotFoundError("Vote session not found.")
        return session
