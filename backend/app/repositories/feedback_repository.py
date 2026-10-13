"""Party feedback data access.

The Negotiation node loads *open* feedback oldest-first, bounded, and marks only
the rows it actually addressed (Requirement 10.1, 10.6). Rows it could not resolve
stay ``open`` so nothing is silently dropped.
"""

from __future__ import annotations

from typing import Any

from app.repositories.base import BaseRepository, is_unique_violation

_TABLE = "feedback"

#: Requirement 10.1 bounds one negotiation run to 50 open rows.
MAX_OPEN_FEEDBACK_PER_RUN = 50


class FeedbackRepository(BaseRepository):
    """Reads open feedback and settles it once addressed."""

    async def create(
        self,
        trip_id: str,
        itinerary_version_id: str,
        member_id: str,
        target: dict[str, Any],
        comment: str,
    ) -> dict[str, Any]:
        """Insert an open feedback row and return it."""
        try:
            response = (
                await self._client.table(_TABLE)
                .insert(
                    {
                        "trip_id": trip_id,
                        "itinerary_version_id": itinerary_version_id,
                        "member_id": member_id,
                        "target": target,
                        "comment": comment,
                        "status": "open",
                    }
                )
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="create", table=_TABLE)

        row = self._first_row(response)
        if row is None:
            self._handle_error(
                ValueError("insert returned no row"), operation="create", table=_TABLE
            )
        return row

    async def upsert_open(
        self,
        trip_id: str,
        itinerary_version_id: str,
        member_id: str,
        target: dict[str, Any],
        comment: str,
    ) -> dict[str, Any]:
        """Create the feedback row, or update it when this member already has an open
        comment on the same version and target.

        Makes a retried submission harmless: the second attempt rewrites the first
        row's comment instead of adding a duplicate. A concurrent insert that loses the
        race against the unique index is retried once as an update.
        """
        existing = await self._find_open(itinerary_version_id, member_id, target)
        if existing is None:
            try:
                return await self.create(trip_id, itinerary_version_id, member_id, target, comment)
            except Exception as exc:
                if not is_unique_violation(exc.__cause__ or exc):
                    raise
                existing = await self._find_open(itinerary_version_id, member_id, target)
                if existing is None:
                    raise
        try:
            response = (
                await self._client.table(_TABLE)
                .update({"comment": comment})
                .eq("id", existing["id"])
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="upsert_open", table=_TABLE)
        return self._first_row(response) or {**existing, "comment": comment}

    async def _find_open(
        self, itinerary_version_id: str, member_id: str, target: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("itinerary_version_id", itinerary_version_id)
                .eq("member_id", member_id)
                .eq("status", "open")
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="find_open", table=_TABLE)
        return next((row for row in self._rows(response) if row.get("target") == target), None)

    async def list_open_by_trip(
        self,
        trip_id: str,
        limit: int = MAX_OPEN_FEEDBACK_PER_RUN,
    ) -> list[dict[str, Any]]:
        """Return open feedback for the trip, oldest first, capped at ``limit``."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("trip_id", trip_id)
                .eq("status", "open")
                .order("created_at")
                .limit(limit)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_open_by_trip", table=_TABLE)
        return self._rows(response)

    async def list_by_version(self, itinerary_version_id: str) -> list[dict[str, Any]]:
        """Return every feedback row targeting a specific itinerary version."""
        try:
            response = (
                await self._client.table(_TABLE)
                .select("*")
                .eq("itinerary_version_id", itinerary_version_id)
                .order("created_at")
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="list_by_version", table=_TABLE)
        return self._rows(response)

    async def mark_addressed(self, feedback_ids: list[str]) -> None:
        """Mark the given feedback rows ``addressed``.

        A no-op for empty input, so a negotiation run that resolved nothing does
        not issue a pointless ``in ()`` update.
        """
        if not feedback_ids:
            return
        try:
            await (
                self._client.table(_TABLE)
                .update({"status": "addressed"})
                .in_("id", feedback_ids)
                .execute()
            )
        except Exception as exc:
            self._handle_error(exc, operation="mark_addressed", table=_TABLE)
