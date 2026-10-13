"""Destination guides: the hand-written fallback data in ``destination_guides``.

Read-only from the backend's side; guides are added and corrected in Supabase. Each guide
comes with its activities in one query (an embedded select), so loading the whole catalog
is a single round trip.
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository

_TABLE = "destination_guides"


class GuideRepository(BaseRepository):
    """Reads the active destination guides with their activities."""

    async def list_active(self) -> list[dict[str, Any]]:
        """Every active guide, each with a ``destination_activities`` list."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*, destination_activities(*)")
                .eq("active", True)
                .order("name")
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_active", table=_TABLE)
        return self._rows(response)
