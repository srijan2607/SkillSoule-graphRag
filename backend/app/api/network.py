"""
Network Math API

Endpoints for skill network analysis using co-occurrence graph:
- Shortest path between skills (Dijkstra)
- Eigenvector centrality rankings
- Job closeness calculations
- Transition index scoring
- Admin: Trigger co-occurrence rebuild

Authentication:
- User endpoints: JWT required
- Admin endpoints: JWT + admin role OR dev environment

Reference: Network Math Implementation - Phase 6 (07-NETWORK-API-ENHANCEMENTS.md)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from typing import List, Optional, Union
import logging
import os

from app.middleware.auth import get_current_user_id
from app.dependencies import (
    get_network_metrics_service,
    get_co_occurrence_builder
)
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder
from app.config import settings
from app.models.network_metrics import (
    PathResponse,
    SkillDetail,
    CentralityResponse,
    SkillCentrality,
    EnhancedJobClosenessRequest,
    EnhancedJobClosenessResponse,
    PerSkillCloseness,
    TransitionIndexDirectRequest,
    TransitionIndexDirectResponse,
    BuildCooccurrenceResponse,
    GDSUnavailableResponse,
    NetworkCapabilities,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/network", tags=["network"])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _is_admin_allowed() -> bool:
    """Check if admin operations are allowed (dev env or explicit flag)."""
    allow_admin = getattr(settings, 'ALLOW_NETWORK_ADMIN', False)
    app_env = getattr(settings, 'APP_ENV', 'production').lower()
    return allow_admin or app_env in ("development", "dev", "local")


# =============================================================================
# CAPABILITIES ENDPOINT
# =============================================================================

@router.get("/capabilities", response_model=NetworkCapabilities)
async def get_network_capabilities(
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Get available network math capabilities.

    Returns which features are available based on GDS/APOC installation.
    Frontend can use this to show/hide features.
    """
    return await metrics_service.get_capabilities()


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.post("/build-cooccurrence", response_model=BuildCooccurrenceResponse)
async def build_cooccurrence(
    background_tasks: BackgroundTasks,
    clear_existing: bool = Query(True, description="Clear existing relationships first"),
    current_user_id: str = Depends(get_current_user_id),
    builder: CoOccurrenceBuilder = Depends(get_co_occurrence_builder)
):
    """
    Trigger co-occurrence relationship rebuild.

    **Admin/Dev only** - Protected by environment flag.

    This operation:
    1. Optionally clears existing CO_OCCURS_WITH relationships
    2. Recomputes co-occurrences from Job-REQUIRES-Skill
    3. Excludes skills in NETWORK_GENERIC_SKILLS_STOPLIST
    4. Creates new CO_OCCURS_WITH with weight and cost

    Returns statistics about the build process.
    """
    if not _is_admin_allowed():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin operations not allowed in this environment"
        )

    logger.info(f"[NetworkAPI] Build co-occurrence triggered by user {current_user_id}")

    try:
        # Run synchronously for now (could be background task for large graphs)
        result = await builder.build_all(clear_existing=clear_existing)

        return BuildCooccurrenceResponse(
            status=result.get("status", "unknown"),
            relationships_created=result.get("relationships_created", 0),
            relationships_deleted=result.get("relationships_deleted", 0) if clear_existing else 0,
            duration_seconds=result.get("duration_seconds", 0),
            statistics=result,
            stoplist_stats=await builder.get_stoplist_stats()
        )

    except Exception as e:
        logger.error(f"[NetworkAPI] Build failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Build failed: {str(e)}"
        )


# =============================================================================
# PATH ENDPOINTS
# =============================================================================

@router.get("/path", response_model=Union[PathResponse, GDSUnavailableResponse])
async def get_shortest_path(
    from_skill: str = Query(..., alias="from", description="Source skill name or ID"),
    to_skill: str = Query(..., alias="to", description="Target skill name or ID"),
    current_user_id: str = Depends(get_current_user_id),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Find shortest path between two skills using Dijkstra algorithm.

    Uses CO_OCCURS_WITH.cost where cost = 1/weight.
    Lower cost = stronger co-occurrence = shorter path.

    **Example**: `/api/network/path?from=React&to=Go`

    Returns:
    - total_cost: Sum of edge costs along path
    - closeness: 1 / (1 + total_cost)
    - path_skill_names: Ordered list of skills in path
    - path_details: Full details for each skill in path
    """
    logger.info(f"[NetworkAPI] Path request: {from_skill} -> {to_skill}")

    # Check GDS availability (will fallback to APOC/BFS if not available)
    capabilities = await metrics_service.get_capabilities()
    if not capabilities.get("capabilities", {}).get("shortest_path", False):
        return GDSUnavailableResponse(
            available=False,
            message="Network metrics unavailable. Path calculations require GDS or APOC.",
            suggestion="Install GDS or APOC, or contact administrator."
        )

    try:
        result = await metrics_service.get_shortest_path(from_skill, to_skill)

        if not result.get("path_exists"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No path found between '{from_skill}' and '{to_skill}'"
            )

        # Convert path_details to SkillDetail objects
        path_details = [
            SkillDetail(id=d.get("id", ""), name=d.get("name", ""))
            for d in result.get("path_details", [])
        ]

        return PathResponse(
            total_cost=result["total_distance"],
            closeness=result["closeness"],
            path_skill_names=result.get("path_names", [d.get("name", "") for d in result.get("path_details", [])]),
            path_details=path_details,
            algorithm=result.get("algorithm", "unknown")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[NetworkAPI] Path calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Path calculation failed: {str(e)}"
        )


# =============================================================================
# CENTRALITY ENDPOINTS
# =============================================================================

@router.get("/centrality", response_model=Union[CentralityResponse, GDSUnavailableResponse])
async def get_eigenvector_centrality(
    topK: int = Query(50, ge=1, le=500, description="Number of top skills to return"),
    current_user_id: str = Depends(get_current_user_id),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Get eigenvector centrality rankings for skills.

    Uses CO_OCCURS_WITH.weight as relationship weight.
    Higher centrality = more important/connected skill in the network.

    **Example**: `/api/network/centrality?topK=50`

    Returns top-k skills ranked by eigenvector centrality score.
    """
    logger.info(f"[NetworkAPI] Centrality request: topK={topK}")

    # Check GDS availability
    capabilities = await metrics_service.get_capabilities()
    if not capabilities.get("capabilities", {}).get("eigenvector_centrality", False):
        return GDSUnavailableResponse(
            available=False,
            message="Eigenvector centrality requires Neo4j GDS library.",
            suggestion="Install GDS or contact administrator. Weighted degree available as fallback."
        )

    try:
        result = await metrics_service.get_eigenvector_centrality(limit=topK)

        # Convert to SkillCentrality objects
        skills = [
            SkillCentrality(
                skill=r.get("skill_name", ""),
                skill_id=r.get("skill_id", ""),
                score=r.get("centrality_score", 0.0)
            )
            for r in result
        ]

        return CentralityResponse(
            skills=skills,
            total_returned=len(skills),
            algorithm="eigenvector_gds" if capabilities.get("gds_available") else "weighted_degree_fallback"
        )

    except Exception as e:
        logger.error(f"[NetworkAPI] Centrality calculation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Centrality calculation failed: {str(e)}"
        )


# =============================================================================
# JOB CLOSENESS ENDPOINTS
# =============================================================================

@router.post("/job-closeness", response_model=Union[EnhancedJobClosenessResponse, GDSUnavailableResponse])
async def calculate_job_closeness(
    request: EnhancedJobClosenessRequest,
    current_user_id: str = Depends(get_current_user_id),
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Calculate how close a user's skills are to a job's requirements.

    **Formula**:
    For each required skill `req` in job J:
    - min_distance(req, U) = min(D(req, u) for u in user_skills)
    - closeness_req = 1 / (1 + min_distance)

    JobCloseness(U, J) = average(closeness_req for all req in J)

    **Request Body**:
    ```json
    {
        "user_skills": ["Python", "Django", "PostgreSQL"],
        "job_id": "job_123",  // Optional: specific job ID
        "job_title": "Backend Developer"  // Optional: search by title
    }
    ```

    **Returns**:
    - overall_closeness: Average closeness score (0-1, higher = better match)
    - per_skill_details: Breakdown for each required skill
    - skills_already_have: User skills that match job requirements
    - skills_to_learn: Job requirements user doesn't have
    """
    logger.info(f"[NetworkAPI] Job closeness request: {len(request.user_skills)} user skills")

    # Check GDS/APOC availability
    capabilities = await metrics_service.get_capabilities()
    if not capabilities.get("capabilities", {}).get("job_closeness", False):
        return GDSUnavailableResponse(
            available=False,
            message="Job closeness requires path calculations (GDS or APOC).",
            suggestion="Install GDS or APOC, or contact administrator."
        )

    try:
        result = await metrics_service.calculate_enhanced_job_closeness(
            user_skills=request.user_skills,
            job_id=request.job_id,
            job_title=request.job_title
        )

        # Convert per_skill_details to PerSkillCloseness objects
        per_skill_details = [
            PerSkillCloseness(
                required_skill=d.get("required_skill", ""),
                closest_user_skill=d.get("closest_user_skill", "N/A"),
                distance=d.get("distance", -1),
                closeness=d.get("closeness", 0.0),
                path=d.get("path", []),
                user_already_has=d.get("user_already_has", False)
            )
            for d in result.get("per_skill_details", [])
        ]

        return EnhancedJobClosenessResponse(
            job_id=result.get("job_id"),
            job_title=result.get("job_title", "Unknown"),
            overall_closeness=result.get("overall_closeness", 0.0),
            per_skill_details=per_skill_details,
            skills_already_have=result.get("skills_already_have", []),
            skills_to_learn=result.get("skills_to_learn", []),
            required_skills_count=result.get("required_skills_count", 0),
            matched_skills_count=result.get("matched_skills_count", 0)
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"[NetworkAPI] Job closeness failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job closeness calculation failed: {str(e)}"
        )


# =============================================================================
# TRANSITION INDEX ENDPOINTS
# =============================================================================

@router.post("/transition-index", response_model=TransitionIndexDirectResponse)
async def calculate_transition_index(
    request: TransitionIndexDirectRequest,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Calculate career transition index score.

    **Formula**:
    TransitionIndex = 0.50 * job_closeness + 0.30 * core_skill_overlap + 0.20 * market_demand

    **IMPORTANT**: This is a heuristic score, NOT a probability.
    Higher score indicates better alignment for transition.

    **Request Body**:
    ```json
    {
        "job_closeness": 0.75,        // From job-closeness endpoint
        "core_skill_overlap": 0.60,   // % of core skills user has
        "market_demand": 0.85         // Market demand score (0-1)
    }
    ```

    **Returns**:
    - transition_index: Combined score (0-1)
    - interpretation: Human-readable assessment
    - breakdown: Individual component contributions
    """
    logger.info(f"[NetworkAPI] Transition index request")

    # Validate inputs (already validated by Pydantic, but double-check)
    for field, value in [
        ("job_closeness", request.job_closeness),
        ("core_skill_overlap", request.core_skill_overlap),
        ("market_demand", request.market_demand)
    ]:
        if not 0 <= value <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field} must be between 0 and 1"
            )

    # Calculate transition index
    WEIGHT_CLOSENESS = 0.50
    WEIGHT_OVERLAP = 0.30
    WEIGHT_DEMAND = 0.20

    transition_index = (
        WEIGHT_CLOSENESS * request.job_closeness +
        WEIGHT_OVERLAP * request.core_skill_overlap +
        WEIGHT_DEMAND * request.market_demand
    )

    # Generate interpretation
    if transition_index >= 0.75:
        interpretation = "Excellent transition fit. Strong alignment between your skills and target role."
    elif transition_index >= 0.50:
        interpretation = "Good transition potential. Some skill gaps to address but achievable."
    elif transition_index >= 0.25:
        interpretation = "Moderate transition difficulty. Significant upskilling required."
    else:
        interpretation = "Challenging transition. Consider intermediate roles or extensive training."

    return TransitionIndexDirectResponse(
        transition_index=round(transition_index, 4),
        interpretation=interpretation,
        breakdown={
            "job_closeness_contribution": round(WEIGHT_CLOSENESS * request.job_closeness, 4),
            "core_skill_overlap_contribution": round(WEIGHT_OVERLAP * request.core_skill_overlap, 4),
            "market_demand_contribution": round(WEIGHT_DEMAND * request.market_demand, 4)
        },
        weights={
            "job_closeness": WEIGHT_CLOSENESS,
            "core_skill_overlap": WEIGHT_OVERLAP,
            "market_demand": WEIGHT_DEMAND
        },
        note="This is a heuristic score, not a probability. Use for guidance, not guarantees."
    )
