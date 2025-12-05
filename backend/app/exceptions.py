"""Custom exception classes for API error handling."""

from typing import List
from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """
    Raised when authentication fails.

    Returns 401 Unauthorized with custom message.
    """

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class CSVValidationError(HTTPException):
    """
    Raised when CSV validation fails.

    Returns 400 Bad Request with validation errors.
    """
    def __init__(self, detail: str, validation_errors: List[str]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "csv_validation_failed",
                "message": detail,
                "validation_errors": validation_errors
            }
        )
