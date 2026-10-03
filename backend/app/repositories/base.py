"""Shared base class and input guards for the repository layer.

Repositories are the only layer that talks to Supabase. Every Supabase failure is
wrapped into ``RepositoryError`` so callers never see Supabase-specific exception types.
"""

from __future__ import annotations

import re
from typing import Any, NoReturn
from uuid import UUID

from supabase import AsyncClient

from app.exceptions import RepositoryError, ValidationError

ROOM_CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,12}$")


def require_uuid(value: str, field: str) -> None:
    """Raise ``ValidationError`` unless ``value`` is a well-formed UUID string."""
    try:
        UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(f"'{field}' must be a valid UUID.") from None


def require_text(value: str, field: str, max_length: int) -> None:
    """Raise ``ValidationError`` unless ``value`` is non-blank and within ``max_length``."""
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValidationError(
            f"'{field}' must be 1-{max_length} characters and not whitespace-only."
        )


class BaseRepository:
    """Holds the injected Supabase client and the shared error wrapper."""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _handle_error(self, exc: Exception, operation: str, table: str) -> NoReturn:
        """Wrap any Supabase exception into a ``RepositoryError`` with a safe message.

        The message is for internal logs only; the API handler returns a fixed message.
        """
        raise RepositoryError(f"Database operation '{operation}' on '{table}' failed.") from exc

    async def _insert_one(self, table: str, data: dict[str, Any]) -> dict:
        """Insert one row and return it, wrapping any failure."""
        try:
            response = await self._client.table(table).insert(data).execute()
        except Exception as exc:
            self._handle_error(exc, operation="insert", table=table)
        if not response.data:
            self._handle_error(ValueError("No data returned"), operation="insert", table=table)
        return response.data[0]

    async def _select_one(self, table: str, **filters: str) -> dict | None:
        """Return the first row matching all ``column=value`` filters, or ``None``."""
        try:
            query = self._client.table(table).select("*")
            for column, value in filters.items():
                query = query.eq(column, value)
            response = await query.limit(1).execute()
        except Exception as exc:
            self._handle_error(exc, operation="select", table=table)
        return response.data[0] if response.data else None
