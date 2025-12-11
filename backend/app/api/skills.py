"""
Skill Network Metrics API

Endpoints for skill-to-skill network analysis:
- Shortest path between skills
- Closeness calculations
- Eigenvector centrality rankings
- Transition index for career planning

All endpoints require JWT authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
import logging

from app.middleware.auth import get_current_user
from app.dependencies import get_network_metrics_service, get_co_occurrence_builder
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder
from app.models.network_metrics import (
    ShortestPathRequest,
    ShortestPathResponse,
    ClosenessRequest,
    ClosenessResponse,
    JobClosenessRequest,
    JobClosenessResponse,
    CentralityListResponse,
    CentralitySkill,
    TransitionRequest,
    TransitionResponse,
    TransitionDetails,
    SkillMetricsResponse,
    CoOccurringSkill,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])


# =============================================================================
# SHORTEST PATH ENDPOINTS
# =============================================================================

@router.post("/path", response_model=ShortestPathResponse)
async def get_shortest_path(
    request: ShortestPathRequest,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Find shortest path between two skills.

    Uses Dijkstra algorithm on CO_OCCURS_WITH.cost where cost = 1/weight.
    Returns path nodes, total distance, and closeness score.

    - **skill_id_1**: Source skill ID
    - **skill_id_2**: Target skill ID
    """
    logger.info(
        f"[SkillsAPI] Shortest path request: {request.skill_id_1} -> {request.skill_id_2} "
        f"by user {current_user_id}"
    )

    try:
        result = await metrics_service.get_shortest_path(
            request.skill_id_1,
            request.skill_id_2
        )

        return ShortestPathResponse(
            path_exists=result["path_exists"],
            total_distance=result["total_distance"],
            closeness=result["closeness"],
            path=result["path"],
            path_details=result["path_details"],
            algorithm=result["algorithm"]
        )

    except Exception as e:
        logger.error(f"[SkillsAPI] Path calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate path: {str(e)}"
        )


@router.get("/path/{skill_id_1}/{skill_id_2}", response_model=ShortestPathResponse)
async def get_shortest_path_get(
    skill_id_1: str,
    skill_id_2: str,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Find shortest path between two skills (GET version).

    Alternative to POST endpoint for simple integrations.
    """
    return await get_shortest_path(
        ShortestPathRequest(skill_id_1=skill_id_1, skill_id_2=skill_id_2),
        current_user_id,
        metrics_service
    )


# =============================================================================
# CLOSENESS ENDPOINTS
# =============================================================================

@router.post("/closeness", response_model=ClosenessResponse)
async def get_closeness(
    request: ClosenessRequest,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Calculate closeness between two skills.

    Formula: closeness = 1 / (1 + D) where D is Dijkstra distance.
    Returns value between 0 (far apart) and 1 (very close).
    """
    try:
        path_result = await metrics_service.get_shortest_path(
            request.skill_id_1,
            request.skill_id_2
        )

        return ClosenessResponse(
            skill_id_1=request.skill_id_1,
            skill_id_2=request.skill_id_2,
            closeness=path_result["closeness"],
            distance=path_result["total_distance"]
        )

    except Exception as e:
        logger.error(f"[SkillsAPI] Closeness calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate closeness: {str(e)}"
        )


@router.post("/closeness/job", response_model=JobClosenessResponse)
async def get_job_closeness(
    request: JobClosenessRequest,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Calculate average closeness for all skill pairs in a job.

    Formula: JobCloseness = average(closeness(si, sj)) for all skill pairs.
    Higher values indicate more cohesive skill requirements.
    """
    try:
        result = await metrics_service.get_job_closeness(request.job_id)

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        return JobClosenessResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] Job closeness calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate job closeness: {str(e)}"
        )


@router.get("/closeness/job/{job_id}", response_model=JobClosenessResponse)
async def get_job_closeness_get(
    job_id: str,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """Get job closeness (GET version)."""
    return await get_job_closeness(
        JobClosenessRequest(job_id=job_id),
        current_user_id,
        metrics_service
    )


# =============================================================================
# CENTRALITY ENDPOINTS
# =============================================================================

@router.get("/centrality", response_model=CentralityListResponse)
async def get_centrality_rankings(
    limit: int = Query(default=100, ge=1, le=500, description="Number of skills to return"),
    use_cache: bool = Query(default=True, description="Use cached results if available"),
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Get eigenvector centrality rankings for skills.

    Returns skills ranked by their importance in the co-occurrence network.
    Higher centrality = more connected/important skill.

    - **limit**: Maximum number of skills to return (1-500)
    - **use_cache**: Whether to use cached results (recommended)
    """
    try:
        skills_raw = await metrics_service.get_eigenvector_centrality(
            limit=limit,
            use_cache=use_cache
        )

        gds_available = await metrics_service.check_gds_available()
        algorithm = "eigenvector_gds" if gds_available else "weighted_degree_fallback"

        # Convert raw dicts to CentralitySkill models
        skills = [
            CentralitySkill(
                skill_id=s["skill_id"],
                skill_name=s["skill_name"],
                centrality_score=s["centrality_score"]
            )
            for s in skills_raw
        ]

        return CentralityListResponse(
            skills=skills,
            count=len(skills),
            algorithm=algorithm
        )

    except Exception as e:
        logger.error(f"[SkillsAPI] Centrality calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate centrality: {str(e)}"
        )


# =============================================================================
# TRANSITION INDEX ENDPOINTS
# =============================================================================

@router.post("/transition", response_model=TransitionResponse)
async def calculate_transition_index(
    request: TransitionRequest,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Calculate transition index for career transition.

    Formula: TransitionIndex = 0.50*AvgCloseness + 0.30*CoreSkillOverlap + 0.20*MarketDemand

    - **source_skills**: List of current skill IDs
    - **target_job_id**: Target job ID to transition to

    Returns:
    - **transition_index**: Overall score (0-1, higher = easier transition)
    - **avg_closeness**: Average closeness between current and target skills
    - **core_skill_overlap**: Percentage of target skills already possessed
    - **market_demand**: Normalized market demand for target skills
    """
    try:
        if not request.source_skills:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_skills cannot be empty"
            )

        result = await metrics_service.calculate_transition_index(
            source_skills=request.source_skills,
            target_job_id=request.target_job_id
        )

        if "error" in result.get("details", {}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["details"]["error"]
            )

        # Build TransitionDetails from raw result
        details_raw = result.get("details", {})
        details = TransitionDetails(
            source_skills_count=details_raw.get("source_skills_count", len(request.source_skills)),
            target_skills_count=details_raw.get("target_skills_count", 0),
            overlapping_skills=details_raw.get("overlapping_skills", []),
            skills_to_learn=details_raw.get("skills_to_learn", []),
            jobs_with_target_skills=details_raw.get("jobs_with_target_skills", 0)
        )

        return TransitionResponse(
            transition_index=result["transition_index"],
            avg_closeness=result["avg_closeness"],
            core_skill_overlap=result["core_skill_overlap"],
            market_demand=result["market_demand"],
            details=details
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] Transition index calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate transition index: {str(e)}"
        )


# =============================================================================
# SKILL METRICS ENDPOINTS
# =============================================================================

@router.get("/metrics/{skill_id}", response_model=SkillMetricsResponse)
async def get_skill_metrics(
    skill_id: str,
    current_user_id: str = Depends(get_current_user),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Get comprehensive metrics for a single skill.

    Returns co-occurrence statistics and top related skills.
    """
    try:
        result = await metrics_service.get_skill_metrics(skill_id)

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )

        # Build CoOccurringSkill models from raw data
        top_co_occurring = [
            CoOccurringSkill(
                id=s["id"],
                name=s["name"],
                weight=s["weight"]
            )
            for s in result.get("top_co_occurring", [])
        ]

        return SkillMetricsResponse(
            skill_id=result["skill_id"],
            skill_name=result["skill_name"],
            co_occurrence_count=result["co_occurrence_count"],
            total_weight=result["total_weight"],
            avg_weight=result["avg_weight"],
            top_co_occurring=top_co_occurring
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SkillsAPI] Skill metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get skill metrics: {str(e)}"
        )


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/admin/rebuild-cooccurrence")
async def rebuild_co_occurrence(
    clear_existing: bool = Query(default=True, description="Clear existing relationships first"),
    min_weight: int = Query(default=2, ge=1, description="Minimum co-occurrence count"),
    current_user_id: str = Depends(get_current_user),
    builder: CoOccurrenceBuilder = Depends(get_co_occurrence_builder)
):
    """
    Rebuild all skill co-occurrence relationships.

    **Admin only.** This is a long-running operation that may take several minutes
    for large graphs.

    - **clear_existing**: If true, delete existing CO_OCCURS_WITH first
    - **min_weight**: Minimum job count for creating relationship
    """
    logger.warning(f"[SkillsAPI] Co-occurrence rebuild triggered by user {current_user_id}")

    try:
        builder.min_weight = min_weight
        result = await builder.build_all(clear_existing=clear_existing)

        return {
            "status": result.get("status"),
            "relationships_created": result.get("relationships_created", 0),
            "duration_seconds": result.get("duration_seconds", 0),
            "statistics": {
                "total": result.get("total_co_occurrence_relationships", 0),
                "avg_weight": result.get("average_weight", 0),
                "min_weight": result.get("min_weight", 0),
                "max_weight": result.get("max_weight", 0)
            }
        }

    except Exception as e:
        logger.error(f"[SkillsAPI] Co-occurrence rebuild failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rebuild co-occurrence: {str(e)}"
        )


@router.get("/admin/cooccurrence-stats")
async def get_co_occurrence_stats(
    current_user_id: str = Depends(get_current_user),
    builder: CoOccurrenceBuilder = Depends(get_co_occurrence_builder)
):
    """
    Get statistics about current co-occurrence relationships.
    """
    try:
        stats = await builder.get_statistics()
        return stats

    except Exception as e:
        logger.error(f"[SkillsAPI] Stats retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )
