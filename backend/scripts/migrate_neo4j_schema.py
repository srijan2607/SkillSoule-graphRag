#!/usr/bin/env python3
"""
Neo4j Schema Migration Script - Phase 7.1

Adds new properties, relationships, and indexes to support:
- Skill name canonicalization with SkillNormalizer
- Stored centrality and demand metrics
- Job similarity relationships
- Deduplication support with UNIQUE constraint

This script is idempotent and can be run multiple times safely.

CRITICAL MIGRATION ORDER:
1. Apply SkillNormalizer to update canonical_name
2. Deduplicate skills (merge by canonical_name)
3. Create UNIQUE constraint on canonical_name (MUST be after dedupe)

Usage:
    cd backend
    python scripts/migrate_neo4j_schema.py
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, ".")

from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.skill_normalizer import SkillNormalizer, SKILL_ALIASES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SchemaMigration:
    """Neo4j schema migration manager."""

    def __init__(self, neo4j_repo: Neo4jRepository):
        self.neo4j_repo = neo4j_repo
        self.migration_results: List[Dict[str, Any]] = []
        self.skill_normalizer = SkillNormalizer()

    async def run_all_migrations(self) -> Dict[str, Any]:
        """
        Run all schema migrations in order.

        Returns:
            Summary of migration results
        """
        start_time = datetime.utcnow()
        logger.info("=" * 60)
        logger.info("Starting Neo4j Schema Migration - Phase 7.1")
        logger.info("=" * 60)

        migrations = [
            ("Add Skill node properties", self._migrate_skill_properties),
            ("Add Job node properties", self._migrate_job_properties),
            ("Create skill indexes", self._create_skill_indexes),
            ("Create job indexes", self._create_job_indexes),
            ("Create SIMILAR_JOB relationship index", self._create_similar_job_index),
            ("Initialize skill canonical names", self._init_canonical_names),
            # NEW: Advanced normalization with SkillNormalizer (MUST run before dedupe)
            ("Apply SkillNormalizer to canonical names", self._apply_skill_normalizer),
            # NEW: Deduplicate skills by canonical_name (MUST run before UNIQUE constraint)
            ("Deduplicate skills by canonical_name", self._deduplicate_skills),
            # NEW: Create UNIQUE constraint (MUST be AFTER dedupe)
            ("Create UNIQUE constraint on canonical_name", self._create_canonical_unique_constraint),
            ("Initialize job skill counts", self._init_job_skill_counts),
            ("Initialize skill demand counts", self._init_skill_demand_counts),
            # Verification checkpoint
            ("Verify no duplicate canonical names", self._verify_no_duplicates),
        ]

        success_count = 0
        error_count = 0

        for name, migration_func in migrations:
            try:
                logger.info(f"\n>>> Running: {name}")
                result = await migration_func()
                self.migration_results.append({
                    "name": name,
                    "status": "success",
                    "result": result
                })
                success_count += 1
                logger.info(f"    [OK] {name}: {result}")
            except Exception as e:
                self.migration_results.append({
                    "name": name,
                    "status": "failed",
                    "error": str(e)
                })
                error_count += 1
                logger.error(f"    [FAILED] {name}: {str(e)}")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        summary = {
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "total_migrations": len(migrations),
            "successful": success_count,
            "failed": error_count,
            "status": "success" if error_count == 0 else "partial",
            "results": self.migration_results
        }

        logger.info("\n" + "=" * 60)
        logger.info(f"Migration Complete: {success_count}/{len(migrations)} successful")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 60)

        return summary

    async def _migrate_skill_properties(self) -> str:
        """
        Add new properties to Skill nodes.

        Properties:
        - canonical_name: Normalized lowercase name for matching
        - centrality: Stored eigenvector centrality score
        - demand_count: Number of jobs requiring this skill
        - co_occurrence_count: Number of CO_OCCURS_WITH edges
        """
        # Note: We don't set default values here to avoid overwriting existing data
        # Instead, we initialize them in separate migrations
        query = """
        MATCH (s:Skill)
        WHERE s.canonical_name IS NULL
        SET s.canonical_name = toLower(trim(s.name)),
            s.centrality = COALESCE(s.centrality, 0.0),
            s.demand_count = COALESCE(s.demand_count, 0),
            s.co_occurrence_count = COALESCE(s.co_occurrence_count, 0)
        RETURN count(s) as updated
        """
        result = await self.neo4j_repo.execute_query(query)
        return f"Updated {result[0]['updated']} Skill nodes"

    async def _migrate_job_properties(self) -> str:
        """
        Add new properties to Job nodes.

        Properties:
        - skill_count: Number of skills required by this job
        - content_hash: Hash for deduplication (will be computed during ingestion)
        """
        query = """
        MATCH (j:Job)
        WHERE j.skill_count IS NULL
        SET j.skill_count = COALESCE(j.skill_count, 0)
        RETURN count(j) as updated
        """
        result = await self.neo4j_repo.execute_query(query)
        return f"Updated {result[0]['updated']} Job nodes"

    async def _create_skill_indexes(self) -> str:
        """Create indexes for Skill node properties."""
        indexes = [
            {
                "name": "skill_canonical",
                "query": "CREATE INDEX skill_canonical IF NOT EXISTS FOR (s:Skill) ON (s.canonical_name)"
            },
            {
                "name": "skill_centrality",
                "query": "CREATE INDEX skill_centrality IF NOT EXISTS FOR (s:Skill) ON (s.centrality)"
            },
            {
                "name": "skill_demand",
                "query": "CREATE INDEX skill_demand IF NOT EXISTS FOR (s:Skill) ON (s.demand_count)"
            }
        ]

        created = []
        for idx in indexes:
            try:
                await self.neo4j_repo.execute_query(idx["query"])
                created.append(idx["name"])
            except Exception as e:
                logger.warning(f"Index {idx['name']} may already exist: {e}")
                created.append(f"{idx['name']} (existed)")

        return f"Indexes: {', '.join(created)}"

    async def _create_job_indexes(self) -> str:
        """Create indexes for Job node properties."""
        indexes = [
            {
                "name": "job_content_hash",
                "query": "CREATE INDEX job_content_hash IF NOT EXISTS FOR (j:Job) ON (j.content_hash)"
            },
            {
                "name": "job_skill_count",
                "query": "CREATE INDEX job_skill_count IF NOT EXISTS FOR (j:Job) ON (j.skill_count)"
            }
        ]

        created = []
        for idx in indexes:
            try:
                await self.neo4j_repo.execute_query(idx["query"])
                created.append(idx["name"])
            except Exception as e:
                logger.warning(f"Index {idx['name']} may already exist: {e}")
                created.append(f"{idx['name']} (existed)")

        return f"Indexes: {', '.join(created)}"

    async def _create_similar_job_index(self) -> str:
        """Create index for SIMILAR_JOB relationship properties."""
        query = """
        CREATE INDEX job_similar_jaccard IF NOT EXISTS
        FOR ()-[r:SIMILAR_JOB]-()
        ON (r.jaccard_score)
        """
        try:
            await self.neo4j_repo.execute_query(query)
            return "Index job_similar_jaccard created"
        except Exception as e:
            return f"Index may already exist: {e}"

    async def _init_canonical_names(self) -> str:
        """Initialize canonical_name for all Skill nodes."""
        query = """
        MATCH (s:Skill)
        WHERE s.canonical_name IS NULL OR s.canonical_name = ''
        SET s.canonical_name = toLower(trim(s.name))
        RETURN count(s) as updated
        """
        result = await self.neo4j_repo.execute_query(query)
        return f"Initialized {result[0]['updated']} canonical names"

    async def _init_job_skill_counts(self) -> str:
        """Calculate and set skill_count for all Job nodes."""
        query = """
        MATCH (j:Job)
        OPTIONAL MATCH (j)-[r:REQUIRES]->(:Skill)
        WITH j, count(r) as skill_count
        SET j.skill_count = skill_count
        RETURN count(j) as updated
        """
        result = await self.neo4j_repo.execute_query(query, timeout=120.0)
        return f"Updated skill_count for {result[0]['updated']} jobs"

    async def _init_skill_demand_counts(self) -> str:
        """Calculate and set demand_count for all Skill nodes."""
        query = """
        MATCH (s:Skill)
        OPTIONAL MATCH (j:Job)-[:REQUIRES]->(s)
        WITH s, count(DISTINCT j) as demand_count
        SET s.demand_count = demand_count
        RETURN count(s) as updated
        """
        result = await self.neo4j_repo.execute_query(query, timeout=120.0)
        return f"Updated demand_count for {result[0]['updated']} skills"

    async def _apply_skill_normalizer(self) -> str:
        """
        Apply SkillNormalizer to all canonical_name values.

        This handles alias mappings (JS->javascript, C#->csharp, etc.)
        and ensures consistent canonicalization.
        """
        # Step 1: Fetch all skills with their names
        fetch_query = """
        MATCH (s:Skill)
        RETURN s.id as id, s.name as name, s.canonical_name as current_canonical
        """
        skills = await self.neo4j_repo.execute_query(fetch_query)

        # Step 2: Compute new canonical names using SkillNormalizer
        updates = []
        for skill in skills:
            skill_name = skill.get("name") or skill.get("current_canonical") or ""
            new_canonical = self.skill_normalizer.normalize(skill_name)
            current_canonical = skill.get("current_canonical") or ""

            # Only update if different
            if new_canonical and new_canonical != current_canonical:
                updates.append({
                    "id": skill["id"],
                    "canonical_name": new_canonical
                })

        # Step 3: Batch update skills
        if updates:
            update_query = """
            UNWIND $updates AS update
            MATCH (s:Skill {id: update.id})
            SET s.canonical_name = update.canonical_name
            RETURN count(s) as updated
            """
            result = await self.neo4j_repo.execute_query(
                update_query,
                {"updates": updates},
                timeout=120.0
            )
            updated_count = result[0]["updated"] if result else 0
        else:
            updated_count = 0

        logger.info(f"    Analyzed {len(skills)} skills, updated {updated_count} canonical names")
        return f"Applied SkillNormalizer: {updated_count}/{len(skills)} skills updated"

    async def _deduplicate_skills(self) -> str:
        """
        Deduplicate skills by canonical_name.

        For skills with the same canonical_name:
        1. Keep the skill with the most relationships (or oldest)
        2. Transfer all relationships to the kept skill
        3. Delete duplicate skills

        CRITICAL: This MUST run BEFORE creating UNIQUE constraint.
        """
        # Step 1: Find duplicate canonical_names
        find_duplicates_query = """
        MATCH (s:Skill)
        WHERE s.canonical_name IS NOT NULL AND s.canonical_name <> ''
        WITH s.canonical_name as cn, collect(s) as skills, count(s) as cnt
        WHERE cnt > 1
        RETURN cn, [s IN skills | {id: s.id, name: s.name}] as skill_list, cnt
        ORDER BY cnt DESC
        """
        duplicates = await self.neo4j_repo.execute_query(find_duplicates_query)

        if not duplicates:
            return "No duplicate canonical_names found"

        total_merged = 0
        total_deleted = 0

        for dup in duplicates:
            canonical_name = dup["cn"]
            skill_list = dup["skill_list"]

            logger.info(f"    Merging {len(skill_list)} skills with canonical_name '{canonical_name}'")

            # Step 2: For each duplicate group, merge into one
            # Strategy: Keep first skill, transfer relationships from others
            merge_query = """
            MATCH (s:Skill)
            WHERE s.canonical_name = $canonical_name
            WITH s ORDER BY
                CASE WHEN s.centrality IS NOT NULL THEN s.centrality ELSE 0 END DESC,
                CASE WHEN s.demand_count IS NOT NULL THEN s.demand_count ELSE 0 END DESC,
                s.id ASC
            WITH collect(s) as skills
            WITH skills[0] as keeper, skills[1..] as duplicates

            // Transfer REQUIRES relationships from duplicates to keeper
            UNWIND duplicates as dup
            OPTIONAL MATCH (j:Job)-[r:REQUIRES]->(dup)
            WITH keeper, dup, j, r
            WHERE j IS NOT NULL
            MERGE (j)-[:REQUIRES]->(keeper)

            // Transfer SIMILAR_TO relationships from duplicates to keeper
            WITH keeper, dup
            OPTIONAL MATCH (dup)-[r:SIMILAR_TO]-(other:Skill)
            WHERE other <> keeper
            WITH keeper, dup, other, r
            WHERE other IS NOT NULL
            MERGE (keeper)-[:SIMILAR_TO]-(other)

            // Transfer BELONGS_TO_CATEGORY relationships
            WITH keeper, dup
            OPTIONAL MATCH (dup)-[r:BELONGS_TO_CATEGORY]->(cat:Category)
            WITH keeper, dup, cat, r
            WHERE cat IS NOT NULL
            MERGE (keeper)-[:BELONGS_TO_CATEGORY]->(cat)

            // Delete duplicate and its relationships
            WITH keeper, dup
            DETACH DELETE dup

            RETURN count(dup) as deleted
            """
            result = await self.neo4j_repo.execute_query(
                merge_query,
                {"canonical_name": canonical_name},
                timeout=60.0
            )

            deleted = result[0]["deleted"] if result and result[0]["deleted"] else 0
            total_deleted += deleted
            total_merged += 1

        return f"Merged {total_merged} duplicate groups, deleted {total_deleted} duplicate skills"

    async def _create_canonical_unique_constraint(self) -> str:
        """
        Create UNIQUE constraint on canonical_name.

        CRITICAL: This MUST run AFTER deduplication, otherwise it will fail
        if duplicates exist.
        """
        constraint_query = """
        CREATE CONSTRAINT skill_canonical_unique IF NOT EXISTS
        FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE
        """
        try:
            await self.neo4j_repo.execute_query(constraint_query)
            return "UNIQUE constraint skill_canonical_unique created"
        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower():
                return "UNIQUE constraint already exists"
            elif "duplicate" in error_msg.lower():
                # Constraint creation failed due to duplicates
                raise RuntimeError(
                    f"Cannot create UNIQUE constraint: duplicates still exist. "
                    f"Run deduplication first. Error: {error_msg}"
                )
            raise

    async def _verify_no_duplicates(self) -> str:
        """
        Verification checkpoint: Ensure no duplicate canonical_names exist.

        This is the verification query from AC5:
        MATCH (s:Skill) WITH s.canonical_name as cn, count(*) as c WHERE c > 1 RETURN cn, c
        """
        verify_query = """
        MATCH (s:Skill)
        WHERE s.canonical_name IS NOT NULL AND s.canonical_name <> ''
        WITH s.canonical_name as cn, count(*) as c
        WHERE c > 1
        RETURN cn, c
        """
        result = await self.neo4j_repo.execute_query(verify_query)

        if result and len(result) > 0:
            # Found duplicates - log them and raise error
            dup_list = [f"{r['cn']}({r['c']})" for r in result[:10]]
            raise RuntimeError(
                f"Verification FAILED: Found {len(result)} duplicate canonical_names: "
                f"{', '.join(dup_list)}"
            )

        return "Verification PASSED: No duplicate canonical_names found"


async def verify_migration(neo4j_repo: Neo4jRepository) -> Dict[str, Any]:
    """
    Verify the migration was successful.

    Returns:
        Verification results
    """
    logger.info("\nVerifying migration...")

    checks = []

    # Check 1: Skill canonical names
    query1 = """
    MATCH (s:Skill)
    WHERE s.canonical_name IS NOT NULL
    RETURN count(s) as count
    """
    result1 = await neo4j_repo.execute_query(query1)
    checks.append({
        "check": "Skills with canonical_name",
        "count": result1[0]["count"]
    })

    # Check 2: Job skill counts
    query2 = """
    MATCH (j:Job)
    WHERE j.skill_count IS NOT NULL AND j.skill_count > 0
    RETURN count(j) as count
    """
    result2 = await neo4j_repo.execute_query(query2)
    checks.append({
        "check": "Jobs with skill_count",
        "count": result2[0]["count"]
    })

    # Check 3: Skill demand counts
    query3 = """
    MATCH (s:Skill)
    WHERE s.demand_count IS NOT NULL AND s.demand_count > 0
    RETURN count(s) as count
    """
    result3 = await neo4j_repo.execute_query(query3)
    checks.append({
        "check": "Skills with demand_count",
        "count": result3[0]["count"]
    })

    # Check 4: Indexes
    query4 = """
    SHOW INDEXES
    """
    result4 = await neo4j_repo.execute_query(query4)
    index_names = [idx.get("name", "unknown") for idx in result4]
    expected_indexes = ["skill_canonical", "skill_centrality", "skill_demand",
                        "job_content_hash", "job_skill_count"]
    found_indexes = [idx for idx in expected_indexes if any(idx in name for name in index_names)]
    checks.append({
        "check": "Expected indexes found",
        "found": found_indexes,
        "missing": [idx for idx in expected_indexes if idx not in found_indexes]
    })

    # Check 5: UNIQUE constraint on canonical_name
    query5 = """
    SHOW CONSTRAINTS
    """
    result5 = await neo4j_repo.execute_query(query5)
    constraint_names = [c.get("name", "unknown") for c in result5]
    has_unique_constraint = any("skill_canonical_unique" in name for name in constraint_names)
    checks.append({
        "check": "skill_canonical_unique constraint",
        "exists": has_unique_constraint,
        "constraint_names": constraint_names
    })

    # Check 6: No duplicate canonical_names (critical verification from AC5)
    query6 = """
    MATCH (s:Skill)
    WHERE s.canonical_name IS NOT NULL AND s.canonical_name <> ''
    WITH s.canonical_name as cn, count(*) as c
    WHERE c > 1
    RETURN cn, c
    """
    result6 = await neo4j_repo.execute_query(query6)
    checks.append({
        "check": "No duplicate canonical_names",
        "passed": len(result6) == 0,
        "duplicates_found": len(result6),
        "examples": [{"cn": r["cn"], "count": r["c"]} for r in result6[:5]] if result6 else []
    })

    for check in checks:
        if "count" in check:
            logger.info(f"  {check['check']}: {check['count']}")
        elif "found" in check:
            logger.info(f"  {check['check']}: {check['found']}")
        elif "exists" in check:
            status = "✓" if check["exists"] else "✗"
            logger.info(f"  {check['check']}: {status}")
        elif "passed" in check:
            status = "✓ PASSED" if check["passed"] else f"✗ FAILED ({check['duplicates_found']} duplicates)"
            logger.info(f"  {check['check']}: {status}")

    return {"verification_checks": checks}


async def main():
    """Run the schema migration."""
    logger.info("Connecting to Neo4j...")

    neo4j_repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )

    try:
        await neo4j_repo.connect()
        logger.info("Connected to Neo4j successfully")

        # Run migrations
        migration = SchemaMigration(neo4j_repo)
        results = await migration.run_all_migrations()

        # Verify
        verification = await verify_migration(neo4j_repo)
        results["verification"] = verification

        # Print summary
        if results["status"] == "success":
            logger.info("\n[SUCCESS] All migrations completed successfully!")
        else:
            logger.warning(f"\n[WARNING] Some migrations failed. Check logs above.")

        return results

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        raise
    finally:
        await neo4j_repo.close()


if __name__ == "__main__":
    asyncio.run(main())
