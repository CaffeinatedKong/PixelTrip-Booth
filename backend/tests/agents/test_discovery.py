"""Tests for discovery_node: profile computation, escalation paths, and the
successful recommendation + vote session write.
"""

from __future__ import annotations

from typing import Any

import pytest
from app.agents.errors import PreferencesNotCollectedError
from app.agents.nodes.discovery import discovery_node
from app.agents.state import AgentState

from tests.agents.conftest import FakeSupabaseClient
from tests.agents.test_messages import ROOM, TRIP, wired_bundle

RUN = "33333333-3333-3333-3333-333333333333"
MEMBER_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MEMBER_2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def make_state(**overrides: Any) -> AgentState:
    base: dict[str, Any] = {"run_id": RUN, "trip_id": TRIP, "run_type": "discovery"}
    base.update(overrides)
    return AgentState(**base)


def preference_row(member_id: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "member_id": member_id,
        "available_dates": [{"start": "2026-06-01", "end": "2026-06-20"}],
        "destinations": [],
        "hard_constraints": [],
        "budget": None,
        "interests": [],
        "activities": [],
        "travel_style": None,
    }
    base.update(overrides)
    return base


def wire_base_context(
    client: FakeSupabaseClient,
    *,
    members: list[dict[str, Any]] | None = None,
    preferences: list[dict[str, Any]] | None = None,
) -> None:
    """Wire the reads ``load_trip_context`` needs for a usable trip/room."""
    client.set_default("trips", [{"id": TRIP, "room_id": ROOM, "status": "trip_created"}])
    client.set_default(
        "party_rooms", [{"id": ROOM, "status": "active", "planning_stage": "discover"}]
    )
    client.set_default(
        "room_members", members if members is not None else [{"id": MEMBER_1}, {"id": MEMBER_2}]
    )
    client.set_default("selections", [])
    client.set_default("itinerary_versions", [])
    client.set_default("feedback", [])
    client.set_default("characters", [])
    client.set_default("travel_preferences", preferences if preferences is not None else [])


async def run_node(client: FakeSupabaseClient, state: AgentState | None = None) -> AgentState:
    bundle = wired_bundle(client)
    config = {"configurable": {"repos": bundle}}
    return await discovery_node(state or make_state(), config)


# ===========================================================================
# Zero preferences (Requirement 7.12)
# ===========================================================================


async def test_zero_preferences_raises_with_no_group_profile_and_no_writes() -> None:
    """No travel_preferences rows at all: hard failure, nothing computed."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[])

    with pytest.raises(PreferencesNotCollectedError):
        await run_node(client)

    assert client.write_calls == []


# ===========================================================================
# Empty availability overlap (Requirement 7.11)
# ===========================================================================


async def test_empty_overlap_escalates_without_recommendation_or_vote_session() -> None:
    """Disjoint date ranges: escalate, emit nothing else."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[
            preference_row(
                MEMBER_1, available_dates=[{"start": "2026-06-01", "end": "2026-06-05"}]
            ),
            preference_row(
                MEMBER_2, available_dates=[{"start": "2026-07-01", "end": "2026-07-05"}]
            ),
        ],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "text"
    assert client.calls_for("vote_sessions") == []


# ===========================================================================
# Candidate set emptied by constraints/budget (Requirement 7.9-7.10)
# ===========================================================================


async def test_a_hard_constraint_eliminating_every_candidate_escalates() -> None:
    """Every seeded destination violates the party's one hard constraint."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[
            preference_row(
                MEMBER_1,
                destinations=["Kyoto, Japan"],
                # One hard constraint per fallback candidate too, so the whole
                # candidate set (seeded + fallback) is eliminated, not just the
                # seeded entry.
                hard_constraints=["no japan", "no lisbon", "no reykjavik"],
            ),
        ],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "text"}])
    client.queue("agent_runs", [{"id": RUN, "status": "running", "started_at": "T0"}])
    client.queue("agent_runs", [{"id": RUN, "status": "completed"}])

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert "eliminated" in sent["content"]["text"].lower()
    assert client.calls_for("vote_sessions") == []
    assert all(c.op != "insert" and c.op != "upsert" for c in client.calls_for("selections"))


# ===========================================================================
# Successful recommendation (Requirement 7.5-7.8)
# ===========================================================================


async def test_a_successful_run_emits_a_recommendation_and_opens_a_vote() -> None:
    """3-5 items, unique ids, a paired open vote session referencing the message."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[
            preference_row(MEMBER_1, destinations=["Kyoto, Japan", "Lisbon, Portugal"]),
            preference_row(MEMBER_2, destinations=["Seoul, South Korea"]),
        ],
    )
    client.queue("vote_sessions", [])  # list_open_by_room: nothing open to close
    client.queue("rpc:insert_message_turn", [{"id": "msg-1", "kind": "recommendation"}])
    client.queue("vote_sessions", [{"id": "vs-1", "status": "open"}])  # create()

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "recommendation"
    items = sent["content"]["items"]
    assert 3 <= len(items) <= 5
    assert len({item["id"] for item in items}) == len(items)

    vote_call = next(c for c in client.calls_for("vote_sessions") if c.op == "insert")
    assert vote_call.payload["message_id"] == "msg-1"
    assert len(vote_call.payload["options"]) == len(items)
    assert {o["id"] for o in vote_call.payload["options"]} == {i["id"] for i in items}


async def test_seeded_destinations_appear_before_any_fallback() -> None:
    """Requirement 7.5: the party's own destinations lead the candidate list."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, destinations=["Kyoto, Japan"])],
    )
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    titles = [item["title"] for item in sent["content"]["items"]]
    assert titles[0] == "Kyoto, Japan"


async def test_a_prior_open_destination_session_is_closed_before_the_new_one() -> None:
    """Requirement 7.8: at most one open destination vote session per room."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, destinations=["Kyoto, Japan"])],
    )
    client.queue(
        "vote_sessions", [{"id": "old-vs", "status": "open", "message_id": "old-msg"}]
    )  # list_open_by_room
    client.queue(
        "messages",
        [{"id": "old-msg", "content": {"category": "destination"}}],
    )  # the linked message lookup
    client.queue("vote_sessions", [{"id": "old-vs", "status": "closed"}])  # close()
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "new-vs", "status": "open"}])  # create()

    await run_node(client)

    close_call = next(c for c in client.calls_for("vote_sessions") if c.op == "update")
    assert close_call.payload == {"status": "closed"}
    create_call = next(c for c in client.calls_for("vote_sessions") if c.op == "insert")
    assert create_call is not None


async def test_a_different_category_open_session_is_left_alone() -> None:
    """A flight vote session must not be closed by a destination run."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, destinations=["Kyoto, Japan"])],
    )
    client.queue(
        "vote_sessions", [{"id": "flight-vs", "status": "open", "message_id": "flight-msg"}]
    )
    client.queue("messages", [{"id": "flight-msg", "content": {"category": "flight"}}])
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "new-vs", "status": "open"}])

    await run_node(client)

    assert all(c.op != "update" for c in client.calls_for("vote_sessions"))


# ===========================================================================
# Group_Profile isolation (Requirement 7.4)
# ===========================================================================


async def test_group_profile_is_never_passed_to_a_repository_write_call() -> None:
    """The profile lives only in Agent_State; no write payload carries it."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, destinations=["Kyoto, Japan"])],
    )
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    await run_node(client)

    for call in client.write_calls:
        payload_text = str(call.payload)
        assert "availability_overlap" not in payload_text
        assert "budget_ceiling" not in payload_text


async def test_the_resulting_state_carries_the_group_profile() -> None:
    """The profile is computed and held, even though it is never persisted."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        preferences=[preference_row(MEMBER_1, destinations=["Kyoto, Japan"])],
    )
    client.queue("vote_sessions", [])  # list_open_by_room
    client.queue("rpc:insert_message_turn", [{"id": "msg-1"}])
    client.queue("vote_sessions", [{"id": "vs-1"}])  # create()

    result = await run_node(client)

    assert result.group_profile is not None
    assert "availability_overlap" in result.group_profile
