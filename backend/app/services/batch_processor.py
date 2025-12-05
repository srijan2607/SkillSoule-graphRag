"""
Batch processing service for CSV ingestion.

Processes CSV records in batches with error handling, progress tracking,
and detailed error logging.
"""

import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.error_logging_service import ErrorLoggingService
from app.repositories.ingestion_repository import IngestionRepository
from app.utils.csv_parser import parse_list_field
from app.config import settings

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Process CSV records in batches with error handling.

    Responsibilities:
    - Generate embeddings for batch
    - Create nodes in Neo4j
    - Create relationships
    - Log failed records
    - Track batch statistics
    """

    def __init__(
        self,
        neo4j_repo: Neo4jRepository,
        embedding_service: EmbeddingService,
        error_logger: ErrorLoggingService,
        ingestion_repo: IngestionRepository = None
    ):
        """
        Initialize batch processor.

        Args:
            neo4j_repo: Neo4j repository for graph operations
            embedding_service: Service for generating embeddings
            error_logger: Service for logging ingestion errors
            ingestion_repo: Ingestion repository for job updates (Story 2.5)
        """
        self.neo4j_repo = neo4j_repo
        self.embedding_service = embedding_service
        self.error_logger = error_logger
        self.ingestion_repo = ingestion_repo

    async def process_skills_batch(
        self,
        batch: List[Dict[str, Any]],
        job_id: str,
        batch_number: int,
        start_row: int
    ) -> Dict[str, Any]:
        """
        Process a batch of skill records.

        Args:
            batch: List of skill records from CSV
            job_id: Ingestion job ID
            batch_number: Current batch number (1-indexed)
            start_row: Starting CSV row number for this batch

        Returns:
            dict: {
                "processed": int,  # Successfully processed records
                "failed": int,     # Failed records
                "errors": List[str]  # Error messages
            }
        """
        processed = 0
        failed = 0
        errors = []
        
        # Track batch processing time (Story 2.5)
        batch_start_time = time.time()

        logger.info(
            f"Processing skills batch {batch_number}: {len(batch)} records "
            f"(rows {start_row} to {start_row + len(batch) - 1})"
        )

        for idx, record in enumerate(batch):
            row_number = start_row + idx

            try:
                # Generate embedding
                description_text = record.get("DESCRIPTION") or record.get("NAME", "")
                embedding_data = await self.embedding_service.generate_embedding(
                    description_text
                )

                # Create Skill node in Neo4j
                # Required fields from CSV: ID, NAME, DESCRIPTION, CATEGORY, SUBCATEGORY
                # Optional fields: LEVEL, TYPE, IS_SOFTWARE, IS_LANGUAGE, VERSION, etc.
                skill_data = {
                    "id": record["ID"],  # Required
                    "name": record["NAME"],  # Required
                    "description": record["DESCRIPTION"],  # Required
                    "level": record.get("LEVEL"),
                    "type": record.get("TYPE"),
                    "is_software": record.get("IS_SOFTWARE", False),
                    "is_language": record.get("IS_LANGUAGE", False),
                    "description_source": record.get("DESCRIPTION_SOURCE"),
                    "version": record.get("VERSION"),
                    "latest_version": record.get("LATEST_VERSION"),
                    "wiki_link": record.get("WIKI_LINK"),
                    "wiki_extract": record.get("WIKI_EXTRACT"),
                    "embedding": embedding_data["embedding"],
                    "embedding_model_version": embedding_data["model_version"]
                }

                await self.neo4j_repo.create_skill_node(skill_data)

                # Create category/subcategory relationships
                if record.get("CATEGORY"):
                    await self.neo4j_repo.create_skill_category_relationship(
                        skill_id=record["ID"],
                        category_id=record["CATEGORY"]
                    )

                if record.get("SUBCATEGORY"):
                    await self.neo4j_repo.create_skill_subcategory_relationship(
                        skill_id=record["ID"],
                        subcategory_id=record["SUBCATEGORY"]
                    )

                # Handle standardized_underscore_skill field (list of related skills)
                # CSV format: "[None, 'Java 8', 'Java']" or "['Python', 'Django']"
                if record.get("standardized_underscore_skill"):
                    related_skills = parse_list_field(record["standardized_underscore_skill"])

                    # Create relationships to related skills if any exist
                    if related_skills:
                        logger.debug(
                            f"Skill {record['ID']} has {len(related_skills)} related skills: "
                            f"{related_skills[:3]}..." if len(related_skills) > 3 else f"{related_skills}"
                        )
                        # TODO: Create RELATED_TO relationships between this skill and related skills
                        # This would require a new method in neo4j_repository like:
                        # await self.neo4j_repo.create_skill_relationships(
                        #     skill_id=record["ID"],
                        #     related_skill_names=related_skills
                        # )

                processed += 1

            except Exception as e:
                # Log error and continue processing
                error_msg = f"Row {row_number}: {str(e)}"
                errors.append(error_msg)
                failed += 1

                # Log to database
                await self.error_logger.log_ingestion_error(
                    job_id=job_id,
                    row_number=row_number,
                    error_message=str(e),
                    raw_data=record
                )

                logger.warning(error_msg)

        # Calculate batch processing time and speed (Story 2.5)
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        batch_speed = len(batch) / batch_duration if batch_duration > 0 else 0.0

        logger.info(
            f"Batch {batch_number} completed: "
            f"{processed} processed, {failed} failed "
            f"({batch_duration:.2f}s, {batch_speed:.2f} records/sec)"
        )

        # Update job with processing speed metrics (Story 2.5)
        # Calculate total processed including this batch
        total_processed_so_far = start_row - 1 + processed
        await self._update_processing_speed(
            job_id=job_id,
            batch_speed=batch_speed,
            processed_count=total_processed_so_far
        )

        return {
            "processed": processed,
            "failed": failed,
            "errors": errors,
            "duration": batch_duration,
            "speed": batch_speed
        }

    async def process_jobs_batch(
        self,
        batch: List[Dict[str, Any]],
        job_id: str,
        batch_number: int,
        start_row: int
    ) -> Dict[str, Any]:
        """
        Process a batch of job records.

        Args:
            batch: List of job records from CSV
            job_id: Ingestion job ID
            batch_number: Current batch number (1-indexed)
            start_row: Starting CSV row number for this batch

        Returns:
            dict: Batch statistics (processed, failed, errors)
        """
        processed = 0
        failed = 0
        errors = []
        
        # Track batch processing time (Story 2.5)
        batch_start_time = time.time()

        logger.info(
            f"Processing jobs batch {batch_number}: {len(batch)} records "
            f"(rows {start_row} to {start_row + len(batch) - 1})"
        )

        for idx, record in enumerate(batch):
            row_number = start_row + idx

            try:
                # Generate embedding from job description
                description_text = record.get("Description") or record.get("Job Title", "")
                embedding_data = await self.embedding_service.generate_embedding(
                    description_text
                )

                # Create Job node
                # Required fields from CSV: Job ID, Job Title, Company Name,
                # Location, standardized_skills
                # Optional fields: District, Via, Salary, Schedule Type, etc.
                job_data = {
                    "job_id": record["Job ID"],  # Required
                    "job_title": record["Job Title"],  # Required
                    "company_name": record["Company Name"],  # Required
                    "location": record["Location"],  # Required
                    "district": record.get("District"),
                    "via": record.get("Via"),
                    "salary": record.get("Salary"),
                    "min_salary": record.get("Minimum Salary"),
                    "max_salary": record.get("Maximum Salary"),
                    "mean_salary": record.get("Mean Salary"),
                    "salary_unit": record.get("Unit of Measure"),
                    "schedule_type": record.get("Schedule Type"),
                    "work_from_home": record.get("Work From Home", False),
                    "posted_at": record.get("Posted At"),
                    "description": record.get("Description"),
                    "job_description": record.get("Job Description"),
                    "apply_options": record.get("Apply Options"),
                    "exact_matched_company": record.get("Exact Matched Company", False),
                    "nco_code": record.get("NCO_Code_algo"),
                    "embedding": embedding_data["embedding"],
                    "embedding_model_version": embedding_data["model_version"]
                }

                await self.neo4j_repo.create_job_node(job_data)

                # Create company relationship
                if record.get("Company Name"):
                    await self.neo4j_repo.create_job_company_relationship(
                        job_id=record["Job ID"],
                        company_name=record["Company Name"]
                    )

                # Create location relationship
                if record.get("Location"):
                    await self.neo4j_repo.create_job_location_relationship(
                        job_id=record["Job ID"],
                        location_name=record["Location"]
                    )

                # Create skill requirements (REQUIRES relationships)
                # standardized_skills is a REQUIRED field containing list of skill names
                # CSV format: "[None, 'Java 8', 'Java']" or "['Python', 'Django']"
                standardized_skills_raw = record.get("standardized_skills", [])
                standardized_skills = parse_list_field(standardized_skills_raw)

                if standardized_skills:
                    logger.debug(
                        f"Job {record['Job ID']} requires {len(standardized_skills)} skills: "
                        f"{standardized_skills[:3]}..." if len(standardized_skills) > 3 else f"{standardized_skills}"
                    )
                    await self.neo4j_repo.create_job_skill_relationships(
                        job_id=record["Job ID"],
                        skill_names=standardized_skills
                    )

                processed += 1

            except Exception as e:
                error_msg = f"Row {row_number}: {str(e)}"
                errors.append(error_msg)
                failed += 1

                await self.error_logger.log_ingestion_error(
                    job_id=job_id,
                    row_number=row_number,
                    error_message=str(e),
                    raw_data=record
                )

                logger.warning(error_msg)

        # Calculate batch processing time and speed (Story 2.5)
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        batch_speed = len(batch) / batch_duration if batch_duration > 0 else 0.0

        logger.info(
            f"Batch {batch_number} completed: "
            f"{processed} processed, {failed} failed "
            f"({batch_duration:.2f}s, {batch_speed:.2f} records/sec)"
        )

        # Update job with processing speed metrics (Story 2.5)
        # Calculate total processed including this batch
        total_processed_so_far = start_row - 1 + processed
        await self._update_processing_speed(
            job_id=job_id,
            batch_speed=batch_speed,
            processed_count=total_processed_so_far
        )

        return {
            "processed": processed,
            "failed": failed,
            "errors": errors,
            "duration": batch_duration,
            "speed": batch_speed
        }

    async def _update_processing_speed(
        self,
        job_id: str,
        batch_speed: float,
        processed_count: int
    ) -> None:
        """
        Update job processing speed with exponential moving average (Story 2.5).

        Uses EMA to smooth out speed fluctuations between batches and provide
        more stable ETA estimates.

        Args:
            job_id: Ingestion job ID
            batch_speed: Current batch speed (records/sec)
            processed_count: Total records processed so far
        """
        if not self.ingestion_repo:
            # If repository not configured, skip speed tracking
            logger.debug("Ingestion repository not configured, skipping speed update")
            return

        # Fetch current job
        job = await self.ingestion_repo.find_by_id(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for speed update")
            return

        # Calculate exponential moving average (alpha = 0.3)
        # This gives 30% weight to new batch, 70% to historical average
        if hasattr(job, 'processing_speed') and job.processing_speed is not None:
            # EMA: new_speed = alpha * batch_speed + (1 - alpha) * old_speed
            alpha = 0.3
            new_speed = alpha * batch_speed + (1 - alpha) * job.processing_speed
        else:
            # First batch - use actual speed
            new_speed = batch_speed

        # Calculate ETA
        remaining_records = job.total_records - processed_count
        if new_speed > 0:
            eta_seconds = remaining_records / new_speed
            estimated_completion_time = datetime.utcnow() + timedelta(seconds=eta_seconds)
        else:
            estimated_completion_time = None

        # Update job
        await self.ingestion_repo.update(
            job_id,
            {
                "processing_speed": new_speed,
                "estimated_completion_time": estimated_completion_time
            }
        )

        logger.debug(
            f"Speed updated for job {job_id}: {new_speed:.2f} records/sec, "
            f"ETA: {eta_seconds:.0f} seconds" if new_speed > 0 else "Speed updated, ETA: N/A"
        )
