"""Job-Skill relationship service with fuzzy matching."""

import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class JobSkillRelationshipService:
    """
    Create REQUIRES relationships between jobs and skills.

    Uses SkillMatchingService for fuzzy matching to handle:
    - Typos (e.g., "Pyton" → "Python")
    - Case variations (e.g., "REACT" → "React")
    - Unknown skills (create orphan for review)
    """

    BATCH_SIZE = 1000

    def __init__(self, neo4j_repo, skill_matching_service):
        self.neo4j_repo = neo4j_repo
        self.skill_matching_service = skill_matching_service

    async def create_job_skill_relationships(
        self,
        jobs_data: List[dict],
        ingestion_job_id: str
    ) -> Dict[str, int]:
        """
        Create REQUIRES relationships for all jobs.

        Args:
            jobs_data: List of job CSV rows
            ingestion_job_id: Parent ingestion job ID

        Returns:
            dict: {
                "relationships_created": 15234,
                "exact_matches": 14500,
                "fuzzy_matches": 534,
                "orphans_created": 200
            }
        """
        stats = {
            "relationships_created": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "orphans_created": 0
        }

        # Refresh skill cache once before processing
        await self.skill_matching_service._refresh_skill_cache()

        # Process in batches
        for batch_idx in range(0, len(jobs_data), self.BATCH_SIZE):
            batch = jobs_data[batch_idx:batch_idx + self.BATCH_SIZE]

            relationships = []
            for job_row in batch:
                job_relationships = await self._process_job_skills(
                    job_row,
                    ingestion_job_id,
                    stats
                )
                relationships.extend(job_relationships)

            # Create batch relationships
            await self._create_relationships_batch(relationships)

            stats["relationships_created"] += len(relationships)

            logger.info(
                f"Creating job-skill relationships: "
                f"{stats['relationships_created']}/{len(jobs_data)} "
                f"(exact: {stats['exact_matches']}, fuzzy: {stats['fuzzy_matches']}, "
                f"orphan: {stats['orphans_created']})"
            )

        return stats

    async def _process_job_skills(
        self,
        job_row: dict,
        ingestion_job_id: str,
        stats: dict
    ) -> List[dict]:
        """
        Process all skills for a single job.

        Returns:
            List of relationship dicts for batch creation
        """
        job_id = job_row.get("Job ID")
        standardized_skills = self._parse_skills_field(job_row.get("standardized_skills", ""))
        similarity_scores = self._parse_scores_field(job_row.get("similarity_scores", ""))

        if not standardized_skills:
            return []

        relationships = []
        for idx, skill_name in enumerate(standardized_skills):
            # Match skill to taxonomy
            match_result = await self.skill_matching_service.match_skill(
                skill_name,
                job_id
            )

            # Track statistics
            if match_result["match_type"] == "exact":
                stats["exact_matches"] += 1
            elif match_result["match_type"] == "fuzzy":
                stats["fuzzy_matches"] += 1
            elif match_result["match_type"] == "orphan":
                stats["orphans_created"] += 1

            # Get similarity score if available
            similarity_score = None
            if similarity_scores and idx < len(similarity_scores):
                similarity_score = similarity_scores[idx]

            # Create relationship record
            relationships.append({
                "job_id": job_id,
                "skill_id": match_result["skill_id"],
                "similarity_score": similarity_score,
                "match_confidence": match_result["confidence"]
            })

        return relationships

    def _parse_skills_field(self, skills_field: str) -> List[str]:
        """
        Parse standardized_skills field (comma-separated or JSON array).

        Examples:
            "Python, FastAPI, Neo4j" → ["Python", "FastAPI", "Neo4j"]
            '["Python", "FastAPI"]' → ["Python", "FastAPI"]
        """
        if not skills_field or skills_field == "NULL":
            return []

        # Try JSON parse first
        try:
            skills_list = json.loads(skills_field)
            if isinstance(skills_list, list):
                return [s.strip() for s in skills_list if s and s.strip()]
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback to comma-separated
        return [s.strip() for s in skills_field.split(",") if s and s.strip()]

    def _parse_scores_field(self, scores_field: str) -> Optional[List[float]]:
        """
        Parse similarity_scores field (comma-separated or JSON array).

        Examples:
            "0.95, 0.87, 0.92" → [0.95, 0.87, 0.92]
            '[0.95, 0.87]' → [0.95, 0.87]
        """
        if not scores_field or scores_field == "NULL":
            return None

        # Try JSON parse first
        try:
            scores_list = json.loads(scores_field)
            if isinstance(scores_list, list):
                return [float(s) for s in scores_list]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

        # Fallback to comma-separated
        try:
            return [float(s.strip()) for s in scores_field.split(",") if s and s.strip()]
        except ValueError:
            logger.warning(f"Failed to parse similarity_scores: {scores_field}")
            return None

    async def _create_relationships_batch(self, relationships: List[dict]) -> None:
        """Create REQUIRES relationships in batch transaction."""
        async with self.neo4j_repo.driver.session() as session:
            await session.execute_write(self._create_relationships_tx, relationships)

    async def _create_relationships_tx(self, tx, relationships: List[dict]) -> None:
        """Transaction function to create REQUIRES relationships."""
        query = """
        UNWIND $relationships as rel
        MATCH (j:Job {job_id: rel.job_id})
        MATCH (s:Skill {id: rel.skill_id})
        MERGE (j)-[r:REQUIRES]->(s)
        ON CREATE SET
          r.similarity_score = rel.similarity_score,
          r.match_confidence = rel.match_confidence,
          r.created_at = datetime()
        """

        await tx.run(query, {"relationships": relationships})
