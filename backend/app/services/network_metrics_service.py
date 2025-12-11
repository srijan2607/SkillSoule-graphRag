"""
Network Metrics Service

Implements ICT-paper-inspired network mathematics for skill analysis:
- Dijkstra shortest path (using cost = 1/weight)
- Closeness calculation (1 / (1 + D))
- Eigenvector centrality (via GDS or fallback)
- TransitionIndex for career transitions

Reference: SkillSoule_ICT_brief.pdf
Reference: Network Math Implementation - Phase 2 (02-SERVICES-LAYER.md)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime
import asyncio

from app.config import settings

if TYPE_CHECKING:
    from app.repositories.neo4j_repository import Neo4jRepository

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

    def __init__(self, neo4j_repo: "Neo4jRepository") -> None:
        """
        Initialize NetworkMetricsService.

        Args:
            neo4j_repo: Neo4jRepository instance for database operations
        """
        self.neo4j_repo = neo4j_repo
        self.cache_ttl = getattr(settings, 'NETWORK_CACHE_TTL', 3600)
        self.dijkstra_timeout = getattr(settings, 'NETWORK_DIJKSTRA_TIMEOUT', 5.0)
        self.max_cache_size = getattr(settings, 'NETWORK_MAX_CACHE_SIZE', 100)
        self.max_job_count = getattr(settings, 'NETWORK_MAX_JOB_COUNT', 1000)
        self._centrality_cache: Dict[str, Tuple[List[Dict[str, Any]], datetime]] = {}
        self._gds_available: Optional[bool] = None

    async def check_gds_available(self) -> bool:
        """
        Check if Neo4j GDS library is installed.

        Returns:
            True if GDS is available, False otherwise
        """
        if self._gds_available is not None:
            return self._gds_available

        try:
            query = "RETURN gds.version() AS version"
            result = await self.neo4j_repo.execute_query(query, timeout=5.0)
            self._gds_available = bool(result)
            if result:
                logger.info(f"GDS available: version {result[0]['version']}")
                self._gds_version = result[0]['version']
        except Exception as e:
            logger.warning(f"GDS not available: {e}")
            self._gds_available = False
            self._gds_version = None

        return self._gds_available

    async def check_apoc_available(self) -> bool:
        """
        Check if APOC library is installed.

        Returns:
            True if APOC is available, False otherwise
        """
        if hasattr(self, '_apoc_available') and self._apoc_available is not None:
            return self._apoc_available

        try:
            query = "RETURN apoc.version() AS version"
            result = await self.neo4j_repo.execute_query(query, timeout=5.0)
            self._apoc_available = bool(result)
            if result:
                logger.info(f"APOC available: version {result[0]['version']}")
        except Exception as e:
            logger.warning(f"APOC not available: {e}")
            self._apoc_available = False

        return self._apoc_available

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Get available network math capabilities based on installed plugins.

        Returns:
            NetworkCapabilities-compatible dict with:
            - gds_available: bool
            - gds_version: Optional[str]
            - apoc_available: bool
            - capabilities: Dict[str, bool]
            - fallback_mode: bool
            - limited_mode: bool
        """
        gds_available = await self.check_gds_available()
        apoc_available = await self.check_apoc_available()

        gds_version = getattr(self, '_gds_version', None) if gds_available else None

        # Determine available capabilities
        capabilities = {
            "shortest_path": gds_available or apoc_available,
            "eigenvector_centrality": gds_available,
            "job_closeness": gds_available or apoc_available,
            "transition_index": True,  # Always available (computed in Python)
            "weighted_degree_centrality": True,  # Fallback always available
        }

        return {
            "gds_available": gds_available,
            "gds_version": gds_version,
            "apoc_available": apoc_available,
            "capabilities": capabilities,
            "fallback_mode": not gds_available and apoc_available,
            "limited_mode": not gds_available and not apoc_available,
        }

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
        # Same skill check
        if skill_id_1 == skill_id_2:
            return {
                "path_exists": True,
                "total_distance": 0.0,
                "closeness": 1.0,
                "path": [skill_id_1],
                "path_details": [{"id": skill_id_1, "name": ""}],
                "algorithm": "same_skill"
            }

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
                    "algorithm": "bfs_fallback"
                }
        except Exception as e:
            logger.warning(f"BFS fallback failed: {e}")

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

        if len(skill_ids) < 2:
            return {
                "job_id": job_id,
                "job_closeness": 1.0,  # Single skill = perfect closeness to itself
                "skill_count": len(skill_ids),
                "pair_count": 0,
                "skills": skill_ids
            }

        # Calculate closeness for all pairs in parallel batches
        pairs = [
            (skill_ids[i], skill_ids[j])
            for i in range(len(skill_ids))
            for j in range(i + 1, len(skill_ids))
        ]

        # Process in batches to avoid overwhelming the database
        batch_size = 10
        total_closeness = 0.0

        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i + batch_size]
            closeness_results = await asyncio.gather(*[
                self.get_skill_closeness(s1, s2)
                for s1, s2 in batch
            ])
            total_closeness += sum(closeness_results)

        pair_count = len(pairs)
        avg_closeness = total_closeness / pair_count if pair_count > 0 else 0.0

        return {
            "job_id": job_id,
            "job_closeness": float(avg_closeness),
            "skill_count": len(skill_ids),
            "pair_count": pair_count,
            "skills": skill_ids
        }

    async def calculate_enhanced_job_closeness(
        self,
        user_skills: List[str],
        job_id: Optional[str] = None,
        job_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate enhanced job closeness with per-skill breakdown.

        For each required skill in the job:
        - Find minimum distance from any user skill
        - Calculate closeness = 1 / (1 + min_distance)
        - Track which user skill provided the closest path

        Formula:
        JobCloseness(U, J) = average(closeness_req for all req in J)

        Args:
            user_skills: List of user's current skill names
            job_id: Optional specific job ID
            job_title: Optional job title to search

        Returns:
            {
                "job_id": str,
                "job_title": str,
                "overall_closeness": float,
                "per_skill_details": [...],
                "skills_already_have": [...],
                "skills_to_learn": [...],
                "required_skills_count": int,
                "matched_skills_count": int
            }
        """
        # Resolve user skill names to IDs
        user_skill_query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) IN $skill_names
        RETURN s.id as id, s.name as name
        """
        user_skill_names_lower = [s.lower().strip() for s in user_skills]
        user_skill_result = await self.neo4j_repo.execute_query(
            user_skill_query,
            {"skill_names": user_skill_names_lower}
        )

        user_skill_map = {
            r["name"].lower(): {"id": r["id"], "name": r["name"]}
            for r in user_skill_result
        } if user_skill_result else {}

        user_skill_ids = [v["id"] for v in user_skill_map.values()]

        # Find job by ID or title
        if job_id:
            job_query = """
            MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
            RETURN j.job_id as job_id, j.job_title as job_title,
                   collect(s.id) as required_skill_ids,
                   collect(s.name) as required_skill_names
            """
            job_result = await self.neo4j_repo.execute_query(
                job_query,
                {"job_id": job_id}
            )
        elif job_title:
            job_query = """
            MATCH (j:Job)-[:REQUIRES]->(s:Skill)
            WHERE toLower(j.job_title) CONTAINS toLower($job_title)
            WITH j, collect(s.id) as required_skill_ids, collect(s.name) as required_skill_names
            RETURN j.job_id as job_id, j.job_title as job_title,
                   required_skill_ids, required_skill_names
            LIMIT 1
            """
            job_result = await self.neo4j_repo.execute_query(
                job_query,
                {"job_title": job_title}
            )
        else:
            raise ValueError("Either job_id or job_title must be provided")

        if not job_result:
            raise ValueError(f"Job not found: {job_id or job_title}")

        job_data = job_result[0]
        resolved_job_id = job_data["job_id"]
        resolved_job_title = job_data["job_title"] or "Unknown"
        required_skill_ids = job_data["required_skill_ids"] or []
        required_skill_names = job_data["required_skill_names"] or []

        if not required_skill_ids:
            return {
                "job_id": resolved_job_id,
                "job_title": resolved_job_title,
                "overall_closeness": 0.0,
                "per_skill_details": [],
                "skills_already_have": [],
                "skills_to_learn": [],
                "required_skills_count": 0,
                "matched_skills_count": 0
            }

        # Build per-skill closeness details
        per_skill_details = []
        skills_already_have = []
        skills_to_learn = []
        total_closeness = 0.0

        # Create normalized name sets for matching
        user_skills_lower = {s.lower().strip() for s in user_skills}

        for req_name, req_id in zip(required_skill_names, required_skill_ids):
            req_name_lower = req_name.lower().strip()

            # Check if user already has this skill
            if req_name_lower in user_skills_lower:
                skills_already_have.append(req_name)
                per_skill_details.append({
                    "required_skill": req_name,
                    "closest_user_skill": req_name,
                    "distance": 0.0,
                    "closeness": 1.0,
                    "path": [req_name],
                    "user_already_has": True
                })
                total_closeness += 1.0
                continue

            skills_to_learn.append(req_name)

            # Find closest user skill
            if not user_skill_ids:
                per_skill_details.append({
                    "required_skill": req_name,
                    "closest_user_skill": "N/A",
                    "distance": -1,
                    "closeness": 0.0,
                    "path": [],
                    "user_already_has": False
                })
                continue

            # Calculate distance from each user skill to this required skill
            min_distance = float('inf')
            closest_user_skill = "N/A"
            best_path = []

            for user_skill_key, user_skill_data in user_skill_map.items():
                user_skill_id = user_skill_data["id"]
                user_skill_name = user_skill_data["name"]
                path_result = await self.get_shortest_path(user_skill_id, req_id)

                if path_result["path_exists"] and path_result["total_distance"] < min_distance:
                    min_distance = path_result["total_distance"]
                    closest_user_skill = user_skill_name
                    best_path = [
                        d.get("name", "") for d in path_result.get("path_details", [])
                    ]

            if min_distance == float('inf'):
                closeness = 0.0
                min_distance = -1  # Indicate unreachable
            else:
                closeness = 1.0 / (1.0 + min_distance)

            per_skill_details.append({
                "required_skill": req_name,
                "closest_user_skill": closest_user_skill,
                "distance": min_distance,
                "closeness": closeness,
                "path": best_path,
                "user_already_has": False
            })
            total_closeness += closeness

        # Calculate overall closeness
        overall_closeness = total_closeness / len(required_skill_ids) if required_skill_ids else 0.0

        return {
            "job_id": resolved_job_id,
            "job_title": resolved_job_title,
            "overall_closeness": float(overall_closeness),
            "per_skill_details": per_skill_details,
            "skills_already_have": skills_already_have,
            "skills_to_learn": skills_to_learn,
            "required_skills_count": len(required_skill_ids),
            "matched_skills_count": len(skills_already_have)
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

        # Cache result with LRU eviction if cache exceeds max size
        if len(self._centrality_cache) >= self.max_cache_size:
            # Remove oldest entry (LRU eviction)
            oldest_key = min(
                self._centrality_cache.keys(),
                key=lambda k: self._centrality_cache[k][1]
            )
            del self._centrality_cache[oldest_key]
            logger.debug(f"Cache eviction: removed {oldest_key}")

        self._centrality_cache[cache_key] = (result, datetime.utcnow())

        return result

    async def _eigenvector_gds(self, limit: int) -> List[Dict[str, Any]]:
        """Eigenvector centrality using GDS."""
        projection_name = getattr(settings, 'GDS_PROJECTION_NAME', 'skillCoOccurrence')

        try:
            # Drop existing projection if exists
            try:
                await self.neo4j_repo.execute_query(
                    f"CALL gds.graph.drop('{projection_name}', false)",
                    timeout=10.0
                )
            except Exception:
                pass  # Projection doesn't exist

            # Create in-memory graph projection
            projection_query = f"""
            CALL gds.graph.project(
                '{projection_name}',
                'Skill',
                {{
                    CO_OCCURS_WITH: {{
                        type: 'CO_OCCURS_WITH',
                        properties: 'weight',
                        orientation: 'UNDIRECTED'
                    }}
                }}
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """

            await self.neo4j_repo.execute_query(projection_query, timeout=30.0)

            # Run eigenvector centrality
            max_iterations = getattr(settings, 'GDS_EIGENVECTOR_ITERATIONS', 100)
            tolerance = getattr(settings, 'GDS_EIGENVECTOR_TOLERANCE', 1e-7)

            centrality_query = f"""
            CALL gds.eigenvector.stream('{projection_name}', {{
                maxIterations: {max_iterations},
                tolerance: {tolerance},
                relationshipWeightProperty: 'weight'
            }})
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
                f"CALL gds.graph.drop('{projection_name}', false)",
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
                    f"CALL gds.graph.drop('{projection_name}', false)",
                    timeout=10.0
                )
            except Exception:
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
        WHERE degree > 0
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

        if not source_skills:
            return {
                "transition_index": 0.0,
                "avg_closeness": 0.0,
                "core_skill_overlap": 0.0,
                "market_demand": 0.0,
                "details": {"error": "No source skills provided"}
            }

        # 1. Calculate average closeness between source and target skills
        pairs = [
            (src_skill, tgt_skill)
            for src_skill in source_skills
            for tgt_skill in target_skills
            if src_skill != tgt_skill
        ]

        if pairs:
            # Process in batches
            batch_size = 20
            closeness_sum = 0.0
            for i in range(0, len(pairs), batch_size):
                batch = pairs[i:i + batch_size]
                closeness_results = await asyncio.gather(*[
                    self.get_skill_closeness(s1, s2)
                    for s1, s2 in batch
                ])
                closeness_sum += sum(closeness_results)

            avg_closeness = closeness_sum / len(pairs)
        else:
            avg_closeness = 0.0

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

        # Normalize market demand using configurable max job count
        market_demand = min(job_count / float(self.max_job_count), 1.0)

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
                "top_co_occurring": [...]
            }
        """
        query = """
        MATCH (s:Skill {id: $skill_id})
        OPTIONAL MATCH (s)-[r:CO_OCCURS_WITH]-(other:Skill)
        WITH s,
             count(r) as co_occurrence_count,
             sum(r.weight) as total_weight,
             avg(r.weight) as avg_weight
        RETURN s.id as skill_id,
               s.name as skill_name,
               co_occurrence_count,
               total_weight,
               avg_weight
        """

        result = await self.neo4j_repo.execute_query(query, {"skill_id": skill_id})

        if not result:
            return {"error": f"Skill {skill_id} not found"}

        r = result[0]

        # Get top co-occurring skills separately
        top_query = """
        MATCH (s:Skill {id: $skill_id})-[r:CO_OCCURS_WITH]-(other:Skill)
        RETURN other.id as id, other.name as name, r.weight as weight
        ORDER BY r.weight DESC
        LIMIT 5
        """
        top_result = await self.neo4j_repo.execute_query(top_query, {"skill_id": skill_id})

        return {
            "skill_id": r["skill_id"],
            "skill_name": r["skill_name"],
            "co_occurrence_count": r["co_occurrence_count"] or 0,
            "total_weight": r["total_weight"] or 0,
            "avg_weight": float(r["avg_weight"]) if r["avg_weight"] else 0.0,
            "top_co_occurring": [
                {"id": tr["id"], "name": tr["name"], "weight": tr["weight"]}
                for tr in top_result
            ] if top_result else []
        }

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._centrality_cache.clear()
        logger.info("Network metrics cache cleared")
