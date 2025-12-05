"""Ingestion Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models.ingestion_mode import IngestionMode


class IngestionJobResponse(BaseModel):
    """Response model for successful file upload (Story 3.7: Enhanced with upsert statistics)."""

    ingestion_job_id: str = Field(..., description="Unique identifier for the ingestion job")
    status: str = Field(default="pending", description="Current status of the job")
    message: str = Field(default="File uploaded successfully and queued for processing")
    mode: IngestionMode = Field(default=IngestionMode.INCREMENTAL, description="Ingestion mode: incremental or full")
    total_records: int = Field(default=0, description="Total number of records in CSV")
    processed_records: int = Field(default=0, description="Number of successfully processed records")
    nodes_created: int = Field(default=0, description="Number of new nodes created (Story 3.7)")
    nodes_updated: int = Field(default=0, description="Number of existing nodes updated (Story 3.7)")
    nodes_unchanged: int = Field(default=0, description="Number of nodes unchanged (Story 3.7)")
    failed_records: int = Field(default=0, description="Number of failed records")
    has_errors: bool = Field(default=False, description="True if any records failed (Story 2.6)")
    error_download_url: Optional[str] = Field(None, description="URL to download error log CSV (Story 2.6)")

    class Config:
        json_schema_extra = {
            "example": {
                "ingestion_job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed_with_errors",
                "message": "40,518 / 40,523 records ingested successfully (5 failed). Download error log to review failures.",
                "total_records": 40523,
                "processed_records": 40518,
                "failed_records": 5,
                "has_errors": True,
                "error_download_url": "/api/ingest/errors/550e8400-e29b-41d4-a716-446655440000"
            }
        }


class IngestionJobDetail(BaseModel):
    """Detailed response model for ingestion job status."""

    id: str
    user_id: str
    file_type: str
    file_name: str
    file_size_mb: float
    status: str
    total_records: int
    processed_records: int
    failed_records: int
    batch_number: Optional[int] = None
    error_log: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For Prisma model compatibility


class CSVPreviewResponse(BaseModel):
    """Response model for CSV preview (Story 2.3).

    Returned when user uploads a CSV file. Contains preview data
    for user confirmation before starting actual ingestion.
    """

    is_valid: bool = Field(..., description="Whether CSV passed validation")
    columns: List[str] = Field(..., description="CSV column names")
    preview_rows: List[Dict[str, Any]] = Field(..., description="First 10 rows of data (sanitized)")
    total_rows: int = Field(..., description="Total number of data rows in CSV")
    has_more: bool = Field(..., description="True if total_rows > preview_rows count")
    validation_errors: List[str] = Field(default=[], description="Validation errors if any (empty if valid)")
    file_hash: str = Field(..., description="SHA-256 hash for confirmation endpoint")
    file_type: str = Field(..., description="CSV type: 'skills' or 'jobs'")

    class Config:
        json_schema_extra = {
            "example": {
                "is_valid": True,
                "columns": ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"],
                "preview_rows": [
                    {"ID": "1", "NAME": "Python", "DESCRIPTION": "Programming language", "CATEGORY": "Tech", "SUBCATEGORY": "Backend"},
                    {"ID": "2", "NAME": "JavaScript", "DESCRIPTION": "Web language", "CATEGORY": "Tech", "SUBCATEGORY": "Frontend"}
                ],
                "total_rows": 150,
                "has_more": True,
                "validation_errors": [],
                "file_hash": "3a5f8b2d...",
                "file_type": "skills"
            }
        }


class ConfirmUploadRequest(BaseModel):
    """Request model for confirming CSV upload (Story 3.7: Enhanced with ingestion mode).

    User sends this after reviewing the preview to start actual ingestion.
    """

    file_hash: str = Field(..., description="SHA-256 hash from preview response")
    file_type: str = Field(..., description="CSV type: 'skills' or 'jobs'")
    mode: IngestionMode = Field(
        default=IngestionMode.INCREMENTAL,
        description="Ingestion mode: 'incremental' (default, safe) or 'full' (requires confirmation)"
    )
    confirmation: Optional[str] = Field(
        None,
        description="Required for FULL mode: must be 'CONFIRM DELETE' to proceed with full data deletion"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "file_hash": "3a5f8b2d1e4c9a7f6b3d2a1c8e5f7d9b4a6c3e1f2d8b5a7c4e9f1d3b6a8c2e5f",
                "file_type": "skills",
                "mode": "incremental"
            }
        }



class IngestionStatusResponse(BaseModel):
    """
    Response model for ingestion job status polling.

    Frontend polls this endpoint every 2 seconds to track progress.
    """
    job_id: str
    status: str = Field(
        ...,
        description="Job status: pending, processing, completed, completed_with_errors, failed"
    )
    total_records: int
    processed_records: int
    failed_records: int
    current_batch: Optional[int] = None
    total_batches: Optional[int] = None
    progress_percentage: float = Field(
        ...,
        ge=0,
        le=100,
        description="Completion percentage (0-100)"
    )
    estimated_time_remaining: Optional[int] = Field(
        None,
        description="Estimated seconds until completion (null if pending)"
    )
    processing_speed: Optional[float] = Field(
        None,
        description="Average records per second"
    )
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "total_records": 40523,
                "processed_records": 15234,
                "failed_records": 5,
                "current_batch": 16,
                "total_batches": 41,
                "progress_percentage": 37.6,
                "estimated_time_remaining": 142,
                "processing_speed": 178.5,
                "started_at": "2025-10-22T14:30:00Z",
                "completed_at": None,
                "error_message": None
            }
        }
