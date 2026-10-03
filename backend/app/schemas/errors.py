"""Standardized API error response schema (the ``API_Error_Response`` envelope).

Every error response from the backend has the shape
``{"error": {"code": "<CODE>", "message": "<safe message>"}}``.
"""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error code plus a safe, human-readable message."""

    code: str = Field(examples=["ROOM_NOT_FOUND"])
    message: str = Field(examples=["Room 'ABC123' not found."])


class ErrorResponse(BaseModel):
    """The error envelope returned by every exception handler."""

    error: ErrorDetail
