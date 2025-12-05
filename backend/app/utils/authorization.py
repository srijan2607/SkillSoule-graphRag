"""Authorization utilities for resource ownership verification."""

from fastapi import HTTPException, status


async def verify_job_ownership(
    job_user_id: str,
    current_user_id: str,
    job_id: str
) -> None:
    """
    Verify that the current user owns the specified job.

    Args:
        job_user_id: User ID from the job record
        current_user_id: Current authenticated user ID
        job_id: Job ID (for error messaging)

    Raises:
        HTTPException 403: User doesn't own the job

    Note:
        This is a utility function for authorization checks.
        Story 2.5 implements the authorization check directly in
        IngestionService.get_job_status_with_progress() for better
        encapsulation, but this utility is available for reuse elsewhere.
    """
    if job_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You do not have permission to access job {job_id}"
        )


def check_resource_ownership(
    resource_user_id: str,
    current_user_id: str,
    resource_type: str = "resource"
) -> bool:
    """
    Check if the current user owns a resource (non-raising version).

    Args:
        resource_user_id: User ID from the resource record
        current_user_id: Current authenticated user ID
        resource_type: Type of resource for logging (default: "resource")

    Returns:
        bool: True if user owns the resource, False otherwise
    """
    return resource_user_id == current_user_id
