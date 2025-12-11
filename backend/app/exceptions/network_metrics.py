"""
Custom exceptions for network metrics operations.

Reference: Network Math Implementation - Phase 2 (02-SERVICES-LAYER.md)
"""


class NetworkMetricsError(Exception):
    """Base exception for network metrics operations."""

    def __init__(self, message: str, detail: str = None):
        self.message = message
        self.detail = detail
        super().__init__(self.message)


class PathNotFoundError(NetworkMetricsError):
    """Raised when no path exists between skills."""

    def __init__(self, skill_id_1: str, skill_id_2: str):
        self.skill_id_1 = skill_id_1
        self.skill_id_2 = skill_id_2
        message = f"No path found between skills {skill_id_1} and {skill_id_2}"
        super().__init__(message, f"Skills may be in disconnected graph components")


class SkillNotFoundError(NetworkMetricsError):
    """Raised when a skill is not found in the graph."""

    def __init__(self, skill_id: str):
        self.skill_id = skill_id
        message = f"Skill {skill_id} not found"
        super().__init__(message)


class JobNotFoundError(NetworkMetricsError):
    """Raised when a job is not found in the graph."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        message = f"Job {job_id} not found"
        super().__init__(message)


class GDSNotAvailableError(NetworkMetricsError):
    """Raised when GDS is required but not installed."""

    def __init__(self):
        message = "Neo4j Graph Data Science (GDS) library is not available"
        detail = "Some advanced algorithms require GDS. Falling back to approximations."
        super().__init__(message, detail)


class NetworkMetricsTimeoutError(NetworkMetricsError):
    """Raised when computation exceeds timeout."""

    def __init__(self, operation: str, timeout_seconds: float):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        message = f"Operation '{operation}' timed out after {timeout_seconds}s"
        detail = "Consider using cached results or reducing query scope"
        super().__init__(message, detail)


class CentralityCacheError(NetworkMetricsError):
    """Raised when centrality cache operation fails."""

    def __init__(self, operation: str):
        message = f"Centrality cache {operation} failed"
        super().__init__(message)


class InvalidSkillSetError(NetworkMetricsError):
    """Raised when provided skill set is invalid for operation."""

    def __init__(self, reason: str):
        message = f"Invalid skill set: {reason}"
        super().__init__(message)
