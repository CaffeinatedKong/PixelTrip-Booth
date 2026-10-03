"""Fixtures for the agent-layer test suite.

Two things live here:

1. **A network blocker.** An autouse fixture replaces ``socket.socket`` so any
   accidental outbound connection fails loudly instead of silently reaching a
   real service (Requirement 21.7, 21.11).
2. **A fake Supabase client.** Repository tests drive real query-builder chains
   (``.table().select().eq().limit().execute()``) against an in-memory recorder
   rather than asserting on a bare ``AsyncMock``. That catches a wrong column,
   a missing filter, or a wrong table name — all of which a loose mock would
   happily accept.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# No-network enforcement
# ---------------------------------------------------------------------------


_NETWORK_BLOCKED_MESSAGE = (
    "Outbound network access is not permitted in this test suite. "
    "Mock the External_Tool or repository instead."
)


def _blocked(*_args: object, **_kwargs: object) -> None:
    """Refuse an outbound connection attempt."""
    raise AssertionError(_NETWORK_BLOCKED_MESSAGE)


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that attempts a real outbound connection.

    Patches the *connect* entry points rather than ``socket.socket`` itself.
    Replacing the class outright also breaks asyncio: the event loop builds an
    internal self-pipe via ``socket.socketpair()`` during setup, so a blanket
    patch makes every async test error out before its body runs.

    Blocking ``connect``/``connect_ex``/``create_connection`` still catches a real
    HTTP call while leaving loop construction and local socket pairs working.
    """
    monkeypatch.setattr(socket.socket, "connect", _blocked, raising=True)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked, raising=True)
    monkeypatch.setattr(socket, "create_connection", _blocked, raising=True)


# ---------------------------------------------------------------------------
# Fake Supabase client
# ---------------------------------------------------------------------------


@dataclass
class RecordedCall:
    """One query-builder chain, captured for assertions."""

    table: str
    op: str
    filters: list[tuple[str, str, Any]] = field(default_factory=list)
    payload: Any = None
    order: list[tuple[str, bool]] = field(default_factory=list)
    limit: int | None = None
    columns: str | None = None
    on_conflict: str | None = None

    def filter_values(self, column: str) -> list[Any]:
        """Return every value filtered against ``column``."""
        return [value for col, _op, value in self.filters if col == column]

    def has_filter(self, column: str, value: Any) -> bool:
        """Return ``True`` if ``column`` was filtered to exactly ``value``."""
        return value in self.filter_values(column)


class _Response:
    """Mimics a Supabase response object's ``.data`` attribute."""

    def __init__(self, data: Any) -> None:
        self.data = data


class _QueryBuilder:
    """Records a fluent query chain and returns a canned response."""

    def __init__(self, client: FakeSupabaseClient, table: str) -> None:
        self._client = client
        self._call = RecordedCall(table=table, op="select")

    # -- terminal-op starters ------------------------------------------------

    def select(self, columns: str = "*") -> _QueryBuilder:
        self._call.op = "select"
        self._call.columns = columns
        return self

    def insert(self, payload: Any) -> _QueryBuilder:
        self._call.op = "insert"
        self._call.payload = payload
        return self

    def update(self, payload: Any) -> _QueryBuilder:
        self._call.op = "update"
        self._call.payload = payload
        return self

    def upsert(self, payload: Any, on_conflict: str | None = None) -> _QueryBuilder:
        self._call.op = "upsert"
        self._call.payload = payload
        self._call.on_conflict = on_conflict
        return self

    def delete(self) -> _QueryBuilder:
        self._call.op = "delete"
        return self

    # -- filters -------------------------------------------------------------

    def eq(self, column: str, value: Any) -> _QueryBuilder:
        self._call.filters.append((column, "eq", value))
        return self

    def neq(self, column: str, value: Any) -> _QueryBuilder:
        self._call.filters.append((column, "neq", value))
        return self

    def lt(self, column: str, value: Any) -> _QueryBuilder:
        self._call.filters.append((column, "lt", value))
        return self

    def gt(self, column: str, value: Any) -> _QueryBuilder:
        self._call.filters.append((column, "gt", value))
        return self

    def in_(self, column: str, values: Any) -> _QueryBuilder:
        self._call.filters.append((column, "in", list(values)))
        return self

    def contains(self, column: str, value: Any) -> _QueryBuilder:
        self._call.filters.append((column, "contains", value))
        return self

    def order(self, column: str, desc: bool = False) -> _QueryBuilder:
        self._call.order.append((column, desc))
        return self

    def limit(self, count: int) -> _QueryBuilder:
        self._call.limit = count
        return self

    # -- execution -----------------------------------------------------------

    async def execute(self) -> _Response:
        """Record the chain and return the queued response (or raise)."""
        self._client.calls.append(self._call)
        return self._client._next_response(self._call)


class _RpcBuilder:
    """Records an RPC invocation and returns a canned response."""

    def __init__(self, client: FakeSupabaseClient, name: str, params: Any) -> None:
        self._client = client
        self._call = RecordedCall(table=f"rpc:{name}", op="rpc", payload=params)

    async def execute(self) -> _Response:
        self._client.calls.append(self._call)
        return self._client._next_response(self._call)


class FakeSupabaseClient:
    """In-memory stand-in for ``supabase.AsyncClient``.

    Responses are queued per table (or ``rpc:<name>``). A queued entry may be a
    value to return or an exception instance to raise, which is how the tests
    simulate a ``23505`` without a real database.
    """

    def __init__(self) -> None:
        self.calls: list[RecordedCall] = []
        self._queues: dict[str, list[Any]] = {}
        self._defaults: dict[str, Any] = {}

    # -- test-side configuration --------------------------------------------

    def queue(self, target: str, *results: Any) -> FakeSupabaseClient:
        """Queue one or more results (or exceptions) for ``target`` in order."""
        self._queues.setdefault(target, []).extend(results)
        return self

    def set_default(self, target: str, result: Any) -> FakeSupabaseClient:
        """Set the response returned for ``target`` once its queue is empty."""
        self._defaults[target] = result
        return self

    def calls_for(self, target: str) -> list[RecordedCall]:
        """Return every recorded call against ``target``."""
        return [c for c in self.calls if c.table == target]

    def ops_for(self, target: str) -> list[str]:
        """Return the operation names recorded against ``target``."""
        return [c.op for c in self.calls_for(target)]

    @property
    def write_calls(self) -> list[RecordedCall]:
        """Return every recorded mutating call (insert / update / upsert / delete / rpc)."""
        return [c for c in self.calls if c.op in {"insert", "update", "upsert", "delete", "rpc"}]

    # -- client surface ------------------------------------------------------

    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self, name)

    def rpc(self, name: str, params: Any = None) -> _RpcBuilder:
        return _RpcBuilder(self, name, params)

    # -- internals -----------------------------------------------------------

    def _next_response(self, call: RecordedCall) -> _Response:
        queue = self._queues.get(call.table, [])
        result = queue.pop(0) if queue else self._defaults.get(call.table, [])
        if isinstance(result, BaseException):
            raise result
        return _Response(result)


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    """Provide a fresh :class:`FakeSupabaseClient`."""
    return FakeSupabaseClient()


# ---------------------------------------------------------------------------
# Simulated Postgres errors
# ---------------------------------------------------------------------------


class FakePostgresError(Exception):
    """A Supabase-style error exposing a SQLSTATE ``code`` attribute."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


def unique_violation(constraint: str) -> FakePostgresError:
    """Build a ``23505`` naming ``constraint``, as supabase-py would surface it."""
    return FakePostgresError(
        f'duplicate key value violates unique constraint "{constraint}"',
        code="23505",
    )
