"""Tell a room what its AI run is doing, the moment it changes.

Browsers used to ask "how is the guide getting on?" every couple of seconds, each of them.
Now the backend says so when something happens (a run starts, moves to its next step,
finishes) by publishing to the room's Supabase Realtime Broadcast channel ``run:<roomId>``,
and browsers keep polling only as a slow backstop (see ``frontend/.../lib/runPoller.ts``).

The payload is the same small shape as ``GET /trips/{id}/runs/latest``: run id, type,
status, step and seconds elapsed. No party data goes on the channel, which anyone who
knows the room id could listen to.

Publishing is fire-and-forget and best-effort: a slow or failing broadcast never delays or
fails a run, and after a failure it rests for a minute rather than failing on every step.
This module also owns the short-lived "latest run" cache the polling endpoint answers
from, so a start or a finish can drop it in the same place that announces it.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.agents.progress import add_phase_listener
from app.core.config import get_settings
from app.core.ttl_cache import TTLCache

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.agents.state import AgentState

logger = logging.getLogger(__name__)

#: How long a trip's "latest run" answer is reused. Browsers still poll as a backstop; this
#: keeps that to about one database read per trip per interval however many people poll.
RUN_PROGRESS_TTL_SECONDS = 2.0

#: ``(trip_id, run_type or None) -> latest run row``; ``{}`` stands for "no run yet".
RUN_PROGRESS_CACHE: TTLCache[tuple[str, str | None], dict[str, Any]] = TTLCache(
    RUN_PROGRESS_TTL_SECONDS
)


def forget_run_progress(trip_id: str) -> None:
    """Drop cached progress for a trip, so a new or finished run shows at once."""
    RUN_PROGRESS_CACHE.invalidate(lambda key: key[0] == trip_id)


#: After a failed publish, stay quiet this long.
BROADCAST_REST_SECONDS = 60.0
BROADCAST_TIMEOUT_SECONDS = 3.0

_resting_until = 0.0
_tasks: set[asyncio.Task[None]] = set()
#: Test hook: lets tests answer the broadcast request without a network.
_transport: httpx.AsyncBaseTransport | None = None
#: ``run_id -> monotonic start``, to report seconds elapsed on each step.
_started: dict[str, float] = {}


def elapsed_seconds(run_id: str) -> int:
    """Seconds since this process first heard of the run."""
    now = time.monotonic()
    if len(_started) > 512:  # a backstop; finished runs are dropped by finish_run
        _started.clear()
    return round(now - _started.setdefault(run_id, now))


def finish_run(run_id: str) -> None:
    _started.pop(run_id, None)


def progress_payload(
    run_id: str, run_type: str, status: str, phase: str | None, elapsed: int
) -> dict[str, Any]:
    return {
        "id": run_id,
        "runType": run_type,
        "status": status,
        "phase": phase,
        "elapsedSeconds": elapsed,
    }


async def _publish(room_id: str, payload: dict[str, Any]) -> None:
    global _resting_until
    if time.monotonic() < _resting_until:
        return
    settings = get_settings()
    try:
        async with httpx.AsyncClient(
            base_url=settings.supabase_url.rstrip("/"),
            timeout=BROADCAST_TIMEOUT_SECONDS,
            transport=_transport,
        ) as http:
            response = await http.post(
                "/realtime/v1/api/broadcast",
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                },
                json={
                    "messages": [
                        {
                            "topic": f"run:{room_id}",
                            "event": "progress",
                            "payload": payload,
                            "private": False,
                        }
                    ]
                },
            )
            response.raise_for_status()
    except Exception as exc:  # best-effort: never let a broadcast touch the run
        _resting_until = time.monotonic() + BROADCAST_REST_SECONDS
        logger.info("Run progress broadcast failed (%s); resting", type(exc).__name__)


def publish_progress(room_id: str | None, payload: dict[str, Any]) -> None:
    """Schedule a broadcast to the room and return at once."""
    if not room_id or not get_settings().broadcast_run_progress:
        return
    try:
        task = asyncio.get_running_loop().create_task(_publish(room_id, payload))
    except RuntimeError:  # no running loop (a sync caller): nothing to schedule on
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def _on_phase(state: AgentState, phase: str) -> None:
    """A run moved to a new step: drop the cached answer and tell the room."""
    forget_run_progress(state.trip_id)
    room_id = (state.trip_context or {}).get("room_id")
    publish_progress(
        room_id,
        progress_payload(
            state.run_id, state.run_type, "running", phase, elapsed_seconds(state.run_id)
        ),
    )


def install() -> None:
    """Start announcing run steps. Call once at startup."""
    add_phase_listener(_on_phase)
