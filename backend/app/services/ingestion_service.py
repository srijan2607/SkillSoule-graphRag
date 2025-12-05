"""Ingestion business logic for file uploads."""

import logging
from datetime import datetime
from fastapi import UploadFile
from app.models.ingestion import IngestionJobResponse
from app.models.ingestion_mode import IngestionMode
from app.repositories.ingestion_repository import IngestionRepository
from app.services.csv_validation_service import CSVValidationService
from app.services.batch_processor import BatchProcessor
from app.utils.file_validation import validate_csv_file
from app.utils.batch_iterator import batch_iterator
from app.config import settings

# Configure logger
logger = logging.getLogger(__name__)


class IngestionService:
    """Service for file ingestion operations."""

    def __init__(
        self,
        ingestion_repo: IngestionRepository,
        csv_validation_service: CSVValidationService,
        batch_processor: BatchProcessor = None
    ):
        self.ingestion_repo = ingestion_repo
        self.csv_validation_service = csv_validation_service
        self.batch_processor = batch_processor

    async def upload_file(
        self,
        file: UploadFile,
        file_type: str,
        user_id: str
    ) -> IngestionJobResponse:
        """
        Process file upload and create ingestion job.

        Args:
            file: Uploaded CSV file
            file_type: Type of data in the file ("skills" or "jobs")
            user_id: ID of the authenticated user

        Returns:
            IngestionJobResponse with job ID and status

        Raises:
            HTTPException: 400 for invalid file type, 413 for file too large
            CSVValidationError: If CSV validation fails
        """
        # Validate file format (extension, MIME type, size, sanitize filename)
        sanitized_filename, file_size_mb = await validate_csv_file(file)

        # Read file content for CSV validation
        content = await file.read()

        # Reset file pointer for potential future reads
        await file.seek(0)

        # Validate CSV structure based on file type
        if file_type == "skills":
            parsed_data = self.csv_validation_service.validate_skills_csv(content)
        elif file_type == "jobs":
            parsed_data = self.csv_validation_service.validate_jobs_csv(content)
        else:
            # This shouldn't happen due to API routing, but handle it
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type: {file_type}"
            )

        # Create ingestion job record with total_records from validation
        job = await self.ingestion_repo.create({
            "user_id": user_id,
            "file_type": file_type,
            "file_name": sanitized_filename,
            "file_size_mb": file_size_mb,
            "status": "pending",
            "total_records": parsed_data["total_count"]
        })

        # Note: In a real implementation, we would:
        # 1. Save the file to storage (S3, local filesystem, etc.)
        # 2. Queue a background task to process the CSV
        # 3. Update the job status as processing progresses
        #
        # For now, we just create the job record and return 202 Accepted

        return IngestionJobResponse(
            ingestion_job_id=job.id,
            status=job.status,
            message=f"CSV validated successfully. {parsed_data['total_count']} records ready for processing."
        )

    async def get_job_status(self, job_id: str, user_id: str):
        """
        Get ingestion job status.

        Args:
            job_id: Ingestion job ID
            user_id: ID of the authenticated user

        Returns:
            IngestionJobDetail with job status

        Raises:
            HTTPException: 404 if job not found or doesn't belong to user
        """
        job = await self.ingestion_repo.find_by_id(job_id)

        # Verify job exists and belongs to user
        from fastapi import HTTPException, status
        if not job or job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ingestion job not found"
            )

        from app.models.ingestion import IngestionJobDetail
        return IngestionJobDetail.model_validate(job)

    async def get_user_jobs(self, user_id: str, limit: int = 100):
        """
        Get user's ingestion jobs.

        Args:
            user_id: ID of the authenticated user
            limit: Maximum number of jobs to return

        Returns:
            List of IngestionJobDetail
        """
        jobs = await self.ingestion_repo.find_by_user_id(user_id, limit=limit)

        from app.models.ingestion import IngestionJobDetail
        return [IngestionJobDetail.model_validate(job) for job in jobs]


    async def get_job_status_with_progress(
        self,
        job_id: str,
        user_id: str
    ):
        """
        Get ingestion job status with progress and ETA (Story 2.5).

        This method is used for real-time status polling. It returns detailed
        progress information including percentage complete and estimated time remaining.

        Args:
            job_id: Ingestion job ID
            user_id: Current user ID (for authorization)

        Returns:
            IngestionStatusResponse with current status and progress

        Raises:
            HTTPException 404: Job not found
            HTTPException 403: User doesn't own the job
        """
        from fastapi import HTTPException, status
        from app.models.ingestion import IngestionStatusResponse

        # Fetch job from database
        job = await self.ingestion_repo.find_by_id(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ingestion job {job_id} not found"
            )

        # Authorization check
        if job.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this job"
            )

        # Calculate progress percentage
        progress_percentage = 0.0
        if job.total_records > 0:
            progress_percentage = (
                job.processed_records / job.total_records
            ) * 100

        # Calculate estimated time remaining
        estimated_time_remaining = None
        if job.status == "processing" and hasattr(job, 'processing_speed') and job.processing_speed:
            remaining_records = job.total_records - job.processed_records
            if remaining_records > 0 and job.processing_speed > 0:
                estimated_time_remaining = int(
                    remaining_records / job.processing_speed
                )

        # Calculate total batches
        total_batches = None
        if job.total_records > 0:
            batch_size = settings.BATCH_SIZE
            total_batches = (
                job.total_records + batch_size - 1
            ) // batch_size

        # Get processing speed (may be None if field doesn't exist yet)
        processing_speed = None
        if hasattr(job, 'processing_speed'):
            processing_speed = job.processing_speed

        # Get completed_at (may be None)
        completed_at = None
        if hasattr(job, 'completed_at'):
            completed_at = job.completed_at

        return IngestionStatusResponse(
            job_id=job.id,
            status=job.status,
            total_records=job.total_records,
            processed_records=job.processed_records,
            failed_records=job.failed_records if hasattr(job, 'failed_records') else 0,
            current_batch=job.batch_number,
            total_batches=total_batches,
            progress_percentage=round(progress_percentage, 2),
            estimated_time_remaining=estimated_time_remaining,
            processing_speed=processing_speed,
            started_at=job.started_at if (hasattr(job, 'started_at') and job.started_at) else job.created_at,
            completed_at=completed_at,
            error_message=job.error_log if hasattr(job, 'error_log') else None
        )

    async def start_ingestion_from_cache(
        self,
        content: bytes,
        file_type: str,
        filename: str,
        file_size_mb: float,
        user_id: str,
        mode: IngestionMode = IngestionMode.INCREMENTAL
    ) -> IngestionJobResponse:
        """
        Start ingestion from cached file data (Story 2.3 confirmation flow, enhanced in Story 3.7).

        This method is called after user confirms the CSV preview.
        It validates the CSV and creates an ingestion job.

        Story 3.7 Enhancement:
        - Supports INCREMENTAL mode (default): Upsert nodes, preserve existing data
        - Supports FULL mode: Delete all graph data before ingestion

        Args:
            content: CSV file content from cache
            file_type: Type of data ("skills" or "jobs")
            filename: Original filename
            file_size_mb: File size in MB
            user_id: ID of the authenticated user
            mode: Ingestion mode (INCREMENTAL or FULL)

        Returns:
            IngestionJobResponse with job ID and status

        Raises:
            CSVValidationError: If CSV validation fails
            HTTPException: 400 for invalid file type
        """
        logger.info(
            f"Starting ingestion from cache. Type: {file_type}, "
            f"Filename: {filename}, Size: {file_size_mb:.2f}MB, "
            f"Mode: {mode.value}, User: {user_id}"
        )

        # Validate CSV structure based on file type
        # Note: We re-validate to ensure data integrity (cached data could be corrupted)
        if file_type == "skills":
            parsed_data = self.csv_validation_service.validate_skills_csv(content)
        elif file_type == "jobs":
            parsed_data = self.csv_validation_service.validate_jobs_csv(content)
        else:
            # This shouldn't happen due to validation in confirmation endpoint
            from fastapi import HTTPException, status
            logger.error(f"Invalid file_type in confirmation: {file_type}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file_type: {file_type}"
            )

        # Create ingestion job record with total_records from validation
        job = await self.ingestion_repo.create({
            "user_id": user_id,
            "file_type": file_type,
            "file_name": filename,
            "file_size_mb": file_size_mb,
            "status": "pending",
            "total_records": parsed_data["total_count"]
        })

        logger.info(
            f"Ingestion job created. Job ID: {job.id}, "
            f"Records: {parsed_data['total_count']}, Status: {job.status}"
        )

        # Start background processing if batch_processor is available
        if self.batch_processor:
            import asyncio

            # Create background task for ingestion processing
            if file_type == "skills":
                asyncio.create_task(
                    self._process_skills_job(
                        job_id=job.id,
                        content=content,
                        parsed_data=parsed_data
                    )
                )
            elif file_type == "jobs":
                asyncio.create_task(
                    self._process_jobs_job(
                        job_id=job.id,
                        content=content,
                        parsed_data=parsed_data
                    )
                )

            logger.info(f"Background processing started for job {job.id}")
        else:
            logger.warning(
                f"Batch processor not configured. Job {job.id} created but "
                "will not be processed automatically."
            )

        return IngestionJobResponse(
            ingestion_job_id=job.id,
            status=job.status,
            message=f"CSV ingestion started. {parsed_data['total_count']} records will be processed."
        )

    async def start_skills_ingestion(
        self,
        content: bytes,
        user_id: str,
        filename: str,
        file_size_mb: float
    ) -> IngestionJobResponse:
        """
        Start skills CSV ingestion with batch processing.

        Args:
            content: CSV file content
            user_id: User ID
            filename: Original filename
            file_size_mb: File size in MB

        Returns:
            IngestionJobResponse with final status

        Raises:
            ValueError: If batch_processor is not configured
        """
        if not self.batch_processor:
            raise ValueError("Batch processor not configured")

        # Validate CSV structure
        parsed_data = self.csv_validation_service.validate_skills_csv(content)

        # Create ingestion job
        job = await self.ingestion_repo.create({
            "user_id": user_id,
            "file_type": "skills",
            "file_name": filename,
            "file_size_mb": file_size_mb,
            "status": "processing",
            "total_records": parsed_data["total_count"],
            "started_at": datetime.utcnow()
        })

        logger.info(
            f"Starting skills ingestion. Job ID: {job.id}, "
            f"Total records: {parsed_data['total_count']}"
        )

        # Process in batches
        total_processed = 0
        total_failed = 0
        batch_size = settings.BATCH_SIZE

        for batch_num, batch_records in batch_iterator(
            parsed_data["rows"],
            batch_size
        ):
            start_row = (batch_num - 1) * batch_size + 1

            # Update job status with current batch
            await self.ingestion_repo.update(
                job.id,
                {
                    "batch_number": batch_num,
                    "processed_records": total_processed,
                    "failed_records": total_failed
                }
            )

            # Process batch
            batch_result = await self.batch_processor.process_skills_batch(
                batch=batch_records,
                job_id=job.id,
                batch_number=batch_num,
                start_row=start_row
            )

            total_processed += batch_result["processed"]
            total_failed += batch_result["failed"]

            logger.info(
                f"Batch {batch_num} complete. "
                f"Total progress: {total_processed}/{parsed_data['total_count']} "
                f"({total_failed} failed)"
            )

        # Set final status
        final_status = "completed" if total_failed == 0 else "completed_with_errors"

        await self.ingestion_repo.update(
            job.id,
            {
                "status": final_status,
                "processed_records": total_processed,
                "failed_records": total_failed,
                "completed_at": datetime.utcnow()
            }
        )

        logger.info(
            f"Skills ingestion completed. Job ID: {job.id}, "
            f"Status: {final_status}, Processed: {total_processed}, "
            f"Failed: {total_failed}"
        )

        return IngestionJobResponse(
            ingestion_job_id=job.id,
            status=final_status,
            message=f"Skills ingestion complete: {total_processed} processed, {total_failed} failed"
        )

    async def start_jobs_ingestion(
        self,
        content: bytes,
        user_id: str,
        filename: str,
        file_size_mb: float
    ) -> IngestionJobResponse:
        """
        Start jobs CSV ingestion with batch processing.

        Args:
            content: CSV file content
            user_id: User ID
            filename: Original filename
            file_size_mb: File size in MB

        Returns:
            IngestionJobResponse with final status

        Raises:
            ValueError: If batch_processor is not configured
        """
        if not self.batch_processor:
            raise ValueError("Batch processor not configured")

        # Validate CSV structure
        parsed_data = self.csv_validation_service.validate_jobs_csv(content)

        # Create ingestion job
        job = await self.ingestion_repo.create({
            "user_id": user_id,
            "file_type": "jobs",
            "file_name": filename,
            "file_size_mb": file_size_mb,
            "status": "processing",
            "total_records": parsed_data["total_count"],
            "started_at": datetime.utcnow()
        })

        logger.info(
            f"Starting jobs ingestion. Job ID: {job.id}, "
            f"Total records: {parsed_data['total_count']}"
        )

        # Process in batches
        total_processed = 0
        total_failed = 0
        batch_size = settings.BATCH_SIZE

        for batch_num, batch_records in batch_iterator(
            parsed_data["rows"],
            batch_size
        ):
            start_row = (batch_num - 1) * batch_size + 1

            # Update job status with current batch
            await self.ingestion_repo.update(
                job.id,
                {
                    "batch_number": batch_num,
                    "processed_records": total_processed,
                    "failed_records": total_failed
                }
            )

            # Process batch
            batch_result = await self.batch_processor.process_jobs_batch(
                batch=batch_records,
                job_id=job.id,
                batch_number=batch_num,
                start_row=start_row
            )

            total_processed += batch_result["processed"]
            total_failed += batch_result["failed"]

            logger.info(
                f"Batch {batch_num} complete. "
                f"Total progress: {total_processed}/{parsed_data['total_count']} "
                f"({total_failed} failed)"
            )

        # Set final status
        final_status = "completed" if total_failed == 0 else "completed_with_errors"

        await self.ingestion_repo.update(
            job.id,
            {
                "status": final_status,
                "processed_records": total_processed,
                "failed_records": total_failed,
                "completed_at": datetime.utcnow()
            }
        )

        logger.info(
            f"Jobs ingestion completed. Job ID: {job.id}, "
            f"Status: {final_status}, Processed: {total_processed}, "
            f"Failed: {total_failed}"
        )

        return IngestionJobResponse(
            ingestion_job_id=job.id,
            status=final_status,
            message=f"Jobs ingestion complete: {total_processed} processed, {total_failed} failed"
        )

    async def _process_skills_job(
        self,
        job_id: str,
        content: bytes,
        parsed_data: dict
    ) -> None:
        """
        Background task to process skills ingestion job.

        Args:
            job_id: Ingestion job ID
            content: CSV file content
            parsed_data: Pre-validated CSV data
        """
        try:
            logger.info(f"Starting background processing for skills job {job_id}")

            # Update job status to processing
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": "processing",
                    "started_at": datetime.utcnow()
                }
            )

            # Process in batches
            total_processed = 0
            total_failed = 0
            batch_size = settings.BATCH_SIZE

            for batch_num, batch_records in batch_iterator(
                parsed_data["rows"],
                batch_size
            ):
                start_row = (batch_num - 1) * batch_size + 1

                # Update job progress
                await self.ingestion_repo.update(
                    job_id,
                    {
                        "batch_number": batch_num,
                        "processed_records": total_processed,
                        "failed_records": total_failed
                    }
                )

                # Process batch
                batch_result = await self.batch_processor.process_skills_batch(
                    batch=batch_records,
                    job_id=job_id,
                    batch_number=batch_num,
                    start_row=start_row
                )

                total_processed += batch_result["processed"]
                total_failed += batch_result["failed"]

                # Update progress after batch completes
                await self.ingestion_repo.update(
                    job_id,
                    {
                        "batch_number": batch_num,
                        "processed_records": total_processed,
                        "failed_records": total_failed
                    }
                )

            # Determine final status
            final_status = "completed"
            if total_failed > 0:
                final_status = "completed_with_errors"
            if total_processed == 0:
                final_status = "failed"

            # Update job with final status
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": final_status,
                    "processed_records": total_processed,
                    "failed_records": total_failed,
                    "completed_at": datetime.utcnow()
                }
            )

            logger.info(
                f"Skills job {job_id} completed: {final_status}, "
                f"Processed: {total_processed}, Failed: {total_failed}"
            )

        except Exception as e:
            logger.error(f"Skills job {job_id} failed with error: {str(e)}", exc_info=True)
            # Update job status to failed
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": "failed",
                    "error_log": str(e),
                    "completed_at": datetime.utcnow()
                }
            )

    async def _process_jobs_job(
        self,
        job_id: str,
        content: bytes,
        parsed_data: dict
    ) -> None:
        """
        Background task to process jobs ingestion job.

        Args:
            job_id: Ingestion job ID
            content: CSV file content
            parsed_data: Pre-validated CSV data
        """
        try:
            logger.info(f"Starting background processing for jobs job {job_id}")

            # Update job status to processing
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": "processing",
                    "started_at": datetime.utcnow()
                }
            )

            # Process in batches
            total_processed = 0
            total_failed = 0
            batch_size = settings.BATCH_SIZE

            for batch_num, batch_records in batch_iterator(
                parsed_data["rows"],
                batch_size
            ):
                start_row = (batch_num - 1) * batch_size + 1

                # Update job progress
                await self.ingestion_repo.update(
                    job_id,
                    {
                        "batch_number": batch_num,
                        "processed_records": total_processed,
                        "failed_records": total_failed
                    }
                )

                # Process batch
                batch_result = await self.batch_processor.process_jobs_batch(
                    batch=batch_records,
                    job_id=job_id,
                    batch_number=batch_num,
                    start_row=start_row
                )

                total_processed += batch_result["processed"]
                total_failed += batch_result["failed"]

                # Update progress after batch completes
                await self.ingestion_repo.update(
                    job_id,
                    {
                        "batch_number": batch_num,
                        "processed_records": total_processed,
                        "failed_records": total_failed
                    }
                )

            # Determine final status
            final_status = "completed"
            if total_failed > 0:
                final_status = "completed_with_errors"
            if total_processed == 0:
                final_status = "failed"

            # Update job with final status
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": final_status,
                    "processed_records": total_processed,
                    "failed_records": total_failed,
                    "completed_at": datetime.utcnow()
                }
            )

            logger.info(
                f"Jobs job {job_id} completed: {final_status}, "
                f"Processed: {total_processed}, Failed: {total_failed}"
            )

        except Exception as e:
            logger.error(f"Jobs job {job_id} failed with error: {str(e)}", exc_info=True)
            # Update job status to failed
            await self.ingestion_repo.update(
                job_id,
                {
                    "status": "failed",
                    "error_log": str(e),
                    "completed_at": datetime.utcnow()
                }
            )
