"""
Job Similarity Builder Service - Phase 7.1

Creates and maintains SIMILAR_JOB relationships based on shared skills (Jaccard similarity).
This enables job recommendation and similarity queries.

Algorithm:
- For each pair of jobs, count shared skills
- Calculate Jaccard similarity: |A ∩ B| / |A ∪ B|
- Create SIMILAR_JOB relationship if above threshold

Relationship Schema:
    (:Job)-[:SIMILAR_JOB {
        jaccard_score: FLOAT,      -- |shared_skills| / |union_skills|
        shared_count: INTEGER,     -- Number of shared skills
        computed_at: DATETIME
    }]->(:Job)

Reference: Phase 7 - Visible Impact Integration (08-VISIBLE-IMPACT-INTEGRATION.md)
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


class JobSimilarityBuilder:
    """
    Service for building and maintaining job similarity relationships.

    The SIMILAR_JOB relationship captures how similar two jobs are based
    on their skill requirements using Jaccard similarity coefficient.
    """

    def __init__(
        self,
        neo4j_repo: "Neo4jRepository",
        min_shared_skills: int = 3,
        min_jaccard: float = 0.2,
        max_similar_per_job: int = 20
    ) -> None:
        """
        Initialize JobSimilarityBuilder.

        Args:
            neo4j_repo: Neo4jRepository instance for database operations
            min_shared_skills: Minimum shared skills required for relationship
            min_jaccard: Minimum Jaccard score threshold (0.0-1.0)
            max_similar_per_job: Maximum similar jobs to store per job
        """
        self.neo4j_repo = neo4j_repo
        self.min_shared_skills = min_shared_skills
        self.min_jaccard = min_jaccard
        self.max_similar_per_job = max_similar_per_job

    async def build_all(self, clear_existing: bool = True) -> Dict[str, Any]:
        """
        Build all SIMILAR_JOB relationships from scratch.

        This is a batch operation that computes similarity for all job pairs.
        Use this for initial setup or full rebuilds.

        Args:
            clear_existing: If True, delete existing SIMILAR_JOB relationships first

        Returns:
            Statistics about the build process
        """
        start_time = datetime.utcnow()
        stats = {
            "started_at": start_time.isoformat(),
            "clear_existing": clear_existing,
            "min_shared_skills": self.min_shared_skills,
            "min_jaccard": self.min_jaccard
        }

        try:
            # Step 1: Clear existing if requested
            if clear_existing:
                deleted = await self._clear_existing()
                stats["relationships_deleted"] = deleted
                logger.info(f"Cleared {deleted} existing SIMILAR_JOB relationships")

            # Step 2: Compute and create new relationships
            created = await self._compute_and_create()
            stats["relationships_created"] = created

            # Step 3: Get statistics
            final_stats = await self.get_statistics()
            stats.update(final_stats)

            end_time = datetime.utcnow()
            stats["completed_at"] = end_time.isoformat()
            stats["duration_seconds"] = (end_time - start_time).total_seconds()
            stats["status"] = "success"

            logger.info(
                f"Job similarity build complete: {created} relationships created "
                f"in {stats['duration_seconds']:.2f}s"
            )

            return stats

        except Exception as e:
            logger.error(f"Job similarity build failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["error"] = str(e)
            return stats

    async def _clear_existing(self) -> int:
        """Delete all existing SIMILAR_JOB relationships."""
        query = """
        MATCH ()-[r:SIMILAR_JOB]-()
        DELETE r
        RETURN count(r) as deleted
        """
        result = await self.neo4j_repo.execute_query(query)
        return result[0]["deleted"] if result else 0

    async def _compute_and_create(self) -> int:
        """
        Compute Jaccard similarity and create SIMILAR_JOB relationships.

        Algorithm:
        1. For each job pair (j1, j2) where id(j1) < id(j2)
        2. Count shared skills between them
        3. Calculate Jaccard: |shared| / (|j1_skills| + |j2_skills| - |shared|)
        4. Create relationship if above thresholds
        """
        query = """
        // Find job pairs with shared skills
        MATCH (j1:Job)-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
        WHERE id(j1) < id(j2)

        // Count shared and total skills
        WITH j1, j2, count(DISTINCT s) as shared_count
        WHERE shared_count >= $min_shared

        // Get total skills for each job
        MATCH (j1)-[:REQUIRES]->(s1:Skill)
        WITH j1, j2, shared_count, count(DISTINCT s1) as j1_count
        MATCH (j2)-[:REQUIRES]->(s2:Skill)
        WITH j1, j2, shared_count, j1_count, count(DISTINCT s2) as j2_count

        // Calculate Jaccard similarity
        WITH j1, j2, shared_count,
             j1_count + j2_count - shared_count as union_count,
             toFloat(shared_count) / (j1_count + j2_count - shared_count) as jaccard
        WHERE jaccard >= $min_jaccard

        // Create bidirectional relationships
        MERGE (j1)-[r:SIMILAR_JOB]->(j2)
        SET r.jaccard_score = jaccard,
            r.shared_count = shared_count,
            r.computed_at = datetime()

        RETURN count(r) as created
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "min_shared": self.min_shared_skills,
                "min_jaccard": self.min_jaccard
            },
            timeout=300.0  # 5 minute timeout for large graphs
        )
        return result[0]["created"] if result else 0

    async def update_for_job(self, job_id: str) -> Dict[str, Any]:
        """
        Incrementally update SIMILAR_JOB relationships for a single job.

        Use this after ingesting a new job to compute its similarity
        with existing jobs.

        Args:
            job_id: The job ID to process

        Returns:
            Statistics about the update
        """
        query = """
        // Find similar jobs to this one
        MATCH (j1:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
        WHERE j1 <> j2

        WITH j1, j2, count(DISTINCT s) as shared_count
        WHERE shared_count >= $min_shared

        MATCH (j1)-[:REQUIRES]->(s1:Skill)
        WITH j1, j2, shared_count, count(DISTINCT s1) as j1_count
        MATCH (j2)-[:REQUIRES]->(s2:Skill)
        WITH j1, j2, shared_count, j1_count, count(DISTINCT s2) as j2_count

        WITH j1, j2, shared_count,
             toFloat(shared_count) / (j1_count + j2_count - shared_count) as jaccard
        WHERE jaccard >= $min_jaccard

        ORDER BY jaccard DESC
        LIMIT $max_per_job

        MERGE (j1)-[r:SIMILAR_JOB]-(j2)
        SET r.jaccard_score = jaccard,
            r.shared_count = shared_count,
            r.computed_at = datetime()

        RETURN count(r) as created
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "job_id": job_id,
                "min_shared": self.min_shared_skills,
                "min_jaccard": self.min_jaccard,
                "max_per_job": self.max_similar_per_job
            }
        )

        return {"edges_created": result[0]["created"] if result else 0}

    async def get_similar_jobs(
        self,
        job_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most similar jobs to a given job.

        Args:
            job_id: The job ID to find similar jobs for
            limit: Maximum number of similar jobs to return

        Returns:
            List of similar jobs with their similarity scores
        """
        query = """
        MATCH (j:Job {job_id: $job_id})-[r:SIMILAR_JOB]-(j2:Job)
        RETURN j2.job_id as job_id,
               j2.job_title as title,
               j2.company_name as company,
               j2.location as location,
               r.jaccard_score as similarity,
               r.shared_count as shared_skills
        ORDER BY r.jaccard_score DESC
        LIMIT $limit
        """
        return await self.neo4j_repo.execute_query(
            query, {"job_id": job_id, "limit": limit}
        )

    async def get_similar_jobs_by_title(
        self,
        job_title: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get similar jobs by searching for a job title.

        Args:
            job_title: Job title to search for (partial match)
            limit: Maximum number of similar jobs to return

        Returns:
            List of similar jobs with their similarity scores
        """
        query = """
        MATCH (j:Job)
        WHERE toLower(j.job_title) CONTAINS toLower($title)
        WITH j LIMIT 1
        MATCH (j)-[r:SIMILAR_JOB]-(j2:Job)
        RETURN j.job_id as source_job_id,
               j.job_title as source_job_title,
               j2.job_id as job_id,
               j2.job_title as title,
               j2.company_name as company,
               j2.location as location,
               r.jaccard_score as similarity,
               r.shared_count as shared_skills
        ORDER BY r.jaccard_score DESC
        LIMIT $limit
        """
        return await self.neo4j_repo.execute_query(
            query, {"title": job_title, "limit": limit}
        )

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current SIMILAR_JOB relationships."""
        query = """
        MATCH ()-[r:SIMILAR_JOB]->()
        WITH r.jaccard_score as score, r.shared_count as shared
        RETURN
            count(*) as total_relationships,
            avg(score) as avg_jaccard,
            min(score) as min_jaccard,
            max(score) as max_jaccard,
            avg(shared) as avg_shared_skills
        """
        result = await self.neo4j_repo.execute_query(query)

        if result and result[0]["total_relationships"]:
            return {
                "total_similar_job_relationships": int(result[0]["total_relationships"]),
                "average_jaccard_score": float(result[0]["avg_jaccard"]) if result[0]["avg_jaccard"] else 0.0,
                "min_jaccard_score": float(result[0]["min_jaccard"]) if result[0]["min_jaccard"] else 0.0,
                "max_jaccard_score": float(result[0]["max_jaccard"]) if result[0]["max_jaccard"] else 0.0,
                "average_shared_skills": float(result[0]["avg_shared_skills"]) if result[0]["avg_shared_skills"] else 0.0
            }
        return {
            "total_similar_job_relationships": 0,
            "average_jaccard_score": 0.0,
            "min_jaccard_score": 0.0,
            "max_jaccard_score": 0.0,
            "average_shared_skills": 0.0
        }

    async def get_job_similarity_score(
        self,
        job_id_1: str,
        job_id_2: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the similarity score between two specific jobs.

        Args:
            job_id_1: First job ID
            job_id_2: Second job ID

        Returns:
            Similarity details or None if no relationship exists
        """
        query = """
        MATCH (j1:Job {job_id: $job_id_1})-[r:SIMILAR_JOB]-(j2:Job {job_id: $job_id_2})
        RETURN r.jaccard_score as similarity,
               r.shared_count as shared_skills,
               r.computed_at as computed_at
        """
        result = await self.neo4j_repo.execute_query(
            query, {"job_id_1": job_id_1, "job_id_2": job_id_2}
        )
        return result[0] if result else None

    async def get_shared_skills_between_jobs(
        self,
        job_id_1: str,
        job_id_2: str
    ) -> List[Dict[str, Any]]:
        """
        Get the skills shared between two jobs.

        Args:
            job_id_1: First job ID
            job_id_2: Second job ID

        Returns:
            List of shared skills
        """
        query = """
        MATCH (j1:Job {job_id: $job_id_1})-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job {job_id: $job_id_2})
        RETURN s.id as skill_id,
               s.name as skill_name,
               s.centrality as centrality,
               s.demand_count as demand_count
        ORDER BY s.demand_count DESC
        """
        return await self.neo4j_repo.execute_query(
            query, {"job_id_1": job_id_1, "job_id_2": job_id_2}
        )

    async def create_indexes(self) -> Dict[str, Any]:
        """
        Create required indexes for SIMILAR_JOB relationships.

        Returns:
            Status of index creation
        """
        indexes_created = []
        errors = []

        index_queries = [
            {
                "name": "job_similar_jaccard",
                "query": """
                CREATE INDEX job_similar_jaccard IF NOT EXISTS
                FOR ()-[r:SIMILAR_JOB]-()
                ON (r.jaccard_score)
                """
            },
            {
                "name": "job_similar_shared",
                "query": """
                CREATE INDEX job_similar_shared IF NOT EXISTS
                FOR ()-[r:SIMILAR_JOB]-()
                ON (r.shared_count)
                """
            }
        ]

        for idx in index_queries:
            try:
                await self.neo4j_repo.execute_query(idx["query"])
                indexes_created.append(idx["name"])
                logger.info(f"Created/verified index: {idx['name']}")
            except Exception as e:
                error_msg = f"Failed to create index {idx['name']}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)

        return {
            "indexes_created": indexes_created,
            "errors": errors,
            "status": "success" if not errors else "partial"
        }

    async def validate_data(self) -> Dict[str, Any]:
        """
        Validate SIMILAR_JOB relationships for data integrity.

        Returns:
            Validation results
        """
        validation_query = """
        MATCH ()-[r:SIMILAR_JOB]->()
        WITH r,
             CASE WHEN r.jaccard_score IS NULL THEN 1 ELSE 0 END as null_jaccard,
             CASE WHEN r.shared_count IS NULL THEN 1 ELSE 0 END as null_shared,
             CASE WHEN r.jaccard_score < 0 OR r.jaccard_score > 1 THEN 1 ELSE 0 END as invalid_jaccard,
             CASE WHEN r.shared_count < 1 THEN 1 ELSE 0 END as invalid_shared
        RETURN
            count(r) as total_relationships,
            sum(null_jaccard) as null_jaccards,
            sum(null_shared) as null_shareds,
            sum(invalid_jaccard) as invalid_jaccards,
            sum(invalid_shared) as invalid_shareds
        """
        result = await self.neo4j_repo.execute_query(validation_query)

        if result:
            r = result[0]
            issues = []
            if r["null_jaccards"] > 0:
                issues.append(f"{int(r['null_jaccards'])} relationships with null jaccard_score")
            if r["null_shareds"] > 0:
                issues.append(f"{int(r['null_shareds'])} relationships with null shared_count")
            if r["invalid_jaccards"] > 0:
                issues.append(f"{int(r['invalid_jaccards'])} relationships with invalid jaccard_score")
            if r["invalid_shareds"] > 0:
                issues.append(f"{int(r['invalid_shareds'])} relationships with invalid shared_count")

            return {
                "total_relationships": int(r["total_relationships"]) if r["total_relationships"] else 0,
                "is_valid": len(issues) == 0,
                "issues": issues
            }

        return {
            "total_relationships": 0,
            "is_valid": True,
            "issues": []
        }
