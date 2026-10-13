"""How many database reads does a full room cost while the guide works?

    python backend/scripts/load_test_run_progress.py [members] [seconds]

Drives the real ``RunEndpointService.get_latest_run`` (and its cache) with N simulated
browsers on a fake clock, under three policies, and counts the reads that reach the
database and the requests that reach the backend:

  before     every browser polls every 2s, no cache
  cache      same polling, answered from the 2s in-process cache
  push       the backend pushes each step; browsers poll only every 10s as a backstop,
             answered from the cache (what ships)

It does not measure latency or the real Supabase Realtime service (that needs a deployed
backend); it shows what the *policy* costs the database. Default: 40 members, 60 seconds.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

os.environ.setdefault("SUPABASE_URL", "https://load-test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "load-test-key")

from app.core.ttl_cache import TTLCache  # noqa: E402
from app.services import run_endpoint_service as svc_module  # noqa: E402
from app.services.run_endpoint_service import RunEndpointService  # noqa: E402

TRIP = "22222222-2222-4222-8222-222222222222"
STEP = 0.05  # simulated seconds per tick


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


class CountingRepo:
    """A repository that counts reads and takes a (simulated) moment to answer."""

    def __init__(self) -> None:
        self.reads = 0

    async def get_latest_for_trip(self, trip_id: str, run_type: str | None) -> dict[str, Any]:
        self.reads += 1
        await asyncio.sleep(0)  # yield, as a real query would
        return {
            "id": "run",
            "run_type": "discovery",
            "status": "running",
            "phase": "asking_guide",
            "started_at": "2026-10-13T10:00:00+00:00",
        }

    async def get_by_id(self, _id: str) -> dict[str, Any]:  # trip lookup
        self.reads += 1
        return {"id": TRIP, "room_id": "room"}


async def run_policy(
    members: int, seconds: float, interval: float, cached: bool
) -> tuple[int, int]:
    clock = Clock()
    svc_module.RUN_PROGRESS_CACHE = TTLCache(2.0 if cached else 0.0, clock=clock)
    runs, trips = CountingRepo(), CountingRepo()
    service = RunEndpointService(
        **{
            name: SimpleNamespace()
            for name in (
                "room_repo",
                "message_repo",
                "member_repo",
                "profile_repo",
                "itinerary_version_repo",
                "selection_repo",
                "feedback_repo",
                "vote_session_repo",
                "vote_repo",
            )
        },
        agent_run_repo=runs,
        trip_repo=trips,
    )
    # Stagger the browsers, as real ones are, so they do not all fire on the same tick.
    next_poll = [i * interval / members for i in range(members)]
    requests = 0
    while clock.now < seconds:
        due = [i for i, t in enumerate(next_poll) if t <= clock.now]
        for i in due:
            requests += 1
            next_poll[i] += interval
        await asyncio.gather(*(service.get_latest_run(TRIP, "discovery") for _ in due))
        clock.now += STEP
    return requests, runs.reads + trips.reads


async def main() -> None:
    members = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 60.0
    print(f"{members} members, {seconds:.0f}s of a run in progress\n")
    print(f"{'policy':<10}{'requests':>10}{'req/s':>9}{'DB reads':>10}{'reads/s':>9}")
    for label, interval, cached in (
        ("before", 2.0, False),
        ("cache", 2.0, True),
        ("push", 10.0, True),
    ):
        requests, reads = await run_policy(members, seconds, interval, cached)
        print(
            f"{label:<10}{requests:>10}{requests / seconds:>9.1f}{reads:>10}{reads / seconds:>9.1f}"
        )


if __name__ == "__main__":
    asyncio.run(main())
