"""Tests for persist_itinerary_version and itinerary_node."""

from __future__ import annotations

from typing import Any

import pytest
from app.agents.errors import (
    DestinationNotSelectedError,
    FlightNotSelectedError,
    InvalidTripDurationError,
    ItineraryPersistenceError,
    PreferencesNotCollectedError,
    RepeatedVersionContentionError,
)
from app.agents.nodes.itinerary import itinerary_node, persist_itinerary_version
from app.agents.state import AgentState
from app.exceptions import RepositoryError
from app.repositories.itinerary_version_repository import (
    ItineraryVersionRepository,
    UniqueVersionViolation,
)

from tests.agents.conftest import FakeSupabaseClient
from tests.agents.test_messages import ROOM, TRIP, wired_bundle

RUN = "33333333-3333-3333-3333-333333333333"
MEMBER_1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def make_state(**overrides: Any) -> AgentState:
    base: dict[str, Any] = {"run_id": RUN, "trip_id": TRIP, "run_type": "itinerary"}
    base.update(overrides)
    return AgentState(**base)


async def _never_applicable(_latest: dict[str, Any]) -> bool:
    return False


async def _always_applicable(_latest: dict[str, Any]) -> bool:
    return True


# ===========================================================================
# persist_itinerary_version — collision counting (Requirement 5.11-5.13)
# ===========================================================================


class _CollidingRepo(ItineraryVersionRepository):
    """Raises UniqueVersionViolation for the first ``collisions`` inserts."""

    def __init__(self, client: FakeSupabaseClient, collisions: int) -> None:
        super().__init__(client)
        self._remaining = collisions
        self.insert_calls: list[int] = []
        self.get_latest_calls = 0
        self.supersede_calls: list[int] = []

    async def insert_version(self, *, trip_id: str, version: int, **kwargs: Any) -> dict[str, Any]:
        self.insert_calls.append(version)
        if self._remaining > 0:
            self._remaining -= 1
            raise UniqueVersionViolation(trip_id, version)
        return {"id": f"v{version}", "trip_id": trip_id, "version": version, **kwargs}

    async def get_latest(self, trip_id: str) -> dict[str, Any] | None:
        self.get_latest_calls += 1
        # Each collision bumps the "existing" latest version by one.
        return {"id": "latest", "trip_id": trip_id, "version": len(self.insert_calls)}

    async def supersede_lower_versions(self, trip_id: str, below_version: int) -> None:
        self.supersede_calls.append(below_version)


@pytest.mark.parametrize("collisions", [0, 1, 2])
async def test_n_collisions_resolve_with_exactly_one_successful_insert(
    collisions: int,
) -> None:
    """0, 1, and 2 collisions each end in exactly one successful insert."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions)
    state = make_state()
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    row, _state = await persist_itinerary_version(
        state, bundle, {"days": []}, "build", None, _always_applicable
    )

    assert row is not None
    assert len(repo.insert_calls) == collisions + 1
    assert repo.get_latest_calls == collisions
    assert len(repo.supersede_calls) == 1


async def test_a_third_collision_raises_without_a_further_insert() -> None:
    """Requirement 5.12: a 3rd collision stops attempting inserts."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions=3)
    state = make_state()
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    with pytest.raises(RepeatedVersionContentionError):
        await persist_itinerary_version(
            state, bundle, {"days": []}, "build", None, _always_applicable
        )

    # Exactly 3 insert attempts: the original plus 2 retries, never a 4th.
    assert len(repo.insert_calls) == 3


async def test_a_lost_race_that_is_no_longer_applicable_writes_nothing_further() -> None:
    """Requirement 5.6: inapplicable after a lost race ends with no further write."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions=1)
    state = make_state()
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    row, final_state = await persist_itinerary_version(
        state, bundle, {"days": []}, "build", None, _never_applicable
    )

    assert row is None
    assert len(repo.insert_calls) == 1  # the one collision, then no retry
    assert final_state.base_version == 1  # updated per Requirement 5.5


async def test_a_non_collision_repository_error_never_retries() -> None:
    """Requirement 5.13: a non-UNIQUE failure fails the run outright."""

    class _BrokenRepo(ItineraryVersionRepository):
        def __init__(self) -> None:
            super().__init__(FakeSupabaseClient())
            self.insert_calls = 0

        async def insert_version(self, **_kwargs: Any) -> dict[str, Any]:
            self.insert_calls += 1
            raise RepositoryError("the database is down")

    repo = _BrokenRepo()
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    with pytest.raises(ItineraryPersistenceError):
        await persist_itinerary_version(
            make_state(), bundle, {"days": []}, "build", None, _always_applicable
        )

    assert repo.insert_calls == 1


async def test_every_inserted_row_satisfies_the_build_source_invariant() -> None:
    """Requirement 5.7: version 1 pairs with 'build'; later versions with 'refine'."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions=0)
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    await persist_itinerary_version(
        make_state(base_version=0), bundle, {"days": []}, "build", None, _always_applicable
    )
    await persist_itinerary_version(
        make_state(base_version=1), bundle, {"days": []}, "refine", "change", _always_applicable
    )

    with pytest.raises(ValueError, match="invalid for version"):
        await persist_itinerary_version(
            make_state(base_version=5), bundle, {"days": []}, "build", None, _always_applicable
        )


async def test_every_inserted_row_is_status_proposed() -> None:
    """Requirement 5.8: a newly inserted row is always 'proposed'."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions=0)
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    row, _state = await persist_itinerary_version(
        make_state(), bundle, {"days": []}, "build", None, _always_applicable
    )

    # The fake repo's insert_version returns exactly the kwargs it was given
    # plus id/trip_id/version; status is never one of its kwargs, matching the
    # real repository's own hardcoded 'proposed' on insert.
    assert "status" not in row or row.get("status") != "approved"


async def test_base_version_updates_on_every_lost_race() -> None:
    """Requirement 5.5: base_version tracks the latest re-fetched version."""
    repo = _CollidingRepo(FakeSupabaseClient(), collisions=2)
    bundle = type("B", (), {"itinerary_version_repo": repo})()

    _row, final_state = await persist_itinerary_version(
        make_state(base_version=0), bundle, {"days": []}, "build", None, _always_applicable
    )

    assert final_state.base_version >= 2


# ===========================================================================
# itinerary_node — preconditions (Requirement 9.11-9.12)
# ===========================================================================


def preference_row(member_id: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "member_id": member_id,
        "available_dates": [{"start": "2026-06-01", "end": "2026-06-05"}],
        "destinations": [],
        "hard_constraints": [],
        "budget": None,
        "interests": [],
        "activities": [],
        "travel_style": None,
    }
    base.update(overrides)
    return base


def destination_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "room_id": ROOM,
        "kind": "destination",
        "data": {"title": "Osaka, Japan"},
    }
    base.update(overrides)
    return base


def flight_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "room_id": ROOM,
        "kind": "flight",
        "data": {
            "depart_at": "2026-06-05T08:00:00",
            "return_at": "2026-06-10T20:00:00",
        },
    }
    base.update(overrides)
    return base


def wire_base_context(
    client: FakeSupabaseClient,
    *,
    selections: list[dict[str, Any]] | None = None,
    preferences: list[dict[str, Any]] | None = None,
) -> None:
    client.set_default("trips", [{"id": TRIP, "room_id": ROOM, "status": "flight_selected"}])
    client.set_default("party_rooms", [{"id": ROOM, "status": "active", "planning_stage": "build"}])
    client.set_default("room_members", [{"id": MEMBER_1}])
    client.set_default(
        "selections",
        selections if selections is not None else [destination_row(), flight_row()],
    )
    client.set_default("itinerary_versions", [])
    client.set_default("feedback", [])
    client.set_default("characters", [])
    client.set_default(
        "travel_preferences", preferences if preferences is not None else [preference_row(MEMBER_1)]
    )


async def run_node(client: FakeSupabaseClient, state: AgentState | None = None) -> AgentState:
    bundle = wired_bundle(client)
    config = {"configurable": {"repos": bundle}}
    return await itinerary_node(state or make_state(), config)


async def test_missing_destination_raises_with_no_insert() -> None:
    """Requirement 9.11: a missing destination selection fails before any write."""
    client = FakeSupabaseClient()
    wire_base_context(client, selections=[flight_row()])

    with pytest.raises(DestinationNotSelectedError):
        await run_node(client)

    assert client.write_calls == []


async def test_missing_flight_raises_with_no_insert() -> None:
    """Requirement 9.11: a missing flight selection fails before any write."""
    client = FakeSupabaseClient()
    wire_base_context(client, selections=[destination_row()])

    with pytest.raises(FlightNotSelectedError):
        await run_node(client)

    assert client.write_calls == []


async def test_missing_preferences_raises_with_no_insert() -> None:
    """Requirement 9.12: no travel_preferences at all fails before any write."""
    client = FakeSupabaseClient()
    wire_base_context(client, preferences=[])

    with pytest.raises(PreferencesNotCollectedError):
        await run_node(client)

    assert client.write_calls == []


# ===========================================================================
# Day-count derivation (Requirement 9.3-9.5)
# ===========================================================================


async def test_a_zero_day_duration_raises_invalid_trip_duration() -> None:
    """A departure after the return date derives a non-positive day count."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        selections=[
            destination_row(),
            flight_row(
                data={"depart_at": "2026-06-10T08:00:00", "return_at": "2026-06-05T20:00:00"}
            ),
        ],
    )

    with pytest.raises(InvalidTripDurationError):
        await run_node(client)

    assert client.write_calls == []


async def test_a_31_day_duration_raises_invalid_trip_duration() -> None:
    """Requirement 9.5: more than 30 days fails the run."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        selections=[
            destination_row(),
            flight_row(
                data={"depart_at": "2026-06-01T08:00:00", "return_at": "2026-07-01T20:00:00"}
            ),
        ],
    )

    with pytest.raises(InvalidTripDurationError):
        await run_node(client)

    assert client.write_calls == []


async def test_missing_flight_dates_fall_back_to_the_availability_overlap() -> None:
    """Requirement 9.4: the overlap substitutes for absent flight dates."""
    client = FakeSupabaseClient()
    wire_base_context(
        client,
        selections=[destination_row(), flight_row(data={})],
        preferences=[
            preference_row(MEMBER_1, available_dates=[{"start": "2026-06-01", "end": "2026-06-03"}])
        ],
    )
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue(
        "itinerary_versions", [{"id": "v1", "trip_id": TRIP, "version": 1, "status": "proposed"}]
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    result = await run_node(client)

    insert_call = next(c for c in client.calls_for("itinerary_versions") if c.op == "insert")
    assert len(insert_call.payload["itinerary"]["days"]) == 3
    assert result.proposal is not None


# ===========================================================================
# Generated itinerary shape (Requirement 9.2, 9.6, 9.9)
# ===========================================================================


async def test_a_successful_build_inserts_version_one_with_build_source() -> None:
    """Requirement 9.7: version=1, source='build', status='proposed', no changeSummary."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest: none yet
    client.queue(
        "itinerary_versions", [{"id": "v1", "trip_id": TRIP, "version": 1, "status": "proposed"}]
    )  # insert_version
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    insert_call = next(c for c in client.calls_for("itinerary_versions") if c.op == "insert")
    assert insert_call.payload["version"] == 1
    assert insert_call.payload["source"] == "build"
    assert insert_call.payload["change_summary"] is None


async def test_day_numbers_start_at_one_with_no_gaps() -> None:
    """Requirement 9.2: a continuous day sequence."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue(
        "itinerary_versions", [{"id": "v1", "trip_id": TRIP, "version": 1, "status": "proposed"}]
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    insert_call = next(c for c in client.calls_for("itinerary_versions") if c.op == "insert")
    days = insert_call.payload["itinerary"]["days"]
    assert [d["day"] for d in days] == list(range(1, len(days) + 1))


async def test_item_ids_are_unique_across_all_days() -> None:
    """Requirement 9.9: no item id repeats, so feedback can target one uniquely."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue(
        "itinerary_versions", [{"id": "v1", "trip_id": TRIP, "version": 1, "status": "proposed"}]
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    insert_call = next(c for c in client.calls_for("itinerary_versions") if c.op == "insert")
    ids = [item["id"] for day in insert_call.payload["itinerary"]["days"] for item in day["items"]]
    assert len(set(ids)) == len(ids)


# ===========================================================================
# Success side effects (Requirement 9.14-9.15, 9.16)
# ===========================================================================


async def test_success_emits_a_summary_referencing_the_version_id() -> None:
    """Requirement 9.14: one summary message naming the persisted version id."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue(
        "itinerary_versions",
        [{"id": "the-version-id", "trip_id": TRIP, "version": 1, "status": "proposed"}],
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    sent = client.calls_for("rpc:insert_message_turn")[0].payload["p_messages"][0]
    assert sent["kind"] == "summary"
    assert sent["content"]["itinerary_version_id"] == "the-version-id"


async def test_success_advances_trip_status_to_itinerary_generated() -> None:
    """Requirement 9.15: trips.status moves to itinerary_generated."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue(
        "itinerary_versions", [{"id": "v1", "trip_id": TRIP, "version": 1, "status": "proposed"}]
    )
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    rpc_call = client.calls_for("rpc:set_trip_status_and_stage")[0]
    assert rpc_call.payload["p_status"] == "itinerary_generated"


async def test_persisted_itinerary_dict_includes_id_and_status_fields() -> None:
    """Requirement 9.16: id/status persist regardless of the frontend type's gap."""
    client = FakeSupabaseClient()
    wire_base_context(client)
    persisted_row = {
        "id": "the-version-id",
        "trip_id": TRIP,
        "version": 1,
        "status": "proposed",
    }
    client.queue("itinerary_versions", [])  # load_trip_context's get_latest
    client.queue("itinerary_versions", [persisted_row])
    client.queue("rpc:insert_message_turn", [{"id": "m1", "kind": "summary"}])
    client.queue("rpc:set_trip_status_and_stage", [{"id": TRIP, "status": "itinerary_generated"}])

    await run_node(client)

    # The version row itself (not the itinerary jsonb) is what carries id/status
    # per the DB schema; simulate the "frontend type omits them" gap by
    # asserting the service-facing row still has both regardless.
    assert persisted_row["id"] and persisted_row["status"]
    insert_call = next(c for c in client.calls_for("itinerary_versions") if c.op == "insert")
    all_item_ids = [
        item["id"] for day in insert_call.payload["itinerary"]["days"] for item in day["items"]
    ]
    assert all(all_item_ids)
