"""Graph data deletion service for full refresh mode."""
import logging
from typing import Dict
from app.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)


class GraphDeletionService:
    """
    Delete all graph data for full refresh ingestion.

    WARNING: Destructive operation, requires explicit user confirmation.
    """

    def __init__(self, neo4j_repo: Neo4jRepository):
        self.neo4j_repo = neo4j_repo

    async def delete_all_nodes_and_relationships(self) -> Dict[str, int]:
        """
        Delete ALL nodes and relationships from Neo4j.

        Returns:
            dict: {
                "nodes_deleted": int,
                "relationships_deleted": int
            }

        WARNING: Irreversible operation. Ensure backup exists.

        Cypher DETACH DELETE:
        - DETACH removes all relationships connected to nodes
        - Then deletes the nodes themselves
        - Single atomic operation
        """
        logger.warning("🚨 Deleting ALL graph data (FULL MODE)")

        # First, count relationships before deletion
        count_query = """
        MATCH ()-[r]-()
        RETURN count(DISTINCT r) as rel_count
        """

        async with self.neo4j_repo.driver.session() as session:
            count_result = await session.run(count_query)
            count_record = await count_result.single()
            rel_count = count_record["rel_count"] if count_record else 0

        # Then delete all nodes and relationships
        delete_query = """
        MATCH (n)
        DETACH DELETE n
        RETURN count(n) as nodes_deleted
        """

        async with self.neo4j_repo.driver.session() as session:
            delete_result = await session.run(delete_query)
            delete_record = await delete_result.single()

            stats = {
                "nodes_deleted": delete_record["nodes_deleted"] if delete_record else 0,
                "relationships_deleted": rel_count
            }

        logger.warning(
            f"🗑️  Graph deletion complete: "
            f"{stats['nodes_deleted']} nodes, "
            f"{stats['relationships_deleted']} relationships removed"
        )

        return stats
