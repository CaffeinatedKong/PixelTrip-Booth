"""The TTL cache, and run progress served from it to a room full of pollers."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.agents.errors import TripNotFoundError
from app.core.ttl_cache import TTLCache
from app.services.run_endpoint_service import RunEndpointService
from app.services.run_events import forget_run_progress

pytestmark = pytest.mark.anyio

TRIP = "22222222-2222-4222-8222-222222222222"
RUN = {
    "id": "r1",
    "run_type": "discovery",
    "status": "running",
    "phase": "asking_guide",
    "started_at": "2026-10-13T10:00:00+00:00",
}


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_a_value_is_reused_until_it_expires() -> None:
    clock = Clock()
    cache: TTLCache[str, int] = TTLCache(2.0, clock=clock)
    loader = AsyncMock(side_effect=[1, 2])

    assert await cache.get_or_load("k", loader) == 1
    clock.now = 1.9
    assert await cache.get_or_load("k", loader) == 1
    clock.now = 2.1
    assert await cache.get_or_load("k", loader) == 2
    assert loader.await_count == 2


async def test_concurrent_callers_share_one_load() -> None:
    cache: TTLCache[str, int] = TTLCache(2.0)
    calls = 0

    async def slow() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return 7

    results = await asyncio.gather(*(cache.get_or_load("k", slow) for _ in range(30)))

    assert results == [7] * 30 and calls == 1


async def test_a_failed_load_is_not_cached() -> None:
    cache: TTLCache[str, int] = TTLCache(2.0)
    loader = AsyncMock(side_effect=[RuntimeError("down"), 5])

    with pytest.raises(RuntimeError):
        await cache.get_or_load("k", loader)
    assert await cache.get_or_load("k", loader) == 5


async def test_invalidate_drops_only_matching_keys() -> None:
    cache: TTLCache[tuple[str, int], int] = TTLCache(60.0)
    cache.set(("a", 1), 1)
    cache.set(("b", 1), 2)

    cache.invalidate(lambda key: key[0] == "a")

    assert cache.get(("a", 1)) is None and cache.get(("b", 1)) == 2


def service(latest: dict | None = RUN) -> RunEndpointService:
    trip_repo = AsyncMock()
    trip_repo.get_by_id.return_value = {"id": TRIP, "room_id": "room"}
    run_repo = AsyncMock()
    run_repo.get_latest_for_trip.return_value = latest
    return RunEndpointService(
        agent_run_repo=run_repo,
        trip_repo=trip_repo,
        room_repo=AsyncMock(),
        message_repo=AsyncMock(),
        member_repo=AsyncMock(),
        profile_repo=AsyncMock(),
        itinerary_version_repo=AsyncMock(),
        selection_repo=AsyncMock(),
        feedback_repo=AsyncMock(),
        vote_session_repo=AsyncMock(),
        vote_repo=AsyncMock(),
        llm_client=None,
    )


async def test_many_pollers_cost_one_read() -> None:
    svc = service()

    answers = await asyncio.gather(*(svc.get_latest_run(TRIP, "discovery") for _ in range(40)))

    assert all(a is not None and a.phase == "asking_guide" for a in answers)
    assert svc.agent_run_repo.get_latest_for_trip.await_count == 1


async def test_different_run_types_are_cached_separately() -> None:
    svc = service()

    await svc.get_latest_run(TRIP, "discovery")
    await svc.get_latest_run(TRIP, "logistics")

    assert svc.agent_run_repo.get_latest_for_trip.await_count == 2


async def test_no_run_yet_is_cached_as_none() -> None:
    svc = service(latest=None)

    assert await svc.get_latest_run(TRIP, None) is None
    assert await svc.get_latest_run(TRIP, None) is None
    assert svc.agent_run_repo.get_latest_for_trip.await_count == 1


async def test_forgetting_a_trip_makes_the_next_read_fresh() -> None:
    svc = service()
    await svc.get_latest_run(TRIP, "discovery")

    forget_run_progress(TRIP)
    await svc.get_latest_run(TRIP, "discovery")

    assert svc.agent_run_repo.get_latest_for_trip.await_count == 2


async def test_an_unknown_trip_is_an_error_and_not_cached() -> None:
    svc = service()
    svc.trip_repo.get_by_id.return_value = None

    with pytest.raises(TripNotFoundError):
        await svc.get_latest_run(TRIP, None)
    svc.trip_repo.get_by_id.return_value = {"id": TRIP, "room_id": "room"}
    assert await svc.get_latest_run(TRIP, None) is not None
