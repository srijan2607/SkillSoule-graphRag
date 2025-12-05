"""
Vector index management service for Neo4j.

Creates and manages vector indexes for similarity search on
Skill, Job, and Company embeddings.
"""

import logging
from typing import Dict, List, Optional
import asyncio

logger = logging.getLogger(__name__)


class VectorIndexService:
    """
    Manage Neo4j vector indexes for embedding similarity search.

    Neo4j 5.x+ Features:
    - Automatic index updates when embeddings change (no manual rebuild)
    - IF NOT EXISTS for idempotent creation
    - SHOW INDEXES for health monitoring
    """

    # Index configuration constants
    EMBEDDING_DIMENSIONS = 384
    SIMILARITY_FUNCTION = "cosine"

    # Index definitions
    VECTOR_INDEXES = [
        {
            "name": "skill_embedding_idx",
            "node_label": "Skill",
            "property": "embedding"
        },
        {
            "name": "job_embedding_idx",
            "node_label": "Job",
            "property": "embedding"
        },
        {
            "name": "company_embedding_idx",
            "node_label": "Company",
            "property": "embedding"
        }
    ]

    def __init__(self, neo4j_repo):
        """
        Initialize VectorIndexService.

        Args:
            neo4j_repo: Neo4jRepository instance for database operations
        """
        self.neo4j_repo = neo4j_repo

    async def create_vector_indexes(self) -> Dict[str, str]:
        """
        Create all vector indexes for embedding similarity search.

        Returns:
            dict: {index_name: "created" | "already_exists" | "error: ..."}

        Example:
            {
                "skill_embedding_idx": "created",
                "job_embedding_idx": "already_exists",
                "company_embedding_idx": "created"
            }
        """
        results = {}

        for index_def in self.VECTOR_INDEXES:
            index_name = index_def["name"]
            node_label = index_def["node_label"]
            property_name = index_def["property"]

            try:
                # Check if index exists
                exists = await self._index_exists(index_name)

                if exists:
                    logger.info(f"Vector index already exists: {index_name}")
                    results[index_name] = "already_exists"
                else:
                    # Create index
                    await self._create_vector_index(
                        index_name,
                        node_label,
                        property_name
                    )
                    logger.info(f"✅ Vector index created: {index_name}")
                    results[index_name] = "created"

            except Exception as e:
                logger.error(f"Failed to create vector index {index_name}: {str(e)}")
                results[index_name] = f"error: {str(e)}"

        return results

    async def _index_exists(self, index_name: str) -> bool:
        """
        Check if vector index already exists.

        Args:
            index_name: Name of the index to check

        Returns:
            bool: True if index exists, False otherwise
        """
        query = """
        SHOW INDEXES
        YIELD name, type
        WHERE name = $index_name AND type = "VECTOR"
        RETURN count(*) > 0 as exists
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {"index_name": index_name}
        )

        return result[0]["exists"] if result else False

    async def _create_vector_index(
        self,
        index_name: str,
        node_label: str,
        property_name: str
    ) -> None:
        """
        Create vector index with cosine similarity.

        Args:
            index_name: Index name (e.g., "skill_embedding_idx")
            node_label: Node label (e.g., "Skill")
            property_name: Property name (e.g., "embedding")

        Neo4j 5.x Syntax:
            CREATE VECTOR INDEX index_name IF NOT EXISTS
            FOR (n:Label)
            ON (n.property)
            OPTIONS {
              indexConfig: {
                `vector.dimensions`: 384,
                `vector.similarity_function`: 'cosine'
              }
            }
        """
        # Note: Using unquoted property names (Neo4j 5.x supports both quoted and unquoted)
        query = f"""
        CREATE VECTOR INDEX {index_name} IF NOT EXISTS
        FOR (n:{node_label})
        ON (n.{property_name})
        OPTIONS {{
          indexConfig: {{
            `vector.dimensions`: {self.EMBEDDING_DIMENSIONS},
            `vector.similarity_function`: '{self.SIMILARITY_FUNCTION}'
          }}
        }}
        """

        await self.neo4j_repo.execute_query(query)
        logger.info(f"Vector index created: {index_name}")

    async def verify_vector_indexes(self) -> Dict[str, dict]:
        """
        Verify all vector indexes are healthy.

        Returns:
            dict: {
                "skill_embedding_idx": {
                    "exists": true,
                    "state": "ONLINE",
                    "population_percent": 100.0,
                    "entity_count": 15234
                },
                ...
            }

        Health Criteria:
        - exists = true
        - state = "ONLINE"
        - population_percent = 100.0
        """
        results = {}

        for index_def in self.VECTOR_INDEXES:
            index_name = index_def["name"]
            node_label = index_def["node_label"]

            try:
                # Get index status
                index_status = await self._get_index_status(index_name)

                # Get entity count
                entity_count = await self._get_entity_count(node_label)

                results[index_name] = {
                    "exists": index_status is not None,
                    "state": index_status["state"] if index_status else None,
                    "population_percent": index_status["populationPercent"] if index_status else None,
                    "entity_count": entity_count
                }
            except Exception as e:
                logger.error(f"Failed to verify index {index_name}: {str(e)}")
                results[index_name] = {
                    "exists": False,
                    "state": None,
                    "population_percent": None,
                    "entity_count": 0,
                    "error": str(e)
                }

        return results

    async def _get_index_status(self, index_name: str) -> Optional[dict]:
        """
        Get index status from SHOW INDEXES.

        Args:
            index_name: Name of the index

        Returns:
            dict with 'state' and 'populationPercent' or None if not found
        """
        query = """
        SHOW INDEXES
        YIELD name, type, state, populationPercent
        WHERE name = $index_name AND type = "VECTOR"
        RETURN name, state, populationPercent
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {"index_name": index_name}
        )

        return dict(result[0]) if result else None

    async def _get_entity_count(self, node_label: str) -> int:
        """
        Count nodes with embeddings for given label.

        Args:
            node_label: Label of the nodes (e.g., "Skill", "Job", "Company")

        Returns:
            int: Number of nodes with embeddings
        """
        query = f"""
        MATCH (n:{node_label})
        WHERE n.embedding IS NOT NULL
        RETURN count(n) as count
        """

        result = await self.neo4j_repo.execute_query(query)
        return result[0]["count"] if result else 0

    async def ensure_vector_indexes_exist(self) -> None:
        """
        Ensure all vector indexes exist (create if missing).

        Called before every ingestion job to guarantee indexes are ready.
        Idempotent: Safe to call multiple times.
        """
        for index_def in self.VECTOR_INDEXES:
            index_name = index_def["name"]
            exists = await self._index_exists(index_name)

            if not exists:
                logger.warning(f"Vector index missing, creating: {index_name}")
                await self._create_vector_index(
                    index_name,
                    index_def["node_label"],
                    index_def["property"]
                )
                logger.info(f"✅ Vector index created: {index_name}")
            else:
                logger.debug(f"Vector index exists: {index_name}")

    async def wait_for_index_population(
        self,
        index_name: str,
        timeout_seconds: int = 300
    ) -> bool:
        """
        Wait for index to reach 100% population.

        Args:
            index_name: Name of the index to wait for
            timeout_seconds: Maximum time to wait (default: 5 minutes)

        Returns:
            bool: True if index reached 100%, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        attempts = 0

        while True:
            status = await self._get_index_status(index_name)

            if not status:
                logger.warning(f"Index {index_name} not found")
                return False

            population = status.get("populationPercent", 0.0)

            if population == 100.0:
                logger.info(f"Index {index_name} fully populated (100%)")
                return True

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout_seconds:
                logger.warning(
                    f"Index {index_name} population timeout "
                    f"({population}% after {timeout_seconds}s)"
                )
                return False

            attempts += 1
            logger.debug(
                f"Index {index_name} population: {population}% "
                f"(attempt {attempts})"
            )

            # Wait 10 seconds before next check
            await asyncio.sleep(10)

    async def rebuild_index_if_corrupted(self, index_name: str) -> dict:
        """
        Rebuild vector index if corrupted (state != ONLINE).

        WARNING: Only use if index verification shows state != "ONLINE".
        Normal embedding updates do NOT require index rebuild (Neo4j 5.x+ auto-updates).

        Args:
            index_name: Index to rebuild

        Returns:
            dict: {
                "action": "rebuild" | "skip",
                "reason": str,
                "new_state": str
            }
        """
        # Check current state
        index_status = await self._get_index_status(index_name)

        if not index_status:
            return {
                "action": "skip",
                "reason": "index_not_found",
                "new_state": None
            }

        if index_status["state"] == "ONLINE":
            return {
                "action": "skip",
                "reason": "index_healthy",
                "new_state": "ONLINE"
            }

        # Index corrupted - rebuild
        logger.warning(
            f"Rebuilding corrupted vector index: {index_name} "
            f"(state: {index_status['state']})"
        )

        # Find index definition
        index_def = next(
            (idx for idx in self.VECTOR_INDEXES if idx["name"] == index_name),
            None
        )

        if not index_def:
            return {
                "action": "skip",
                "reason": "unknown_index",
                "new_state": None
            }

        # Drop corrupted index
        drop_query = f"DROP INDEX {index_name} IF EXISTS"
        await self.neo4j_repo.execute_query(drop_query)
        logger.info(f"Dropped corrupted index: {index_name}")

        # Recreate index
        await self._create_vector_index(
            index_name,
            index_def["node_label"],
            index_def["property"]
        )
        logger.info(f"Recreated index: {index_name}")

        # Wait for index to come online
        await asyncio.sleep(2)
        new_status = await self._get_index_status(index_name)

        return {
            "action": "rebuild",
            "reason": f"corrupted_state_{index_status['state']}",
            "new_state": new_status["state"] if new_status else None
        }
