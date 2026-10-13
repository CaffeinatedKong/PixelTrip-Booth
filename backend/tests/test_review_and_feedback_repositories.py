"""ReviewRepository and FeedbackRepository.upsert_open against the fake Supabase client."""

from __future__ import annotations

import pytest
from app.exceptions import RepositoryError
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.review_repository import ReviewRepository

from tests.agents.conftest import FakeSupabaseClient

TRIP = "22222222-2222-4222-8222-222222222222"
VERSION = "55555555-5555-4555-8555-555555555555"
MEMBER = "44444444-4444-4444-8444-444444444444"
TARGET = {"day": 2}


async def test_review_upsert_writes_one_row_per_member_and_version() -> None:
    client = FakeSupabaseClient()
    client.queue(
        "itinerary_reviews",
        [{"itinerary_version_id": VERSION, "member_id": MEMBER, "decision": "refine"}],
    )

    row = await ReviewRepository(client).upsert(TRIP, VERSION, MEMBER, "refine")

    assert row["decision"] == "refine"
    call = client.calls_for("itinerary_reviews")[0]
    assert call.payload == {
        "trip_id": TRIP,
        "itinerary_version_id": VERSION,
        "member_id": MEMBER,
        "decision": "refine",
    }


async def test_review_repository_wraps_failures() -> None:
    client = FakeSupabaseClient()
    client.queue("itinerary_reviews", RuntimeError("boom"))

    with pytest.raises(RepositoryError):
        await ReviewRepository(client).upsert(TRIP, VERSION, MEMBER, "approve")


async def test_feedback_upsert_inserts_when_nothing_matches() -> None:
    client = FakeSupabaseClient()
    client.queue("feedback", [])  # nothing open for this member/version/target
    client.queue("feedback", [{"id": "f1", "comment": "first", "target": TARGET}])

    row = await FeedbackRepository(client).upsert_open(TRIP, VERSION, MEMBER, TARGET, "first")

    assert row["id"] == "f1"
    assert [c.op for c in client.calls_for("feedback")] == ["select", "insert"]


async def test_feedback_upsert_rewrites_the_existing_row_instead_of_duplicating() -> None:
    client = FakeSupabaseClient()
    client.queue("feedback", [{"id": "f1", "comment": "first", "target": TARGET}])
    client.queue("feedback", [{"id": "f1", "comment": "second", "target": TARGET}])

    row = await FeedbackRepository(client).upsert_open(TRIP, VERSION, MEMBER, TARGET, "second")

    assert row["comment"] == "second"
    ops = [c.op for c in client.calls_for("feedback")]
    assert ops == ["select", "update"], "a retry must not insert a second row"


async def test_feedback_on_a_different_target_is_a_new_row() -> None:
    client = FakeSupabaseClient()
    client.queue("feedback", [{"id": "f1", "comment": "x", "target": {"day": 1}}])
    client.queue("feedback", [{"id": "f2", "comment": "y", "target": TARGET}])

    row = await FeedbackRepository(client).upsert_open(TRIP, VERSION, MEMBER, TARGET, "y")

    assert row["id"] == "f2"
    assert [c.op for c in client.calls_for("feedback")] == ["select", "insert"]
