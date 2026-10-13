"""SelectionRepository.change_trip_dates: the atomic date-change RPC wrapper."""

from __future__ import annotations

import pytest
from app.exceptions import RepositoryError
from app.repositories.selection_repository import SelectionRepository

from tests.agents.conftest import FakeSupabaseClient

pytestmark = pytest.mark.anyio

ROOM = "11111111-1111-4111-8111-111111111111"
PLAN = {"tripDays": 4, "tripStart": "2026-11-12", "tripEnd": "2026-11-15"}


async def test_the_function_gets_the_room_the_plan_we_read_and_the_new_data() -> None:
    client = FakeSupabaseClient()
    client.queue("rpc:change_trip_dates", "ok")

    outcome = await SelectionRepository(client).change_trip_dates(ROOM, PLAN, {"tripDays": 6})

    assert outcome == "ok"
    call = client.calls_for("rpc:change_trip_dates")[0]
    assert call.payload == {"p_room_id": ROOM, "p_expected": PLAN, "p_data": {"tripDays": 6}}


@pytest.mark.parametrize("word", ["flight_locked", "changed", "no_destination", "no_room"])
async def test_every_status_word_is_passed_through(word: str) -> None:
    client = FakeSupabaseClient()
    client.queue("rpc:change_trip_dates", word)

    assert await SelectionRepository(client).change_trip_dates(ROOM, PLAN, {}) == word


async def test_an_unexpected_answer_is_not_mistaken_for_success() -> None:
    client = FakeSupabaseClient()
    client.queue("rpc:change_trip_dates", None)

    assert await SelectionRepository(client).change_trip_dates(ROOM, PLAN, {}) == "error"


async def test_a_database_error_is_wrapped() -> None:
    client = FakeSupabaseClient()
    client.queue("rpc:change_trip_dates", RuntimeError("function does not exist"))

    with pytest.raises(RepositoryError):
        await SelectionRepository(client).change_trip_dates(ROOM, PLAN, {})
