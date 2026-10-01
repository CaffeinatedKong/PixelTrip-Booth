"""Domain exceptions for the PixelArt Trip Planner backend.

Architecture rule: the backend owns all business mutations and all error translation.
Repositories and services raise these exceptions; the handlers registered in
``app/main.py`` are the only place that turns them into HTTP responses, and every error
response uses the ``API_Error_Response`` envelope
(``{"error": {"code": ..., "message": ...}}``). The frontend may only read/subscribe
via the Supabase anon key.

Messages passed to these exceptions must be safe, developer-authored text. Never pass raw
Supabase payloads, SQL, constraint names, or secrets. ``RepositoryError`` messages are for
internal logs only; its handler always returns a fixed message.

Note: ``ValidationError`` here is our repository input-guard error, not Pydantic's.
Where both are needed, import Pydantic's as ``PydanticValidationError``.
"""


class BackendError(Exception):
    """Base class for all domain errors."""


class RoomNotFoundError(BackendError):
    """No room matches the given room code. Maps to HTTP 404 ``ROOM_NOT_FOUND``."""


class MemberAlreadyExistsError(BackendError):
    """A member with the same name already exists in the room (concurrent join).

    Maps to HTTP 409 ``MEMBER_ALREADY_EXISTS``.
    """


class InvalidDisplayNameError(BackendError):
    """Display name is empty or whitespace-only. Maps to HTTP 422 ``INVALID_DISPLAY_NAME``."""


class RepositoryError(BackendError):
    """An unexpected Supabase/database failure. Maps to HTTP 503 ``DATABASE_ERROR``."""


class RoomCodeExhaustedError(BackendError):
    """No unused room code was found after all retries. Maps to HTTP 500
    ``ROOM_CODE_EXHAUSTED``."""


class ValidationError(BackendError):
    """A repository input guard rejected an argument before any database call.

    Maps to HTTP 422 ``VALIDATION_ERROR``.
    """
