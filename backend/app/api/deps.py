"""FastAPI dependency providers.

Wiring: Supabase client -> repositories -> service, each through ``Depends()``. Routes
depend only on ``get_room_service``. This module is the single place tests override with
``app.dependency_overrides``.
"""

from typing import Annotated

from fastapi import Depends
from supabase import AsyncClient

from app.db.supabase_client import create_supabase_client
from app.repositories.member_repository import MemberRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.room_repository import RoomRepository
from app.services.room_service import RoomService


async def get_supabase_client() -> AsyncClient:
    """Expose the client from the low-level factory via ``Depends()``."""
    return await create_supabase_client()


SupabaseClient = Annotated[AsyncClient, Depends(get_supabase_client)]


def get_room_repo(client: SupabaseClient) -> RoomRepository:
    return RoomRepository(client)


def get_member_repo(client: SupabaseClient) -> MemberRepository:
    return MemberRepository(client)


def get_profile_repo(client: SupabaseClient) -> ProfileRepository:
    return ProfileRepository(client)


def get_room_service(
    room_repo: Annotated[RoomRepository, Depends(get_room_repo)],
    member_repo: Annotated[MemberRepository, Depends(get_member_repo)],
    profile_repo: Annotated[ProfileRepository, Depends(get_profile_repo)],
) -> RoomService:
    return RoomService(room_repo, member_repo, profile_repo)
