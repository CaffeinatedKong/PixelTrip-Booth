"""Low-level Supabase client factory.

Creates the async Supabase client with the service-role key. This module defines no
FastAPI dependencies; ``app/api/deps.py`` wraps it as ``get_supabase_client()`` for
``Depends()``. Only the repository layer receives the client.
"""

from supabase import AsyncClient, acreate_client

from app.core.config import get_settings


async def create_supabase_client() -> AsyncClient:
    """Create an initialized async Supabase client."""
    settings = get_settings()
    return await acreate_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
