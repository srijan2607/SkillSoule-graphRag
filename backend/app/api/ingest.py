"""Ingestion API endpoints for CSV file uploads.

Story 2.3 Changes:
- Upload endpoints now return CSV preview (200) instead of immediate job (202)
- User must confirm via /confirm endpoint to start actual ingestion
- Files are temporarily cached for 1 hour while awaiting confirmation
"""

import logging
import io
from fastapi import APIRouter, Depends, File, UploadFile, status, HTTPException
from fastapi.responses import StreamingResponse
from typing import Annotated

from app.models.ingestion import (
    CSVPreviewResponse,
    ConfirmUploadRequest,
    IngestionJobResponse,
    IngestionJobDetail,
    IngestionStatusResponse
)
from app.models.ingestion_mode import IngestionMode
from app.services.ingestion_service import IngestionService
from app.services.csv_validation_service import CSVValidationService
from app.services.error_logging_service import ErrorLoggingService
from app.middleware.auth import get_current_user
from app.dependencies import get_ingestion_service, get_csv_validation_service, get_error_logging_service
from app.utils.file_validation import validate_csv_file
from app.utils.file_cache import store_temp_file, retrieve_temp_file, delete_temp_file
from app.utils.csv_export import errors_to_csv

# Configure logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "/skills",
    response_model=CSVPreviewResponse,
    status_code=status.HTTP_200_OK,  # Changed from 202 to 200 (Story 2.3)
    summary="Upload skills CSV and get preview"
)
async def upload_skills_csv(
    file: Annotated[UploadFile, File(description="CSV file containing skills data")],
    user_id: str = Depends(get_current_user),
    validation_service: CSVValidationService = Depends(get_csv_validation_service)
) -> CSVPreviewResponse:
    """
    Upload skills CSV and return preview for user confirmation.

    **Story 2.3 Behavior Change:**
    - Returns preview data with first 10 rows (does NOT start ingestion)
    - User must call POST /ingest/confirm to start actual ingestion
    - File is cached temporarily (1 hour TTL) while awaiting confirmation

    Protected endpoint - requires JWT authentication.

    Args:
        file: CSV file (max 500MB)
        user_id: Extracted from JWT token
        validation_service: Injected service

    Returns:
        200 OK with preview data

    Raises:
        400: Invalid file type or CSV validation error
        401: Unauthorized (missing/invalid token)
        413: File too large
        422: Validation error
    """
    logger.info(
        f"Skills CSV upload requested by user {user_id}. "
        f"Filename: {file.filename}"
    )

    # Validate file format (extension, MIME type, size, sanitize filename)
    sanitized_filename, file_size_mb = await validate_csv_file(file)

    # Read file content for validation and preview
    content = await file.read()

    logger.debug(
        f"File read successfully. Size: {file_size_mb:.2f}MB, "
        f"Sanitized filename: {sanitized_filename}"
    )

    # Validate CSV structure and get preview
    preview_data = validation_service.validate_and_preview_skills(
        content,
        preview_rows=10
    )

    # Store file temporarily for confirmation (with metadata for job creation)
    file_hash = store_temp_file(
        content=content,
        file_type="skills",
        filename=sanitized_filename,
        ttl_hours=1
    )

    logger.info(
        f"Skills CSV preview generated for user {user_id}. "
        f"Total rows: {preview_data['total_rows']}, "
        f"Preview rows: {len(preview_data['preview_rows'])}, "
        f"File hash: {file_hash[:16]}..."
    )

    return CSVPreviewResponse(
        **preview_data,
        file_hash=file_hash,
        file_type="skills"
    )


@router.post(
    "/jobs",
    response_model=CSVPreviewResponse,
    status_code=status.HTTP_200_OK,  # Changed from 202 to 200 (Story 2.3)
    summary="Upload jobs CSV and get preview"
)
async def upload_jobs_csv(
    file: Annotated[UploadFile, File(description="CSV file containing jobs data")],
    user_id: str = Depends(get_current_user),
    validation_service: CSVValidationService = Depends(get_csv_validation_service)
) -> CSVPreviewResponse:
    """
    Upload jobs CSV and return preview for user confirmation.

    **Story 2.3 Behavior Change:**
    - Returns preview data with first 10 rows (does NOT start ingestion)
    - User must call POST /ingest/confirm to start actual ingestion
    - File is cached temporarily (1 hour TTL) while awaiting confirmation

    Protected endpoint - requires JWT authentication.

    Args:
        file: CSV file (max 500MB)
        user_id: Extracted from JWT token
        validation_service: Injected service

    Returns:
        200 OK with preview data

    Raises:
        400: Invalid file type or CSV validation error
        401: Unauthorized (missing/invalid token)
        413: File too large
        422: Validation error
    """
    logger.info(
        f"Jobs CSV upload requested by user {user_id}. "
        f"Filename: {file.filename}"
    )

    # Validate file format (extension, MIME type, size, sanitize filename)
    sanitized_filename, file_size_mb = await validate_csv_file(file)

    # Read file content for validation and preview
    content = await file.read()

    logger.debug(
        f"File read successfully. Size: {file_size_mb:.2f}MB, "
        f"Sanitized filename: {sanitized_filename}"
    )

    # Validate CSV structure and get preview
    preview_data = validation_service.validate_and_preview_jobs(
        content,
        preview_rows=10
    )

    # Store file temporarily for confirmation (with metadata for job creation)
    file_hash = store_temp_file(
        content=content,
        file_type="jobs",
        filename=sanitized_filename,
        ttl_hours=1
    )

    logger.info(
        f"Jobs CSV preview generated for user {user_id}. "
        f"Total rows: {preview_data['total_rows']}, "
        f"Preview rows: {len(preview_data['preview_rows'])}, "
        f"File hash: {file_hash[:16]}..."
    )

    return CSVPreviewResponse(
        **preview_data,
        file_hash=file_hash,
        file_type="jobs"
    )


@router.post(
    "/confirm",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Confirm CSV upload and start ingestion"
)
async def confirm_upload(
    confirmation: ConfirmUploadRequest,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> IngestionJobResponse:
    """
    Confirm CSV upload and start ingestion process (Story 3.7: Enhanced with ingestion modes).

    After reviewing the preview, user calls this endpoint to start actual
    ingestion. Retrieves temporarily cached file and creates IngestionJob.

    **Story 3.7 - Ingestion Modes:**
    - INCREMENTAL (default): Upsert nodes, preserve existing data
    - FULL: Delete all graph data before ingestion (requires confirmation='CONFIRM DELETE')

    Protected endpoint - requires JWT authentication.

    Args:
        confirmation: Request with file_hash, file_type, mode, and confirmation
        user_id: Extracted from JWT token
        ingestion_service: Injected service

    Returns:
        202 Accepted with ingestion_job_id

    Raises:
        400: Invalid file_type, full mode without confirmation, or incorrect confirmation text
        401: Unauthorized
        404: File not found or expired (user must re-upload)
    """
    logger.info(
        f"Ingestion confirmation requested by user {user_id}. "
        f"File hash: {confirmation.file_hash[:16]}..., "
        f"Type: {confirmation.file_type}, Mode: {confirmation.mode}"
    )

    # Validate full mode confirmation (Story 3.7)
    if confirmation.mode == IngestionMode.FULL:
        if not confirmation.confirmation or confirmation.confirmation != "CONFIRM DELETE":
            logger.warning(
                f"Full mode ingestion attempted without proper confirmation. "
                f"User: {user_id}, Confirmation: {confirmation.confirmation}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Full mode requires explicit confirmation. "
                    "Set confirmation='CONFIRM DELETE' to proceed. "
                    "WARNING: This will delete ALL existing graph data."
                )
            )

        logger.warning(
            f"⚠️  FULL MODE INGESTION initiated by user {user_id}. "
            f"All graph data will be deleted. File: {confirmation.file_type}"
        )

    # Retrieve file from temporary storage
    file_data = retrieve_temp_file(confirmation.file_hash)

    if not file_data:
        logger.warning(
            f"File not found or expired for confirmation. "
            f"Hash: {confirmation.file_hash[:16]}..., User: {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found or expired. Please upload the file again."
        )

    # Verify file_type matches cached data (security check)
    if file_data["file_type"] != confirmation.file_type:
        logger.error(
            f"File type mismatch. Requested: {confirmation.file_type}, "
            f"Cached: {file_data['file_type']}, Hash: {confirmation.file_hash[:16]}..."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type mismatch. Expected {file_data['file_type']}, got {confirmation.file_type}."
        )

    # Start ingestion from cached data
    response = await ingestion_service.start_ingestion_from_cache(
        content=file_data["content"],
        file_type=file_data["file_type"],
        filename=file_data["filename"],
        file_size_mb=file_data["file_size_mb"],
        user_id=user_id,
        mode=confirmation.mode
    )

    # Clean up temporary file after successful job creation
    if delete_temp_file(confirmation.file_hash):
        logger.debug(f"Temporary file cleaned up: {confirmation.file_hash[:16]}...")

    logger.info(
        f"Ingestion confirmed and started. Job ID: {response.ingestion_job_id}, "
        f"User: {user_id}"
    )

    return response


@router.get(
    "/status/{job_id}",
    response_model=IngestionStatusResponse,
    summary="Poll ingestion job status (real-time progress)"
)
async def poll_ingestion_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> IngestionStatusResponse:
    """
    Poll ingestion job status and progress (Story 2.5).

    Frontend should poll this endpoint every 2 seconds while status
    is "pending" or "processing".

    Polling stops when status is "completed", "completed_with_errors", or "failed".

    Protected endpoint - requires JWT authentication.

    Authorization:
    - User must own the job (user_id must match job.user_id)

    Args:
        job_id: Ingestion job ID
        user_id: Extracted from JWT token
        ingestion_service: Injected service

    Returns:
        Real-time status with progress percentage and ETA

    Raises:
        401: Unauthorized
        403: Forbidden (user doesn't own the job)
        404: Job not found
    """
    logger.debug(
        f"Status poll requested for job {job_id} by user {user_id}"
    )

    return await ingestion_service.get_job_status_with_progress(job_id, user_id)


@router.get(
    "/errors/{job_id}",
    summary="Download error log as CSV (Story 2.6)"
)
async def download_error_log(
    job_id: str,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    error_service: ErrorLoggingService = Depends(get_error_logging_service)
) -> StreamingResponse:
    """
    Download error log for ingestion job as CSV (Story 2.6).

    Returns CSV file with columns: row_number, error_message, raw_data

    Protected endpoint - requires JWT authentication.

    Authorization:
    - User must own the job (user_id must match job.user_id)

    Args:
        job_id: Ingestion job ID
        user_id: Extracted from JWT token
        ingestion_service: Injected service
        error_service: Injected error logging service

    Returns:
        CSV file download (Content-Disposition: attachment)

    Raises:
        401: Unauthorized (missing/invalid token)
        403: Forbidden (user doesn't own the job)
        404: Job not found
        400: No errors to download for this job

    Example:
        GET /api/ingest/errors/550e8400-e29b-41d4-a716-446655440000
        Returns: ingestion_errors_550e8400-e29b-41d4-a716-446655440000.csv
    """
    logger.info(
        f"Error log download requested for job {job_id} by user {user_id}"
    )

    # Verify job exists and user owns it
    job = await ingestion_service.ingestion_repo.find_by_id(job_id)

    if not job:
        logger.warning(f"Job not found: {job_id}, User: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingestion job {job_id} not found"
        )

    if job.user_id != user_id:
        logger.warning(
            f"Unauthorized error log access attempt. "
            f"Job: {job_id}, User: {user_id}, Owner: {job.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this job"
        )

    # Check if there are errors to download
    if job.failed_records == 0:
        logger.info(
            f"No errors to download for job {job_id}. "
            f"Failed records: {job.failed_records}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No errors to download for this job"
        )

    # Fetch errors from database
    errors = await error_service.get_job_errors(job_id, limit=10000)

    logger.debug(
        f"Retrieved {len(errors)} errors for job {job_id}"
    )

    # Convert to CSV
    csv_content = errors_to_csv(errors)

    logger.info(
        f"Error log CSV generated for job {job_id}. "
        f"Size: {len(csv_content)} bytes, Errors: {len(errors)}"
    )

    # Return as downloadable file
    return StreamingResponse(
        io.BytesIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=ingestion_errors_{job_id}.csv"
        }
    )


@router.get(
    "/jobs/{job_id}",
    response_model=IngestionJobDetail,
    summary="Get ingestion job status"
)
async def get_ingestion_job_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> IngestionJobDetail:
    """
    Get ingestion job status and details.

    Protected endpoint - requires JWT authentication.

    Args:
        job_id: Ingestion job ID
        user_id: Extracted from JWT token
        ingestion_service: Injected service

    Returns:
        Detailed job information

    Raises:
        401: Unauthorized
        404: Job not found or doesn't belong to user
    """
    return await ingestion_service.get_job_status(job_id, user_id)


@router.get(
    "/jobs",
    response_model=list[IngestionJobDetail],
    summary="Get user's ingestion jobs"
)
async def get_user_ingestion_jobs(
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> list[IngestionJobDetail]:
    """
    Get all ingestion jobs for the authenticated user.

    Protected endpoint - requires JWT authentication.

    Args:
        user_id: Extracted from JWT token
        ingestion_service: Injected service

    Returns:
        List of user's ingestion jobs (most recent first)

    Raises:
        401: Unauthorized
    """
    return await ingestion_service.get_user_jobs(user_id)
