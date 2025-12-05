"""
Monitored Neo4j Repository - Wrapper with Query Logging.

Extends Neo4jRepository with automatic query monitoring and logging.
All Cypher queries are logged to PostgreSQL and broadcasted via WebSocket.
"""

import logging
from typing import Dict, Any, List, Optional
from prisma import Prisma

from app.repositories.neo4j_repository import Neo4jRepository
from app.services.neo4j_monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)


class MonitoredNeo4jRepository(Neo4jRepository):
    """
    Neo4j repository with built-in query monitoring and logging.

    Automatically logs all Cypher queries with execution time, parameters,
    and results to PostgreSQL and broadcasts to WebSocket clients.

    Usage:
        >>> repo = MonitoredNeo4jRepository(uri, user, password, prisma_client)
        >>> await repo.connect()
        >>> # All queries are automatically monitored
        >>> results = await repo.vector_search_skills(embedding, k=10)
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        prisma_client: Prisma,
        session_id: Optional[str] = None,
        enable_monitoring: bool = True
    ):
        """
        Initialize monitored Neo4j repository.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            prisma_client: Prisma client for logging
            session_id: Optional session ID for grouping queries
            enable_monitoring: Enable/disable monitoring (default: True)
        """
        super().__init__(uri, user, password)
        self.prisma = prisma_client
        self.session_id = session_id
        self.enable_monitoring = enable_monitoring
        self._monitoring_service = None

    def _get_monitoring_service(self):
        """Lazy load monitoring service."""
        if self._monitoring_service is None:
            self._monitoring_service = get_monitoring_service(self.prisma)
        return self._monitoring_service

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        source: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute Cypher query with automatic monitoring.

        Args:
            query: Cypher query string
            parameters: Query parameters
            timeout: Query timeout in seconds
            source: Source identifier (e.g., "ingestion", "query_pipeline")
            user_id: Optional user ID

        Returns:
            Query results
        """
        if not self.enable_monitoring:
            return await super().execute_query(query, parameters, timeout)

        monitoring_service = self._get_monitoring_service()

        async def execute_fn():
            return await super().execute_query(query, parameters, timeout)

        return await monitoring_service.execute_and_log(
            query_func=execute_fn,
            query_text=query,
            parameters=parameters,
            user_id=user_id,
            session_id=self.session_id,
            source=source or "execute_query",
            metadata={"timeout": timeout}
        )

    async def vector_search_skills(
        self,
        query_embedding: List[float],
        k: int = 15,
        threshold: float = 0.5,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Vector search skills with monitoring."""
        if not self.enable_monitoring:
            return await Neo4jRepository.vector_search_skills(self, query_embedding, k, threshold)

        monitoring_service = self._get_monitoring_service()

        query = """
        CALL db.index.vector.queryNodes('skill_embedding_idx', $k, $query_embedding)
        YIELD node, score
        WHERE score > $threshold
        MATCH (node:Skill)
        OPTIONAL MATCH (node)-[:BELONGS_TO]->(cat:Category)
        OPTIONAL MATCH (node)-[:BELONGS_TO]->(sub:Subcategory)
        RETURN node.id AS id,
               node.name AS name,
               node.description AS description,
               node.type AS type,
               node.level AS level,
               score,
               cat.category_name AS category,
               sub.subcategory_name AS subcategory,
               'Skill' AS node_type
        ORDER BY score DESC
        LIMIT $k
        """

        # Capture parent method reference to avoid super() issues in nested function
        parent_method = Neo4jRepository.vector_search_skills

        async def execute_fn():
            return await parent_method(self, query_embedding, k, threshold)

        return await monitoring_service.execute_and_log(
            query_func=execute_fn,
            query_text=query,
            parameters={"k": k, "threshold": threshold, "query_embedding": "[embedding]"},
            user_id=user_id,
            session_id=self.session_id,
            source="entity_extraction_vector_search_skills",
            metadata={"embedding_dim": len(query_embedding), "k": k, "threshold": threshold}
        )

    async def vector_search_jobs(
        self,
        query_embedding: List[float],
        k: int = 15,
        threshold: float = 0.5,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Vector search jobs with monitoring."""
        if not self.enable_monitoring:
            return await Neo4jRepository.vector_search_jobs(self, query_embedding, k, threshold)

        monitoring_service = self._get_monitoring_service()

        query = """
        CALL db.index.vector.queryNodes('job_embedding_idx', $k, $query_embedding)
        YIELD node, score
        WHERE score > $threshold
        MATCH (node:Job)
        OPTIONAL MATCH (node)-[:POSTED_BY]->(company:Company)
        OPTIONAL MATCH (node)-[:LOCATED_IN]->(loc:Location)
        RETURN node.job_id AS id,
               node.job_title AS name,
               node.description AS description,
               node.salary AS salary,
               node.schedule_type AS schedule_type,
               score,
               company.company_name AS company,
               loc.location_name AS location,
               'Job' AS node_type
        ORDER BY score DESC
        LIMIT $k
        """

        # Capture parent method reference to avoid super() issues in nested function
        parent_method = Neo4jRepository.vector_search_jobs

        async def execute_fn():
            return await parent_method(self, query_embedding, k, threshold)

        return await monitoring_service.execute_and_log(
            query_func=execute_fn,
            query_text=query,
            parameters={"k": k, "threshold": threshold, "query_embedding": "[embedding]"},
            user_id=user_id,
            session_id=self.session_id,
            source="entity_extraction_vector_search_jobs",
            metadata={"embedding_dim": len(query_embedding), "k": k, "threshold": threshold}
        )

    async def create_skill_node(
        self,
        skill_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create skill node with monitoring."""
        if not self.enable_monitoring:
            return await super().create_skill_node(skill_data)

        monitoring_service = self._get_monitoring_service()

        query = """
        MERGE (s:Skill {id: $id})
        SET s.name = $name,
            s.description = $description,
            s.level = $level,
            s.type = $type,
            s.is_software = $is_software,
            s.is_language = $is_language,
            s.description_source = $description_source,
            s.version = $version,
            s.latest_version = $latest_version,
            s.wiki_link = $wiki_link,
            s.wiki_extract = $wiki_extract,
            s.embedding = $embedding,
            s.embedding_model_version = $embedding_model_version,
            s.updated_at = datetime()
        SET s.created_at = coalesce(s.created_at, datetime())
        RETURN s
        """

        async def execute_fn():
            return await super().create_skill_node(skill_data)

        return await monitoring_service.execute_and_log(
            query_func=execute_fn,
            query_text=query,
            parameters={"id": skill_data.get("id"), "name": skill_data.get("name")},
            user_id=user_id,
            session_id=self.session_id,
            source="ingestion_skills",
            metadata={"node_type": "Skill"}
        )

    async def create_job_node(
        self,
        job_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create job node with monitoring."""
        if not self.enable_monitoring:
            return await super().create_job_node(job_data)

        monitoring_service = self._get_monitoring_service()

        async def execute_fn():
            return await super().create_job_node(job_data)

        return await monitoring_service.execute_and_log(
            query_func=execute_fn,
            query_text="MERGE (j:Job {job_id: $job_id}) SET j += $props RETURN j",
            parameters={"job_id": job_data.get("job_id")},
            user_id=user_id,
            session_id=self.session_id,
            source="ingestion_jobs",
            metadata={"node_type": "Job"}
        )
