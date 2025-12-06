"""
Co-Occurrence Builder Service

Computes and maintains skill co-occurrence relationships based on
job requirements. This is the foundation for network math calculations.

Algorithm:
- For each job, find all skill pairs
- Count how many jobs require both skills
- Create CO_OCCURS_WITH relationship with weight=count, cost=1/count

Reference: Network Math Implementation - Phase 1 (01-DATA-LAYER.md)
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from datetime import datetime

from app.config import settings

if TYPE_CHECKING:
    from app.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


class CoOccurrenceBuilder:
    """
    Service for building and updating skill co-occurrence relationships.

    The CO_OCCURS_WITH relationship captures how frequently two skills
    appear together in job requirements. This is derived from the
    bipartite Job-REQUIRES-Skill graph.

    Relationship Schema:
        (:Skill)-[:CO_OCCURS_WITH {
            weight: INTEGER,     -- Number of jobs requiring BOTH skills
            cost: FLOAT,         -- 1.0 / weight (for Dijkstra)
            created_at: DATETIME,
            updated_at: DATETIME
        }]-(:Skill)
    """

    def __init__(self, neo4j_repo: "Neo4jRepository") -> None:
        """
        Initialize CoOccurrenceBuilder.

        Args:
            neo4j_repo: Neo4jRepository instance for database operations
        """
        self.neo4j_repo = neo4j_repo
        self.min_weight = getattr(settings, 'NETWORK_MIN_CO_OCCURRENCE', 2)

    async def build_all(self, clear_existing: bool = True) -> Dict[str, Any]:
        """
        Build all co-occurrence relationships from scratch.

        Args:
            clear_existing: If True, delete existing CO_OCCURS_WITH first

        Returns:
            Statistics about the build process
        """
        start_time = datetime.utcnow()
        stats = {
            "started_at": start_time.isoformat(),
            "clear_existing": clear_existing,
            "min_weight": self.min_weight
        }

        try:
            # Step 1: Clear existing if requested
            if clear_existing:
                deleted = await self._clear_existing()
                stats["relationships_deleted"] = deleted
                logger.info(f"Cleared {deleted} existing CO_OCCURS_WITH relationships")

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
                f"Co-occurrence build complete: {created} relationships created "
                f"in {stats['duration_seconds']:.2f}s"
            )

            return stats

        except Exception as e:
            logger.error(f"Co-occurrence build failed: {str(e)}", exc_info=True)
            stats["status"] = "failed"
            stats["error"] = str(e)
            return stats

    async def _clear_existing(self) -> int:
        """Delete all existing CO_OCCURS_WITH relationships."""
        query = """
        MATCH ()-[r:CO_OCCURS_WITH]-()
        DELETE r
        RETURN count(r) as deleted
        """
        result = await self.neo4j_repo.execute_query(query)
        return result[0]["deleted"] if result else 0

    async def _compute_and_create(self) -> int:
        """
        Compute co-occurrences and create relationships.

        Algorithm:
        1. For each Job, find all skill pairs (s1, s2) where id(s1) < id(s2)
        2. Count distinct jobs requiring both skills
        3. Create CO_OCCURS_WITH with weight=count, cost=1/count
        """
        query = """
        MATCH (j:Job)-[:REQUIRES]->(s1:Skill)
        MATCH (j)-[:REQUIRES]->(s2:Skill)
        WHERE id(s1) < id(s2)
        WITH s1, s2, count(DISTINCT j) as weight
        WHERE weight >= $min_weight
        MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)
        SET r.weight = weight,
            r.cost = 1.0 / weight,
            r.created_at = datetime(),
            r.updated_at = datetime()
        RETURN count(r) as created
        """
        result = await self.neo4j_repo.execute_query(
            query,
            {"min_weight": self.min_weight},
            timeout=300.0  # 5 minute timeout for large graphs
        )
        return result[0]["created"] if result else 0

    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about current co-occurrence relationships."""
        query = """
        MATCH ()-[r:CO_OCCURS_WITH]-()
        WITH r.weight as weight
        RETURN
            count(*) / 2 as total_relationships,
            avg(weight) as avg_weight,
            min(weight) as min_weight,
            max(weight) as max_weight
        """
        result = await self.neo4j_repo.execute_query(query)

        if result and result[0]["total_relationships"]:
            return {
                "total_co_occurrence_relationships": int(result[0]["total_relationships"]),
                "average_weight": float(result[0]["avg_weight"]) if result[0]["avg_weight"] else 0.0,
                "min_weight": result[0]["min_weight"],
                "max_weight": result[0]["max_weight"]
            }
        return {
            "total_co_occurrence_relationships": 0,
            "average_weight": 0.0,
            "min_weight": 0,
            "max_weight": 0
        }

    async def update_for_job(self, job_id: str) -> Dict[str, Any]:
        """
        Update co-occurrences for a single job (incremental update).

        Use this after ingesting a new job to update its skill pairs.

        Args:
            job_id: The job ID to process

        Returns:
            Statistics about the update
        """
        query = """
        MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s1:Skill)
        MATCH (j)-[:REQUIRES]->(s2:Skill)
        WHERE id(s1) < id(s2)
        WITH s1, s2

        // Get total count across all jobs
        MATCH (any_job:Job)-[:REQUIRES]->(s1)
        MATCH (any_job)-[:REQUIRES]->(s2)
        WITH s1, s2, count(DISTINCT any_job) as weight
        WHERE weight >= $min_weight

        MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)
        SET r.weight = weight,
            r.cost = 1.0 / weight,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()

        RETURN count(r) as updated
        """
        result = await self.neo4j_repo.execute_query(
            query,
            {"job_id": job_id, "min_weight": self.min_weight}
        )
        return {"relationships_updated": result[0]["updated"] if result else 0}

    async def get_top_co_occurrences(self, skill_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top co-occurring skills for a given skill.

        Args:
            skill_id: The skill ID to query
            limit: Maximum number of results

        Returns:
            List of co-occurring skills with weights
        """
        query = """
        MATCH (s:Skill {id: $skill_id})-[r:CO_OCCURS_WITH]-(other:Skill)
        RETURN other.id as skill_id,
               other.name as skill_name,
               r.weight as weight,
               r.cost as cost
        ORDER BY r.weight DESC
        LIMIT $limit
        """
        return await self.neo4j_repo.execute_query(
            query,
            {"skill_id": skill_id, "limit": limit}
        )

    async def create_indexes(self) -> Dict[str, Any]:
        """
        Create required indexes for CO_OCCURS_WITH relationships.

        Returns:
            Status of index creation
        """
        indexes_created = []
        errors = []

        # Index definitions
        index_queries = [
            {
                "name": "skill_cooccurs_weight",
                "query": """
                CREATE INDEX skill_cooccurs_weight IF NOT EXISTS
                FOR ()-[r:CO_OCCURS_WITH]-()
                ON (r.weight)
                """
            },
            {
                "name": "skill_cooccurs_cost",
                "query": """
                CREATE INDEX skill_cooccurs_cost IF NOT EXISTS
                FOR ()-[r:CO_OCCURS_WITH]-()
                ON (r.cost)
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
        Validate CO_OCCURS_WITH relationships for data integrity.

        Returns:
            Validation results
        """
        validation_query = """
        MATCH ()-[r:CO_OCCURS_WITH]-()
        WITH r,
             CASE WHEN r.weight IS NULL THEN 1 ELSE 0 END as null_weight,
             CASE WHEN r.cost IS NULL THEN 1 ELSE 0 END as null_cost,
             CASE WHEN r.weight < 1 THEN 1 ELSE 0 END as invalid_weight,
             CASE WHEN r.cost <= 0 THEN 1 ELSE 0 END as invalid_cost
        RETURN
            count(r) / 2 as total_relationships,
            sum(null_weight) / 2 as null_weights,
            sum(null_cost) / 2 as null_costs,
            sum(invalid_weight) / 2 as invalid_weights,
            sum(invalid_cost) / 2 as invalid_costs
        """
        result = await self.neo4j_repo.execute_query(validation_query)

        if result:
            r = result[0]
            issues = []
            if r["null_weights"] > 0:
                issues.append(f"{int(r['null_weights'])} relationships with null weight")
            if r["null_costs"] > 0:
                issues.append(f"{int(r['null_costs'])} relationships with null cost")
            if r["invalid_weights"] > 0:
                issues.append(f"{int(r['invalid_weights'])} relationships with invalid weight (<1)")
            if r["invalid_costs"] > 0:
                issues.append(f"{int(r['invalid_costs'])} relationships with invalid cost (<=0)")

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
