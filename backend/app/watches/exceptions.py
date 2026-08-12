# TODO: Validate
"""Errors raised by the watches service, and how they map to responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


# TODO: Validate
class WatchAlreadyExistsError(Exception):
    """The `Episode` already has an unverified `Watch`."""


# TODO: Validate
async def handle_watch_already_exists(
    _request: Request,
    exception: Exception,
) -> JSONResponse:
    """Return the 409 response for a `WatchAlreadyExistsError`."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exception)},
    )
