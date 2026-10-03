"""FastAPI dependency providers.

This is the single place repositories and services are constructed. Two
consequences that the layering rules depend on:

* Routes and services never import the Supabase client — they declare a
  repository dependency and receive a ready instance.
* Tests override any provider through ``app.dependency_overrides`` without
  touching production wiring.

Spec 03 extends this module with the eight agent-layer repository providers and
the agent services; the pattern below is what those follow.

Two deliberate style choices, both load-bearing:

1. Dependencies are declared with ``Annotated[T, Depends(...)]`` rather than
   ``t: T = Depends(...)``. The latter trips ruff's ``B008`` (function call in an
   argument default) and is the older FastAPI idiom; ``Annotated`` is equivalent
   and lint-clean.
2. ``AsyncClient`` is imported at runtime, not under ``TYPE_CHECKING``. Because
   this module uses ``from __future__ import annotations``, every annotation is a
   string, and FastAPI resolves them via ``get_type_hints`` at startup — a
   type only available to the type checker would raise ``NameError`` there.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from supabase import AsyncClient

from app.db.supabase_client import create_supabase_client
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.itinerary_version_repository import ItineraryVersionRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.room_repository import RoomRepository
from app.repositories.selection_repository import SelectionRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.vote_repository import VoteRepository
from app.repositories.vote_session_repository import VoteSessionRepository
from app.services.agent_run_service import AgentRunService


async def get_supabase_client() -> AsyncClient:
    """Expose the client factory as a FastAPI dependency."""
    return await create_supabase_client()


#: Reusable alias so each provider below stays a single readable line.
SupabaseClient = Annotated[AsyncClient, Depends(get_supabase_client)]


# --- Spec 02 repositories (reused read-only by the agent layer) -------------


def get_member_repo(client: SupabaseClient) -> MemberRepository:
    """Provide a :class:`MemberRepository`."""
    return MemberRepository(client)


def get_profile_repo(client: SupabaseClient) -> ProfileRepository:
    """Provide a :class:`ProfileRepository`."""
    return ProfileRepository(client)


# --- Spec 03 agent-layer repositories ---------------------------------------


def get_trip_repo(client: SupabaseClient) -> TripRepository:
    """Provide a :class:`TripRepository`."""
    return TripRepository(client)


def get_room_repo(client: SupabaseClient) -> RoomRepository:
    """Provide a :class:`RoomRepository`."""
    return RoomRepository(client)


def get_message_repo(client: SupabaseClient) -> MessageRepository:
    """Provide a :class:`MessageRepository`."""
    return MessageRepository(client)


def get_vote_session_repo(client: SupabaseClient) -> VoteSessionRepository:
    """Provide a :class:`VoteSessionRepository`."""
    return VoteSessionRepository(client)


def get_vote_repo(client: SupabaseClient) -> VoteRepository:
    """Provide a :class:`VoteRepository`."""
    return VoteRepository(client)


def get_selection_repo(client: SupabaseClient) -> SelectionRepository:
    """Provide a :class:`SelectionRepository`."""
    return SelectionRepository(client)


def get_itinerary_version_repo(client: SupabaseClient) -> ItineraryVersionRepository:
    """Provide an :class:`ItineraryVersionRepository`."""
    return ItineraryVersionRepository(client)


def get_feedback_repo(client: SupabaseClient) -> FeedbackRepository:
    """Provide a :class:`FeedbackRepository`."""
    return FeedbackRepository(client)


def get_agent_run_repo(client: SupabaseClient) -> AgentRunRepository:
    """Provide an :class:`AgentRunRepository`."""
    return AgentRunRepository(client)


# --- Spec 03 agent-layer services --------------------------------------------


def get_agent_run_service(
    agent_run_repo: Annotated[AgentRunRepository, Depends(get_agent_run_repo)],
    trip_repo: Annotated[TripRepository, Depends(get_trip_repo)],
    room_repo: Annotated[RoomRepository, Depends(get_room_repo)],
    message_repo: Annotated[MessageRepository, Depends(get_message_repo)],
    member_repo: Annotated[MemberRepository, Depends(get_member_repo)],
    profile_repo: Annotated[ProfileRepository, Depends(get_profile_repo)],
    itinerary_version_repo: Annotated[
        ItineraryVersionRepository, Depends(get_itinerary_version_repo)
    ],
    selection_repo: Annotated[SelectionRepository, Depends(get_selection_repo)],
    feedback_repo: Annotated[FeedbackRepository, Depends(get_feedback_repo)],
    vote_session_repo: Annotated[VoteSessionRepository, Depends(get_vote_session_repo)],
    vote_repo: Annotated[VoteRepository, Depends(get_vote_repo)],
) -> AgentRunService:
    """Provide an :class:`AgentRunService` wired to every repository it needs."""
    return AgentRunService(
        agent_run_repo=agent_run_repo,
        trip_repo=trip_repo,
        room_repo=room_repo,
        message_repo=message_repo,
        member_repo=member_repo,
        profile_repo=profile_repo,
        itinerary_version_repo=itinerary_version_repo,
        selection_repo=selection_repo,
        feedback_repo=feedback_repo,
        vote_session_repo=vote_session_repo,
        vote_repo=vote_repo,
    )
