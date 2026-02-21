"""Structured JSON error handlers for FastAPI.

All exceptions return a consistent JSON envelope so clients can
reliably parse error responses regardless of the failure type.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")


def _error_response(status_code: int, detail: Any) -> JSONResponse:
    """Build a standardized JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"status_code": status_code, "detail": detail}},
    )


async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle HTTPException with a structured JSON envelope."""
    return _error_response(exc.status_code, exc.detail)


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with field-level detail."""
    errors = [
        {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return _error_response(422, errors)


async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled exceptions. Never leaks stack traces."""
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(500, "Internal server error")


def register_error_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
