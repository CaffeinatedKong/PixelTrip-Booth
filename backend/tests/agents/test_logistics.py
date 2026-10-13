"""Tests for logistics_node: destination precondition, both pre-tool escalation
paths, filtering/ranking, and the successful recommendation + vote write.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.agents.errors import DestinationNotSelectedError
from app.agents.nodes import logistics as logistics_module
from app.agents.nodes.logistics import logistics_node
from app.agents.state import AgentState

from tests.agents.conftest import FakeSupabaseClient
from tests.agents.test_messages import ROOM, TRIP, wired_bundle

RUN = "33333333-3333-3333-3333-333333333333"
MEMBER_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def make_state(**overrides: Any) -> AgentState:
    base: dict[str, Any] = {"run_id": RUN, "trip_id": TRIP, "run_type": "logistics"}
    base.update(overrides)
    return AgentState(**base)


def preference_row(member_id: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "member_id": member_id,
        "available_dates": [{"start": "2026-06-01", "end": "2026-06-20"}],
        "destinations": [],
        "hard_constraints": [
            {"type": "departure_origin", "value": "NRT"},
        ],
        "budget": None,
        "interests": [],
        "activities": [],
        "travel_style": None,
    }
    base.update(overrides)
    return base


def flight_option(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "F-1",
        "carrier": "ANA",
        "flight_number": "NH123",
        "origin": "NRT",
        "destination": "KIX",
        "depart_at": "2026-06-05T08:00:00",
        "arrive_at": "2026-06-05T10:00:00",
        "price": 500.0,
        "duration_minutes": 120,
        "stops": 0,
    }
    base.update(overrides)
    return base


def three_flight_options(**overrides: Any) -> list[dict[str, Any]]:
    """Three distinct flight options — the minimum a recommendation needs."""
    base = [
        flight_option(id="F-1", price=400.0),
        flight_option(id="F-2", price=500.0),
        flight_option(id="F-3", price=600.0),
    ]
    if overrides:
        base[0].update(overrides)
    return base


def wire_base_context(
    client: FakeSupabaseClient,
    *,
    members: list[dict[str, Any]] | None = None,
    preferences: list[dict[str, Any]] | None = None,
    destination_selection: dict[str, Any] | None = None,
) -> None:
    """Wire the reads ``load_trip_context`` needs for a usable trip/room."""
    client.set_default("trips", [{"id": TRIP, "room_id": ROOM, "status": "destination_selected"}])
    client.set_default(
        "party_rooms", [{"id": ROOM, "status": "active", "planning_stage": "logistics"}]
    )
    client.set_default("room_members", members if members is not None else [{"id": MEMBER_1}])
    client.set_default(
        "selections",
        [destination_selection]
        if destination_selection is not None
        else [{"room_id": ROOM, "kind": "destination", "data": {"title": "Osaka, Japan"}}],
    )
    client.set_default("itinerary_versions", [])
    client.set_default("feedback", [])
    client.set_default("characters", [])
    client.set_default("travel_preferences", preferences if preferences is not None else [])


async def run_node(
    client: FakeSupabaseClient,
    *,
    flight_options: list[dict[str, Any]] | None = None,
    state: AgentState | None = None,
    monkeypatch: pytest.MonkeyPatch | None = None,
) -> AgentState:
    """Run the node with FlightSearchTool._call stubbed to a canned response."""
    if monkeypatch is not None:
        options = flight_options if flight_options is not None else [flight_option()]

        async def _fake_call(self: Any, **_params: Any) -> dict[str, Any]:
            return {"options": options}

        monkeypatch.setattr(logistics_module.FlightSearchTool, "_call", _fake_call)

    bundle = wired_bundle(client)
    config = {"configurable": {"repos": bundle}}
    return await logistics_node(state or make_state(), config)


# ===========================================================================
# Missing destination selection (Requirement 8.2)
# ===========================================================================


async def test_missing_destination_raises_with_no_flight_tool_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No locked destination: hard failure before any tool call or write."""
    client = FakeSupabaseClient()
    wire_base_context(client, destination_selection={})
    client.set_default("selections", [])

    called = False

    async def _fake_call(self: Any, **_params: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"options": []}

    monkeypatch.setattr(logistics_module.FlightSearchTool, "_call", _fake_call)

    with pytest.raises(DestinationNotSelectedError):
        await run_node(client)

    assert called is False
    assert client.write_calls == []


# ===========================================================================
# Empty availability overlap (Requirement 8.10)
# ===========================================================================


async def test_empty_overlap_escalates_without_calling_the_flight_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disjoint date ranges: escalate, never reach FlightSearchTool."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        members=[{"id": MEMBER_1}, {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"}],
        preferences=[
            preference_row(
                MEMBER_1, available_dates=[{"start": "2026-06-01", "end": "2026-06-05"}]
            ),
            preference_row(
                "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                available_dates=[{"start": "2026-07-01", "end": "2026-07-05"}],
            ),
        ],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    called = False

    async def _fake_call(self: Any, **_params: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"options": []}

    monkeypatch.setattr(logistics_module.FlightSearchTool, "_call", _fake_call)

    await run_node(client)

    assert called is False
    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "text"
    assert client.calls_for("vote_sessions") == []


async def test_dates_that_have_passed_escalate_without_calling_the_flight_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A shared window wholly before "today" cannot be flown: ask, never search."""
    past = [{"start": "2026-03-01", "end": "2026-03-09"}]
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, available_dates=past)],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])
    called = False

    async def _fake_call(self: Any, **_params: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {"options": []}

    monkeypatch.setattr(logistics_module.FlightSearchTool, "_call", _fake_call)

    await run_node(client)

    assert called is False
    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert "passed" in str(sent)


# ===========================================================================
# Unresolved departure origin (Requirement 8.11)
# ===========================================================================


async def test_unresolved_origin_escalates_without_calling_the_flight_tool() -> None:
    """No conventioned departure_origin entry: escalate, never call the tool."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, hard_constraints=[])],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    await run_node(client)  # no monkeypatch: a real tool call would fail loudly

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert "departure" in sent["content"]["text"].lower()
    assert client.calls_for("vote_sessions") == []


async def test_origin_is_never_inferred_from_the_destination() -> None:
    """A destination-only hint must not be mistaken for a resolved origin."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        destination_selection={
            "room_id": ROOM,
            "kind": "destination",
            "data": {"title": "Osaka, Japan"},
        },
        preferences=[preference_row(MEMBER_1, hard_constraints=[])],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert "osaka" not in sent["content"]["text"].lower()


# ===========================================================================
# Filtering emptied by budget/dates (Requirement 8.6-8.7)
# ===========================================================================


async def test_every_option_over_budget_is_shown_marked_over_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never a dead end: when no fare fits the budget, the cheapest are still offered,
    labelled with how far over they are, and the party votes."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, budget=100)],
    )
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1", "kind": "recommendation"}])
    client.queue("vote_sessions", [{"id": "vs-1", "status": "open"}])  # create()

    await run_node(
        client,
        flight_options=[
            flight_option(id="f1", price=500.0),
            flight_option(id="f2", price=650.0),
            flight_option(id="f3", price=700.0),
        ],
        monkeypatch=monkeypatch,
    )

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "recommendation"
    items = sent["content"]["items"]
    assert [i["id"] for i in items] == ["f1", "f2", "f3"]  # cheapest first
    assert all(i["meta"]["tags"][0] == "Over budget" for i in items)
    assert "400 over what the party's budget leaves for flights" in items[0]["meta"]["tradeOff"]
    assert any(c.op == "insert" for c in client.calls_for("vote_sessions"))


async def test_every_option_outside_dates_escalates(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fare departing outside the party's shared window is excluded."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[
            preference_row(MEMBER_1, available_dates=[{"start": "2026-06-01", "end": "2026-06-05"}])
        ],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    # Two progress writes (asking/searching, then checking_budget) come first.
    client.queue("agent_runs", [{"id": RUN, "phase": "step"}])
    client.queue("agent_runs", [{"id": RUN, "phase": "step"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    await run_node(
        client,
        flight_options=[flight_option(depart_at="2026-09-01T08:00:00")],
        monkeypatch=monkeypatch,
    )

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert "dates" in sent["content"]["text"].lower()
    assert client.calls_for("vote_sessions") == []


async def test_unconstrained_budget_excludes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every member's budget NULL means price excludes no option."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1, budget=None)])
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    await run_node(
        client,
        flight_options=[
            flight_option(id="F-1", price=999_999.0),
            flight_option(id="F-2", price=1_000_000.0),
            flight_option(id="F-3", price=1_000_001.0),
        ],
        monkeypatch=monkeypatch,
    )

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "recommendation"
    assert len(sent["content"]["items"]) == 3


# ===========================================================================
# Ranking (Requirement 8.8)
# ===========================================================================


async def test_ranking_is_price_then_duration_then_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cheapest, fastest, fewest-stops option leads."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1)])
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    options = [
        flight_option(id="F-expensive", price=900.0, duration_minutes=60, stops=0),
        flight_option(id="F-cheapest", price=400.0, duration_minutes=180, stops=1),
        flight_option(id="F-mid", price=600.0, duration_minutes=90, stops=0),
        flight_option(id="F-fourth", price=950.0, duration_minutes=200, stops=2),
    ]

    await run_node(client, flight_options=options, monkeypatch=monkeypatch)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    ids = [item["id"] for item in sent["content"]["items"]]
    assert ids == ["F-cheapest", "F-mid", "F-expensive", "F-fourth"]


# ===========================================================================
# Factual fields (Requirement 8.3)
# ===========================================================================


async def test_factual_fields_always_equal_the_tool_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Price, carrier, etc. in the emitted recommendation match the tool, never
    a model-generated value — enforced here by construction, since this node
    builds `meta` directly from the typed `FlightOption`, not from any LLM
    output.
    """
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1)])
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    options = [
        flight_option(id="F-1", carrier="JAL", price=321.0, stops=2),
        flight_option(id="F-2", carrier="ANA", price=400.0),
        flight_option(id="F-3", carrier="SKY", price=500.0),
    ]
    await run_node(client, flight_options=options, monkeypatch=monkeypatch)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    meta = sent["content"]["items"][0]["meta"]
    assert meta["carrier"] == "JAL"
    assert meta["price"] == 321.0
    assert meta["stops"] == 2


# ===========================================================================
# Successful recommendation + vote (Requirement 8.4-8.5, 8.9)
# ===========================================================================


async def test_a_successful_run_emits_a_recommendation_and_opens_a_vote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1)])
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1", "kind": "recommendation"}])
    client.queue("vote_sessions", [{"id": "vs-1", "status": "open"}])  # create()

    await run_node(client, flight_options=three_flight_options(), monkeypatch=monkeypatch)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "recommendation"
    assert sent["content"]["category"] == "flight"
    items = sent["content"]["items"]
    assert 1 <= len(items) <= 5
    assert len({item["id"] for item in items}) == len(items)

    vote_call = next(c for c in client.calls_for("vote_sessions") if c.op == "insert")
    assert vote_call.payload["message_id"] == "msg-1"
    assert len(vote_call.payload["options"]) == len(items)


async def test_a_prior_open_flight_session_is_closed_before_the_new_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requirement 8.9: at most one open flight vote session per room."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1)])
    client.queue(
        "vote_sessions", [{"id": "old-vs", "status": "open", "message_id": "old-msg"}]
    )  # list_open_by_room
    client.queue(
        "messages", [{"id": "old-msg", "content": {"category": "flight"}}]
    )  # linked message
    client.queue("vote_sessions", [{"id": "old-vs", "status": "closed"}])  # close()
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "new-vs", "status": "open"}])  # create()

    await run_node(client, flight_options=three_flight_options(), monkeypatch=monkeypatch)

    close_call = next(c for c in client.calls_for("vote_sessions") if c.op == "update")
    assert close_call.payload == {"status": "closed"}


async def test_a_different_category_open_session_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A destination vote session must not be closed by a logistics run."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[preference_row(MEMBER_1)])
    client.queue(
        "vote_sessions",
        [{"id": "dest-vs", "status": "open", "message_id": "dest-msg"}],
    )
    client.queue("messages", [{"id": "dest-msg", "content": {"category": "destination"}}])
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "new-vs", "status": "open"}])

    await run_node(client, flight_options=three_flight_options(), monkeypatch=monkeypatch)

    assert all(c.op != "update" for c in client.calls_for("vote_sessions"))


# ===========================================================================
# The saved-search cache around the flight providers
# ===========================================================================


class FakeFlightCache:
    """An in-memory ``FlightCacheRepository``."""

    def __init__(self, saved: Any = None, *, fail_reads: bool = False, fail_writes: bool = False):
        self.saved = saved
        self.writes: list[tuple[str, list[dict[str, Any]], str]] = []
        self.fail_reads, self.fail_writes = fail_reads, fail_writes

    async def get(self, key: str) -> Any:
        if self.fail_reads:
            raise RuntimeError("cache down")
        return self.saved

    async def put(self, key: str, options: list[dict[str, Any]], currency: str) -> None:
        if self.fail_writes:
            raise RuntimeError("cache down")
        self.writes.append((key, options, currency))


def saved_search(age_seconds: float) -> Any:
    from datetime import UTC, datetime, timedelta

    from app.repositories.flight_cache_repository import CachedSearch

    return CachedSearch(
        three_flight_options(), "SGD", datetime.now(UTC) - timedelta(seconds=age_seconds)
    )


SEARCH = {
    "origin": "NRT",
    "destination": "Osaka, Japan",
    "depart_after": "2026-06-05",
    "depart_before": "2026-06-10",
}


def tool_returning(options: list[dict[str, Any]] | Exception) -> Any:
    from unittest.mock import AsyncMock

    from app.agents.tools.base import FlightSearchResponse

    tool = AsyncMock()
    if isinstance(options, Exception):
        tool.invoke.side_effect = options
    else:
        response = FlightSearchResponse.model_validate({"options": options})
        tool.invoke.return_value = (response, make_state().append_tool_response({"ok": True}))
    return tool


def bundle_with_cache(cache: FakeFlightCache) -> Any:
    import dataclasses

    return dataclasses.replace(wired_bundle(FakeSupabaseClient()), flight_cache_repo=cache)


async def test_a_recent_saved_search_is_reused_without_calling_the_provider() -> None:
    cache = FakeFlightCache(saved_search(600))
    tool = tool_returning(RuntimeError("must not be called"))

    response, state, saved_at = await logistics_module._search_flights(
        bundle_with_cache(cache), make_state(), tool, SEARCH
    )

    tool.invoke.assert_not_awaited()
    assert [o.id for o in response.options] == ["F-1", "F-2", "F-3"]
    assert saved_at is None, "a fresh saved search is not presented as old"
    assert state.external_tool_responses, "the guardrail checks flights against this record"


async def test_a_live_search_is_saved_for_next_time() -> None:
    cache = FakeFlightCache(saved_search(4 * 3600))  # saved, but too old to reuse
    tool = tool_returning(three_flight_options())

    _response, _state, saved_at = await logistics_module._search_flights(
        bundle_with_cache(cache), make_state(), tool, SEARCH
    )

    tool.invoke.assert_awaited_once()
    assert saved_at is None
    key, options, currency = cache.writes[0]
    assert key == "nrt|osaka, japan|2026-06-05|2026-06-10"
    assert [o["id"] for o in options] == ["F-1", "F-2", "F-3"] and currency


async def test_an_empty_live_answer_is_not_saved_over_a_good_one() -> None:
    cache = FakeFlightCache()
    tool = tool_returning([])

    await logistics_module._search_flights(bundle_with_cache(cache), make_state(), tool, SEARCH)

    assert cache.writes == []


async def test_when_every_provider_fails_the_last_saved_search_is_shown_with_its_age() -> None:
    from app.agents.errors import ExternalToolUnavailableError

    cache = FakeFlightCache(saved_search(2 * 86400))
    tool = tool_returning(ExternalToolUnavailableError("flight_search"))

    response, state, saved_at = await logistics_module._search_flights(
        bundle_with_cache(cache), make_state(), tool, SEARCH
    )

    assert len(response.options) == 3
    assert saved_at is not None
    assert state.external_tool_responses


async def test_with_nothing_saved_a_provider_outage_still_fails_the_run() -> None:
    from app.agents.errors import ExternalToolUnavailableError

    with pytest.raises(ExternalToolUnavailableError):
        await logistics_module._search_flights(
            bundle_with_cache(FakeFlightCache()),
            make_state(),
            tool_returning(ExternalToolUnavailableError("flight_search")),
            SEARCH,
        )


async def test_a_search_too_old_to_trust_is_not_shown_during_an_outage() -> None:
    from app.agents.errors import ExternalToolUnavailableError

    with pytest.raises(ExternalToolUnavailableError):
        await logistics_module._search_flights(
            bundle_with_cache(FakeFlightCache(saved_search(10 * 86400))),
            make_state(),
            tool_returning(ExternalToolUnavailableError("flight_search")),
            SEARCH,
        )


async def test_a_broken_cache_never_breaks_the_search() -> None:
    cache = FakeFlightCache(fail_reads=True, fail_writes=True)
    tool = tool_returning(three_flight_options())

    response, _state, saved_at = await logistics_module._search_flights(
        bundle_with_cache(cache), make_state(), tool, SEARCH
    )

    assert len(response.options) == 3 and saved_at is None


async def test_no_cache_configured_behaves_as_before() -> None:
    import dataclasses

    bundle = dataclasses.replace(wired_bundle(FakeSupabaseClient()), flight_cache_repo=None)
    tool = tool_returning(three_flight_options())

    response, _state, saved_at = await logistics_module._search_flights(
        bundle, make_state(), tool, SEARCH
    )

    assert len(response.options) == 3 and saved_at is None


def test_saved_prices_are_labelled_on_the_card_and_never_passed_off_as_live() -> None:
    from datetime import UTC, datetime, timedelta

    from app.agents.tools.base import FlightOption

    options = [FlightOption(**o) for o in three_flight_options()]
    saved_at = datetime.now(UTC) - timedelta(hours=5)

    proposal = logistics_module._build_proposal(options, saved_at=saved_at)

    for item in proposal["items"]:
        meta = item["meta"]
        assert meta["tradeOff"].startswith("Saved price from 5 hours ago")
        assert "Saved price" in meta["tags"]
        assert meta["priceAsOf"] == saved_at.isoformat()
    live = logistics_module._build_proposal(options)
    assert all("priceAsOf" not in i["meta"] for i in live["items"])
