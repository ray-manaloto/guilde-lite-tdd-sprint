"""Exception handlers for FastAPI application.

These handlers convert domain exceptions to proper HTTP responses.
"""

import logging
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions.

    Logs 5xx errors as errors and 4xx as warnings.
    Returns a standardized JSON error response.

    """
    method = request.method

    log_extra = {
        "error_code": exc.code,
        "status_code": exc.status_code,
        "details": exc.details,
        "path": request.url.path,
        "method": method,
    }

    if exc.status_code >= 500:
        logger.error(f"{exc.code}: {exc.message}", extra=log_extra)
    else:
        logger.warning(f"{exc.code}: {exc.message}", extra=log_extra)

    headers: dict[str, str] = {}
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = "Bearer"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details or None,
            }
        },
        headers=headers,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.

    In production: Logs the full exception but returns a generic error to the client
    to avoid leaking sensitive information (stack traces, internal details).

    In development/local: Re-raises the exception to show full stack traces for debugging.
    """
    # In non-production environments, re-raise to show full stack traces
    if settings.ENVIRONMENT not in ("production", "staging"):
        raise exc

    method = request.method

    logger.exception(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": method,
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": None,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Call this after creating the FastAPI application instance.

    The unhandled exception handler is always registered to prevent
    leaking stack traces in production/staging environments.
    In development/local, it re-raises exceptions for debugging.
    """
    app.add_exception_handler(AppException, cast(ExceptionHandler, app_exception_handler))
    app.add_exception_handler(Exception, cast(ExceptionHandler, unhandled_exception_handler))
