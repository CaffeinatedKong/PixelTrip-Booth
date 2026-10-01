"""FastAPI application entrypoint for the PixelArt Trip Planner backend.

Creates the app, configures CORS, includes the routers, and registers the exception
handlers. The handlers are the only place exceptions become HTTP responses, and every
error response uses the ``API_Error_Response`` envelope
(``{"error": {"code": ..., "message": ...}}``).

Run locally with:
    uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, rooms
from app.core.config import get_settings
from app.exceptions import (
    InvalidDisplayNameError,
    MemberAlreadyExistsError,
    RepositoryError,
    RoomCodeExhaustedError,
    RoomNotFoundError,
    ValidationError,
)
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(rooms.router)


def _err(code: str, message: str) -> dict:
    """Build the standard error envelope."""
    return ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump()


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_err(code, message))


# Messages of these exceptions are authored by us and safe to return.
@app.exception_handler(RoomNotFoundError)
async def room_not_found_handler(request: Request, exc: RoomNotFoundError) -> JSONResponse:
    return _error_response(404, "ROOM_NOT_FOUND", str(exc))


@app.exception_handler(MemberAlreadyExistsError)
async def member_conflict_handler(request: Request, exc: MemberAlreadyExistsError) -> JSONResponse:
    return _error_response(409, "MEMBER_ALREADY_EXISTS", str(exc))


@app.exception_handler(InvalidDisplayNameError)
async def invalid_name_handler(request: Request, exc: InvalidDisplayNameError) -> JSONResponse:
    return _error_response(422, "INVALID_DISPLAY_NAME", str(exc))


@app.exception_handler(ValidationError)
async def repo_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return _error_response(422, "VALIDATION_ERROR", str(exc))


@app.exception_handler(RoomCodeExhaustedError)
async def code_exhausted_handler(request: Request, exc: RoomCodeExhaustedError) -> JSONResponse:
    return _error_response(500, "ROOM_CODE_EXHAUSTED", str(exc))


@app.exception_handler(RepositoryError)
async def repo_error_handler(request: Request, exc: RepositoryError) -> JSONResponse:
    # Details stay in internal logs only; the response carries a fixed safe message.
    logger.error("Repository error", exc_info=exc)
    return _error_response(503, "DATABASE_ERROR", "Database operation failed.")


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Replaces FastAPI's default {"detail": [...]} with the standard envelope.
    fields = ", ".join(".".join(str(part) for part in error["loc"]) for error in exc.errors())
    return _error_response(422, "VALIDATION_ERROR", f"Validation failed: {fields}")


@app.exception_handler(Exception)
async def catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error", exc_info=exc)
    return _error_response(500, "INTERNAL_ERROR", "An internal error occurred.")
