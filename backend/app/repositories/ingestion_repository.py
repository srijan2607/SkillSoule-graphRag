"""Ingestion job database operations."""

from typing import Optional, List
from prisma import Prisma, Json
from prisma.models import IngestionJob, OrphanSkillLog


class IngestionRepository:
    """Repository for IngestionJob model operations."""

    def __init__(self, db: Prisma):
        self.db = db

    async def create(self, job_data: dict) -> IngestionJob:
        """
        Create new ingestion job.

        Args:
            job_data: Dictionary with job fields

        Returns:
            Created ingestion job

        Raises:
            Exception: If database operation fails
        """
        return await self.db.ingestionjob.create(data=job_data)

    async def find_by_id(self, job_id: str) -> Optional[IngestionJob]:
        """
        Find ingestion job by ID.

        Args:
            job_id: Ingestion job ID

        Returns:
            IngestionJob if found, None otherwise
        """
        return await self.db.ingestionjob.find_unique(where={"id": job_id})

    async def find_by_user_id(
        self,
        user_id: str,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[IngestionJob]:
        """
        Find ingestion jobs by user ID.

        Args:
            user_id: User ID
            limit: Maximum number of jobs to return
            status: Optional status filter

        Returns:
            List of ingestion jobs
        """
        where_clause = {"user_id": user_id}
        if status:
            where_clause["status"] = status

        return await self.db.ingestionjob.find_many(
            where=where_clause,
            order={"created_at": "desc"},
            take=limit
        )

    async def update_status(
        self,
        job_id: str,
        status: str,
        error_log: Optional[str] = None
    ) -> IngestionJob:
        """
        Update ingestion job status.

        Args:
            job_id: Ingestion job ID
            status: New status
            error_log: Optional error log for failed jobs

        Returns:
            Updated ingestion job

        Raises:
            Exception: If database operation fails
        """
        update_data = {"status": status}
        if error_log:
            update_data["error_log"] = error_log

        return await self.db.ingestionjob.update(
            where={"id": job_id},
            data=update_data
        )

    async def update_progress(
        self,
        job_id: str,
        processed_records: int,
        total_records: int
    ) -> IngestionJob:
        """
        Update ingestion job progress.

        Args:
            job_id: Ingestion job ID
            processed_records: Number of records processed
            total_records: Total number of records

        Returns:
            Updated ingestion job

        Raises:
            Exception: If database operation fails
        """
        return await self.db.ingestionjob.update(
            where={"id": job_id},
            data={
                "processed_records": processed_records,
                "total_records": total_records
            }
        )

    async def update(
        self,
        job_id: str,
        data: dict
    ) -> IngestionJob:
        """
        Generic update method for ingestion job.

        Args:
            job_id: Ingestion job ID
            data: Dictionary of fields to update

        Returns:
            Updated ingestion job

        Raises:
            Exception: If database operation fails
        """
        return await self.db.ingestionjob.update(
            where={"id": job_id},
            data=data
        )

    async def create_orphan_log(
        self,
        skill_id: str,
        skill_name: str,
        job_id: str,
        orphan_reason: str,
        fuzzy_candidates: List[str],
        status: str = "pending_review"
    ) -> OrphanSkillLog:
        """
        Create orphan skill log for admin review.

        Args:
            skill_id: Neo4j skill node ID
            skill_name: Normalized skill name
            job_id: Job ID that referenced this skill
            orphan_reason: Reason for orphan creation ("no_match", "ambiguous_fuzzy_match", "too_short")
            fuzzy_candidates: List of potential fuzzy matches (if ambiguous)
            status: Review status (default: "pending_review")

        Returns:
            Created OrphanSkillLog record

        Raises:
            Exception: If database operation fails
        """
        # Build data dict, omitting fuzzy_candidates if empty
        data = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "job_id": job_id,
            "orphan_reason": orphan_reason,
            "status": status
        }

        # Only include fuzzy_candidates if not empty (wrap with Json for Prisma)
        if fuzzy_candidates:
            data["fuzzy_candidates"] = Json(fuzzy_candidates)

        return await self.db.orphanskilllog.create(data=data)
