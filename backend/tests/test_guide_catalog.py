"""Destination guides: the bundled data, the Supabase-backed loader, and its fallbacks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.agents import fallback_catalog
from app.agents.fallback_catalog import GuideCatalog, bundled_catalog, fallback_days
from app.agents.guide_catalog_loader import GUIDE_CACHE, MIN_SUGGESTIONS, load_catalog
from app.agents.nodes import discovery
from app.agents.party_brief import build_party_brief
from app.repositories.guide_repository import GuideRepository

from tests.agents.conftest import FakeSupabaseClient

pytestmark = pytest.mark.anyio

ROOT = Path(__file__).resolve().parents[2]


def guide_row(name: str, *, suggest: bool = True, activities: list[dict] | None = None) -> dict:
    return {
        "name": name,
        "keywords": ["asia", "food"],
        "description": f"About {name}.",
        "details": f"Details of {name}.",
        "tags": ["Food"],
        "daily_cost_sgd": 90,
        "typical_days": 3,
        "suggest": suggest,
        "active": True,
        "destination_activities": activities
        if activities is not None
        else [
            {"sort_order": 1, "title": "Evening noodles", "slot": "evening", "cost_sgd": 5},
            {
                "sort_order": 0,
                "title": "Old quarter walk",
                "slot": "morning",
                "start_time": "08:15",
                "cost_sgd": 0,
                "tags": ["culture"],
            },
        ],
    }


# --- the bundled data --------------------------------------------------------------------


def test_every_bundled_guide_is_usable() -> None:
    catalog = bundled_catalog()

    assert len(catalog) >= 20 and len(catalog.pool) >= MIN_SUGGESTIONS
    for guide in catalog.guides:
        assert guide.description and guide.details and guide.tags
        assert guide.daily_cost_sgd > 0 and 1 <= guide.typical_days <= 30
        titles = [a.title for a in guide.activities]
        assert len(titles) == len(set(titles)), f"{guide.name} repeats an activity"
        for slot in fallback_catalog.SLOTS:
            assert any(a.slot == slot for a in guide.activities), f"{guide.name} has no {slot}"
        assert all(a.cost_sgd >= 0 for a in guide.activities)


def test_the_seed_migration_matches_the_json_it_is_generated_from() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "backend/scripts/export_guides_seed.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout


def test_rows_from_supabase_become_guides_in_authoring_order() -> None:
    catalog = GuideCatalog.from_rows([guide_row("Hanoi, Vietnam")])

    guide = catalog.lookup("hanoi")
    assert guide is not None and guide.name == "Hanoi, Vietnam"
    assert [a.title for a in guide.activities] == ["Old quarter walk", "Evening noodles"]
    assert guide.activities[0].time == "08:15"
    assert guide.activities[0].tags == frozenset({"culture"})


def test_unusable_rows_are_skipped_not_fatal() -> None:
    bad = [{"name": "", "description": "x"}, {"name": "Nowhere, X"}, "not a row"]

    catalog = GuideCatalog.from_rows([r for r in bad if isinstance(r, dict)])

    assert len(catalog) == 0


# --- the repository ----------------------------------------------------------------------


async def test_the_repository_reads_active_guides_with_their_activities() -> None:
    client = FakeSupabaseClient()
    client.queue("destination_guides", [guide_row("Hanoi, Vietnam")])

    rows = await GuideRepository(client).list_active()

    assert rows[0]["name"] == "Hanoi, Vietnam"
    call = client.calls_for("destination_guides")[0]
    assert call.columns == "*, destination_activities(*)"
    assert ("active", "eq", True) in call.filters


# --- the loader --------------------------------------------------------------------------


def bundle_with(repo: object | None) -> SimpleNamespace:
    return SimpleNamespace(guide_repo=repo)


async def test_without_a_repository_the_bundled_guides_are_used() -> None:
    assert await load_catalog(bundle_with(None)) is bundled_catalog()


async def test_guides_from_the_database_win_and_are_cached() -> None:
    repo = AsyncMock()
    repo.list_active.return_value = [guide_row(f"City{i}, Land") for i in range(MIN_SUGGESTIONS)]

    first = await load_catalog(bundle_with(repo))
    second = await load_catalog(bundle_with(repo))

    assert first.lookup("City0, Land") is not None
    assert first.lookup("Kyoto, Japan") is None, "the table is the source when it has enough"
    assert second.lookup("City0, Land") is not None
    assert repo.list_active.await_count == 1


async def test_a_database_failure_falls_back_to_the_bundled_guides() -> None:
    repo = AsyncMock()
    repo.list_active.side_effect = RuntimeError("relation does not exist")

    assert await load_catalog(bundle_with(repo)) is bundled_catalog()
    assert GUIDE_CACHE.get("active") is None, "a failure is not cached"


async def test_an_empty_table_falls_back_to_the_bundled_guides() -> None:
    repo = AsyncMock()
    repo.list_active.return_value = []

    assert await load_catalog(bundle_with(repo)) is bundled_catalog()


async def test_a_nearly_empty_table_is_topped_up_so_there_is_always_enough_to_offer() -> None:
    repo = AsyncMock()
    repo.list_active.return_value = [guide_row("Hanoi, Vietnam")]

    catalog = await load_catalog(bundle_with(repo))

    assert catalog.lookup("Hanoi, Vietnam") is not None
    assert len(catalog.pool) >= MIN_SUGGESTIONS
    assert catalog.lookup("Kyoto, Japan") is not None


# --- the stages use whichever catalog they are given ---------------------------------


def test_discovery_offers_and_describes_a_guide_that_only_the_database_has() -> None:
    catalog = GuideCatalog.from_rows([guide_row(f"City{i}, Land{i}") for i in range(6)])
    brief = build_party_brief(
        [{"id": "m1", "display_name": "Gerald"}],
        [{"member_id": "m1", "destinations": ["asia"], "interests": ["food"]}],
        [],
        [{"start": "2026-12-20", "end": "2026-12-24"}],
    )

    names, cards = discovery._choose_destinations(brief, [], {"interests": ["food"]}, catalog)
    items = discovery._build_proposal(names, cards, brief, {}, catalog)["items"]

    assert len(items) == 5 and all(i["title"].startswith("City") for i in items)
    assert items[0]["description"].startswith("About City")
    assert items[0]["meta"]["estimatedDailyCostSgd"] == 90


def test_the_day_planner_uses_the_activities_from_the_catalog_it_is_given() -> None:
    catalog = GuideCatalog.from_rows([guide_row("Hanoi, Vietnam")])

    plan = fallback_days(
        "Hanoi, Vietnam",
        4,
        words=set(),
        allowed=lambda _text: True,
        ceiling=None,
        catalog=catalog,
    )

    assert plan[2][0].title == "Old quarter walk" and plan[2][0].time == "08:15"
    assert any(i.title == "Evening noodles" for items in plan.values() for i in items)
