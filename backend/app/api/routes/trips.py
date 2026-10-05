"""Trip routes: start an AI run, check a run, and list itinerary versions.

An AI run can take a minute or more, so ``POST /trips/{trip_id}/runs`` returns the run
straight away (HTTP 202) and executes it in the background. Progress and results reach
the party as chat messages and itinerary versions over Realtime; ``GET /runs/{run_id}``
reports the run's status.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.api.deps import get_itinerary_service, get_run_endpoint_service
from app.schemas.agent_run import AgentRunSchema
from app.schemas.errors import ErrorResponse
from app.schemas.planning import ItineraryVersionSchema, StartRunRequest
from app.services.itinerary_service import ItineraryService
from app.services.run_endpoint_service import RunEndpointService

router = APIRouter(tags=["ai-runs"])

RunServiceDep = Annotated[RunEndpointService, Depends(get_run_endpoint_service)]
ItineraryServiceDep = Annotated[ItineraryService, Depends(get_itinerary_service)]


@router.post(
    "/trips/{trip_id}/runs",
    response_model=AgentRunSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an AI run",
    description=(
        "Starts a `discovery`, `logistics`, `itinerary`, or `refinement` run and returns "
        "it immediately with status `pending`; the AI works in the background. If a run "
        "of this type is already in progress for the trip, or the same `idempotencyKey` "
        "was used before, that existing run is returned instead of starting another."
    ),
    responses={
        202: {"description": "Run accepted (new or existing)"},
        404: {"model": ErrorResponse, "description": "Trip not found"},
        409: {"model": ErrorResponse, "description": "Idempotency key used for another run"},
        422: {
            "model": ErrorResponse,
            "description": "Validation error, or the member is not in this trip's room",
        },
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def start_run(
    trip_id: UUID,
    body: StartRunRequest,
    background_tasks: BackgroundTasks,
    service: RunServiceDep,
) -> AgentRunSchema:
    """Start (or return the existing) AI run for this trip and run type."""
    started = await service.start_run(
        str(trip_id), body.run_type, str(body.member_id), body.idempotency_key
    )
    if started.execute is not None:
        background_tasks.add_task(started.execute)
    return started.run


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunSchema,
    summary="Get an AI run's status",
    description="Returns the run with its current status (`pending`, `running`, "
    "`completed`, or `failed`) and, when finished, `resultVersionId` or `error`.",
    responses={
        200: {"description": "The run"},
        404: {"model": ErrorResponse, "description": "Run not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def get_run(run_id: UUID, service: RunServiceDep) -> AgentRunSchema:
    """Return the AI run's current status."""
    return await service.get_run(str(run_id))


@router.get(
    "/trips/{trip_id}/itinerary/versions",
    response_model=list[ItineraryVersionSchema],
    summary="List itinerary versions",
    description="Every itinerary version for the trip, oldest first. The version under "
    "review is the latest `proposed` one; at most one is `approved`.",
    responses={
        200: {"description": "The versions (possibly empty)"},
        404: {"model": ErrorResponse, "description": "Trip not found"},
        503: {"model": ErrorResponse, "description": "Database unavailable"},
    },
)
async def list_itinerary_versions(
    trip_id: UUID, service: ItineraryServiceDep
) -> list[ItineraryVersionSchema]:
    """List the trip's itinerary versions."""
    return await service.list_versions(str(trip_id))
