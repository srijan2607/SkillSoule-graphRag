# Phase 1: Data Layer Implementation

## Overview

This phase establishes the co-occurrence relationship layer in Neo4j, which serves as the foundation for all network math calculations. The existing `(:Job)-[:REQUIRES]->(:Skill)` bipartite graph remains the source of truth.

---

## 1. Graph Schema Design

### New Relationship: CO_OCCURS_WITH

```cypher
(:Skill)-[:CO_OCCURS_WITH {
    weight: INTEGER,     -- Number of jobs requiring BOTH skills
    cost: FLOAT,         -- 1.0 / weight (for Dijkstra)
    created_at: DATETIME,
    updated_at: DATETIME
}]-(:Skill)
```

### Properties Explanation

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| weight | INTEGER | Count of jobs requiring both skills | 150 |
| cost | FLOAT | Inverse of weight (1/weight) | 0.00667 |
| created_at | DATETIME | First computation timestamp | 2025-12-06T... |
| updated_at | DATETIME | Last recomputation timestamp | 2025-12-06T... |

### Relationship Direction

- **Bidirectional**: CO_OCCURS_WITH is symmetric
- **Implementation**: Store as undirected (one edge per pair)
- **Query Pattern**: Use undirected match `(s1)-[:CO_OCCURS_WITH]-(s2)`

---

## 2. Index Creation

### Required Indexes

```cypher
-- Performance index for weight lookups
CREATE INDEX skill_cooccurs_weight IF NOT EXISTS
FOR ()-[r:CO_OCCURS_WITH]->()
ON (r.weight);

-- Performance index for cost-based pathfinding
CREATE INDEX skill_cooccurs_cost IF NOT EXISTS
FOR ()-[r:CO_OCCURS_WITH]->()
ON (r.cost);

-- Composite index for range queries
CREATE INDEX skill_cooccurs_composite IF NOT EXISTS
FOR ()-[r:CO_OCCURS_WITH]->()
ON (r.weight, r.cost);
```

### Existing Indexes (Verify)

```cypher
-- These should already exist
SHOW INDEXES;

-- Expected:
-- skill_embedding_idx (vector index)
-- job_embedding_idx (vector index)
-- Skill.id (unique constraint)
-- Job.job_id (unique constraint)
```

---

## 3. Co-Occurrence Computation Algorithm

### Algorithm: Batch Co-Occurrence Builder

```
INPUT: All Job-REQUIRES-Skill relationships
OUTPUT: Skill-CO_OCCURS_WITH-Skill relationships

ALGORITHM:
1. For each Job:
   a. Get all skills S = {s1, s2, ..., sn} required by job
   b. For each unique pair (si, sj) where i < j:
      - Increment co-occurrence count for (si, sj)

2. For each skill pair with count >= MIN_THRESHOLD:
   a. Create/Update CO_OCCURS_WITH relationship
   b. Set weight = count
   c. Set cost = 1.0 / count
```

### Cypher Implementation (Batch Mode)

```cypher
// Step 1: Compute all co-occurrences
CALL apoc.periodic.iterate(
  "MATCH (j:Job)
   RETURN j",
  "MATCH (j)-[:REQUIRES]->(s1:Skill)
   MATCH (j)-[:REQUIRES]->(s2:Skill)
   WHERE id(s1) < id(s2)
   WITH s1, s2, count(*) as weight
   WHERE weight >= $min_weight
   MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)
   ON CREATE SET
     r.weight = weight,
     r.cost = 1.0 / weight,
     r.created_at = datetime()
   ON MATCH SET
     r.weight = weight,
     r.cost = 1.0 / weight,
     r.updated_at = datetime()",
  {batchSize: 1000, parallel: false, params: {min_weight: 2}}
)
```

### Alternative: Pure Cypher (No APOC)

```cypher
// Full rebuild - use when APOC not available
// Run in transaction batches

// Step 1: Clear existing relationships
MATCH ()-[r:CO_OCCURS_WITH]->()
DELETE r;

// Step 2: Build new relationships
MATCH (j:Job)-[:REQUIRES]->(s1:Skill)
MATCH (j)-[:REQUIRES]->(s2:Skill)
WHERE id(s1) < id(s2)
WITH s1, s2, count(DISTINCT j) as weight
WHERE weight >= 2
MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)
SET r.weight = weight,
    r.cost = 1.0 / weight,
    r.created_at = datetime()
RETURN count(r) as relationships_created;
```

---

## 4. Python Service: CoOccurrenceBuilder

### File: `backend/app/services/co_occurrence_builder.py`

```python
"""
Co-Occurrence Builder Service

Computes and maintains skill co-occurrence relationships based on
job requirements. This is the foundation for network math calculations.

Algorithm:
- For each job, find all skill pairs
- Count how many jobs require both skills
- Create CO_OCCURS_WITH relationship with weight=count, cost=1/count
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.repositories.neo4j_repository import Neo4jRepository
from app.config import settings

logger = logging.getLogger(__name__)


class CoOccurrenceBuilder:
    """
    Service for building and updating skill co-occurrence relationships.

    The CO_OCCURS_WITH relationship captures how frequently two skills
    appear together in job requirements. This is derived from the
    bipartite Job-REQUIRES-Skill graph.
    """

    def __init__(self, neo4j_repo: Neo4jRepository):
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
        MATCH ()-[r:CO_OCCURS_WITH]->()
        DELETE r
        RETURN count(r) as deleted
        """
        result = await self.neo4j_repo.execute_query(query)
        return result[0]["deleted"] if result else 0

    async def _compute_and_create(self) -> int:
        """Compute co-occurrences and create relationships."""
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
        MATCH ()-[r:CO_OCCURS_WITH]->()
        WITH count(r) as total_relationships,
             avg(r.weight) as avg_weight,
             min(r.weight) as min_weight,
             max(r.weight) as max_weight
        RETURN total_relationships, avg_weight, min_weight, max_weight
        """
        result = await self.neo4j_repo.execute_query(query)

        if result:
            return {
                "total_co_occurrence_relationships": result[0]["total_relationships"],
                "average_weight": float(result[0]["avg_weight"]) if result[0]["avg_weight"] else 0,
                "min_weight": result[0]["min_weight"],
                "max_weight": result[0]["max_weight"]
            }
        return {
            "total_co_occurrence_relationships": 0,
            "average_weight": 0,
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

    async def get_top_co_occurrences(self, skill_id: str, limit: int = 10) -> list:
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
```

---

## 5. Batch Script: Build Co-Occurrence

### File: `backend/scripts/build_co_occurrence.py`

```python
#!/usr/bin/env python3
"""
Batch script to build skill co-occurrence relationships.

Usage:
    python scripts/build_co_occurrence.py [--clear] [--min-weight N]

Options:
    --clear         Clear existing CO_OCCURS_WITH before building
    --min-weight N  Minimum co-occurrence count (default: 2)
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.co_occurrence_builder import CoOccurrenceBuilder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(clear: bool, min_weight: int):
    """Main entry point for co-occurrence build."""
    logger.info("=" * 60)
    logger.info("SKILL CO-OCCURRENCE BUILD")
    logger.info("=" * 60)
    logger.info(f"Clear existing: {clear}")
    logger.info(f"Minimum weight: {min_weight}")

    # Initialize repository
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )

    try:
        await repo.connect()
        logger.info("Connected to Neo4j")

        # Get initial stats
        initial_stats = await repo.get_database_stats()
        logger.info(f"Initial graph: {initial_stats['skills_count']} skills, "
                   f"{initial_stats['jobs_count']} jobs")

        # Build co-occurrences
        builder = CoOccurrenceBuilder(repo)
        builder.min_weight = min_weight

        result = builder.build_all(clear_existing=clear)
        result = await result

        # Log results
        logger.info("=" * 60)
        logger.info("BUILD RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {result.get('status', 'unknown')}")
        logger.info(f"Relationships created: {result.get('relationships_created', 0)}")
        logger.info(f"Duration: {result.get('duration_seconds', 0):.2f}s")

        if result.get('total_co_occurrence_relationships'):
            logger.info(f"Total relationships: {result['total_co_occurrence_relationships']}")
            logger.info(f"Average weight: {result.get('average_weight', 0):.2f}")
            logger.info(f"Weight range: {result.get('min_weight', 0)} - {result.get('max_weight', 0)}")

        if result.get('error'):
            logger.error(f"Error: {result['error']}")
            sys.exit(1)

    finally:
        await repo.close()
        logger.info("Disconnected from Neo4j")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build skill co-occurrence relationships")
    parser.add_argument("--clear", action="store_true", help="Clear existing relationships")
    parser.add_argument("--min-weight", type=int, default=2, help="Minimum co-occurrence count")

    args = parser.parse_args()
    asyncio.run(main(args.clear, args.min_weight))
```

---

## 6. Integration with Existing Ingestion

### Update: `batch_processor.py`

After job ingestion, trigger incremental co-occurrence update:

```python
# Add to process_jobs_batch method after creating REQUIRES relationships

# Trigger incremental co-occurrence update for this job
if hasattr(self, 'co_occurrence_builder') and self.co_occurrence_builder:
    await self.co_occurrence_builder.update_for_job(job_id)
```

### Alternative: Post-Ingestion Hook

```python
# In ingestion_service.py, after job ingestion completes

async def _on_jobs_ingestion_complete(self, job_id: str):
    """Hook called after jobs ingestion completes."""
    # Rebuild co-occurrences for all affected skills
    from app.services.co_occurrence_builder import CoOccurrenceBuilder
    builder = CoOccurrenceBuilder(self.neo4j_repo)
    await builder.build_all(clear_existing=True)
```

---

## 7. Validation Queries

### Verify Co-Occurrence Data

```cypher
// Count total relationships
MATCH ()-[r:CO_OCCURS_WITH]->()
RETURN count(r) as total;

// Top 10 strongest co-occurrences
MATCH (s1:Skill)-[r:CO_OCCURS_WITH]-(s2:Skill)
RETURN s1.name, s2.name, r.weight
ORDER BY r.weight DESC
LIMIT 10;

// Distribution of weights
MATCH ()-[r:CO_OCCURS_WITH]->()
RETURN
  CASE
    WHEN r.weight < 5 THEN '1-4'
    WHEN r.weight < 10 THEN '5-9'
    WHEN r.weight < 50 THEN '10-49'
    WHEN r.weight < 100 THEN '50-99'
    ELSE '100+'
  END as weight_bucket,
  count(*) as count
ORDER BY weight_bucket;

// Skills with most co-occurrences (hub skills)
MATCH (s:Skill)-[r:CO_OCCURS_WITH]-()
RETURN s.name, count(r) as connections, sum(r.weight) as total_weight
ORDER BY connections DESC
LIMIT 20;
```

---

## 8. Estimated Statistics

Based on 88k nodes and ~400k REQUIRES relationships:

| Metric | Estimate |
|--------|----------|
| Unique skill pairs | ~50,000 - 200,000 |
| CO_OCCURS_WITH relationships | ~30,000 - 100,000 (after threshold) |
| Average weight | ~5-15 jobs per pair |
| Max weight | ~500+ for popular skill pairs |
| Build time | 2-10 minutes |

---

## 9. Rollback Procedure

If issues occur:

```cypher
// Delete all CO_OCCURS_WITH relationships
MATCH ()-[r:CO_OCCURS_WITH]->()
DELETE r;

// Verify deletion
MATCH ()-[r:CO_OCCURS_WITH]->()
RETURN count(r);  // Should be 0

// Drop indexes if needed
DROP INDEX skill_cooccurs_weight IF EXISTS;
DROP INDEX skill_cooccurs_cost IF EXISTS;
```

---

## 10. Success Criteria

1. **Schema Created**: CO_OCCURS_WITH relationships exist with weight/cost
2. **Data Populated**: >10,000 relationships created
3. **Indexes Working**: Query response < 100ms for single lookups
4. **Incremental Works**: New job ingestion updates co-occurrences
5. **No Regressions**: Existing REQUIRES, SIMILAR_TO unaffected

---

*Next: Phase 2 - Services Layer Implementation*
