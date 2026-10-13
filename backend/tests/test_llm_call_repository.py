"""LlmCallRepository and the process-wide sink in deps."""

from __future__ import annotations

import pytest
from app.api import deps
from app.exceptions import RepositoryError
from app.repositories.llm_call_repository import LlmCallRepository

from tests.agents.conftest import FakeSupabaseClient

pytestmark = pytest.mark.anyio


async def test_a_call_is_stored_without_any_text_fields() -> None:
    client = FakeSupabaseClient()
    client.queue("llm_calls", [{"id": "1"}])

    await LlmCallRepository(client).record("destination_recommendation", "gemini-x", "ok", 812)

    payload = client.calls_for("llm_calls")[0].payload
    assert payload == {
        "operation": "destination_recommendation",
        "model": "gemini-x",
        "outcome": "ok",
        "latency_ms": 812,
    }


async def test_an_unknown_outcome_is_refused_before_any_write() -> None:
    client = FakeSupabaseClient()

    with pytest.raises(ValueError):
        await LlmCallRepository(client).record("op", None, "weird", 1)
    assert client.calls == []


async def test_database_errors_are_wrapped() -> None:
    client = FakeSupabaseClient()
    client.queue("llm_calls", RuntimeError("no such table"))

    with pytest.raises(RepositoryError):
        await LlmCallRepository(client).record("op", None, "ok", 1)


async def test_after_a_failed_write_the_log_rests_instead_of_failing_every_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = 0

    async def fake_client() -> object:
        nonlocal created
        created += 1
        raise RuntimeError("cannot connect")

    monkeypatch.setattr(deps, "create_supabase_client", fake_client)
    monkeypatch.setattr(deps, "_llm_log_client", None)
    monkeypatch.setattr(deps, "_llm_log_resting_until", 0.0)

    with pytest.raises(RuntimeError):
        await deps._log_llm_call("op", None, "ok", 1)
    await deps._log_llm_call("op", None, "ok", 1)  # resting: returns quietly, no new attempt

    assert created == 1
