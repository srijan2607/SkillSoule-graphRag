"""Relationship cleanup service for incremental updates."""
import logging
from typing import List
from app.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


class RelationshipCleanupService:
    """
    Cleanup existing relationships before re-creating from CSV.

    Ensures job-skill relationships match current CSV state, not
    accumulated relationships from previous uploads.
    """

    def __init__(self, neo4j_repo: Neo4jRepository):
        self.neo4j_repo = neo4j_repo

    async def delete_job_skill_relationships(self, job_ids: List[str]) -> int:
        """
        Delete all REQUIRES relationships for given jobs.

        Args:
            job_ids: List of Job IDs to clean

        Returns:
            int: Number of relationships deleted

        Called before re-creating REQUIRES relationships from CSV
        to ensure clean state.
        """
        query = """
        MATCH (j:Job)-[r:REQUIRES]->(:Skill)
        WHERE j.job_id IN $job_ids
        DELETE r
        RETURN count(r) as deleted_count
        """

        async with self.neo4j_repo.driver.session() as session:
            result = await session.run(query, {"job_ids": job_ids})
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0

        logger.info(
            f"Deleted {deleted_count} REQUIRES relationships "
            f"for {len(job_ids)} jobs (cleanup before re-ingestion)"
        )

        return deleted_count

    async def delete_all_skill_relationships(self, skill_ids: List[str]) -> int:
        """
        Delete all relationships for given skills.

        Args:
            skill_ids: List of Skill IDs to clean

        Returns:
            int: Number of relationships deleted

        Used when re-ingesting skills taxonomy to ensure
        BELONGS_TO_CATEGORY and SIMILAR_TO relationships are fresh.
        """
        query = """
        MATCH (s:Skill)-[r]-()
        WHERE s.id IN $skill_ids
        DELETE r
        RETURN count(r) as deleted_count
        """

        async with self.neo4j_repo.driver.session() as session:
            result = await session.run(query, {"skill_ids": skill_ids})
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0

        logger.info(
            f"Deleted {deleted_count} relationships "
            f"for {len(skill_ids)} skills (cleanup before re-ingestion)"
        )

        return deleted_count
