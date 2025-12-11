# Phase 2: Services Layer Implementation

Status: ✅ QA Approved | Ready for Phase 3

## Overview

This phase implements the core network mathematics services that power skill distance calculations, closeness metrics, and centrality analysis. These services build on the CO_OCCURS_WITH relationships created in Phase 1.

---

## 1. NetworkMetricsService

### File: `backend/app/services/network_metrics_service.py`

```python
"""
Network Metrics Service

Implements ICT-paper-inspired network mathematics for skill analysis:
- Dijkstra shortest path (using cost = 1/weight)
- Closeness calculation (1 / (1 + D))
- Eigenvector centrality (via GDS or fallback)
- TransitionIndex for career transitions

Reference: SkillSoule_ICT_brief.pdf
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
from functools import lru_cache

from app.repositories.neo4j_repository import Neo4jRepository
from app.config import settings

logger = logging.getLogger(__name__)


class NetworkMetricsService:
    """
    Service for computing network-based skill metrics.

    Core Formulas:
    - Edge Cost: cost(s1, s2) = 1 / weight(s1, s2)
    - Path Distance: D(A, B) = sum of costs along Dijkstra shortest path
    - Closeness: closeness(A, B) = 1 / (1 + D(A, B))
    - JobCloseness: average closeness of all skill pairs in a job
    - TransitionIndex: 0.50*AvgCloseness + 0.30*CoreSkillOverlap + 0.20*MarketDemand
    """

    def __init__(self, neo4j_repo: Neo4jRepository):
        self.neo4j_repo = neo4j_repo
        self.cache_ttl = getattr(settings, 'NETWORK_CACHE_TTL', 3600)
        self.dijkstra_timeout = getattr(settings, 'NETWORK_DIJKSTRA_TIMEOUT', 5.0)
        self._centrality_cache: Dict[str, Tuple[Dict[str, float], datetime]] = {}
        self._gds_available: Optional[bool] = None

    async def check_gds_available(self) -> bool:
        """Check if Neo4j GDS library is installed."""
        if self._gds_available is not None:
            return self._gds_available

        try:
            query = "RETURN gds.version() AS version"
            result = await self.neo4j_repo.execute_query(query, timeout=5.0)
            self._gds_available = bool(result)
            logger.info(f"GDS available: version {result[0]['version']}")
        except Exception as e:
            logger.warning(f"GDS not available: {e}")
            self._gds_available = False

        return self._gds_available

    # =========================================================================
    # SHORTEST PATH & DISTANCE
    # =========================================================================

    async def get_shortest_path(
        self,
        skill_id_1: str,
        skill_id_2: str
    ) -> Dict[str, Any]:
        """
        Find shortest path between two skills using Dijkstra algorithm.

        Uses CO_OCCURS_WITH.cost property where cost = 1/weight.
        Lower cost = stronger connection = shorter path.

        Args:
            skill_id_1: Source skill ID
            skill_id_2: Target skill ID

        Returns:
            {
                "path_exists": bool,
                "total_distance": float,
                "closeness": float,
                "path": [skill_ids],
                "path_details": [{name, id}, ...]
            }
        """
        # Try GDS Dijkstra first (faster for large graphs)
        if await self.check_gds_available():
            return await self._dijkstra_gds(skill_id_1, skill_id_2)
        else:
            return await self._dijkstra_native(skill_id_1, skill_id_2)

    async def _dijkstra_gds(
        self,
        skill_id_1: str,
        skill_id_2: str
    ) -> Dict[str, Any]:
        """Dijkstra using Neo4j GDS library."""
        query = """
        MATCH (source:Skill {id: $source_id})
        MATCH (target:Skill {id: $target_id})

        CALL gds.shortestPath.dijkstra.stream({
            sourceNode: source,
            targetNode: target,
            nodeProjection: 'Skill',
            relationshipProjection: {
                CO_OCCURS_WITH: {
                    type: 'CO_OCCURS_WITH',
                    properties: 'cost',
                    orientation: 'UNDIRECTED'
                }
            },
            relationshipWeightProperty: 'cost'
        })
        YIELD index, sourceNode, targetNode, totalCost, nodeIds, costs, path

        RETURN totalCost,
               [nodeId IN nodeIds | gds.util.asNode(nodeId).id] AS path_ids,
               [nodeId IN nodeIds | gds.util.asNode(nodeId).name] AS path_names
        """

        try:
            result = await self.neo4j_repo.execute_query(
                query,
                {"source_id": skill_id_1, "target_id": skill_id_2},
                timeout=self.dijkstra_timeout
            )

            if result and result[0].get("totalCost") is not None:
                total_cost = result[0]["totalCost"]
                path_ids = result[0]["path_ids"]
                path_names = result[0]["path_names"]

                closeness = 1.0 / (1.0 + total_cost)

                return {
                    "path_exists": True,
                    "total_distance": float(total_cost),
                    "closeness": float(closeness),
                    "path": path_ids,
                    "path_details": [
                        {"id": pid, "name": pname}
                        for pid, pname in zip(path_ids, path_names)
                    ],
                    "algorithm": "gds_dijkstra"
                }

        except Exception as e:
            logger.warning(f"GDS Dijkstra failed, falling back to native: {e}")

        # Fallback to native
        return await self._dijkstra_native(skill_id_1, skill_id_2)

    async def _dijkstra_native(
        self,
        skill_id_1: str,
        skill_id_2: str
    ) -> Dict[str, Any]:
        """Dijkstra using native Cypher (APOC or shortestPath)."""
        # Try APOC dijkstra first
        apoc_query = """
        MATCH (source:Skill {id: $source_id})
        MATCH (target:Skill {id: $target_id})

        CALL apoc.algo.dijkstra(
            source,
            target,
            'CO_OCCURS_WITH',
            'cost'
        )
        YIELD path, weight

        RETURN weight as totalCost,
               [n IN nodes(path) | n.id] AS path_ids,
               [n IN nodes(path) | n.name] AS path_names
        """

        try:
            result = await self.neo4j_repo.execute_query(
                apoc_query,
                {"source_id": skill_id_1, "target_id": skill_id_2},
                timeout=self.dijkstra_timeout
            )

            if result and result[0].get("totalCost") is not None:
                total_cost = result[0]["totalCost"]
                path_ids = result[0]["path_ids"]
                path_names = result[0]["path_names"]

                closeness = 1.0 / (1.0 + total_cost)

                return {
                    "path_exists": True,
                    "total_distance": float(total_cost),
                    "closeness": float(closeness),
                    "path": path_ids,
                    "path_details": [
                        {"id": pid, "name": pname}
                        for pid, pname in zip(path_ids, path_names)
                    ],
                    "algorithm": "apoc_dijkstra"
                }

        except Exception as e:
            logger.warning(f"APOC Dijkstra not available: {e}")

        # Final fallback: BFS-based approximation
        return await self._path_bfs_fallback(skill_id_1, skill_id_2)

    async def _path_bfs_fallback(
        self,
        skill_id_1: str,
        skill_id_2: str,
        max_depth: int = 6
    ) -> Dict[str, Any]:
        """BFS-based path finding as ultimate fallback."""
        query = f"""
        MATCH (source:Skill {{id: $source_id}})
        MATCH (target:Skill {{id: $target_id}})
        MATCH path = shortestPath((source)-[:CO_OCCURS_WITH*1..{max_depth}]-(target))

        WITH path,
             reduce(cost = 0.0, r IN relationships(path) | cost + r.cost) as totalCost

        RETURN totalCost,
               [n IN nodes(path) | n.id] AS path_ids,
               [n IN nodes(path) | n.name] AS path_names
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {"source_id": skill_id_1, "target_id": skill_id_2},
            timeout=self.dijkstra_timeout
        )

        if result and result[0].get("totalCost") is not None:
            total_cost = result[0]["totalCost"]
            path_ids = result[0]["path_ids"]
            path_names = result[0]["path_names"]

            closeness = 1.0 / (1.0 + total_cost)

            return {
                "path_exists": True,
                "total_distance": float(total_cost),
                "closeness": float(closeness),
                "path": path_ids,
                "path_details": [
                    {"id": pid, "name": pname}
                    for pid, pname in zip(path_ids, path_names)
                ],
                "algorithm": "bfs_fallback"
            }

        # No path found
        return {
            "path_exists": False,
            "total_distance": float('inf'),
            "closeness": 0.0,
            "path": [],
            "path_details": [],
            "algorithm": "no_path"
        }

    # =========================================================================
    # CLOSENESS CALCULATIONS
    # =========================================================================

    async def get_skill_closeness(
        self,
        skill_id_1: str,
        skill_id_2: str
    ) -> float:
        """
        Calculate closeness between two skills.

        Formula: closeness = 1 / (1 + D) where D is Dijkstra distance

        Args:
            skill_id_1: First skill ID
            skill_id_2: Second skill ID

        Returns:
            Closeness value (0.0 to 1.0)
        """
        result = await self.get_shortest_path(skill_id_1, skill_id_2)
        return result["closeness"]

    async def get_job_closeness(self, job_id: str) -> Dict[str, Any]:
        """
        Calculate average closeness for all skill pairs in a job.

        Formula: JobCloseness = average(closeness(si, sj)) for all pairs

        Args:
            job_id: Job ID

        Returns:
            {
                "job_id": str,
                "job_closeness": float,
                "skill_count": int,
                "pair_count": int,
                "skills": [skill_ids]
            }
        """
        # Get all skills for this job
        query = """
        MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
        RETURN collect(s.id) as skill_ids, collect(s.name) as skill_names
        """

        result = await self.neo4j_repo.execute_query(query, {"job_id": job_id})

        if not result or not result[0].get("skill_ids"):
            return {
                "job_id": job_id,
                "job_closeness": 0.0,
                "skill_count": 0,
                "pair_count": 0,
                "skills": []
            }

        skill_ids = result[0]["skill_ids"]
        skill_names = result[0]["skill_names"]

        if len(skill_ids) < 2:
            return {
                "job_id": job_id,
                "job_closeness": 1.0,  # Single skill = perfect closeness to itself
                "skill_count": len(skill_ids),
                "pair_count": 0,
                "skills": skill_ids
            }

        # Calculate closeness for all pairs
        pair_count = 0
        total_closeness = 0.0

        for i in range(len(skill_ids)):
            for j in range(i + 1, len(skill_ids)):
                closeness = await self.get_skill_closeness(skill_ids[i], skill_ids[j])
                total_closeness += closeness
                pair_count += 1

        avg_closeness = total_closeness / pair_count if pair_count > 0 else 0.0

        return {
            "job_id": job_id,
            "job_closeness": float(avg_closeness),
            "skill_count": len(skill_ids),
            "pair_count": pair_count,
            "skills": skill_ids
        }

    # =========================================================================
    # EIGENVECTOR CENTRALITY
    # =========================================================================

    async def get_eigenvector_centrality(
        self,
        limit: int = 100,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Calculate eigenvector centrality for all skills.

        Uses CO_OCCURS_WITH.weight for importance calculation.
        Higher centrality = more important/connected skill.

        Args:
            limit: Maximum skills to return
            use_cache: Whether to use cached results

        Returns:
            List of {skill_id, skill_name, centrality_score}
        """
        # Check cache
        cache_key = f"eigenvector_{limit}"
        if use_cache and cache_key in self._centrality_cache:
            cached, timestamp = self._centrality_cache[cache_key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < self.cache_ttl:
                logger.info(f"Using cached eigenvector centrality (age: {age:.0f}s)")
                return cached

        # Try GDS first
        if await self.check_gds_available():
            result = await self._eigenvector_gds(limit)
        else:
            result = await self._eigenvector_fallback(limit)

        # Cache result
        self._centrality_cache[cache_key] = (result, datetime.utcnow())

        return result

    async def _eigenvector_gds(self, limit: int) -> List[Dict[str, Any]]:
        """Eigenvector centrality using GDS."""
        # Create in-memory graph projection
        projection_query = """
        CALL gds.graph.project(
            'skillCoOccurrence',
            'Skill',
            {
                CO_OCCURS_WITH: {
                    type: 'CO_OCCURS_WITH',
                    properties: 'weight',
                    orientation: 'UNDIRECTED'
                }
            }
        )
        YIELD graphName, nodeCount, relationshipCount
        RETURN graphName, nodeCount, relationshipCount
        """

        try:
            # Create projection
            await self.neo4j_repo.execute_query(projection_query, timeout=30.0)

            # Run eigenvector centrality
            centrality_query = """
            CALL gds.eigenvector.stream('skillCoOccurrence', {
                maxIterations: 100,
                tolerance: 1e-7,
                relationshipWeightProperty: 'weight'
            })
            YIELD nodeId, score
            WITH gds.util.asNode(nodeId) AS node, score
            RETURN node.id AS skill_id,
                   node.name AS skill_name,
                   score AS centrality_score
            ORDER BY score DESC
            LIMIT $limit
            """

            result = await self.neo4j_repo.execute_query(
                centrality_query,
                {"limit": limit},
                timeout=60.0
            )

            # Clean up projection
            await self.neo4j_repo.execute_query(
                "CALL gds.graph.drop('skillCoOccurrence', false)",
                timeout=10.0
            )

            return [
                {
                    "skill_id": r["skill_id"],
                    "skill_name": r["skill_name"],
                    "centrality_score": float(r["centrality_score"])
                }
                for r in result
            ]

        except Exception as e:
            logger.error(f"GDS eigenvector failed: {e}")
            # Try to clean up projection
            try:
                await self.neo4j_repo.execute_query(
                    "CALL gds.graph.drop('skillCoOccurrence', false)",
                    timeout=10.0
                )
            except:
                pass
            return await self._eigenvector_fallback(limit)

    async def _eigenvector_fallback(self, limit: int) -> List[Dict[str, Any]]:
        """
        Fallback: Use weighted degree centrality as approximation.

        Not true eigenvector, but correlates well for most use cases.
        """
        query = """
        MATCH (s:Skill)-[r:CO_OCCURS_WITH]-()
        WITH s, sum(r.weight) as weighted_degree, count(r) as degree
        RETURN s.id as skill_id,
               s.name as skill_name,
               weighted_degree * 1.0 / degree as centrality_score
        ORDER BY centrality_score DESC
        LIMIT $limit
        """

        result = await self.neo4j_repo.execute_query(query, {"limit": limit})

        return [
            {
                "skill_id": r["skill_id"],
                "skill_name": r["skill_name"],
                "centrality_score": float(r["centrality_score"])
            }
            for r in result
        ]

    # =========================================================================
    # TRANSITION INDEX
    # =========================================================================

    async def calculate_transition_index(
        self,
        source_skills: List[str],
        target_job_id: str
    ) -> Dict[str, Any]:
        """
        Calculate TransitionIndex for career transition.

        Formula: TransitionIndex = 0.50*AvgCloseness + 0.30*CoreSkillOverlap + 0.20*MarketDemand

        Args:
            source_skills: List of current skill IDs
            target_job_id: Target job ID

        Returns:
            {
                "transition_index": float (0-1),
                "avg_closeness": float,
                "core_skill_overlap": float,
                "market_demand": float,
                "details": {...}
            }
        """
        # Get target job skills
        query = """
        MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
        RETURN collect(s.id) as target_skills
        """
        result = await self.neo4j_repo.execute_query(query, {"job_id": target_job_id})
        target_skills = result[0]["target_skills"] if result else []

        if not target_skills:
            return {
                "transition_index": 0.0,
                "avg_closeness": 0.0,
                "core_skill_overlap": 0.0,
                "market_demand": 0.0,
                "details": {"error": "Target job has no skills"}
            }

        # 1. Calculate average closeness between source and target skills
        closeness_sum = 0.0
        closeness_count = 0
        for src_skill in source_skills:
            for tgt_skill in target_skills:
                if src_skill != tgt_skill:
                    closeness = await self.get_skill_closeness(src_skill, tgt_skill)
                    closeness_sum += closeness
                    closeness_count += 1

        avg_closeness = closeness_sum / closeness_count if closeness_count > 0 else 0.0

        # 2. Calculate core skill overlap
        source_set = set(source_skills)
        target_set = set(target_skills)
        overlap = len(source_set & target_set)
        core_skill_overlap = overlap / len(target_set) if target_set else 0.0

        # 3. Calculate market demand (jobs requiring target skills)
        demand_query = """
        MATCH (j:Job)-[:REQUIRES]->(s:Skill)
        WHERE s.id IN $target_skills
        RETURN count(DISTINCT j) as job_count
        """
        demand_result = await self.neo4j_repo.execute_query(
            demand_query,
            {"target_skills": target_skills}
        )
        job_count = demand_result[0]["job_count"] if demand_result else 0

        # Normalize market demand (assume max 1000 jobs)
        market_demand = min(job_count / 1000.0, 1.0)

        # Calculate TransitionIndex
        transition_index = (
            0.50 * avg_closeness +
            0.30 * core_skill_overlap +
            0.20 * market_demand
        )

        return {
            "transition_index": float(transition_index),
            "avg_closeness": float(avg_closeness),
            "core_skill_overlap": float(core_skill_overlap),
            "market_demand": float(market_demand),
            "details": {
                "source_skills_count": len(source_skills),
                "target_skills_count": len(target_skills),
                "overlapping_skills": list(source_set & target_set),
                "skills_to_learn": list(target_set - source_set),
                "jobs_with_target_skills": job_count
            }
        }

    # =========================================================================
    # SKILL METRICS SUMMARY
    # =========================================================================

    async def get_skill_metrics(self, skill_id: str) -> Dict[str, Any]:
        """
        Get comprehensive metrics for a single skill.

        Returns:
            {
                "skill_id": str,
                "skill_name": str,
                "co_occurrence_count": int,
                "total_weight": int,
                "avg_weight": float,
                "centrality_rank": int,
                "top_co_occurring": [...]
            }
        """
        query = """
        MATCH (s:Skill {id: $skill_id})
        OPTIONAL MATCH (s)-[r:CO_OCCURS_WITH]-(other:Skill)
        WITH s,
             count(r) as co_occurrence_count,
             sum(r.weight) as total_weight,
             avg(r.weight) as avg_weight,
             collect({id: other.id, name: other.name, weight: r.weight})[0..5] as top_co_occurring

        RETURN s.id as skill_id,
               s.name as skill_name,
               co_occurrence_count,
               total_weight,
               avg_weight,
               top_co_occurring
        """

        result = await self.neo4j_repo.execute_query(query, {"skill_id": skill_id})

        if not result:
            return {"error": f"Skill {skill_id} not found"}

        r = result[0]
        return {
            "skill_id": r["skill_id"],
            "skill_name": r["skill_name"],
            "co_occurrence_count": r["co_occurrence_count"] or 0,
            "total_weight": r["total_weight"] or 0,
            "avg_weight": float(r["avg_weight"]) if r["avg_weight"] else 0.0,
            "top_co_occurring": r["top_co_occurring"] or []
        }
```

---

## 2. Pydantic Models

### File: `backend/app/models/network_metrics.py`

```python
"""
Pydantic models for network metrics API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PathNode(BaseModel):
    """A node in a skill path."""
    id: str
    name: str


class ShortestPathRequest(BaseModel):
    """Request for shortest path between skills."""
    skill_id_1: str = Field(..., description="Source skill ID")
    skill_id_2: str = Field(..., description="Target skill ID")


class ShortestPathResponse(BaseModel):
    """Response for shortest path query."""
    path_exists: bool
    total_distance: float
    closeness: float
    path: List[str]
    path_details: List[PathNode]
    algorithm: str


class ClosenessRequest(BaseModel):
    """Request for closeness calculation."""
    skill_id_1: str
    skill_id_2: str


class ClosenessResponse(BaseModel):
    """Response for closeness calculation."""
    skill_id_1: str
    skill_id_2: str
    closeness: float
    distance: float


class JobClosenessRequest(BaseModel):
    """Request for job closeness calculation."""
    job_id: str


class JobClosenessResponse(BaseModel):
    """Response for job closeness calculation."""
    job_id: str
    job_closeness: float
    skill_count: int
    pair_count: int
    skills: List[str]


class CentralityResponse(BaseModel):
    """Response for centrality query."""
    skill_id: str
    skill_name: str
    centrality_score: float


class CentralityListResponse(BaseModel):
    """Response for centrality list query."""
    skills: List[CentralityResponse]
    count: int
    algorithm: str = "eigenvector"


class TransitionRequest(BaseModel):
    """Request for transition index calculation."""
    source_skills: List[str] = Field(..., description="Current skill IDs")
    target_job_id: str = Field(..., description="Target job ID")


class TransitionDetails(BaseModel):
    """Details of transition analysis."""
    source_skills_count: int
    target_skills_count: int
    overlapping_skills: List[str]
    skills_to_learn: List[str]
    jobs_with_target_skills: int


class TransitionResponse(BaseModel):
    """Response for transition index calculation."""
    transition_index: float = Field(..., ge=0.0, le=1.0)
    avg_closeness: float
    core_skill_overlap: float
    market_demand: float
    details: TransitionDetails


class SkillMetricsResponse(BaseModel):
    """Comprehensive metrics for a single skill."""
    skill_id: str
    skill_name: str
    co_occurrence_count: int
    total_weight: int
    avg_weight: float
    top_co_occurring: List[Dict[str, Any]]
```

---

## 3. Configuration Updates

### File: `backend/app/config.py` (additions)

```python
# Add to Settings class

# Network Metrics Configuration
NETWORK_MIN_CO_OCCURRENCE: int = 2       # Minimum jobs for edge creation
NETWORK_DIJKSTRA_TIMEOUT: float = 5.0    # Dijkstra query timeout (seconds)
NETWORK_CACHE_TTL: int = 3600            # Centrality cache TTL (seconds)
NETWORK_BATCH_SIZE: int = 1000           # Batch size for co-occurrence build

# GDS Configuration (if using Neo4j Graph Data Science)
GDS_PROJECTION_NAME: str = "skillNetwork"
GDS_EIGENVECTOR_ITERATIONS: int = 100
GDS_EIGENVECTOR_TOLERANCE: float = 1e-7
```

---

## 4. Service Dependencies

### File: `backend/app/dependencies.py` (additions)

```python
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder


async def get_network_metrics_service() -> NetworkMetricsService:
    """Get NetworkMetricsService instance."""
    repo = await get_neo4j_repository()
    return NetworkMetricsService(repo)


async def get_co_occurrence_builder() -> CoOccurrenceBuilder:
    """Get CoOccurrenceBuilder instance."""
    repo = await get_neo4j_repository()
    return CoOccurrenceBuilder(repo)
```

---

## 5. Service Integration Points

### With Existing SkillSimilarityService

The new NetworkMetricsService complements (not replaces) the existing SkillSimilarityService:

| Service | Relationship Type | Based On | Use Case |
|---------|------------------|----------|----------|
| SkillSimilarityService | SIMILAR_TO | Embedding cosine similarity | Semantic similarity |
| NetworkMetricsService | CO_OCCURS_WITH | Job co-occurrence | Market-based proximity |

### Hybrid Queries

For comprehensive skill analysis, combine both:

```python
async def get_hybrid_skill_analysis(skill_id: str):
    """Get both semantic and co-occurrence based relationships."""

    # Semantic similarity (existing)
    similar_query = """
    MATCH (s:Skill {id: $skill_id})-[r:SIMILAR_TO]-(other:Skill)
    RETURN other.id, other.name, r.similarity_score
    ORDER BY r.similarity_score DESC
    LIMIT 10
    """

    # Co-occurrence (new)
    cooccur_query = """
    MATCH (s:Skill {id: $skill_id})-[r:CO_OCCURS_WITH]-(other:Skill)
    RETURN other.id, other.name, r.weight, r.cost
    ORDER BY r.weight DESC
    LIMIT 10
    """

    # Execute both in parallel
    semantic_results, cooccur_results = await asyncio.gather(
        neo4j_repo.execute_query(similar_query, {"skill_id": skill_id}),
        neo4j_repo.execute_query(cooccur_query, {"skill_id": skill_id})
    )

    return {
        "semantic_similar": semantic_results,
        "market_co_occurring": cooccur_results
    }
```

---

## 6. Performance Considerations

### Caching Strategy

```python
# In NetworkMetricsService

class CacheManager:
    """LRU cache with TTL for network metrics."""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if (datetime.utcnow() - timestamp).seconds < self.ttl:
                return value
            else:
                del self.cache[key]
        return None

    def set(self, key: str, value: Any):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest = min(self.cache, key=lambda k: self.cache[k][1])
            del self.cache[oldest]
        self.cache[key] = (value, datetime.utcnow())
```

### Batch Processing

For large-scale calculations (e.g., all pairwise closeness):

```python
async def calculate_all_closeness_batch(self, skill_ids: List[str]) -> Dict:
    """Calculate closeness for all pairs in batches."""
    results = {}
    batch_size = 100

    pairs = [(skill_ids[i], skill_ids[j])
             for i in range(len(skill_ids))
             for j in range(i+1, len(skill_ids))]

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i+batch_size]
        batch_results = await asyncio.gather(*[
            self.get_skill_closeness(s1, s2)
            for s1, s2 in batch
        ])
        for (s1, s2), closeness in zip(batch, batch_results):
            results[(s1, s2)] = closeness

    return results
```

---

## 7. Error Handling

```python
class NetworkMetricsError(Exception):
    """Base exception for network metrics."""
    pass


class PathNotFoundError(NetworkMetricsError):
    """Raised when no path exists between skills."""
    pass


class GDSNotAvailableError(NetworkMetricsError):
    """Raised when GDS is required but not installed."""
    pass


class TimeoutError(NetworkMetricsError):
    """Raised when computation exceeds timeout."""
    pass
```

---

## 8. Success Criteria

1. **Shortest Path**: Returns correct path with distance < 500ms
2. **Closeness**: Accurate calculation matching formula
3. **Eigenvector**: Returns ranked skills with GDS or fallback
4. **TransitionIndex**: Calculates composite score correctly
5. **Caching**: Reduces repeated computation by 90%
6. **Error Handling**: Graceful degradation when GDS unavailable

---

*Next: Phase 3 - API Layer Implementation*

---

## QA Review Comment

**Implementation Date**: 2025-12-06
**Implemented By**: Claude (James - Full Stack Developer)

### What Was Done

1. **Created `backend/app/services/network_metrics_service.py`**
   - `NetworkMetricsService` class with all methods from plan:
     - `check_gds_available()` - Check if GDS library is installed
     - `get_shortest_path()` - Dijkstra shortest path between skills
     - `_dijkstra_gds()` - GDS-based Dijkstra implementation
     - `_dijkstra_native()` - APOC-based Dijkstra fallback
     - `_path_bfs_fallback()` - BFS-based fallback for environments without APOC
     - `get_skill_closeness()` - Calculate closeness between two skills
     - `get_job_closeness()` - Calculate average closeness for job's skills
     - `get_eigenvector_centrality()` - Eigenvector centrality with caching
     - `_eigenvector_gds()` - GDS-based eigenvector centrality
     - `_eigenvector_fallback()` - Weighted degree centrality approximation
     - `calculate_transition_index()` - TransitionIndex formula implementation
     - `get_skill_metrics()` - Comprehensive skill metrics
     - `clear_cache()` - Cache management

2. **Created `backend/app/models/network_metrics.py`**
   - All Pydantic models for API request/response:
     - `PathNode`, `ShortestPathRequest`, `ShortestPathResponse`
     - `ClosenessRequest`, `ClosenessResponse`
     - `JobClosenessRequest`, `JobClosenessResponse`
     - `CentralitySkill`, `CentralityListRequest`, `CentralityListResponse`
     - `TransitionRequest`, `TransitionDetails`, `TransitionResponse`
     - `CoOccurringSkill`, `SkillMetricsRequest`, `SkillMetricsResponse`
     - `NetworkStatsResponse`, `ErrorResponse`

3. **Created `backend/app/exceptions/network_metrics.py`**
   - Custom exceptions:
     - `NetworkMetricsError` - Base exception
     - `PathNotFoundError` - No path between skills
     - `SkillNotFoundError` - Skill not in graph
     - `JobNotFoundError` - Job not in graph
     - `GDSNotAvailableError` - GDS library not installed
     - `NetworkMetricsTimeoutError` - Computation timeout
     - `CentralityCacheError` - Cache operation failed
     - `InvalidSkillSetError` - Invalid skill set for operation

4. **Created `backend/app/exceptions/__init__.py`**
   - Package initialization with all exports

5. **Updated `backend/app/dependencies.py`**
   - Added imports for `NetworkMetricsService` and `CoOccurrenceBuilder`
   - Added `get_network_metrics_service()` factory function
   - Added `get_co_occurrence_builder()` factory function

### Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `network_metrics_service.py` | CREATED | Core service implementation |
| `models/network_metrics.py` | CREATED | Pydantic request/response models |
| `exceptions/network_metrics.py` | CREATED | Custom exceptions |
| `exceptions/__init__.py` | CREATED | Package initialization |
| `dependencies.py` | MODIFIED | Added service factory functions |

### Key Implementation Details

1. **Graceful Degradation**: Service automatically falls back from GDS → APOC → BFS
2. **Caching**: Eigenvector centrality results cached with configurable TTL
3. **Parallel Processing**: Job closeness calculation uses asyncio.gather for batches
4. **Type Hints**: Full TYPE_CHECKING pattern for repository type hints
5. **Configuration**: Uses settings from `app.config` with safe defaults

### Verification Steps

1. **Syntax Check** - All files pass Python syntax validation
2. **Import Check** - Service uses existing patterns from codebase
3. **Type Safety** - TYPE_CHECKING pattern prevents circular imports

### How to Test

```bash
# Navigate to backend
cd backend

# Test service can be instantiated
python -c "from app.services.network_metrics_service import NetworkMetricsService; print('Service imports OK')"

# Test models can be instantiated
python -c "from app.models.network_metrics import ShortestPathResponse; print('Models import OK')"

# Test exceptions can be instantiated
python -c "from app.exceptions import PathNotFoundError; print('Exceptions import OK')"
```

### Notes for QA

- Service requires Neo4j connection with CO_OCCURS_WITH relationships (from Phase 1)
- GDS is optional - service gracefully degrades to APOC or BFS
- TransitionIndex formula: `0.50*AvgCloseness + 0.30*CoreSkillOverlap + 0.20*MarketDemand`
- Caching uses in-memory dict with TTL (configurable via NETWORK_CACHE_TTL)

### Ready for Phase 3

Once approved, Phase 3 (API Layer) can begin, which will implement:

- FastAPI endpoints for all network metrics operations
- Request validation using Pydantic models
- Error handling using custom exceptions

---

## QA Results

### Review Date: 2025-12-06

### Reviewed By: Quinn (Test Architect)

### Code Quality Assessment

**Overall Assessment: GOOD with critical gaps**

The Phase 2 Services Layer implementation demonstrates excellent software engineering practices:

| Aspect | Assessment |
|--------|------------|
| Code Structure | ✅ Clean separation of concerns |
| Documentation | ✅ Comprehensive docstrings with formulas |
| Type Safety | ✅ TYPE_CHECKING pattern, Pydantic models |
| Error Handling | ✅ Custom exception hierarchy |
| Graceful Degradation | ✅ GDS → APOC → BFS fallback chain |
| Caching | ✅ TTL-based cache for centrality |
| Parallel Processing | ✅ asyncio.gather for batch operations |
| Configuration | ✅ getattr() with safe defaults |

**Critical Gap**: Zero test coverage for NetworkMetricsService.

### Refactoring Performed

No refactoring performed. Code quality is good but tests must be added.

### Compliance Check

- Coding Standards: ✓ Follows Python best practices, proper async patterns
- Project Structure: ✓ Files in correct directories (services/, models/, exceptions/)
- Testing Strategy: ✗ **NO TESTS** - Critical gap
- All ACs Met: ✓ Implementation matches design specification

### Implementation Verification

| File | Lines | Status |
|------|-------|--------|
| `services/network_metrics_service.py` | 733 | ✅ Verified |
| `models/network_metrics.py` | 145 | ✅ Verified |
| `exceptions/network_metrics.py` | 79 | ✅ Verified |
| `exceptions/__init__.py` | - | ✅ Verified |
| `dependencies.py` | +19 | ✅ Factory functions added |

### Improvements Checklist

**Must Address Before Production (P0):**

- [ ] Add unit tests for `NetworkMetricsService` class
- [ ] Add integration tests for Neo4j network operations
- [ ] Add tests for fallback chain (GDS → APOC → BFS)

**Recommended Improvements (P1):**

- [ ] Add skill existence validation before path queries
- [ ] Add cache size limits to prevent unbounded growth
- [ ] Consider parameterizing max_depth in BFS fallback (currently hardcoded 6)
- [ ] Make "max 1000 jobs" normalization configurable for TransitionIndex

**Nice-to-Have (P2):**

- [ ] Add metrics/telemetry for algorithm selection (track GDS vs APOC vs BFS usage)
- [ ] Consider connection pooling for high-frequency closeness calculations
- [ ] Add request-level caching for repeated skill pair queries

### Security Review

**Status: PASS**

- No user input directly in Cypher (parameterized queries) ✓
- Exception messages don't leak sensitive data ✓
- No authentication bypass vectors ✓
- Internal service only (not exposed directly to API yet) ✓

**Note**: BFS fallback uses f-string for max_depth (`*1..{max_depth}`), but this is internally controlled (default=6), not user input.

### Performance Considerations

**Status: PASS with monitoring recommendations**

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Dijkstra Timeout | ✓ | 5s configurable timeout |
| Batch Processing | ✓ | 10-20 item batches for parallel queries |
| Caching | ✓ | TTL-based centrality cache |
| Fallback Chain | ✓ | Graceful degradation on GDS/APOC unavailability |

**Recommendations:**
1. Monitor algorithm distribution (GDS vs APOC vs BFS) in production
2. Track cache hit rates for optimization
3. Consider circuit breaker for repeated GDS failures

### Test Design Requirements (P0)

**Unit Tests** (`backend/tests/unit/test_network_metrics_service.py`):

```
Given NetworkMetricsService with mocked Neo4jRepository
When get_shortest_path() is called for same skill
Then return distance=0, closeness=1.0 immediately

Given NetworkMetricsService with GDS available
When get_shortest_path() is called
Then use _dijkstra_gds() algorithm

Given NetworkMetricsService with GDS unavailable
When get_shortest_path() is called
Then fall back to _dijkstra_native()

Given NetworkMetricsService with cached centrality
When get_eigenvector_centrality() is called with use_cache=True
Then return cached result without querying Neo4j

Given NetworkMetricsService
When calculate_transition_index() is called
Then return composite score with correct formula weights
```

**Integration Tests** (`backend/tests/integration/test_network_metrics_neo4j.py`):

```
Given Neo4j with CO_OCCURS_WITH relationships
When get_shortest_path() is called for connected skills
Then return valid path with calculated closeness

Given Neo4j with CO_OCCURS_WITH relationships
When get_job_closeness() is called
Then return average closeness of all skill pairs

Given Neo4j with skills
When get_eigenvector_centrality() is called
Then return skills ordered by centrality score
```

### Gate Status

Gate: **PASS** → `docs/qa/gates/2.1-services-layer.yml`

*Updated 2025-12-06: All P0 blockers resolved, gate upgraded from CONCERNS to PASS*

### Recommended Status

**✓ Ready for Done** - All P0 blockers addressed

(Story owner decides final status)

---

### Re-Review: 2025-12-06

**Reviewed By**: Quinn (Test Architect)

**Fixes Verified**:
- [x] Unit tests created: 563 lines (test_network_metrics_service.py) ✅
- [x] Integration tests created: 370 lines (test_network_metrics_neo4j.py) ✅
- [x] Fallback chain tests included ✅
- [x] GDS/APOC/BFS test coverage ✅
- [x] Caching behavior tests ✅
- [x] TransitionIndex formula tests ✅

**Test Coverage Summary**:
| Category | File | Lines | Coverage |
|----------|------|-------|----------|
| Unit | test_network_metrics_service.py | 563 | All public methods + fallback |
| Integration | test_network_metrics_neo4j.py | 370 | Neo4j operations |
| **Total** | | **933** | **Comprehensive** |

**Gate Decision**: CONCERNS → **PASS**

All P0 blockers have been resolved. Phase 2 Services Layer is production-ready.
