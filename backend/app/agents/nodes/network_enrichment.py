"""
Network Enrichment Node - Story 7.4

Enriches queries with network metrics based on detected intent:
- career_transition: Transition metrics and skill gap analysis
- skill_bridge: Shortest path between skills
- skill_importance: Top skills by centrality
- job_similarity: Similar jobs based on Jaccard similarity

This node runs after graph_traversal and before context_construction,
adding network-based insights to enhance LLM responses.
"""

from typing import Dict, Any, List, Optional
from app.agents.graph import GraphRAGState
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics
from app.dependencies import get_network_metrics_service, get_neo4j_repository
from app.config import get_settings
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)

settings = get_settings()


def _extract_skill_entities(entities: List[Dict[str, Any]]) -> List[str]:
    """
    Extract skill IDs from entities.

    Args:
        entities: Extracted entities from query understanding

    Returns:
        List of skill IDs
    """
    skill_ids = []
    for entity in entities:
        if entity.get("type") == "skill":
            # Use graph_node_id if available, otherwise fallback to value
            skill_id = entity.get("graph_node_id") or entity.get("value", "").lower().replace(" ", "_")
            if skill_id:
                skill_ids.append(skill_id)
    return skill_ids


def _extract_job_entity(entities: List[Dict[str, Any]], vector_results: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract job ID from entities or vector results.

    Args:
        entities: Extracted entities from query understanding
        vector_results: Vector search results

    Returns:
        Job ID or None
    """
    # First: check entities
    for entity in entities:
        if entity.get("type") in ["job", "role"]:
            job_id = entity.get("graph_node_id") or entity.get("value", "").lower().replace(" ", "_")
            if job_id:
                return job_id

    # Fallback: first job from vector results
    for result in vector_results[:5]:
        if result.get("node_type", "").lower() in ["job", "jobrole"]:
            job_id = result.get("id") or result.get("node_id") or result.get("job_id")
            if job_id:
                return job_id

    return None


def _extract_job_from_graph_context(graph_context: List[Dict[str, Any]]) -> Optional[str]:
    """
    Extract job ID from graph context as fallback.

    Args:
        graph_context: Graph traversal results

    Returns:
        Job ID or None
    """
    for ctx in graph_context:
        if ctx.get("node_type") in ["Job", "job"]:
            job_id = ctx.get("node_id") or ctx.get("job_id")
            if job_id:
                return job_id
    return None


async def network_enrichment_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Enrich query with network metrics based on detected intent.

    This node runs after graph_traversal and before context_construction.
    It adds network-based insights like skill paths, centrality rankings,
    and job similarity data.

    Intents handled:
    - career_transition: Calculate transition index and skill gaps
    - skill_bridge: Find shortest path between skills
    - skill_importance: Retrieve top skills by centrality
    - job_similarity: Query SIMILAR_JOB relationships

    Args:
        state: Current graph state with intent and entities

    Returns:
        Updated state with network_enrichment field
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("network_enrichment")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started
    await pipeline_monitor.emit_network_enrichment(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED
    )

    try:
        # Extract intents and entities
        intents = state.intents or [state.intent] if state.intent else []
        entities = state.entities or []
        vector_results = state.vector_results or []
        graph_context = state.graph_context or []

        # Initialize enrichment data structure
        enrichment = {
            "skill_paths": [],
            "top_skills_by_centrality": [],
            "similar_jobs": [],
            "transition_metrics": None,
        }

        # Check if network enrichment is relevant
        network_intents = {"career_transition", "skill_bridge", "skill_importance", "job_similarity"}
        detected_network_intents = network_intents & set(intents)

        if not detected_network_intents:
            logger.info("[NetworkEnrichment] Skipping - no network intents detected")
            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("network_enrichment")

            # Emit stage completed (skipped)
            await pipeline_monitor.emit_network_enrichment(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.COMPLETED,
                duration_ms=duration_ms,
                skill_paths_count=0,
                top_skills_count=0,
                similar_jobs_count=0,
                has_transition_metrics=False,
                enrichment_intents=[]
            )

            return {
                "network_enrichment": enrichment,
                "metadata": {
                    **state.metadata,
                    "network_enrichment_skipped": True,
                    "skip_reason": "no_network_intents"
                }
            }

        logger.info(f"[NetworkEnrichment] Processing intents: {detected_network_intents}")

        # Get NetworkMetricsService (may raise if neo4j_repo unavailable)
        try:
            network_service = await get_network_metrics_service()
        except Exception as e:
            logger.warning(f"[NetworkEnrichment] NetworkMetricsService unavailable: {e}")
            # Return empty enrichment gracefully
            return {
                "network_enrichment": enrichment,
                "metadata": {
                    **state.metadata,
                    "network_enrichment_error": "service_unavailable"
                }
            }

        # =====================================================================
        # INTENT: career_transition
        # =====================================================================
        if "career_transition" in intents:
            logger.info("[NetworkEnrichment] Processing career_transition intent")
            try:
                source_skills = _extract_skill_entities(entities)
                target_job_id = _extract_job_entity(entities, vector_results)

                # Fallback: try to find job from graph context
                if not target_job_id:
                    target_job_id = _extract_job_from_graph_context(graph_context)

                if target_job_id and source_skills:
                    result = await network_service.calculate_transition_index(
                        source_skills=source_skills,
                        target_job_id=target_job_id
                    )
                    enrichment["transition_metrics"] = result
                    logger.info(
                        f"[NetworkEnrichment] Transition index calculated: "
                        f"{result['transition_index']:.3f}"
                    )
                else:
                    logger.warning(
                        f"[NetworkEnrichment] Missing data for transition: "
                        f"target_job={target_job_id}, source_skills={len(source_skills)}"
                    )
            except Exception as e:
                logger.error(f"[NetworkEnrichment] career_transition failed: {e}")

        # =====================================================================
        # INTENT: skill_bridge
        # =====================================================================
        if "skill_bridge" in intents:
            logger.info("[NetworkEnrichment] Processing skill_bridge intent")
            try:
                skill_ids = _extract_skill_entities(entities)

                # Need at least 2 skills for a path
                if len(skill_ids) >= 2:
                    # Calculate paths between all pairs (limit to first 3 pairs to avoid explosion)
                    paths = []
                    for i in range(min(len(skill_ids) - 1, 3)):
                        for j in range(i + 1, min(len(skill_ids), 4)):
                            path_result = await network_service.get_shortest_path(
                                skill_id_1=skill_ids[i],
                                skill_id_2=skill_ids[j]
                            )
                            if path_result["path_exists"]:
                                paths.append({
                                    "from_skill": skill_ids[i],
                                    "to_skill": skill_ids[j],
                                    "distance": path_result["total_distance"],
                                    "closeness": path_result["closeness"],
                                    "path": path_result["path"],
                                    "path_details": path_result["path_details"]
                                })
                    enrichment["skill_paths"] = paths
                    logger.info(f"[NetworkEnrichment] Found {len(paths)} skill paths")
                else:
                    logger.warning(
                        f"[NetworkEnrichment] Need 2+ skills for path, got {len(skill_ids)}"
                    )
            except Exception as e:
                logger.error(f"[NetworkEnrichment] skill_bridge failed: {e}")

        # =====================================================================
        # INTENT: skill_importance
        # =====================================================================
        if "skill_importance" in intents:
            logger.info("[NetworkEnrichment] Processing skill_importance intent")
            try:
                # Get top skills by centrality (use STORED metrics, not live GDS)
                top_skills = await network_service.get_eigenvector_centrality(
                    limit=20,
                    use_cache=True
                )
                enrichment["top_skills_by_centrality"] = top_skills
                logger.info(f"[NetworkEnrichment] Retrieved {len(top_skills)} top skills")
            except Exception as e:
                logger.error(f"[NetworkEnrichment] skill_importance failed: {e}")
                # Fallback: query skills ordered by demand_count if available
                try:
                    neo4j_repo = await get_neo4j_repository()
                    try:
                        fallback_query = """
                        MATCH (s:Skill)
                        WHERE s.demand_count IS NOT NULL
                        RETURN s.id as skill_id, s.name as skill_name, s.demand_count as centrality_score
                        ORDER BY s.demand_count DESC
                        LIMIT 20
                        """
                        results = await neo4j_repo.execute_query(fallback_query)

                        enrichment["top_skills_by_centrality"] = [
                            {
                                "skill_id": r["skill_id"],
                                "skill_name": r["skill_name"],
                                "centrality_score": float(r.get("centrality_score", 0))
                            }
                            for r in results
                        ] if results else []
                        logger.info("[NetworkEnrichment] Used demand_count fallback")
                    finally:
                        await neo4j_repo.close()
                except Exception as fallback_error:
                    logger.error(f"[NetworkEnrichment] Fallback also failed: {fallback_error}")

        # =====================================================================
        # INTENT: job_similarity
        # =====================================================================
        if "job_similarity" in intents:
            logger.info("[NetworkEnrichment] Processing job_similarity intent")
            try:
                # Get job entity from query
                job_id = _extract_job_entity(entities, vector_results)

                # Fallback: try graph context
                if not job_id:
                    job_id = _extract_job_from_graph_context(graph_context)

                if job_id:
                    # Query SIMILAR_JOB relationships
                    neo4j_repo = await get_neo4j_repository()
                    try:
                        similarity_query = """
                        MATCH (j:Job {job_id: $job_id})-[sim:SIMILAR_JOB]->(similar:Job)
                        RETURN similar.job_id as job_id,
                               similar.job_title as job_title,
                               sim.jaccard_score as jaccard_score,
                               sim.shared_count as shared_count
                        ORDER BY sim.jaccard_score DESC
                        LIMIT 10
                        """
                        results = await neo4j_repo.execute_query(
                            similarity_query,
                            {"job_id": job_id}
                        )

                        enrichment["similar_jobs"] = [
                            {
                                "job_id": r["job_id"],
                                "job_title": r["job_title"],
                                "jaccard_score": float(r["jaccard_score"]),
                                "shared_count": r["shared_count"]
                            }
                            for r in results
                        ] if results else []
                        logger.info(f"[NetworkEnrichment] Found {len(enrichment['similar_jobs'])} similar jobs")
                    finally:
                        await neo4j_repo.close()
                else:
                    logger.warning("[NetworkEnrichment] No job entity found for similarity")
            except Exception as e:
                logger.error(f"[NetworkEnrichment] job_similarity failed: {e}")

        # End timing
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("network_enrichment")
            logger.info(f"[NetworkEnrichment] Completed in {duration_ms:.2f}ms")

        # Emit stage completed
        await pipeline_monitor.emit_network_enrichment(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.COMPLETED,
            duration_ms=duration_ms,
            skill_paths_count=len(enrichment["skill_paths"]),
            top_skills_count=len(enrichment["top_skills_by_centrality"]),
            similar_jobs_count=len(enrichment["similar_jobs"]),
            has_transition_metrics=enrichment["transition_metrics"] is not None,
            enrichment_intents=list(detected_network_intents)
        )

        return {
            "network_enrichment": enrichment,
            "metadata": {
                **state.metadata,
                "network_enrichment_completed": True,
                "enrichment_intents": list(detected_network_intents),
                "skill_paths_count": len(enrichment["skill_paths"]),
                "top_skills_count": len(enrichment["top_skills_by_centrality"]),
                "similar_jobs_count": len(enrichment["similar_jobs"]),
                "has_transition_metrics": enrichment["transition_metrics"] is not None,
            }
        }

    except Exception as e:
        logger.error(f"[NetworkEnrichment] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("network_enrichment")

        # Emit stage failed
        await pipeline_monitor.emit_network_enrichment(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        # Return empty enrichment on error (graceful degradation)
        return {
            "network_enrichment": {
                "skill_paths": [],
                "top_skills_by_centrality": [],
                "similar_jobs": [],
                "transition_metrics": None,
            },
            "metadata": {
                **state.metadata,
                "network_enrichment_error": str(e)
            }
        }
