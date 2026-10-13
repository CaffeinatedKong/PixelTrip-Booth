"""Run progress pushed to the room over Supabase Realtime Broadcast."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from app.agents.progress import _phase_listeners, report_phase
from app.agents.state import AgentState
from app.core.config import get_settings
from app.services import run_events
from app.services.run_endpoint_service import RunEndpointService

pytestmark = pytest.mark.anyio

ROOM = "11111111-1111-4111-8111-111111111111"
TRIP = "22222222-2222-4222-8222-222222222222"
RUN = "33333333-3333-3333-3333-333333333333"
MEMBER = "44444444-4444-4444-8444-444444444444"


@pytest.fixture(autouse=True)
def isolated_events(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    monkeypatch.setattr(run_events, "_transport", httpx.MockTransport(handler))
    monkeypatch.setattr(run_events, "_resting_until", 0.0)
    run_events._started.clear()
    return requests


async def settle() -> None:
    await asyncio.gather(*list(run_events._tasks))


def body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content)["messages"][0]


async def test_a_step_is_broadcast_to_the_rooms_channel(isolated_events) -> None:
    run_events.publish_progress(
        ROOM, run_events.progress_payload(RUN, "discovery", "running", "asking_guide", 4)
    )
    await settle()

    (request,) = isolated_events
    assert request.url.path == "/realtime/v1/api/broadcast"
    key = get_settings().supabase_service_role_key
    assert request.headers["apikey"] == key and request.headers["authorization"] == f"Bearer {key}"
    message = body(request)
    assert message["topic"] == f"run:{ROOM}" and message["event"] == "progress"
    assert message["payload"] == {
        "id": RUN,
        "runType": "discovery",
        "status": "running",
        "phase": "asking_guide",
        "elapsedSeconds": 4,
    }


async def test_the_channel_carries_no_party_data(isolated_events) -> None:
    run_events.publish_progress(
        ROOM, run_events.progress_payload(RUN, "itinerary", "running", "drafting_days", 1)
    )
    await settle()

    assert set(body(isolated_events[0])["payload"]) == {
        "id",
        "runType",
        "status",
        "phase",
        "elapsedSeconds",
    }


async def test_nothing_is_sent_without_a_room_or_when_switched_off(
    isolated_events, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_events.publish_progress(None, {"id": RUN})
    monkeypatch.setattr(get_settings(), "broadcast_run_progress", False)
    run_events.publish_progress(ROOM, {"id": RUN})
    await settle()

    assert isolated_events == []


async def test_a_failed_broadcast_rests_instead_of_failing_every_step(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    monkeypatch.setattr(run_events, "_transport", httpx.MockTransport(handler))

    for _ in range(3):
        run_events.publish_progress(ROOM, {"id": RUN})
        await settle()

    assert calls == 1


async def test_a_run_step_clears_the_cache_and_broadcasts_it(isolated_events) -> None:
    run_events.install()
    run_events.RUN_PROGRESS_CACHE.set((TRIP, None), {"id": RUN})
    state = AgentState(
        run_id=RUN, trip_id=TRIP, run_type="logistics", trip_context={"room_id": ROOM}
    )

    await report_phase(AsyncMock(), state, "searching_flights")
    await settle()

    assert run_events.RUN_PROGRESS_CACHE.get((TRIP, None)) is None
    message = body(isolated_events[0])
    assert message["topic"] == f"run:{ROOM}"
    assert message["payload"]["phase"] == "searching_flights"
    assert message["payload"]["runType"] == "logistics"


async def test_install_is_idempotent() -> None:
    run_events.install()
    run_events.install()

    assert _phase_listeners.count(run_events._on_phase) == 1


async def test_a_step_before_the_room_is_known_is_skipped(isolated_events) -> None:
    run_events.install()
    state = AgentState(run_id=RUN, trip_id=TRIP, run_type="discovery")  # no trip_context yet

    await report_phase(AsyncMock(), state, "reading_party")
    await settle()

    assert isolated_events == []


def service() -> RunEndpointService:
    trip_repo = AsyncMock()
    trip_repo.get_by_id.return_value = {"id": TRIP, "room_id": ROOM}
    member_repo = AsyncMock()
    member_repo.get_by_id.return_value = {"id": MEMBER, "room_id": ROOM}
    runs = AsyncMock()
    runs.get_active.return_value = None
    runs.get_by_idempotency_key.return_value = None
    runs.create_pending.return_value = {
        "id": RUN,
        "trip_id": TRIP,
        "run_type": "discovery",
        "status": "pending",
        "base_version": 0,
        "created_by_member_id": MEMBER,
        "idempotency_key": None,
        "created_at": "2026-10-13T10:00:00+00:00",
    }
    runs.get_by_id.return_value = {
        **runs.create_pending.return_value,
        "status": "completed",
        "phase": "posting",
    }
    versions = AsyncMock()
    versions.get_latest_version_number.return_value = 0
    return RunEndpointService(
        agent_run_repo=runs,
        trip_repo=trip_repo,
        room_repo=AsyncMock(),
        message_repo=AsyncMock(),
        member_repo=member_repo,
        profile_repo=AsyncMock(),
        itinerary_version_repo=versions,
        selection_repo=AsyncMock(),
        feedback_repo=AsyncMock(),
        vote_session_repo=AsyncMock(),
        vote_repo=AsyncMock(),
        llm_client=None,
    )


async def test_starting_and_finishing_a_run_are_announced(
    isolated_events, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc = service()
    monkeypatch.setattr(RunEndpointService, "_execute_run", AsyncMock())

    started = await svc.start_run(TRIP, "discovery", MEMBER)
    await started.execute()
    await settle()

    sent = [body(r)["payload"]["status"] for r in isolated_events]
    assert sent == ["pending", "running", "completed"]
    assert all(body(r)["topic"] == f"run:{ROOM}" for r in isolated_events)
    assert run_events._started == {}, "a finished run is forgotten"
