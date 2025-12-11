# Implementation Phases

## Phase 7.1: Neo4j Schema Enhancements
**Files**: Neo4j schema, repository methods
**Effort**: 2-3 hours

Add derived relationships and stored metrics that enable visible improvements.

### 7.1.1 Enhanced Node Properties

```cypher
-- Skill node enhancements
(:Skill {
    id: STRING,
    name: STRING,
    canonical_name: STRING,       -- NEW: Normalized name (lowercase, trimmed)
    embedding: LIST<FLOAT>,
    centrality: FLOAT,            -- NEW: Eigenvector centrality (stored)
    demand_count: INTEGER,        -- NEW: Count of jobs requiring this skill
    co_occurrence_count: INTEGER, -- NEW: Count of CO_OCCURS_WITH edges
    created_at: DATETIME,
    updated_at: DATETIME
})

-- Job node enhancements
(:Job {
    job_id: STRING,
    job_title: STRING,
    company_name: STRING,
    location: STRING,
    embedding: LIST<FLOAT>,
    skill_count: INTEGER,         -- NEW: Count of required skills
    content_hash: STRING,         -- NEW: For deduplication
    created_at: DATETIME,
    updated_at: DATETIME
})
```

### 7.1.2 New Relationship: JOB_SIMILAR

```cypher
-- Job similarity based on shared skills (Jaccard)
(:Job)-[:SIMILAR_JOB {
    jaccard_score: FLOAT,         -- |shared_skills| / |union_skills|
    shared_count: INTEGER,        -- Number of shared skills
    computed_at: DATETIME
}]->(:Job)
```

### 7.1.3 Required Indexes

```cypher
-- Performance indexes (safe to create anytime)
CREATE INDEX skill_canonical IF NOT EXISTS FOR (s:Skill) ON (s.canonical_name);
CREATE INDEX skill_centrality IF NOT EXISTS FOR (s:Skill) ON (s.centrality);
CREATE INDEX skill_demand IF NOT EXISTS FOR (s:Skill) ON (s.demand_count);
CREATE INDEX job_content_hash IF NOT EXISTS FOR (j:Job) ON (j.content_hash);
CREATE INDEX job_similar_score IF NOT EXISTS FOR ()-[r:SIMILAR_JOB]-() ON (r.jaccard_score);
```

> ⚠️ **CRITICAL**: The unique constraint on `canonical_name` is NOT created here.
> It MUST be created by the migration script AFTER duplicates are merged.
> See section 7.1.4 for the correct migration order.

### 7.1.4 Migration Script (REQUIRED ORDER)

**New File**: `backend/scripts/migrate_neo4j_schema.py`

The migration MUST follow this exact order or it will fail:

```python
"""
Neo4j Schema Migration Script

CRITICAL: This script must be run ONCE before Phase 7 features are enabled.
The order of operations is non-negotiable:
  1. Set canonical_name on all skills
  2. Find and merge duplicate skills (move relationships)
  3. Delete duplicate skill nodes
  4. THEN add the unique constraint

Running steps out of order will cause constraint violations.
"""

import asyncio
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class Neo4jSchemaMigration:
    """Handles Phase 7 schema migration with proper ordering."""

    def __init__(self, neo4j_repo: "Neo4jRepository"):
        self.neo4j_repo = neo4j_repo

    async def run_full_migration(self) -> Dict:
        """
        Run complete migration in correct order.

        Returns summary of changes made.
        """
        results = {
            "skills_normalized": 0,
            "duplicates_merged": 0,
            "relationships_moved": 0,
            "constraint_created": False,
            "errors": []
        }

        try:
            # STEP 1: Set canonical_name on all skills
            logger.info("Step 1: Setting canonical names...")
            results["skills_normalized"] = await self._set_canonical_names()

            # STEP 2: Find duplicate skills (same canonical_name)
            logger.info("Step 2: Finding duplicates...")
            duplicates = await self._find_duplicates()
            logger.info(f"Found {len(duplicates)} duplicate groups")

            # STEP 3: Merge duplicates (move relationships to canonical node)
            logger.info("Step 3: Merging duplicates...")
            for canonical_name, skill_ids in duplicates:
                moved = await self._merge_duplicate_skills(canonical_name, skill_ids)
                results["relationships_moved"] += moved
                results["duplicates_merged"] += len(skill_ids) - 1

            # STEP 4: Delete duplicate nodes (keeping one per canonical)
            logger.info("Step 4: Deleting duplicate nodes...")
            await self._delete_duplicate_nodes()

            # STEP 5: NOW create the unique constraint
            logger.info("Step 5: Creating unique constraint...")
            await self._create_unique_constraint()
            results["constraint_created"] = True

            logger.info("Migration complete!")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            results["errors"].append(str(e))

        return results

    async def _set_canonical_names(self) -> int:
        """Set canonical_name on all skills that don't have one."""
        query = """
        MATCH (s:Skill)
        WHERE s.canonical_name IS NULL
        SET s.canonical_name = toLower(trim(
            replace(replace(replace(s.name, '.js', ''), '.', ''), '-', ' ')
        ))
        RETURN count(s) as updated
        """
        result = await self.neo4j_repo.execute_query(query)
        return result[0]["updated"] if result else 0

    async def _find_duplicates(self) -> List[Tuple[str, List[str]]]:
        """Find skills with the same canonical_name."""
        query = """
        MATCH (s:Skill)
        WITH s.canonical_name as canonical, collect(s.id) as ids
        WHERE size(ids) > 1
        RETURN canonical, ids
        """
        results = await self.neo4j_repo.execute_query(query)
        return [(r["canonical"], r["ids"]) for r in results]

    async def _merge_duplicate_skills(self, canonical_name: str, skill_ids: List[str]) -> int:
        """
        Merge duplicate skills into one canonical node.

        Keeps the first skill_id as canonical, moves all relationships to it.
        """
        canonical_id = skill_ids[0]
        duplicate_ids = skill_ids[1:]

        # Move REQUIRES relationships
        move_requires_query = """
        MATCH (j:Job)-[r:REQUIRES]->(dup:Skill)
        WHERE dup.id IN $duplicate_ids
        MATCH (canonical:Skill {id: $canonical_id})
        MERGE (j)-[:REQUIRES]->(canonical)
        DELETE r
        RETURN count(r) as moved
        """

        # Move CO_OCCURS_WITH relationships
        move_cooccurs_query = """
        MATCH (dup:Skill)-[r:CO_OCCURS_WITH]-(other:Skill)
        WHERE dup.id IN $duplicate_ids AND other.id <> $canonical_id
        MATCH (canonical:Skill {id: $canonical_id})
        MERGE (canonical)-[:CO_OCCURS_WITH]-(other)
        DELETE r
        RETURN count(r) as moved
        """

        # Move SIMILAR_TO relationships
        move_similar_query = """
        MATCH (dup:Skill)-[r:SIMILAR_TO]-(other:Skill)
        WHERE dup.id IN $duplicate_ids AND other.id <> $canonical_id
        MATCH (canonical:Skill {id: $canonical_id})
        MERGE (canonical)-[:SIMILAR_TO]-(other)
        DELETE r
        RETURN count(r) as moved
        """

        params = {"duplicate_ids": duplicate_ids, "canonical_id": canonical_id}

        r1 = await self.neo4j_repo.execute_query(move_requires_query, params)
        r2 = await self.neo4j_repo.execute_query(move_cooccurs_query, params)
        r3 = await self.neo4j_repo.execute_query(move_similar_query, params)

        total_moved = sum([
            r1[0]["moved"] if r1 else 0,
            r2[0]["moved"] if r2 else 0,
            r3[0]["moved"] if r3 else 0
        ])

        return total_moved

    async def _delete_duplicate_nodes(self):
        """Delete skill nodes that are now orphaned duplicates."""
        query = """
        MATCH (s:Skill)
        WHERE NOT (s)-[:REQUIRES|CO_OCCURS_WITH|SIMILAR_TO]-()
        AND s.canonical_name IS NOT NULL
        // Double-check: only delete if another skill with same canonical exists
        WITH s
        MATCH (other:Skill)
        WHERE other.canonical_name = s.canonical_name AND other <> s
        DETACH DELETE s
        RETURN count(s) as deleted
        """
        await self.neo4j_repo.execute_query(query)

    async def _create_unique_constraint(self):
        """Create unique constraint on canonical_name AFTER deduplication."""
        query = """
        CREATE CONSTRAINT skill_canonical_unique IF NOT EXISTS
        FOR (s:Skill) REQUIRE s.canonical_name IS UNIQUE
        """
        await self.neo4j_repo.execute_query(query)


# CLI entry point
async def main():
    from app.repositories.neo4j_repository import Neo4jRepository

    repo = Neo4jRepository()
    await repo.connect()

    migration = Neo4jSchemaMigration(repo)
    results = await migration.run_full_migration()

    print("Migration Results:")
    print(f"  Skills normalized: {results['skills_normalized']}")
    print(f"  Duplicates merged: {results['duplicates_merged']}")
    print(f"  Relationships moved: {results['relationships_moved']}")
    print(f"  Constraint created: {results['constraint_created']}")
    if results["errors"]:
        print(f"  Errors: {results['errors']}")

    await repo.close()


if __name__ == "__main__":
    asyncio.run(main())
```

> ⚠️ **NON-NEGOTIABLE**: Run this migration script ONCE before enabling Phase 7.
> The constraint will FAIL if duplicates exist. Always: normalize → dedupe → constraint.

---

## Phase 7.2: Enhanced Ingestion Pipeline
**Files**: `ingest.py`, `batch_processor.py`, new `skill_normalizer.py`, new `job_similarity_builder.py`
**Effort**: 4-5 hours

Transform ingestion from "dump data" to "intelligent enrichment".

### 7.2.1 Skill Name Normalization

**New File**: `backend/app/services/skill_normalizer.py`

```python
"""
Skill name normalization service.

Handles common variations:
- JS → JavaScript
- Python3 → Python
- React.js → React
- node.js → Node.js
- C# → CSharp (for indexing)

Maintains both:
- canonical_name: Lowercase normalized form for matching/indexing
- display_name: Human-readable form for UI display
"""

import re  # CRITICAL: Don't forget this import!
from typing import Tuple, Optional


# Maps raw input variations to canonical forms
SKILL_ALIASES = {
    # JavaScript ecosystem
    "js": "javascript",
    "javascript": "javascript",
    "es6": "javascript",
    "ecmascript": "javascript",
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "node.js": "nodejs",
    "node": "nodejs",
    "express.js": "express",
    "expressjs": "express",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "angular.js": "angular",
    "angularjs": "angular",

    # Python ecosystem
    "python3": "python",
    "python2": "python",
    "py": "python",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",

    # C family
    "c#": "csharp",          # CRITICAL: Include C# mapping
    "c sharp": "csharp",
    "csharp": "csharp",
    "c++": "cpp",
    "cplusplus": "cpp",
    "c plus plus": "cpp",
    "objective-c": "objectivec",
    "obj-c": "objectivec",

    # Databases
    "postgres": "postgresql",
    "psql": "postgresql",
    "postgresql": "postgresql",
    "mongo": "mongodb",
    "mongodb": "mongodb",
    "mysql": "mysql",
    "mssql": "sqlserver",
    "sql server": "sqlserver",
    "ms sql": "sqlserver",

    # Cloud
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "azure": "azure",
    "microsoft azure": "azure",

    # General tech
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "tf": "terraform",
    "ci/cd": "cicd",
    "ci cd": "cicd",
}

# Maps canonical names to preferred display names
DISPLAY_NAMES = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "vue": "Vue.js",
    "nodejs": "Node.js",
    "express": "Express.js",
    "nextjs": "Next.js",
    "angular": "Angular",
    "python": "Python",
    "django": "Django",
    "flask": "Flask",
    "fastapi": "FastAPI",
    "csharp": "C#",
    "cpp": "C++",
    "objectivec": "Objective-C",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "sqlserver": "SQL Server",
    "aws": "AWS",
    "gcp": "Google Cloud",
    "azure": "Azure",
    "kubernetes": "Kubernetes",
    "terraform": "Terraform",
    "cicd": "CI/CD",
    "machine learning": "Machine Learning",
    "artificial intelligence": "Artificial Intelligence",
    "deep learning": "Deep Learning",
    "natural language processing": "NLP",
    "computer vision": "Computer Vision",
}


class SkillNormalizer:
    """Normalize skill names to canonical form while preserving display names."""

    def __init__(self):
        self.aliases = SKILL_ALIASES
        self.display_names = DISPLAY_NAMES
        self._build_lookup()

    def _build_lookup(self):
        """Build reverse lookup for fast matching."""
        self.lookup = {}
        for alias, canonical in self.aliases.items():
            self.lookup[alias.lower().strip()] = canonical

    def normalize(self, skill_name: str) -> str:
        """
        Normalize a skill name to its canonical form.

        Args:
            skill_name: Raw skill name from CSV/API

        Returns:
            Canonical skill name (lowercase, normalized)
        """
        if not skill_name:
            return ""

        # Clean input - preserve # for C#
        cleaned = skill_name.lower().strip()
        # Only remove truly problematic characters, keep # + -
        cleaned = re.sub(r'[^\w\s\.\-\+\#]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Check alias lookup first
        if cleaned in self.lookup:
            return self.lookup[cleaned]

        # Return cleaned version if no alias
        return cleaned

    def get_display_name(self, canonical_name: str) -> str:
        """
        Get the preferred display name for a canonical skill.

        Args:
            canonical_name: The normalized canonical name

        Returns:
            Human-readable display name
        """
        return self.display_names.get(canonical_name, canonical_name.title())

    def get_canonical_and_display(self, skill_name: str) -> Tuple[str, str]:
        """
        Get both canonical (for matching) and display (for UI) names.

        Args:
            skill_name: Raw skill name input

        Returns:
            (canonical_name, display_name)
        """
        canonical = self.normalize(skill_name)
        display = self.get_display_name(canonical)
        return canonical, display

    def normalize_batch(self, skill_names: list) -> list:
        """
        Normalize a batch of skill names.

        Args:
            skill_names: List of raw skill names

        Returns:
            List of (canonical_name, display_name) tuples
        """
        return [self.get_canonical_and_display(name) for name in skill_names]
```

> ⚠️ **Common Bugs Fixed**:
> - Added `import re` (was missing)
> - Added C# → csharp mapping (was missing)
> - Added display name mapping for proper UI rendering
> - Preserves # character for C# detection

### 7.2.2 Job Deduplication

**Update**: `backend/app/services/batch_processor.py`

```python
import hashlib

def compute_job_hash(job_data: dict) -> str:
    """
    Compute content hash for job deduplication.

    Uses: title + company + location (normalized)
    """
    components = [
        job_data.get("job_title", "").lower().strip(),
        job_data.get("company_name", "").lower().strip(),
        job_data.get("location", "").lower().strip(),
    ]
    content = "|".join(components)
    return hashlib.sha256(content.encode()).hexdigest()[:32]

async def check_job_duplicate(self, job_hash: str) -> Optional[str]:
    """Check if job with this hash already exists."""
    query = """
    MATCH (j:Job {content_hash: $hash})
    RETURN j.job_id as job_id
    LIMIT 1
    """
    result = await self.neo4j_repo.execute_query(query, {"hash": job_hash})
    return result[0]["job_id"] if result else None
```

### 7.2.3 Auto-Enrichment After Ingestion

**Update**: `backend/app/services/ingestion_service.py`

```python
async def post_ingestion_enrichment(self, job_id: str) -> dict:
    """
    Run enrichment tasks after job ingestion.

    1. Update CO_OCCURS_WITH edges for new job's skills
    2. Update JOB_SIMILAR edges
    3. Update skill metrics (demand_count)
    4. Update job metrics (skill_count)
    """
    enrichment_results = {
        "co_occurrence_edges_created": 0,
        "job_similar_edges_created": 0,
        "skills_updated": 0,
    }

    # 1. Update co-occurrence for this job's skills
    co_builder = CoOccurrenceBuilder(self.neo4j_repo)
    co_result = await co_builder.update_for_job(job_id)
    enrichment_results["co_occurrence_edges_created"] = co_result.get("edges_created", 0)

    # 2. Update job similarity
    sim_builder = JobSimilarityBuilder(self.neo4j_repo)
    sim_result = await sim_builder.update_for_job(job_id)
    enrichment_results["job_similar_edges_created"] = sim_result.get("edges_created", 0)

    # 3. Update skill demand counts
    await self._update_skill_demand_counts(job_id)

    # 4. Update job skill count
    await self._update_job_skill_count(job_id)

    return enrichment_results

async def _update_skill_demand_counts(self, job_id: str):
    """Increment demand_count for all skills in this job."""
    query = """
    MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
    SET s.demand_count = COALESCE(s.demand_count, 0) + 1
    """
    await self.neo4j_repo.execute_query(query, {"job_id": job_id})

async def _update_job_skill_count(self, job_id: str):
    """Update skill_count on job node."""
    query = """
    MATCH (j:Job {job_id: $job_id})-[r:REQUIRES]->(:Skill)
    WITH j, count(r) as skill_count
    SET j.skill_count = skill_count
    """
    await self.neo4j_repo.execute_query(query, {"job_id": job_id})
```

### 7.2.4 Co-Occurrence Builder

**New File**: `backend/app/services/co_occurrence_builder.py`

```python
"""
Skill Co-Occurrence Builder Service.

Creates CO_OCCURS_WITH relationships between skills that appear together in jobs.

CRITICAL SEMANTICS:
- weight: Raw co-occurrence count (higher = more common together)
- cost: 1/weight (lower = stronger connection, for Dijkstra shortest path)

Use `weight` for: Centrality calculations, ranking
Use `cost` for: Shortest path (Dijkstra), distance calculations
"""

import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Skills that are too generic and flatten the graph - exclude from co-occurrence
SKILL_STOPLIST: Set[str] = {
    "communication",
    "teamwork",
    "problem solving",
    "microsoft office",
    "excel",
    "word",
    "powerpoint",
    "email",
    "written communication",
    "verbal communication",
    "time management",
    "organization",
    "detail oriented",
    "self motivated",
}


class CoOccurrenceBuilder:
    """Build and maintain skill co-occurrence relationships."""

    def __init__(self, neo4j_repo: "Neo4jRepository"):
        self.neo4j_repo = neo4j_repo
        self.min_co_occurrence = 2  # Minimum count to create edge
        self.stoplist = SKILL_STOPLIST

    async def build_all(self, clear_existing: bool = True) -> dict:
        """
        Build all CO_OCCURS_WITH relationships from scratch.

        IMPORTANT: Only creates edges where id(s1) < id(s2) to avoid duplicates.
        The relationship is treated as undirected in GDS with orientation:'UNDIRECTED'.
        """
        if clear_existing:
            await self._clear_existing()

        query = """
        // Find skill pairs that co-occur in jobs
        MATCH (j:Job)-[:REQUIRES]->(s1:Skill),
              (j)-[:REQUIRES]->(s2:Skill)
        WHERE id(s1) < id(s2)  // Enforce ordering to avoid duplicates
          AND NOT toLower(s1.canonical_name) IN $stoplist
          AND NOT toLower(s2.canonical_name) IN $stoplist

        // Count co-occurrences
        WITH s1, s2, count(DISTINCT j) as weight
        WHERE weight >= $min_count

        // Create relationship with both weight and cost
        MERGE (s1)-[r:CO_OCCURS_WITH]->(s2)
        SET r.weight = weight,
            r.cost = 1.0 / weight,  // Inverse for Dijkstra
            r.updated_at = datetime()

        RETURN count(r) as created
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "min_count": self.min_co_occurrence,
                "stoplist": list(self.stoplist)
            },
            timeout=300.0
        )

        return {
            "status": "completed",
            "edges_created": result[0]["created"] if result else 0
        }

    async def update_for_job(self, job_id: str) -> dict:
        """
        Incrementally update CO_OCCURS_WITH for a single job's skills.

        Safe for use during ingestion - only affects skills in this job.
        """
        query = """
        // Get skills for this job
        MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
        WHERE NOT toLower(s.canonical_name) IN $stoplist
        WITH collect(s) as skills

        // For each pair of skills
        UNWIND skills as s1
        UNWIND skills as s2
        WITH s1, s2 WHERE id(s1) < id(s2)  // Enforce ordering

        // Find all jobs where both skills appear (for accurate count)
        MATCH (job:Job)-[:REQUIRES]->(s1),
              (job)-[:REQUIRES]->(s2)
        WITH s1, s2, count(DISTINCT job) as weight
        WHERE weight >= $min_count

        // Create or update relationship
        MERGE (s1)-[r:CO_OCCURS_WITH]->(s2)
        SET r.weight = weight,
            r.cost = 1.0 / weight,
            r.updated_at = datetime()

        RETURN count(r) as updated
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "job_id": job_id,
                "min_count": self.min_co_occurrence,
                "stoplist": list(self.stoplist)
            }
        )

        return {"edges_created": result[0]["updated"] if result else 0}

    async def _clear_existing(self):
        """Remove all existing CO_OCCURS_WITH relationships."""
        await self.neo4j_repo.execute_query(
            "MATCH ()-[r:CO_OCCURS_WITH]->() DELETE r"
        )

    async def get_co_occurring_skills(
        self, skill_id: str, limit: int = 20
    ) -> list:
        """Get skills that frequently co-occur with a given skill."""
        query = """
        MATCH (s:Skill {id: $skill_id})-[r:CO_OCCURS_WITH]-(other:Skill)
        RETURN other.id as skill_id,
               other.name as name,
               other.canonical_name as canonical,
               r.weight as co_occurrence_count,
               r.cost as path_cost
        ORDER BY r.weight DESC
        LIMIT $limit
        """
        return await self.neo4j_repo.execute_query(
            query, {"skill_id": skill_id, "limit": limit}
        )
```

> 📊 **Weight vs Cost Semantics**:
> - **weight**: Use for ranking, centrality (higher = stronger connection)
> - **cost**: Use for Dijkstra shortest path (lower = closer skills)
>
> Example: If Python and Django co-occur in 50 jobs:
> - `weight = 50` → High importance for centrality
> - `cost = 0.02` → Low distance for path finding

### 7.2.5 Job Similarity Builder

**New File**: `backend/app/services/job_similarity_builder.py`

```python
"""
Job similarity builder service.

Creates SIMILAR_JOB relationships based on shared skills using GDS Node Similarity.

CRITICAL: Uses GDS nodeSimilarity algorithm to avoid O(n²) explosion.
With 88k jobs, naive pairwise comparison is not feasible.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class JobSimilarityBuilder:
    """Build and maintain job similarity relationships using GDS."""

    def __init__(self, neo4j_repo: "Neo4jRepository"):
        self.neo4j_repo = neo4j_repo
        self.similarity_cutoff = 0.2    # Minimum Jaccard score
        self.top_k = 20                 # Max similar jobs per job
        self.degree_cutoff = 1          # Min skills required

    async def check_gds_available(self) -> bool:
        """Check if GDS plugin is installed."""
        try:
            result = await self.neo4j_repo.execute_query(
                "RETURN gds.version() as version"
            )
            logger.info(f"GDS available: {result[0]['version']}")
            return True
        except Exception:
            logger.warning("GDS not available - job similarity limited")
            return False

    async def build_all_gds(self, clear_existing: bool = True) -> dict:
        """
        Build all SIMILAR_JOB relationships using GDS nodeSimilarity.

        This is the ONLY recommended way to build similarity at scale.
        Uses GDS's optimized algorithm that handles large graphs efficiently.

        Algorithm: Jaccard similarity based on shared Skill neighbors.
        """
        if clear_existing:
            await self._clear_existing()

        # Check GDS availability
        if not await self.check_gds_available():
            return {
                "status": "failed",
                "error": "GDS not installed. Use update_for_job() for incremental updates.",
                "edges_created": 0
            }

        # Step 1: Create in-memory graph projection
        projection_query = """
        CALL gds.graph.project(
            'job-skill-graph',
            ['Job', 'Skill'],
            {
                REQUIRES: {
                    type: 'REQUIRES',
                    orientation: 'UNDIRECTED'
                }
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        try:
            projection_result = await self.neo4j_repo.execute_query(projection_query)
            logger.info(f"Graph projected: {projection_result}")
        except Exception as e:
            # Graph might already exist, drop and retry
            await self.neo4j_repo.execute_query(
                "CALL gds.graph.drop('job-skill-graph', false)"
            )
            projection_result = await self.neo4j_repo.execute_query(projection_query)

        # Step 2: Run nodeSimilarity and write results
        similarity_query = """
        CALL gds.nodeSimilarity.write('job-skill-graph', {
            similarityCutoff: $cutoff,
            topK: $top_k,
            degreeCutoff: $degree_cutoff,
            writeRelationshipType: 'SIMILAR_JOB',
            writeProperty: 'jaccard_score'
        })
        YIELD nodesCompared, relationshipsWritten, similarityDistribution
        RETURN nodesCompared, relationshipsWritten, similarityDistribution
        """

        result = await self.neo4j_repo.execute_query(
            similarity_query,
            {
                "cutoff": self.similarity_cutoff,
                "top_k": self.top_k,
                "degree_cutoff": self.degree_cutoff
            },
            timeout=600.0  # 10 min timeout for large graphs
        )

        # Step 3: Add computed_at timestamp to relationships
        await self.neo4j_repo.execute_query("""
            MATCH ()-[r:SIMILAR_JOB]->()
            WHERE r.computed_at IS NULL
            SET r.computed_at = datetime()
        """)

        # Step 4: Clean up projection
        await self.neo4j_repo.execute_query(
            "CALL gds.graph.drop('job-skill-graph', false)"
        )

        edges_created = result[0]["relationshipsWritten"] if result else 0

        return {
            "status": "completed",
            "edges_created": edges_created,
            "nodes_compared": result[0]["nodesCompared"] if result else 0,
            "algorithm": "gds.nodeSimilarity"
        }

    async def update_for_job(self, job_id: str) -> dict:
        """
        Incrementally update SIMILAR_JOB for a single new job.

        This is safe to use without GDS for single-job updates.
        Only computes similarity for ONE job, not O(n²).
        """
        query = """
        // Find similar jobs to this one
        MATCH (j1:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
        WHERE j1 <> j2

        WITH j1, j2, count(DISTINCT s) as shared_count
        WHERE shared_count >= 2

        MATCH (j1)-[:REQUIRES]->(s1:Skill)
        WITH j1, j2, shared_count, count(DISTINCT s1) as j1_count
        MATCH (j2)-[:REQUIRES]->(s2:Skill)
        WITH j1, j2, shared_count, j1_count, count(DISTINCT s2) as j2_count

        WITH j1, j2, shared_count,
             toFloat(shared_count) / (j1_count + j2_count - shared_count) as jaccard
        WHERE jaccard >= $min_jaccard

        ORDER BY jaccard DESC
        LIMIT $max_per_job

        MERGE (j1)-[r:SIMILAR_JOB]->(j2)
        SET r.jaccard_score = jaccard,
            r.shared_count = shared_count,
            r.computed_at = datetime()

        RETURN count(r) as created
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "job_id": job_id,
                "min_jaccard": self.similarity_cutoff,
                "max_per_job": self.top_k
            }
        )

        return {"edges_created": result[0]["created"] if result else 0}

    async def _clear_existing(self):
        """Remove all existing SIMILAR_JOB relationships."""
        await self.neo4j_repo.execute_query(
            "MATCH ()-[r:SIMILAR_JOB]->() DELETE r"
        )

    async def get_similar_jobs(self, job_id: str, limit: int = 10) -> list:
        """Get most similar jobs to a given job."""
        query = """
        MATCH (j:Job {job_id: $job_id})-[r:SIMILAR_JOB]-(j2:Job)
        RETURN j2.job_id as job_id,
               j2.job_title as title,
               j2.company_name as company,
               r.jaccard_score as similarity,
               r.shared_count as shared_skills
        ORDER BY r.jaccard_score DESC
        LIMIT $limit
        """
        return await self.neo4j_repo.execute_query(
            query, {"job_id": job_id, "limit": limit}
        )
```

> ⚠️ **CRITICAL**: The `build_all_gds()` method REQUIRES Neo4j GDS plugin.
> If GDS is not installed, only use `update_for_job()` for incremental updates.
> Never attempt naive O(n²) pairwise comparison on large graphs.

### 7.2.5 Ingestion Status Enhancement

**Update**: `backend/app/api/ingest.py`

Add detailed progress tracking:

```python
@router.get("/status/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(job_id: str):
    """
    Get detailed ingestion status with enrichment progress.

    Returns:
    - nodes_created, nodes_updated, duplicates_skipped
    - edges_created (REQUIRES, CO_OCCURS_WITH, SIMILAR_JOB)
    - enrichment_status (pending, running, completed)
    - warnings (validation issues)
    """
    # ... implementation
```

---

## Phase 7.3: Query Pipeline Integration
**Files**: `graph_traversal.py`, `context_construction.py`, new `network_enrichment.py`
**Effort**: 6-8 hours

This is the CORE change that makes queries better.

### 7.3.1 New Intent Types

**Update**: `backend/app/agents/nodes/query_understanding.py`

```python
# Add new intent patterns
INTENT_PATTERNS = {
    # Existing
    "skill_requirement": [
        r"what skills.*(need|require|for)",
        r"skills.*(for|to become)",
    ],
    "career_path": [
        r"how (do|can) I (become|transition|move)",
        r"path (to|from|between)",
    ],

    # NEW: Career Transition (explicit from→to)
    "career_transition": [
        r"(from|as a?)\s+(\w+(?:\s+\w+)?)\s+(to|→|->)\s+(\w+(?:\s+\w+)?)",
        r"transition.*from.*to",
        r"switch.*from.*to",
        r"move.*from.*to",
    ],

    # NEW: Skill Bridge (skill A to skill B)
    "skill_bridge": [
        r"(from|learn)\s+(\w+)\s+(to|→|->)\s+(\w+)",
        r"path.*between.*skills?",
        r"how.*(\w+).*relate.*(\w+)",
    ],

    # NEW: Skill Importance
    "skill_importance": [
        r"(most|top|key|important|essential)\s+skills?",
        r"skills?.*most (important|valuable|in demand)",
        r"what skills? matter",
    ],

    # NEW: Job Similarity
    "job_similarity": [
        r"(similar|like|closest|related)\s+(jobs?|roles?|positions?)",
        r"jobs? (similar|like|close) to",
        r"what.*jobs?.*similar",
    ],
}
```

### 7.3.2 New Pipeline Node: Network Enrichment

**New File**: `backend/app/agents/nodes/network_enrichment.py`

```python
"""
Network Enrichment Node

Augments graph traversal results with network metrics:
- Skill paths (for CAREER_TRANSITION, SKILL_BRIDGE)
- Job similarity (for JOB_SIMILARITY)
- Centrality rankings (for SKILL_IMPORTANCE)
- Job closeness scores

This node runs AFTER graph_traversal and BEFORE context_construction.

IMPORTANT: This implementation uses EXISTING Phase 6 methods only.
Non-existent methods have been removed or replaced with direct queries.
"""

import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def network_enrichment_node(state: "GraphRAGState") -> Dict[str, Any]:
    """
    Enrich state with network metrics based on detected intents.

    Adds to state.metadata:
    - skill_paths: List of computed skill bridge paths
    - similar_jobs: List of similar jobs with scores
    - top_skills: Centrality-ranked skills
    - job_closeness: User skill → job closeness breakdown
    - network_facts: Structured facts for LLM context
    """
    intents = state.intents or [state.intent]
    entities = state.entities or []

    network_data = {
        "skill_paths": [],
        "similar_jobs": [],
        "top_skills": [],
        "job_closeness": None,
        "network_facts": [],
        "enrichment_applied": False,
        "gds_available": False,
    }

    # Get neo4j_repo from the langgraph service (injected properly)
    # NOTE: The LangGraphService must inject neo4j_repo into state.metadata
    neo4j_repo = state.metadata.get("neo4j_repo")
    if not neo4j_repo:
        logger.warning("neo4j_repo not found in state.metadata - skipping enrichment")
        network_data["network_facts"].append({
            "type": "error",
            "message": "Database connection not available for network enrichment"
        })
        state.metadata["network_enrichment"] = network_data
        return {"metadata": state.metadata}

    try:
        # Check if GDS is available (simple check)
        gds_available = await _check_gds_available(neo4j_repo)
        network_data["gds_available"] = gds_available

        if not gds_available:
            network_data["network_facts"].append({
                "type": "info",
                "message": "Using stored metrics (GDS not available for live computation)"
            })

        # CAREER_TRANSITION or SKILL_BRIDGE: Compute skill paths
        if any(i in intents for i in ["career_transition", "skill_bridge", "transition_path"]):
            paths = await _compute_skill_paths(state, neo4j_repo, gds_available)
            network_data["skill_paths"] = paths
            if paths:
                network_data["enrichment_applied"] = True

        # JOB_SIMILARITY: Find similar jobs
        if "job_similarity" in intents:
            job_entities = [e for e in entities if e.get("type") in ["job", "role"]]
            if job_entities:
                similar = await _get_similar_jobs(job_entities[0], neo4j_repo)
                network_data["similar_jobs"] = similar
                if similar:
                    network_data["enrichment_applied"] = True

        # SKILL_IMPORTANCE: Get centrality rankings from STORED metrics
        if "skill_importance" in intents:
            top_skills = await _get_top_skills_by_centrality(neo4j_repo, limit=20)
            network_data["top_skills"] = top_skills
            if top_skills:
                network_data["enrichment_applied"] = True
                network_data["network_facts"].append({
                    "type": "centrality",
                    "message": f"Top {len(top_skills)} skills by network importance",
                    "data": [s["skill"] for s in top_skills[:5]]
                })

        # JOB closeness - MVP approach: Extract skills from query text
        user_skills = _extract_user_skills_mvp(state.user_query, entities)
        job_entities = [e for e in entities if e.get("type") in ["job", "role"]]

        if user_skills and job_entities:
            closeness = await _calculate_job_closeness_simple(
                neo4j_repo=neo4j_repo,
                user_skills=user_skills,
                job_title=job_entities[0].get("value", "")
            )
            if closeness:
                network_data["job_closeness"] = closeness
                network_data["enrichment_applied"] = True
                network_data["network_facts"].append({
                    "type": "job_closeness",
                    "message": f"Job fit analysis: {closeness['overall_closeness']:.1%} match",
                    "skills_have": closeness.get("skills_already_have", []),
                    "skills_need": closeness.get("skills_to_learn", [])
                })

    except Exception as e:
        logger.error(f"Network enrichment failed: {e}", exc_info=True)
        network_data["network_facts"].append({
            "type": "error",
            "message": f"Network enrichment error (continuing without): {str(e)}"
        })

    # Update state metadata
    state.metadata["network_enrichment"] = network_data

    return {"metadata": state.metadata}


async def _check_gds_available(neo4j_repo) -> bool:
    """Check if GDS plugin is installed."""
    try:
        result = await neo4j_repo.execute_query("RETURN gds.version() as v")
        return bool(result)
    except Exception:
        return False


async def _compute_skill_paths(state, neo4j_repo, gds_available: bool) -> List[Dict]:
    """
    Compute skill bridge paths from entities.

    Uses GDS Dijkstra if available, falls back to simple BFS traversal.
    """
    paths = []
    entities = state.entities or []
    skills = [e for e in entities if e.get("type") == "skill"]

    if len(skills) < 2:
        return paths

    for i, skill1 in enumerate(skills[:-1]):
        for skill2 in skills[i+1:]:
            try:
                skill1_name = skill1.get("value", "").lower()
                skill2_name = skill2.get("value", "").lower()

                if gds_available:
                    # Use GDS Dijkstra with cost property
                    path_result = await _dijkstra_path(neo4j_repo, skill1_name, skill2_name)
                else:
                    # Fallback: Simple BFS traversal via CO_OCCURS_WITH
                    path_result = await _bfs_path(neo4j_repo, skill1_name, skill2_name)

                if path_result and path_result.get("path_exists"):
                    paths.append({
                        "from": skill1.get("value"),
                        "to": skill2.get("value"),
                        "path": path_result.get("path_names", []),
                        "distance": path_result.get("total_distance"),
                        "closeness": path_result.get("closeness"),
                        "algorithm": path_result.get("algorithm")
                    })
            except Exception as e:
                logger.warning(f"Path computation failed for {skill1} -> {skill2}: {e}")

    return paths


async def _dijkstra_path(neo4j_repo, skill1_name: str, skill2_name: str) -> Optional[Dict]:
    """Compute shortest path using GDS Dijkstra with cost property."""
    query = """
    MATCH (a:Skill), (b:Skill)
    WHERE toLower(a.canonical_name) = $skill1 AND toLower(b.canonical_name) = $skill2
    CALL gds.shortestPath.dijkstra.stream({
        sourceNode: id(a),
        targetNode: id(b),
        relationshipWeightProperty: 'cost'  // CRITICAL: Use cost, not weight
    })
    YIELD nodeIds, totalCost
    RETURN [n IN nodeIds | gds.util.asNode(n).name] AS path,
           totalCost,
           1.0 / (1.0 + totalCost) AS closeness
    """
    result = await neo4j_repo.execute_query(query, {"skill1": skill1_name, "skill2": skill2_name})

    if result and result[0].get("path"):
        return {
            "path_exists": True,
            "path_names": result[0]["path"],
            "total_distance": result[0]["totalCost"],
            "closeness": result[0]["closeness"],
            "algorithm": "gds_dijkstra"
        }
    return None


async def _bfs_path(neo4j_repo, skill1_name: str, skill2_name: str, max_depth: int = 4) -> Optional[Dict]:
    """Fallback: Simple BFS path via CO_OCCURS_WITH (no GDS required)."""
    query = """
    MATCH (a:Skill), (b:Skill)
    WHERE toLower(a.canonical_name) = $skill1 AND toLower(b.canonical_name) = $skill2
    MATCH path = shortestPath((a)-[:CO_OCCURS_WITH*1..4]-(b))
    RETURN [n IN nodes(path) | n.name] AS path_names,
           length(path) AS hops
    LIMIT 1
    """
    result = await neo4j_repo.execute_query(
        query, {"skill1": skill1_name, "skill2": skill2_name}
    )

    if result and result[0].get("path_names"):
        hops = result[0]["hops"]
        return {
            "path_exists": True,
            "path_names": result[0]["path_names"],
            "total_distance": hops,
            "closeness": 1.0 / (1.0 + hops),
            "algorithm": "bfs_fallback"
        }
    return None


async def _get_similar_jobs(job_entity, neo4j_repo) -> List[Dict]:
    """Get similar jobs using stored SIMILAR_JOB relationships."""
    job_value = job_entity.get("value", "")

    query = """
    MATCH (j:Job)
    WHERE toLower(j.job_title) CONTAINS toLower($title)
    WITH j LIMIT 1
    MATCH (j)-[r:SIMILAR_JOB]-(j2:Job)
    RETURN j2.job_id as job_id,
           j2.job_title as title,
           j2.company_name as company,
           r.jaccard_score as similarity
    ORDER BY r.jaccard_score DESC
    LIMIT 10
    """

    result = await neo4j_repo.execute_query(query, {"title": job_value})
    return result or []


async def _get_top_skills_by_centrality(neo4j_repo, limit: int = 20) -> List[Dict]:
    """Get top skills by STORED centrality (computed during ingestion)."""
    query = """
    MATCH (s:Skill)
    WHERE s.centrality IS NOT NULL
    RETURN s.name as skill,
           s.canonical_name as canonical,
           s.centrality as score,
           s.demand_count as demand
    ORDER BY s.centrality DESC
    LIMIT $limit
    """
    result = await neo4j_repo.execute_query(query, {"limit": limit})
    return result or []


def _extract_user_skills_mvp(query: str, entities: List[Dict]) -> List[str]:
    """
    MVP: Extract user's skills from query text patterns.

    Looks for patterns like:
    - "I know Python and SQL"
    - "I have experience with React"
    - "My skills include JavaScript"

    NOTE: User profiles are Phase 2. This is the MVP workaround.
    """
    user_skills = []

    # Pattern 1: "I know/have/learned X, Y, Z"
    patterns = [
        r"I (?:know|have|learned|use|work with)\s+(.+?)(?:\.|,\s*(?:and|but)|$)",
        r"(?:my skills?|experience) (?:include|are|with)\s+(.+?)(?:\.|,\s*(?:and|but)|$)",
        r"I(?:'m| am) (?:familiar|experienced|proficient) (?:with|in)\s+(.+?)(?:\.|,\s*(?:and|but)|$)",
    ]

    query_lower = query.lower()

    for pattern in patterns:
        matches = re.findall(pattern, query_lower, re.IGNORECASE)
        for match in matches:
            # Split by common delimiters
            skills = re.split(r',\s*|\s+and\s+|\s*&\s*', match)
            user_skills.extend([s.strip() for s in skills if s.strip()])

    # Also include skills from entities that were extracted from the query
    # (not from user_profile, which doesn't exist yet)
    for entity in entities:
        if entity.get("type") == "skill":
            # Only include if it seems like user's skill (mentioned positively)
            skill_value = entity.get("value", "")
            if skill_value and skill_value.lower() not in [s.lower() for s in user_skills]:
                # Check if this skill is mentioned in "I know" context
                if any(p in query_lower for p in ["i know", "i have", "my skill", "experience with"]):
                    user_skills.append(skill_value)

    return list(set(user_skills))


async def _calculate_job_closeness_simple(
    neo4j_repo,
    user_skills: List[str],
    job_title: str
) -> Optional[Dict]:
    """
    Simple job closeness calculation using direct query.

    Returns what skills user has vs needs for the job.
    """
    if not user_skills or not job_title:
        return None

    # Get required skills for the job
    query = """
    MATCH (j:Job)-[:REQUIRES]->(s:Skill)
    WHERE toLower(j.job_title) CONTAINS toLower($job_title)
    RETURN collect(DISTINCT s.canonical_name) as required_skills,
           collect(DISTINCT s.name) as required_skill_names
    LIMIT 1
    """

    result = await neo4j_repo.execute_query(query, {"job_title": job_title})

    if not result or not result[0].get("required_skills"):
        return None

    required_skills = set(result[0]["required_skills"])
    required_names = result[0]["required_skill_names"]

    # Normalize user skills for comparison
    user_skills_normalized = set(s.lower().strip() for s in user_skills)

    # Calculate overlap
    skills_have = [s for s in required_names if s.lower() in user_skills_normalized]
    skills_need = [s for s in required_names if s.lower() not in user_skills_normalized]

    if not required_skills:
        return None

    overall_closeness = len(skills_have) / len(required_skills)

    return {
        "overall_closeness": overall_closeness,
        "skills_already_have": skills_have,
        "skills_to_learn": skills_need,
        "total_required": len(required_skills),
        "matching_count": len(skills_have)
    }
```

> ⚠️ **Issues Fixed**:
> - Removed non-existent `get_capabilities()` method
> - Removed non-existent `calculate_enhanced_job_closeness()` method
> - Fixed brittle repo injection - now validates neo4j_repo exists
> - Added MVP user skill extraction (doesn't require user profiles)
> - Added GDS check with BFS fallback for path computation
> - Uses STORED centrality instead of live computation

### 7.3.3 Enhanced Graph Traversal with Scoring

**Update**: `backend/app/agents/nodes/graph_traversal.py`

Add hybrid retrieval scoring:

```python
async def scored_graph_traversal(state: "GraphRAGState") -> Dict[str, Any]:
    """
    Enhanced graph traversal with hybrid scoring.

    Score = 0.50 * vector_similarity
          + 0.30 * centrality_normalized
          + 0.20 * demand_normalized

    Returns top-k nodes by combined score.
    """
    vector_results = state.vector_results or []

    # Get IDs of vector results
    skill_ids = [r["id"] for r in vector_results if r.get("node_type") == "Skill"]
    job_ids = [r["id"] for r in vector_results if r.get("node_type") == "Job"]

    # Fetch centrality and demand scores for skills
    scored_skills = await _score_skills(skill_ids, state.metadata.get("neo4j_repo"))
    scored_jobs = await _score_jobs(job_ids, state.metadata.get("neo4j_repo"))

    # Merge with vector scores
    final_results = _merge_scores(vector_results, scored_skills, scored_jobs)

    # Apply caps
    MAX_NODES = 40
    MIN_SKILLS = 5
    MIN_JOBS = 5

    # Ensure diversity
    skills = [r for r in final_results if r.get("node_type") == "Skill"][:max(MIN_SKILLS, MAX_NODES//2)]
    jobs = [r for r in final_results if r.get("node_type") == "Job"][:max(MIN_JOBS, MAX_NODES//2)]

    return {
        "graph_context": skills + jobs,
        "metadata": {
            **state.metadata,
            "retrieval_scoring": "hybrid",
            "nodes_selected": len(skills) + len(jobs)
        }
    }


async def _score_skills(skill_ids: List[str], neo4j_repo) -> Dict[str, Dict]:
    """Fetch and normalize skill scores."""
    if not skill_ids:
        return {}

    query = """
    MATCH (s:Skill)
    WHERE s.id IN $ids
    RETURN s.id as id,
           COALESCE(s.centrality, 0) as centrality,
           COALESCE(s.demand_count, 0) as demand
    """

    results = await neo4j_repo.execute_query(query, {"ids": skill_ids})

    # Normalize scores
    max_centrality = max((r["centrality"] for r in results), default=1) or 1
    max_demand = max((r["demand"] for r in results), default=1) or 1

    return {
        r["id"]: {
            "centrality_norm": r["centrality"] / max_centrality,
            "demand_norm": r["demand"] / max_demand
        }
        for r in results
    }
```

### 7.3.4 Update Workflow Graph

**Update**: `backend/app/agents/graph.py`

Add network_enrichment node to pipeline:

```python
from app.agents.nodes.network_enrichment import network_enrichment_node

def create_rag_workflow():
    """Create the RAG workflow with network enrichment."""

    workflow = StateGraph(GraphRAGState)

    # Existing nodes
    workflow.add_node("query_understanding", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)

    # NEW: Network enrichment node
    workflow.add_node("network_enrichment", network_enrichment_node)

    # Existing nodes
    workflow.add_node("context_construction", context_construction_node)
    workflow.add_node("response_generation", response_generation_node)

    # Updated edges
    workflow.add_edge("query_understanding", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")
    workflow.add_edge("graph_traversal", "network_enrichment")  # NEW
    workflow.add_edge("network_enrichment", "context_construction")  # NEW
    workflow.add_edge("context_construction", "response_generation")

    workflow.set_entry_point("query_understanding")
    workflow.set_finish_point("response_generation")

    return workflow.compile()
```

### 7.3.5 Enhanced Context Construction

**Update**: `backend/app/agents/nodes/context_construction.py`

Add network facts to LLM context:

```python
def _build_network_section(state: "GraphRAGState") -> str:
    """Build network insights section for context."""
    network_data = state.metadata.get("network_enrichment", {})

    if not network_data.get("enrichment_applied"):
        return ""

    sections = []

    # Skill Paths
    if network_data.get("skill_paths"):
        sections.append("## Skill Bridge Paths")
        for path in network_data["skill_paths"]:
            path_str = " → ".join(path["path"])
            sections.append(f"- **{path['from']}** to **{path['to']}**: {path_str}")
            sections.append(f"  - Closeness: {path['closeness']:.2f}")

    # Similar Jobs
    if network_data.get("similar_jobs"):
        sections.append("\n## Similar Jobs")
        for job in network_data["similar_jobs"][:5]:
            sections.append(f"- {job['title']} at {job['company']} (similarity: {job['similarity']:.1%})")

    # Top Skills by Importance
    if network_data.get("top_skills"):
        sections.append("\n## Top Skills by Market Importance")
        for skill in network_data["top_skills"][:10]:
            sections.append(f"- {skill['skill']} (centrality: {skill['score']:.3f})")

    # Job Closeness
    if network_data.get("job_closeness"):
        jc = network_data["job_closeness"]
        sections.append(f"\n## Job Fit Analysis: {jc['overall_closeness']:.1%} Match")
        sections.append(f"**Skills you already have**: {', '.join(jc.get('skills_already_have', []))}")
        sections.append(f"**Skills to develop**: {', '.join(jc.get('skills_to_learn', []))}")

    # Network Facts
    if network_data.get("network_facts"):
        sections.append("\n## Network Analysis Notes")
        for fact in network_data["network_facts"]:
            if fact["type"] == "warning":
                sections.append(f"⚠️ {fact['message']}")
            else:
                sections.append(f"📊 {fact['message']}")

    return "\n".join(sections)
```

---

## Phase 7.4: Enhanced Query Response Schema
**Files**: `query.py`, models
**Effort**: 2-3 hours

Update API response to include network data for frontend.

### 7.4.1 Updated Response Model

**Update**: `backend/app/models/query.py`

```python
class NetworkInsights(BaseModel):
    """Network-derived insights included in query response."""

    skill_paths: Optional[List[SkillPath]] = Field(
        default=None,
        description="Computed skill bridge paths"
    )
    similar_jobs: Optional[List[SimilarJob]] = Field(
        default=None,
        description="Jobs similar to queried job"
    )
    top_skills: Optional[List[SkillRanking]] = Field(
        default=None,
        description="Top skills by centrality"
    )
    job_closeness: Optional[JobClosenessResult] = Field(
        default=None,
        description="User-to-job skill fit analysis"
    )


class QueryResponse(BaseModel):
    """Enhanced query response with network insights."""

    query: str
    response: str
    sources: List[Source]
    processing_time_ms: int
    metadata: Dict[str, Any]

    # NEW: Network insights for frontend
    network_insights: Optional[NetworkInsights] = Field(
        default=None,
        description="Network-derived insights"
    )
```

---

## Phase 7.5: Frontend Integration
**Files**: React components
**Effort**: 3-4 hours

Create collapsible panels to display network insights.

### 7.5.1 Network Insights Panel Component

**New File**: `frontend/src/components/NetworkInsightsPanel.tsx`

```tsx
import React, { useState } from 'react';
import { ChevronDown, ChevronUp, GitBranch, Briefcase, Star, Target } from 'lucide-react';

interface NetworkInsightsPanelProps {
  insights: {
    skill_paths?: SkillPath[];
    similar_jobs?: SimilarJob[];
    top_skills?: SkillRanking[];
    job_closeness?: JobClosenessResult;
  };
}

export const NetworkInsightsPanel: React.FC<NetworkInsightsPanelProps> = ({ insights }) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    paths: false,
    jobs: false,
    skills: false,
    closeness: true, // Default open
  });

  if (!insights) return null;

  const toggle = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="mt-4 space-y-2 border-t pt-4">
      <h3 className="text-sm font-semibold text-gray-500 uppercase">Network Insights</h3>

      {/* Skill Bridge Paths */}
      {insights.skill_paths?.length > 0 && (
        <CollapsibleSection
          title="Skill Bridge Paths"
          icon={<GitBranch className="w-4 h-4" />}
          expanded={expanded.paths}
          onToggle={() => toggle('paths')}
        >
          {insights.skill_paths.map((path, i) => (
            <div key={i} className="mb-2 p-2 bg-gray-50 rounded">
              <div className="flex items-center gap-1 text-sm">
                {path.path.map((skill, j) => (
                  <React.Fragment key={j}>
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                      {skill}
                    </span>
                    {j < path.path.length - 1 && <span className="text-gray-400">→</span>}
                  </React.Fragment>
                ))}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Closeness: {(path.closeness * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </CollapsibleSection>
      )}

      {/* Similar Jobs */}
      {insights.similar_jobs?.length > 0 && (
        <CollapsibleSection
          title="Similar Jobs"
          icon={<Briefcase className="w-4 h-4" />}
          expanded={expanded.jobs}
          onToggle={() => toggle('jobs')}
        >
          <ul className="space-y-1">
            {insights.similar_jobs.slice(0, 5).map((job, i) => (
              <li key={i} className="flex justify-between text-sm">
                <span>{job.title} at {job.company}</span>
                <span className="text-green-600">{(job.similarity * 100).toFixed(0)}% match</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}

      {/* Top Skills */}
      {insights.top_skills?.length > 0 && (
        <CollapsibleSection
          title="Top Skills by Market Importance"
          icon={<Star className="w-4 h-4" />}
          expanded={expanded.skills}
          onToggle={() => toggle('skills')}
        >
          <div className="flex flex-wrap gap-1">
            {insights.top_skills.slice(0, 10).map((skill, i) => (
              <span
                key={i}
                className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded"
              >
                {skill.skill}
              </span>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Job Closeness */}
      {insights.job_closeness && (
        <CollapsibleSection
          title={`Job Fit: ${(insights.job_closeness.overall_closeness * 100).toFixed(0)}% Match`}
          icon={<Target className="w-4 h-4" />}
          expanded={expanded.closeness}
          onToggle={() => toggle('closeness')}
        >
          <div className="space-y-2">
            {insights.job_closeness.skills_already_have?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-green-700">Skills you have:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {insights.job_closeness.skills_already_have.map((skill, i) => (
                    <span key={i} className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                      ✓ {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {insights.job_closeness.skills_to_learn?.length > 0 && (
              <div>
                <span className="text-xs font-medium text-orange-700">Skills to develop:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {insights.job_closeness.skills_to_learn.map((skill, i) => (
                    <span key={i} className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded">
                      + {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
};

const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}> = ({ title, icon, expanded, onToggle, children }) => (
  <div className="border rounded-lg">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-3 hover:bg-gray-50"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="font-medium text-sm">{title}</span>
      </div>
      {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
    </button>
    {expanded && <div className="px-3 pb-3">{children}</div>}
  </div>
);
```

---
