"""Global error handling middleware for FastAPI."""

import logging
import uuid
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from neo4j.exceptions import ServiceUnavailable as Neo4jServiceUnavailable
from prisma.errors import PrismaError

logger = logging.getLogger(__name__)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Returns 422 Unprocessable Entity with validation error details.

    Args:
        request: FastAPI request
        exc: Pydantic validation error

    Returns:
        JSON response with validation error details

    Example Response:
        {
            "error": "validation_error",
            "message": "Request validation failed",
            "details": [
                {
                    "loc": ["body", "email"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ]
        }
    """
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors()
        }
    )


async def global_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle all uncaught exceptions.

    Logs full error details with stack trace for debugging but returns
    sanitized message to user (don't leak internal implementation details).

    Args:
        request: FastAPI request
        exc: Uncaught exception

    Returns:
        JSON response with 500 Internal Server Error

    Security:
        - Full error details logged for debugging
        - Sanitized message returned to user
        - Request ID included for support/debugging

    Example Response:
        {
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    # Generate request ID for debugging
    request_id = str(uuid.uuid4())

    # Log full error with stack trace
    logger.error(
        f"Unhandled exception (request_id: {request_id}): {str(exc)}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "client_host": request.client.host if request.client else "unknown"
        }
    )

    # Return sanitized error to user
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": request_id  # User can provide this for support
        }
    )


async def neo4j_connection_error_handler(
    request: Request,
    exc: Neo4jServiceUnavailable
) -> JSONResponse:
    """
    Handle Neo4j connection failures.

    Returns 503 Service Unavailable when graph database is unreachable.

    Args:
        request: FastAPI request
        exc: Neo4j service unavailable exception

    Returns:
        JSON response with 503 Service Unavailable

    Example Response:
        {
            "error": "service_unavailable",
            "message": "Graph database temporarily unavailable. Please try again later."
        }
    """
    logger.error(
        f"Neo4j connection error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "service_unavailable",
            "message": "Graph database temporarily unavailable. Please try again later."
        }
    )


async def postgres_connection_error_handler(
    request: Request,
    exc: PrismaError
) -> JSONResponse:
    """
    Handle PostgreSQL connection failures.

    Returns 503 Service Unavailable when database is unreachable.

    Args:
        request: FastAPI request
        exc: Prisma database error

    Returns:
        JSON response with 503 Service Unavailable

    Example Response:
        {
            "error": "service_unavailable",
            "message": "Database temporarily unavailable. Please try again later."
        }
    """
    logger.error(
        f"PostgreSQL connection error on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "service_unavailable",
            "message": "Database temporarily unavailable. Please try again later."
        }
    )
