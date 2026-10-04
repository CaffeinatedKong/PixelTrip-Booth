"""Vote routes: cast a vote, and let the room owner close a vote early.

Vote sessions are opened by the AI (discovery and logistics runs), not by an endpoint.
A session closes on its own once every member has voted.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_voting_endpoint_service
from app.schemas.errors import ErrorResponse
from app.schemas.planning import (
    CastVoteRequest,
    CastVoteResponse,
    CloseVoteRequest,
    VoteResolutionResponse,
)
from app.services.voting_endpoint_service import VotingEndpointService

router = APIRouter(prefix="/votes", tags=["votes"])

VotingServiceDep = Annotated[VotingEndpointService, Depends(get_voting_endpoint_service)]

_ERRORS = {
    404: {"model": ErrorResponse, "description": "Vote session not found"},
    422: {
        "model": ErrorResponse,
        "description": "Validation error, vote already closed, or member not allowed",
    },
    503: {"model": ErrorResponse, "description": "Database unavailable"},
}


@router.post(
    "/{vote_session_id}/cast",
    response_model=CastVoteResponse,
    summary="Cast or change a vote",
    description=(
        "Records the member's choice; voting again replaces it. When this is the last "
        "member to vote, the session closes, the winner is locked in as the destination "
        "or flight, and the trip advances (`sessionStatus` is then `closed`)."
    ),
    responses={200: {"description": "Vote recorded"}, **_ERRORS},
)
async def cast_vote(
    vote_session_id: UUID,
    body: CastVoteRequest,
    service: VotingServiceDep,
) -> CastVoteResponse:
    """Cast or change a member's vote."""
    return await service.cast(str(vote_session_id), str(body.member_id), body.option_id)


@router.post(
    "/{vote_session_id}/close",
    response_model=VoteResolutionResponse,
    summary="Close a vote early (room owner only)",
    description=(
        "Closes the vote with the votes cast so far and locks in the winner. Ties go "
        "to the option listed first. Only the room owner may close a vote."
    ),
    responses={200: {"description": "Vote closed and winner locked in"}, **_ERRORS},
)
async def close_vote(
    vote_session_id: UUID,
    body: CloseVoteRequest,
    service: VotingServiceDep,
) -> VoteResolutionResponse:
    """Close the vote and lock in the winner."""
    return await service.close(str(vote_session_id), str(body.member_id))
