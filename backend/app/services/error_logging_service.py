"""
Error logging service for ingestion errors.

Tracks failed records during CSV ingestion with detailed error information
and raw data for debugging and recovery.
"""

import json
import logging
from typing import Dict, Any, List

from prisma import Prisma
from prisma.models import IngestionError

logger = logging.getLogger(__name__)


class ErrorLoggingService:
    """
    Service for logging ingestion errors to PostgreSQL.

    Responsibilities:
    - Log individual record failures with row number and error details
    - Store raw data for debugging
    - Support batch insertion for performance
    - Track errors per ingestion job
    """

    def __init__(self, db: Prisma):
        """
        Initialize error logging service.

        Args:
            db: Prisma database client
        """
        self.db = db

    async def log_ingestion_error(
        self,
        job_id: str,
        row_number: int,
        error_message: str,
        raw_data: Dict[str, Any]
    ) -> IngestionError:
        """
        Log a single ingestion error.

        Args:
            job_id: Ingestion job ID
            row_number: 1-indexed CSV row number
            error_message: Error description
            raw_data: Dictionary of the failed row data

        Returns:
            IngestionError: Created error record

        Example:
            >>> error = await service.log_ingestion_error(
            ...     job_id="abc-123",
            ...     row_number=42,
            ...     error_message="Missing required field: NAME",
            ...     raw_data={"ID": "skill-001", "DESCRIPTION": "..."}
            ... )
        """
        try:
            # Convert raw_data dict to JSON string
            raw_data_json = json.dumps(raw_data, ensure_ascii=False)

            # Create error record
            error = await self.db.ingestionerror.create(
                data={
                    "job_id": job_id,
                    "row_number": row_number,
                    "error_message": error_message,
                    "raw_data": raw_data_json,
                }
            )

            logger.debug(
                f"Logged ingestion error for job {job_id}, row {row_number}: "
                f"{error_message}"
            )

            return error

        except Exception as e:
            # Don't let error logging failures crash the ingestion
            logger.error(
                f"Failed to log ingestion error for job {job_id}, "
                f"row {row_number}: {str(e)}"
            )
            raise

    async def log_batch_errors(
        self,
        errors: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert multiple ingestion errors for performance.

        Args:
            errors: List of error dictionaries with keys:
                - job_id: str
                - row_number: int
                - error_message: str
                - raw_data: dict

        Returns:
            int: Number of errors successfully logged

        Example:
            >>> errors = [
            ...     {
            ...         "job_id": "abc-123",
            ...         "row_number": 42,
            ...         "error_message": "Invalid field",
            ...         "raw_data": {"ID": "skill-001"}
            ...     },
            ...     # ... more errors
            ... ]
            >>> count = await service.log_batch_errors(errors)
        """
        if not errors:
            return 0

        try:
            # Convert raw_data dicts to JSON strings
            prepared_errors = []
            for error in errors:
                prepared_errors.append({
                    "job_id": error["job_id"],
                    "row_number": error["row_number"],
                    "error_message": error["error_message"],
                    "raw_data": json.dumps(error["raw_data"], ensure_ascii=False),
                })

            # Batch create
            result = await self.db.ingestionerror.create_many(
                data=prepared_errors
            )

            logger.info(f"Batch logged {result} ingestion errors")

            return result

        except Exception as e:
            logger.error(f"Failed to batch log ingestion errors: {str(e)}")
            raise

    async def get_job_errors(
        self,
        job_id: str,
        limit: int = 100
    ) -> List[IngestionError]:
        """
        Retrieve errors for a specific ingestion job.

        Args:
            job_id: Ingestion job ID
            limit: Maximum number of errors to retrieve (default: 100)

        Returns:
            List[IngestionError]: List of error records

        Example:
            >>> errors = await service.get_job_errors("abc-123", limit=50)
        """
        try:
            errors = await self.db.ingestionerror.find_many(
                where={"job_id": job_id},
                order={"row_number": "asc"},
                take=limit
            )

            return errors

        except Exception as e:
            logger.error(f"Failed to retrieve errors for job {job_id}: {str(e)}")
            raise

    async def get_error_count(self, job_id: str) -> int:
        """
        Get total error count for an ingestion job.

        Args:
            job_id: Ingestion job ID

        Returns:
            int: Total number of errors for this job

        Example:
            >>> count = await service.get_error_count("abc-123")
        """
        try:
            count = await self.db.ingestionerror.count(
                where={"job_id": job_id}
            )

            return count

        except Exception as e:
            logger.error(
                f"Failed to get error count for job {job_id}: {str(e)}"
            )
            raise
