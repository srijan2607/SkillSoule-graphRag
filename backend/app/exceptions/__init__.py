"""Custom exceptions for the application."""

from app.exceptions.network_metrics import (
    NetworkMetricsError,
    PathNotFoundError,
    SkillNotFoundError,
    JobNotFoundError,
    GDSNotAvailableError,
    NetworkMetricsTimeoutError,
    CentralityCacheError,
    InvalidSkillSetError,
)
from app.exceptions.csv_validation import CSVValidationError
from app.exceptions.auth import AuthenticationError, AuthorizationError

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "CSVValidationError",
    "NetworkMetricsError",
    "PathNotFoundError",
    "SkillNotFoundError",
    "JobNotFoundError",
    "GDSNotAvailableError",
    "NetworkMetricsTimeoutError",
    "CentralityCacheError",
    "InvalidSkillSetError",
]
