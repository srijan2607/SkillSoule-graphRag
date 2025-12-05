"""
Neo4j repository for graph database operations.

Handles creation and management of skills, jobs, companies, locations,
and their relationships in the Neo4j knowledge graph.
"""

import logging
from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jRepository:
    """
    Repository for Neo4j graph database operations.

    Responsibilities:
    - Create and update Skill, Job, Company, Location nodes
    - Create and manage relationships
    - Execute graph queries
    - Handle transactions
    """

    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize Neo4j repository.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Verify connectivity
            await self.driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise

    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await self.driver.close()
            logger.info("Neo4j connection closed")

    async def create_skill_node(self, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a Skill node in Neo4j.

        Args:
            skill_data: Dictionary with skill properties:
                - id (required): Unique skill ID
                - name (required): Skill name
                - description: Skill description
                - level: Skill level (1-5)
                - type: Skill type (e.g., "programming_language", "framework")
                - is_software: Boolean flag
                - is_language: Boolean flag
                - embedding: Vector embedding (List[float])
                - embedding_model_version: Model version string
                - ... other optional fields

        Returns:
            dict: Created/updated skill node properties

        Example:
            >>> skill = await repo.create_skill_node({
            ...     "id": "python-001",
            ...     "name": "Python",
            ...     "description": "High-level programming language",
            ...     "embedding": [0.1, 0.2, ..., 0.384]
            ... })
        """
        async with self.driver.session() as session:
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

            result = await session.run(query, **skill_data)
            record = await result.single()
            return dict(record["s"]) if record else None

    async def create_skill_category_relationship(self, skill_id: str, category_id: str):
        """
        Create BELONGS_TO relationship between Skill and Category.

        Args:
            skill_id: Skill node ID
            category_id: Category ID

        Example:
            >>> await repo.create_skill_category_relationship(
            ...     "python-001", "programming"
            ... )
        """
        async with self.driver.session() as session:
            query = """
            MATCH (s:Skill {id: $skill_id})
            MERGE (c:Category {category_id: $category_id})
            MERGE (s)-[r:BELONGS_TO]->(c)
            RETURN r
            """

            await session.run(query, skill_id=skill_id, category_id=category_id)

    async def create_skill_subcategory_relationship(self, skill_id: str, subcategory_id: str):
        """
        Create BELONGS_TO relationship between Skill and Subcategory.

        Args:
            skill_id: Skill node ID
            subcategory_id: Subcategory ID
        """
        async with self.driver.session() as session:
            query = """
            MATCH (s:Skill {id: $skill_id})
            MERGE (sc:Subcategory {subcategory_id: $subcategory_id})
            MERGE (s)-[r:BELONGS_TO]->(sc)
            RETURN r
            """

            await session.run(query, skill_id=skill_id, subcategory_id=subcategory_id)

    async def create_job_node(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a Job node in Neo4j.

        Args:
            job_data: Dictionary with job properties:
                - job_id (required): Unique job ID
                - job_title (required): Job title
                - company_name: Company name
                - location: Location name
                - description: Job description
                - embedding: Vector embedding
                - ... other optional fields

        Returns:
            dict: Created/updated job node properties
        """
        async with self.driver.session() as session:
            query = """
            MERGE (j:Job {job_id: $job_id})
            SET j.job_title = $job_title,
                j.company_name = $company_name,
                j.location = $location,
                j.district = $district,
                j.via = $via,
                j.salary = $salary,
                j.min_salary = $min_salary,
                j.max_salary = $max_salary,
                j.mean_salary = $mean_salary,
                j.salary_unit = $salary_unit,
                j.schedule_type = $schedule_type,
                j.work_from_home = $work_from_home,
                j.posted_at = $posted_at,
                j.description = $description,
                j.job_description = $job_description,
                j.apply_options = $apply_options,
                j.exact_matched_company = $exact_matched_company,
                j.nco_code = $nco_code,
                j.embedding = $embedding,
                j.embedding_model_version = $embedding_model_version,
                j.updated_at = datetime()
            SET j.created_at = coalesce(j.created_at, datetime())
            RETURN j
            """

            result = await session.run(query, **job_data)
            record = await result.single()
            return dict(record["j"]) if record else None

    async def create_job_company_relationship(self, job_id: str, company_name: str):
        """
        Create POSTED_BY relationship between Job and Company.

        Args:
            job_id: Job node ID
            company_name: Company name
        """
        async with self.driver.session() as session:
            query = """
            MATCH (j:Job {job_id: $job_id})
            MERGE (c:Company {company_name: $company_name})
            MERGE (j)-[r:POSTED_BY]->(c)
            RETURN r
            """

            await session.run(query, job_id=job_id, company_name=company_name)

    async def create_job_location_relationship(self, job_id: str, location_name: str):
        """
        Create LOCATED_IN relationship between Job and Location.

        Args:
            job_id: Job node ID
            location_name: Location name
        """
        async with self.driver.session() as session:
            query = """
            MATCH (j:Job {job_id: $job_id})
            MERGE (l:Location {location_name: $location_name})
            MERGE (j)-[r:LOCATED_IN]->(l)
            RETURN r
            """

            await session.run(query, job_id=job_id, location_name=location_name)

    async def create_job_skill_relationships(self, job_id: str, skill_names: List[str]):
        """
        Create REQUIRES relationships between Job and multiple Skills.

        Args:
            job_id: Job node ID
            skill_names: List of skill names (will match by name)
        """
        if not skill_names:
            return

        async with self.driver.session() as session:
            query = """
            MATCH (j:Job {job_id: $job_id})
            UNWIND $skill_names AS skill_name
            MATCH (s:Skill)
            WHERE toLower(s.name) = toLower(skill_name)
            MERGE (j)-[r:REQUIRES]->(s)
            RETURN count(r) as relationships_created
            """

            result = await session.run(query, job_id=job_id, skill_names=skill_names)
            record = await result.single()
            logger.debug(
                f"Created {record['relationships_created']} REQUIRES relationships "
                f"for job {job_id}"
            )

    async def vector_search_skills(
        self, query_embedding: List[float], k: int = 15, threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on Skill nodes.

        Args:
            query_embedding: Query embedding vector (384-dim)
            k: Number of top results to return (default: 15)
            threshold: Minimum similarity score threshold (default: 0.5)

        Returns:
            List of dictionaries with skill properties and similarity scores

        Example:
            >>> results = await repo.vector_search_skills(
            ...     query_embedding=[0.1, 0.2, ..., 0.384],
            ...     k=10,
            ...     threshold=0.6
            ... )
        """
        async with self.driver.session() as session:
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

            result = await session.run(
                query, query_embedding=query_embedding, k=k, threshold=threshold
            )
            records = await result.data()
            return records

    async def vector_search_jobs(
        self, query_embedding: List[float], k: int = 15, threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on Job nodes.

        Args:
            query_embedding: Query embedding vector (384-dim)
            k: Number of top results to return (default: 15)
            threshold: Minimum similarity score threshold (default: 0.5)

        Returns:
            List of dictionaries with job properties and similarity scores
        """
        async with self.driver.session() as session:
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

            result = await session.run(
                query, query_embedding=query_embedding, k=k, threshold=threshold
            )
            records = await result.data()
            return records

    async def vector_search_companies(
        self, query_embedding: List[float], k: int = 15, threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search on Company nodes.

        Args:
            query_embedding: Query embedding vector (384-dim)
            k: Number of top results to return (default: 15)
            threshold: Minimum similarity score threshold (default: 0.5)

        Returns:
            List of dictionaries with company properties and similarity scores
        """
        async with self.driver.session() as session:
            query = """
            CALL db.index.vector.queryNodes('company_embedding_idx', $k, $query_embedding)
            YIELD node, score
            WHERE score > $threshold
            MATCH (node:Company)
            OPTIONAL MATCH (node)<-[:POSTED_BY]-(jobs:Job)
            WITH node, score, count(jobs) as job_count
            RETURN node.company_name AS id,
                   node.company_name AS name,
                   node.description AS description,
                   score,
                   job_count,
                   'Company' AS node_type
            ORDER BY score DESC
            LIMIT $k
            """

            result = await session.run(
                query, query_embedding=query_embedding, k=k, threshold=threshold
            )
            records = await result.data()
            return records

    async def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None, timeout: float = 30.0
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Optional query parameters
            timeout: Query timeout in seconds (default: 30s)

        Returns:
            List[dict]: Query results as list of dictionaries

        Raises:
            neo4j.exceptions.TransactionError: If query times out

        Example:
            >>> results = await repo.execute_query(
            ...     "MATCH (s:Skill) RETURN s.name as name LIMIT 10"
            ... )
        """
        async with self.driver.session() as session:
            result = await session.run(query, parameters or {}, timeout=timeout)
            records = await result.data()
            return records

    def transaction(self):
        """
        Create a transaction context manager.

        Returns:
            AsyncSession: Neo4j session for transaction

        Example:
            >>> async with repo.transaction() as tx:
            ...     await tx.run("CREATE (n:Node {id: $id})", id="123")
        """
        return self.driver.session()

    async def get_database_stats(self) -> dict:
        """
        Get statistics about the current graph database.

        Returns:
            dict: {
                "skills_count": int,
                "jobs_count": int,
                "companies_count": int,
                "locations_count": int,
                "categories_count": int,
                "subcategories_count": int,
                "relationships_count": int
            }
        """
        async with self.driver.session() as session:
            query = """
            MATCH (s:Skill) WITH count(s) as skills
            MATCH (j:Job) WITH skills, count(j) as jobs
            MATCH (c:Company) WITH skills, jobs, count(c) as companies
            MATCH (l:Location) WITH skills, jobs, companies, count(l) as locations
            MATCH (cat:Category) WITH skills, jobs, companies, locations, count(cat) as categories
            MATCH (sc:Subcategory) WITH skills, jobs, companies, locations, categories, count(sc) as subcategories
            MATCH ()-[r]->() WITH skills, jobs, companies, locations, categories, subcategories, count(r) as relationships
            RETURN skills, jobs, companies, locations, categories, subcategories, relationships
            """
            result = await session.run(query)
            record = await result.single()

            if record:
                return {
                    "skills_count": record["skills"],
                    "jobs_count": record["jobs"],
                    "companies_count": record["companies"],
                    "locations_count": record["locations"],
                    "categories_count": record["categories"],
                    "subcategories_count": record["subcategories"],
                    "relationships_count": record["relationships"]
                }
            return {
                "skills_count": 0,
                "jobs_count": 0,
                "companies_count": 0,
                "locations_count": 0,
                "categories_count": 0,
                "subcategories_count": 0,
                "relationships_count": 0
            }

    async def delete_all_data(self) -> dict:
        """
        Delete ALL nodes and relationships from the graph database.

        ⚠️ WARNING: This is a destructive operation and cannot be undone!

        Use this for:
        - FULL mode ingestion (Story 3.7)
        - Testing/development cleanup
        - Starting fresh with new data

        Returns:
            dict: {
                "nodes_deleted": int,
                "relationships_deleted": int
            }
        """
        async with self.driver.session() as session:
            # Delete all relationships and nodes
            query = """
            MATCH (n)
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            result = await session.run(query)
            record = await result.single()
            deleted_count = record["deleted_count"] if record else 0

            logger.warning(f"⚠️  Deleted {deleted_count} nodes and all relationships from Neo4j")

            return {
                "nodes_deleted": deleted_count,
                "relationships_deleted": deleted_count  # DETACH DELETE removes relationships too
            }
