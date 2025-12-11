"""
Transition Metrics Node - Calculates transition path metrics using NetworkMetricsService.

Phase 4: This node computes closeness scores, transition index, and skill gap
analysis for career transition queries.
"""

from typing import Dict, Any, List, Optional
from app.agents.graph import GraphRAGState
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics
from app.dependencies import get_network_metrics_service
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)


def _extract_source_skills(
    entities: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]]
) -> List[str]:
    """
    Extract source skills (user's current skills) from entities or vector results.

    Args:
        entities: Extracted entities from query understanding
        vector_results: Vector search results

    Returns:
        List of skill IDs representing user's current skills
    """
    source_skills = []

    # First priority: skills from entities (what user mentioned they know)
    for entity in entities:
        if entity.get("type") == "skill":
            # Use graph_node_id if available, otherwise use value
            skill_id = entity.get("graph_node_id") or entity.get("value", "").lower().replace(" ", "_")
            if skill_id:
                source_skills.append(skill_id)

    # Fallback: if no skills in entities, take first few skills from vector results
    if not source_skills:
        for result in vector_results[:5]:
            if result.get("node_type", "").lower() in ["skill", "skills"]:
                skill_id = result.get("id") or result.get("node_id")
                if skill_id:
                    source_skills.append(skill_id)

    return source_skills


def _extract_target_job(
    entities: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Extract target job ID from entities or vector results.

    Args:
        entities: Extracted entities from query understanding
        vector_results: Vector search results

    Returns:
        Target job ID or None
    """
    # First priority: job/role from entities (what user wants to transition to)
    for entity in entities:
        if entity.get("type") in ["job", "role"]:
            job_id = entity.get("graph_node_id") or entity.get("value", "").lower().replace(" ", "_")
            if job_id:
                return job_id

    # Fallback: first job from vector results
    for result in vector_results:
        if result.get("node_type", "").lower() in ["job", "jobrole"]:
            job_id = result.get("id") or result.get("node_id") or result.get("job_id")
            if job_id:
                return job_id

    return None


def _extract_skill_names_from_graph(
    graph_context: List[Dict[str, Any]],
    skill_ids: List[str]
) -> List[str]:
    """
    Extract skill names from graph context for display.

    Args:
        graph_context: Graph traversal results
        skill_ids: List of skill IDs to look up

    Returns:
        List of skill names (or IDs if names not found)
    """
    # Build a lookup dict from graph context
    skill_names = {}
    for item in graph_context:
        if item.get("node_type") in ["Skill", "skill"]:
            node_id = item.get("node_id") or item.get("id")
            name = item.get("name") or item.get("properties", {}).get("name")
            if node_id and name:
                skill_names[node_id] = name

    # Map IDs to names
    return [skill_names.get(sid, sid) for sid in skill_ids]


async def transition_metrics_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Calculate transition metrics for career transition queries.

    This node is conditionally executed when transition_path intent is detected.
    It uses NetworkMetricsService to compute:
    - Closeness score (skill proximity)
    - Transition index (composite feasibility score)
    - Source and target skill lists

    Args:
        state: Current graph state with vector_results, graph_context, entities

    Returns:
        Dict with transition fields (source_skills, target_skills, closeness_score, transition_index)
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("transition_metrics")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started (reuse graph_traversal event type or create custom)
    await pipeline_monitor.emit_graph_traversal(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED,
        traversal_patterns=["transition_metrics"]
    )

    try:
        # Check if transition_path intent is detected
        intents = state.intents or [state.intent] if state.intent else []

        if "transition_path" not in intents:
            logger.info("[TransitionMetrics] Skipping - not a transition_path query")
            return {
                "metadata": {
                    **state.metadata,
                    "transition_metrics_skipped": True,
                    "skip_reason": "not_transition_intent"
                }
            }

        logger.info("[TransitionMetrics] Starting transition analysis")

        # Extract data from state
        entities = state.entities or []
        vector_results = state.vector_results or []
        graph_context = state.graph_context or []

        # Extract source skills and target job
        source_skill_ids = _extract_source_skills(entities, vector_results)
        target_job_id = _extract_target_job(entities, vector_results)

        logger.info(
            f"[TransitionMetrics] Extracted | "
            f"source_skills={len(source_skill_ids)} | target_job={target_job_id}"
        )

        # If no target job, try to find from graph context
        if not target_job_id:
            for ctx in graph_context:
                if ctx.get("node_type") in ["Job", "job"]:
                    target_job_id = ctx.get("node_id") or ctx.get("job_id")
                    if target_job_id:
                        break

        if not target_job_id:
            logger.warning("[TransitionMetrics] No target job found for transition analysis")
            return {
                "metadata": {
                    **state.metadata,
                    "transition_metrics_error": "no_target_job_found"
                }
            }

        if not source_skill_ids:
            logger.warning("[TransitionMetrics] No source skills found for transition analysis")
            # Continue anyway - will calculate based on target job skills only

        # Get NetworkMetricsService and calculate transition index
        network_service = await get_network_metrics_service()

        try:
            transition_result = await network_service.calculate_transition_index(
                source_skills=source_skill_ids,
                target_job_id=target_job_id
            )

            logger.info(
                f"[TransitionMetrics] Calculated | "
                f"transition_index={transition_result['transition_index']:.3f} | "
                f"closeness={transition_result['avg_closeness']:.3f} | "
                f"overlap={transition_result['core_skill_overlap']:.3f}"
            )

            # Extract skill names for display
            details = transition_result.get("details", {})
            target_skill_ids = []

            # Build target skills list from details
            overlapping = details.get("overlapping_skills", [])
            to_learn = details.get("skills_to_learn", [])
            target_skill_ids = overlapping + to_learn

            # Get skill names from graph context
            source_skill_names = _extract_skill_names_from_graph(graph_context, source_skill_ids)
            target_skill_names = _extract_skill_names_from_graph(graph_context, target_skill_ids)

            # Use names if available, otherwise IDs
            final_source_skills = source_skill_names if source_skill_names else source_skill_ids
            final_target_skills = target_skill_names if target_skill_names else target_skill_ids

            # Build transition path recommendation
            transition_path = {
                "path": to_learn[:5],  # Top 5 skills to learn
                "overlapping_skills": overlapping,
                "skills_to_learn": to_learn,
                "market_demand": transition_result.get("market_demand", 0),
                "jobs_with_target_skills": details.get("jobs_with_target_skills", 0)
            }

            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("transition_metrics")
                logger.info(f"[TransitionMetrics] Completed in {duration_ms:.2f}ms")

            # Emit stage completed
            await pipeline_monitor.emit_graph_traversal(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.COMPLETED,
                duration_ms=duration_ms,
                nodes_accessed=len(source_skill_ids) + len(target_skill_ids),
                traversal_patterns=["transition_metrics"]
            )

            return {
                "source_skills": final_source_skills,
                "target_skills": final_target_skills,
                "closeness_score": transition_result["avg_closeness"],
                "transition_index": transition_result["transition_index"],
                "transition_path": transition_path,
                "metadata": {
                    **state.metadata,
                    "transition_metrics_completed": True,
                    "transition_index": transition_result["transition_index"],
                    "avg_closeness": transition_result["avg_closeness"],
                    "core_skill_overlap": transition_result["core_skill_overlap"],
                    "market_demand": transition_result["market_demand"],
                    "source_skills_count": len(source_skill_ids),
                    "target_skills_count": details.get("target_skills_count", 0),
                    "skills_to_learn_count": len(to_learn),
                }
            }

        finally:
            # NetworkMetricsService manages its own connection
            pass

    except Exception as e:
        logger.error(f"[TransitionMetrics] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("transition_metrics")

        # Emit stage failed
        await pipeline_monitor.emit_graph_traversal(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "metadata": {
                **state.metadata,
                "transition_metrics_error": str(e)
            }
        }
