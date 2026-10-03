"""Shared repository behaviour.

Every repository extends :class:`BaseRepository`, which holds the injected
Supabase client and centralizes error wrapping so each concrete repository stays
focused on its own queries.

Two invariants this module enforces for the whole repository layer:

1. **No raw Supabase error escapes.** Every unexpected exception is wrapped in
   :class:`~app.exceptions.RepositoryError` carrying a developer-authored message
   that names the operation and table. The HTTP handler then substitutes a fixed
   safe message, so database internals never reach a response body.
2. **Postgres error codes are detected, not guessed.** Uniqueness violations are
   identified by the ``23505`` SQLSTATE marker via :func:`is_unique_violation`,
   letting callers distinguish "someone else won the race" from a genuine fault.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn

from app.exceptions import RepositoryError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from supabase import AsyncClient

#: PostgreSQL SQLSTATE for ``unique_violation``.
UNIQUE_VIOLATION_SQLSTATE = "23505"


def is_unique_violation(exc: BaseException) -> bool:
    """Return ``True`` when ``exc`` represents a Postgres uniqueness violation.

    ``supabase-py`` surfaces Postgres errors as ``APIError``-style objects whose
    ``code`` attribute carries the SQLSTATE, but the exact type varies across
    versions. Checking the attribute first and falling back to a substring scan
    keeps detection working without pinning to one client internal.
    """
    code = getattr(exc, "code", None)
    if code is not None and str(code) == UNIQUE_VIOLATION_SQLSTATE:
        return True
    return UNIQUE_VIOLATION_SQLSTATE in str(exc)


def constraint_mentioned(exc: BaseException, constraint_fragment: str) -> bool:
    """Return ``True`` when ``exc``'s text names ``constraint_fragment``.

    Used to tell *which* unique constraint a ``23505`` came from, so a caller can
    treat a version collision differently from, say, an idempotency-key
    collision. Matching is case-insensitive.
    """
    return constraint_fragment.lower() in str(exc).lower()


class BaseRepository:
    """Base class for all repositories.

    Args:
        client: The injected async Supabase client. Repositories never construct
            their own client; it always arrives through dependency injection.
    """

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _handle_error(
        self,
        exc: BaseException,
        operation: str,
        table: str,
    ) -> NoReturn:
        """Wrap any Supabase exception in a :class:`RepositoryError` and raise.

        Args:
            exc: The originating exception, chained via ``from`` for internal logs.
            operation: Short verb naming what was attempted, e.g. ``"insert"``.
            table: The table involved, for internal diagnostics.

        Raises:
            RepositoryError: Always. This function never returns.
        """
        raise RepositoryError(f"Database operation '{operation}' on '{table}' failed.") from exc

    @staticmethod
    def _rows(response: Any) -> list[dict[str, Any]]:
        """Return the row list from a Supabase response, never ``None``."""
        data = getattr(response, "data", None)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    @classmethod
    def _first_row(cls, response: Any) -> dict[str, Any] | None:
        """Return the first row of a Supabase response, or ``None`` if empty."""
        rows = cls._rows(response)
        return rows[0] if rows else None
