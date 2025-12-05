"""
Vector Search Node - Performs vector similarity search in Neo4j.
"""
import asyncio
from typing import Dict, Any
from app.agents.graph import GraphRAGState
from app.repositories.neo4j_repository import Neo4jRepository
from app.config import settings
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)


async def vector_search_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Perform vector similarity search in Neo4j.

    This node executes parallel vector searches across Skills, Jobs, and Companies,
    combines results, and returns the top-k most similar nodes.

    Args:
        state: Current graph state with query_embedding

    Returns:
        Dict with vector_results updates:
        - vector_results: List of {node_type, id, name, description, score, ...}
        - metadata: Updated with search statistics
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("vector_search")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started
    await pipeline_monitor.emit_vector_search(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED
    )

    try:
        # Extract query embedding from state
        query_embedding = state.query_embedding

        if not query_embedding:
            logger.warning("[VectorSearch] No query_embedding in state, returning empty results")
            return {
                "vector_results": [],
                "metadata": {
                    **state.metadata,
                    "vector_search_completed": False,
                    "vector_search_error": "No query embedding available"
                }
            }

        # Get configurable parameters from state.metadata or use defaults
        k = state.metadata.get("vector_search_k", 15)
        threshold = state.metadata.get("vector_search_threshold", 0.5)

        logger.info(
            f"[VectorSearch] Starting search with k={k}, threshold={threshold}, "
            f"embedding_dim={len(query_embedding)}"
        )

        # Initialize Neo4j repository
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )

        await neo4j_repo.connect()

        try:
            # Execute vector searches in parallel for all node types
            skills_task = neo4j_repo.vector_search_skills(query_embedding, k, threshold)
            jobs_task = neo4j_repo.vector_search_jobs(query_embedding, k, threshold)
            companies_task = neo4j_repo.vector_search_companies(query_embedding, k, threshold)

            skills_results, jobs_results, companies_results = await asyncio.gather(
                skills_task,
                jobs_task,
                companies_task,
                return_exceptions=True
            )

            # Handle exceptions from individual searches
            if isinstance(skills_results, Exception):
                logger.warning(f"[VectorSearch] Skills search failed: {skills_results}")
                skills_results = []
            if isinstance(jobs_results, Exception):
                logger.warning(f"[VectorSearch] Jobs search failed: {jobs_results}")
                jobs_results = []
            if isinstance(companies_results, Exception):
                logger.warning(f"[VectorSearch] Companies search failed: {companies_results}")
                companies_results = []

            # Combine all results
            all_results = []
            all_results.extend(skills_results)
            all_results.extend(jobs_results)
            all_results.extend(companies_results)

            # Sort by similarity score descending and take top-k
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            vector_results = all_results[:k]

            logger.info(
                f"[VectorSearch] Found {len(vector_results)} results "
                f"(Skills: {len(skills_results)}, Jobs: {len(jobs_results)}, "
                f"Companies: {len(companies_results)})"
            )

            # Handle empty results
            if not vector_results:
                logger.warning(
                    f"[VectorSearch] No similar nodes found with threshold={threshold}. "
                    "Consider lowering the threshold."
                )

            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("vector_search")
                logger.info(f"[VectorSearch] Completed in {duration_ms:.2f}ms")

            # Emit stage completed
            await pipeline_monitor.emit_vector_search(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.COMPLETED,
                duration_ms=duration_ms,
                skills_found=len(skills_results),
                jobs_found=len(jobs_results),
                companies_found=len(companies_results),
                total_results=len(vector_results),
                threshold=threshold
            )

            return {
                "vector_results": vector_results,
                "metadata": {
                    **state.metadata,
                    "vector_search_completed": True,
                    "vector_results_count": len(vector_results),
                    "skills_count": len(skills_results),
                    "jobs_count": len(jobs_results),
                    "companies_count": len(companies_results),
                    "vector_search_k": k,
                    "vector_search_threshold": threshold
                }
            }

        finally:
            # Always close the Neo4j connection
            await neo4j_repo.close()

    except Exception as e:
        logger.error(f"[VectorSearch] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("vector_search")

        # Emit stage failed
        await pipeline_monitor.emit_vector_search(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "vector_results": [],
            "metadata": {
                **state.metadata,
                "vector_search_completed": False,
                "vector_search_error": str(e)
            }
        }
