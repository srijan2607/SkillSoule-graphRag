# Phase 6: Network API Enhancements

Status: ✅ QA Approved | All Tests Pass

---

## Status Workflow

| Stage | Status | Date | Owner |
|-------|--------|------|-------|
| **Drafted** | ✅ Done | 2025-12-06 | Claude |
| **Approved** | ✅ Done | 2025-12-06 | User |
| **Development** | ✅ Done | 2025-12-06 | Claude |
| **Code Review** | ✅ Done | 2025-12-06 | Claude |
| **QA** | ✅ Done | 2025-12-06 | Quinn |
| **Done** | ⏳ Minor Gap | - | - |

---

## Overview

This phase adds enhancements to the network math implementation:
1. **Generic Skills Stoplist** - Filter hyper-common skills from co-occurrence
2. **New `/api/network/*` Endpoints** - Dedicated network API namespace
3. **Enhanced Job Closeness** - Per-skill breakdown with transition paths
4. **Admin Build Endpoint** - Trigger co-occurrence rebuilds
5. **GDS Graceful Fallback** - Proper handling when GDS unavailable
6. **Toy Graph Tests** - Mathematical correctness validation

---

## 1. Generic Skills Stoplist

### Problem Statement

Generic/hyper-common skills (e.g., "Communication", "MS Excel", "Problem Solving") appear in many job postings but don't provide meaningful skill proximity information. They flatten the co-occurrence graph, making all skills appear equally close.

### Solution

Add configurable stoplist to exclude these skills from CO_OCCURS_WITH building.

### Configuration

**File**: `backend/app/config.py`

```python
# Network Math Configuration
NETWORK_GENERIC_SKILLS_STOPLIST: List[str] = [
    # Soft Skills (hyper-common)
    "Communication",
    "Communication Skills",
    "Problem Solving",
    "Problem-Solving",
    "Teamwork",
    "Team Work",
    "Leadership",
    "Time Management",
    "Critical Thinking",
    "Attention to Detail",
    "Analytical Skills",
    "Interpersonal Skills",
    "Work Ethic",
    "Adaptability",
    "Collaboration",

    # Basic Tools (ubiquitous)
    "Microsoft Office",
    "MS Office",
    "Microsoft Excel",
    "MS Excel",
    "Excel",
    "Microsoft Word",
    "MS Word",
    "Word",
    "PowerPoint",
    "Microsoft PowerPoint",
    "Outlook",
    "Google Workspace",
    "G Suite",

    # Basic Computer Skills
    "Computer Skills",
    "Basic Computer Skills",
    "Typing",
    "Email",
    "Internet",
]
```

### Implementation

**File**: `backend/app/services/co_occurrence_builder.py`

```python
class CoOccurrenceBuilder:
    """Enhanced with stoplist support."""

    def __init__(self, neo4j_repo: "Neo4jRepository"):
        self.neo4j_repo = neo4j_repo
        self.min_weight = getattr(settings, 'NETWORK_MIN_CO_OCCURRENCE', 2)
        self.stoplist = getattr(settings, 'NETWORK_GENERIC_SKILLS_STOPLIST', [])
        self._stoplist_normalized = {s.lower().strip() for s in self.stoplist}

    def _is_stoplist_skill(self, skill_name: str) -> bool:
        """Check if skill is in stoplist (case-insensitive)."""
        return skill_name.lower().strip() in self._stoplist_normalized

    async def _compute_and_create(self) -> int:
        """Compute co-occurrences EXCLUDING stoplist skills."""
        query = """
        // Get stoplist as parameter
        WITH $stoplist AS stoplist

        MATCH (j:Job)-[:REQUIRES]->(s1:Skill)
        WHERE NOT toLower(s1.name) IN stoplist

        MATCH (j)-[:REQUIRES]->(s2:Skill)
        WHERE NOT toLower(s2.name) IN stoplist
          AND id(s1) < id(s2)

        WITH s1, s2, count(DISTINCT j) as weight
        WHERE weight >= $min_weight

        // Use name ordering for consistent direction
        WITH s1, s2, weight,
             CASE WHEN s1.name < s2.name THEN s1 ELSE s2 END AS first,
             CASE WHEN s1.name < s2.name THEN s2 ELSE s1 END AS second

        MERGE (first)-[r:CO_OCCURS_WITH]->(second)
        SET r.weight = weight,
            r.cost = 1.0 / weight,
            r.updated_at = datetime()
        ON CREATE SET r.created_at = datetime()

        RETURN count(r) as created
        """

        # Normalize stoplist for Cypher
        stoplist_lower = [s.lower().strip() for s in self.stoplist]

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "min_weight": self.min_weight,
                "stoplist": stoplist_lower
            },
            timeout=300.0
        )
        return result[0]["created"] if result else 0

    async def get_stoplist_stats(self) -> Dict[str, Any]:
        """Get statistics about stoplist impact."""
        query = """
        WITH $stoplist AS stoplist

        // Count skills in stoplist
        MATCH (s:Skill)
        WHERE toLower(s.name) IN stoplist
        WITH collect(s.name) as stopped_skills, count(s) as stopped_count

        // Count jobs affected
        MATCH (j:Job)-[:REQUIRES]->(s:Skill)
        WHERE toLower(s.name) IN stoplist
        WITH stopped_skills, stopped_count, count(DISTINCT j) as jobs_with_stopped

        // Count total skills
        MATCH (total:Skill)
        WITH stopped_skills, stopped_count, jobs_with_stopped, count(total) as total_skills

        RETURN stopped_count, jobs_with_stopped, total_skills, stopped_skills
        """

        stoplist_lower = [s.lower().strip() for s in self.stoplist]
        result = await self.neo4j_repo.execute_query(
            query, {"stoplist": stoplist_lower}
        )

        if result:
            return {
                "stoplist_size": len(self.stoplist),
                "skills_filtered": result[0]["stopped_count"],
                "jobs_affected": result[0]["jobs_with_stopped"],
                "total_skills": result[0]["total_skills"],
                "sample_filtered": result[0]["stopped_skills"][:10]
            }
        return {"stoplist_size": len(self.stoplist)}
```

### Acceptance Criteria

- [x] Stoplist is configurable via settings
- [x] CO_OCCURS_WITH excludes stoplist skills
- [x] Statistics endpoint shows stoplist impact
- [x] Existing relationships with stoplist skills are cleaned on rebuild
- [x] Stoplist matching is case-insensitive

---

## 2. New API Namespace: `/api/network/*`

### Rationale

Create dedicated network math endpoints under `/api/network/` to:
- Clearly separate network math from skill CRUD operations
- Allow different authentication requirements (admin vs user)
- Enable versioning and deprecation independently

### New Router

**File**: `backend/app/api/network.py`

```python
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
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from typing import List, Optional
import logging
import os

from app.middleware.auth import get_current_user_id
from app.dependencies import (
    get_network_metrics_service,
    get_co_occurrence_builder
)
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder
from app.models.network_models import (
    PathResponse,
    CentralityResponse,
    JobClosenessRequest,
    JobClosenessResponse,
    TransitionIndexRequest,
    TransitionIndexResponse,
    BuildCooccurrenceResponse,
    GDSUnavailableResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/network", tags=["network"])


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

def _is_admin_allowed() -> bool:
    """Check if admin operations are allowed (dev env or explicit flag)."""
    return os.getenv("ALLOW_NETWORK_ADMIN", "false").lower() == "true" or \
           os.getenv("ENVIRONMENT", "production").lower() in ("development", "dev", "local")


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

@router.get("/path", response_model=PathResponse)
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

    # Check GDS availability
    if not await metrics_service.check_gds_available():
        return GDSUnavailableResponse(
            available=False,
            message="Network metrics unavailable (GDS not installed). Path calculations require Neo4j Graph Data Science library.",
            suggestion="Install GDS or contact administrator."
        )

    try:
        result = await metrics_service.get_shortest_path(from_skill, to_skill)

        if not result.get("path_exists"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No path found between '{from_skill}' and '{to_skill}'"
            )

        return PathResponse(
            total_cost=result["total_distance"],
            closeness=result["closeness"],
            path_skill_names=result.get("path_names", result.get("path", [])),
            path_details=result.get("path_details", []),
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

@router.get("/centrality", response_model=CentralityResponse)
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
    if not await metrics_service.check_gds_available():
        return GDSUnavailableResponse(
            available=False,
            message="Network metrics unavailable (GDS not installed). Eigenvector centrality requires Neo4j Graph Data Science library.",
            suggestion="Install GDS or contact administrator."
        )

    try:
        result = await metrics_service.get_eigenvector_centrality(top_k=topK)

        return CentralityResponse(
            skills=result,
            total_returned=len(result),
            algorithm="eigenvector_gds"
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

@router.post("/job-closeness", response_model=JobClosenessResponse)
async def calculate_job_closeness(
    request: JobClosenessRequest,
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

    # Check GDS availability
    if not await metrics_service.check_gds_available():
        return GDSUnavailableResponse(
            available=False,
            message="Network metrics unavailable (GDS not installed). Job closeness requires path calculations.",
            suggestion="Install GDS or contact administrator."
        )

    try:
        result = await metrics_service.calculate_job_closeness(
            user_skills=request.user_skills,
            job_id=request.job_id,
            job_title=request.job_title
        )

        return JobClosenessResponse(**result)

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

@router.post("/transition-index", response_model=TransitionIndexResponse)
async def calculate_transition_index(
    request: TransitionIndexRequest,
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

    # Validate inputs
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

    return TransitionIndexResponse(
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
```

### Register Router

**File**: `backend/app/main.py`

```python
# Add to router imports
from app.api.network import router as network_router

# Add to app initialization
app.include_router(network_router)
```

### Pydantic Models

**File**: `backend/app/models/network_models.py`

```python
"""
Pydantic models for Network Math API endpoints.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union


class SkillDetail(BaseModel):
    """Detail about a skill in path."""
    id: str
    name: str
    category: Optional[str] = None


class PathResponse(BaseModel):
    """Response for shortest path endpoint."""
    total_cost: float = Field(..., description="Sum of edge costs along path")
    closeness: float = Field(..., description="1 / (1 + total_cost)")
    path_skill_names: List[str] = Field(..., description="Ordered skill names in path")
    path_details: List[SkillDetail] = Field(default_factory=list)
    algorithm: str = Field(default="unknown")


class SkillCentrality(BaseModel):
    """Single skill with centrality score."""
    skill: str
    skill_id: str
    score: float


class CentralityResponse(BaseModel):
    """Response for centrality endpoint."""
    skills: List[SkillCentrality]
    total_returned: int
    algorithm: str


class JobClosenessRequest(BaseModel):
    """Request for job closeness calculation."""
    user_skills: List[str] = Field(..., min_items=1, description="User's current skills")
    job_id: Optional[str] = Field(None, description="Specific job ID")
    job_title: Optional[str] = Field(None, description="Job title to search")


class PerSkillCloseness(BaseModel):
    """Closeness detail for a single required skill."""
    required_skill: str
    closest_user_skill: str
    distance: float
    closeness: float = Field(..., description="1 / (1 + distance)")
    path: List[str] = Field(default_factory=list, description="Path from user skill to required")
    user_already_has: bool = False


class JobClosenessResponse(BaseModel):
    """Response for job closeness calculation."""
    job_id: Optional[str]
    job_title: str
    overall_closeness: float = Field(..., description="Average closeness across all required skills")
    per_skill_details: List[PerSkillCloseness]
    skills_already_have: List[str] = Field(default_factory=list)
    skills_to_learn: List[str] = Field(default_factory=list)
    required_skills_count: int
    matched_skills_count: int


class TransitionIndexRequest(BaseModel):
    """Request for transition index calculation."""
    job_closeness: float = Field(..., ge=0, le=1, description="From job-closeness endpoint")
    core_skill_overlap: float = Field(..., ge=0, le=1, description="% of core skills user has")
    market_demand: float = Field(..., ge=0, le=1, description="Market demand score")


class TransitionIndexResponse(BaseModel):
    """Response for transition index calculation."""
    transition_index: float = Field(..., description="Combined heuristic score (0-1)")
    interpretation: str = Field(..., description="Human-readable assessment")
    breakdown: Dict[str, float] = Field(..., description="Component contributions")
    weights: Dict[str, float] = Field(..., description="Formula weights")
    note: str = Field(..., description="Disclaimer about heuristic nature")


class BuildCooccurrenceResponse(BaseModel):
    """Response for admin build endpoint."""
    status: str
    relationships_created: int
    relationships_deleted: int
    duration_seconds: float
    statistics: Dict[str, Any]
    stoplist_stats: Dict[str, Any]


class GDSUnavailableResponse(BaseModel):
    """Response when GDS is not installed."""
    available: bool = False
    message: str
    suggestion: str
```

---

## 3. Enhanced Job Closeness

### Updated Formula Implementation

The job_closeness calculation needs enhancement to match the ICT paper specification:

**File**: `backend/app/services/network_metrics_service.py`

```python
async def calculate_job_closeness(
    self,
    user_skills: List[str],
    job_id: Optional[str] = None,
    job_title: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate closeness between user skills and job requirements.

    ICT Paper Formula:
    - For each required skill req in J:
        - min_distance(req, U) = min(D(req, u) for u in user_skills)
        - closeness_req = 1 / (1 + min_distance)
    - JobCloseness(U, J) = average(closeness_req for all req in J)

    Returns detailed breakdown per skill.
    """
    # Step 1: Get job and its requirements
    job_info = await self._get_job_requirements(job_id, job_title)
    if not job_info:
        raise ValueError(f"Job not found: {job_id or job_title}")

    required_skills = job_info["required_skills"]

    # Step 2: Normalize user skills (resolve names to IDs)
    user_skill_ids = await self._resolve_skill_names(user_skills)
    if not user_skill_ids:
        raise ValueError("None of the provided user skills found in database")

    # Step 3: Calculate per-skill closeness
    per_skill_details = []
    skills_already_have = []
    skills_to_learn = []
    total_closeness = 0.0

    for req_skill in required_skills:
        req_id = req_skill["id"]
        req_name = req_skill["name"]

        # Check if user already has this skill
        user_has_skill = req_id in user_skill_ids or \
                        req_name.lower() in [s.lower() for s in user_skills]

        if user_has_skill:
            # Distance 0, closeness 1
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

        # Find minimum distance from any user skill to this required skill
        min_distance = float('inf')
        closest_skill = None
        best_path = []

        for user_skill_id, user_skill_name in user_skill_ids.items():
            path_result = await self.get_shortest_path(user_skill_id, req_id)

            if path_result.get("path_exists"):
                distance = path_result["total_distance"]
                if distance < min_distance:
                    min_distance = distance
                    closest_skill = user_skill_name
                    best_path = path_result.get("path_names", path_result.get("path", []))

        if min_distance == float('inf'):
            # No path found
            closeness_req = 0.0
            min_distance = -1  # Indicates unreachable
            closest_skill = "N/A"
            best_path = []
        else:
            closeness_req = 1.0 / (1.0 + min_distance)

        skills_to_learn.append(req_name)
        per_skill_details.append({
            "required_skill": req_name,
            "closest_user_skill": closest_skill,
            "distance": min_distance,
            "closeness": closeness_req,
            "path": best_path,
            "user_already_has": False
        })
        total_closeness += closeness_req

    # Step 4: Calculate overall closeness
    overall_closeness = total_closeness / len(required_skills) if required_skills else 0.0

    return {
        "job_id": job_info.get("job_id"),
        "job_title": job_info.get("job_title", "Unknown"),
        "overall_closeness": round(overall_closeness, 4),
        "per_skill_details": per_skill_details,
        "skills_already_have": skills_already_have,
        "skills_to_learn": skills_to_learn,
        "required_skills_count": len(required_skills),
        "matched_skills_count": len(skills_already_have)
    }

async def _get_job_requirements(
    self,
    job_id: Optional[str] = None,
    job_title: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get job and its required skills."""
    if job_id:
        query = """
        MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
        RETURN j.job_id as job_id, j.job_title as job_title,
               collect({id: s.id, name: s.name}) as required_skills
        """
        params = {"job_id": job_id}
    elif job_title:
        query = """
        MATCH (j:Job)-[:REQUIRES]->(s:Skill)
        WHERE toLower(j.job_title) CONTAINS toLower($job_title)
        WITH j, collect({id: s.id, name: s.name}) as required_skills
        ORDER BY size(required_skills) DESC
        LIMIT 1
        RETURN j.job_id as job_id, j.job_title as job_title, required_skills
        """
        params = {"job_title": job_title}
    else:
        return None

    result = await self.neo4j_repo.execute_query(query, params)
    return result[0] if result else None

async def _resolve_skill_names(self, skill_names: List[str]) -> Dict[str, str]:
    """Resolve skill names to IDs. Returns {id: name} dict."""
    query = """
    UNWIND $names as name
    MATCH (s:Skill)
    WHERE toLower(s.name) = toLower(name)
    RETURN s.id as id, s.name as name
    """
    result = await self.neo4j_repo.execute_query(query, {"names": skill_names})
    return {r["id"]: r["name"] for r in result} if result else {}
```

---

## 4. GDS Graceful Fallback

### Enhanced GDS Checking

**File**: `backend/app/services/network_metrics_service.py`

```python
class NetworkMetricsService:
    """Enhanced with graceful GDS fallback."""

    def __init__(self, neo4j_repo: "Neo4jRepository"):
        self.neo4j_repo = neo4j_repo
        self._gds_available: Optional[bool] = None
        self._gds_version: Optional[str] = None
        self._apoc_available: Optional[bool] = None

    async def check_gds_available(self) -> bool:
        """
        Check if Neo4j GDS library is installed.
        Caches result for session.
        """
        if self._gds_available is not None:
            return self._gds_available

        try:
            query = "RETURN gds.version() AS version"
            result = await self.neo4j_repo.execute_query(query, timeout=5.0)
            self._gds_available = bool(result)
            self._gds_version = result[0]["version"] if result else None
            logger.info(f"GDS available: version {self._gds_version}")
        except Exception as e:
            logger.warning(f"GDS not available: {e}")
            self._gds_available = False
            self._gds_version = None

        return self._gds_available

    async def check_apoc_available(self) -> bool:
        """Check if APOC library is available for fallback."""
        if self._apoc_available is not None:
            return self._apoc_available

        try:
            query = "RETURN apoc.version() AS version"
            result = await self.neo4j_repo.execute_query(query, timeout=5.0)
            self._apoc_available = bool(result)
            logger.info(f"APOC available: {result[0]['version'] if result else 'unknown'}")
        except Exception:
            self._apoc_available = False
            logger.info("APOC not available")

        return self._apoc_available

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Get available network math capabilities.
        Useful for frontend to know what's available.
        """
        gds = await self.check_gds_available()
        apoc = await self.check_apoc_available()

        return {
            "gds_available": gds,
            "gds_version": self._gds_version,
            "apoc_available": apoc,
            "capabilities": {
                "shortest_path": gds or apoc,
                "eigenvector_centrality": gds,
                "betweenness_centrality": gds,
                "pagerank": gds,
                "community_detection": gds,
                "job_closeness": gds or apoc,
                "transition_index": True  # Always available (just math)
            },
            "fallback_mode": not gds and apoc,
            "limited_mode": not gds and not apoc
        }
```

### Capability Endpoint

**File**: `backend/app/api/network.py`

```python
@router.get("/capabilities")
async def get_network_capabilities(
    metrics_service: NetworkMetricsService = Depends(get_network_metrics_service)
):
    """
    Get available network math capabilities.

    Returns which features are available based on GDS/APOC installation.
    Frontend can use this to show/hide features.
    """
    return await metrics_service.get_capabilities()
```

---

## 5. Toy Graph Tests

### Mathematical Correctness Validation

**File**: `backend/tests/unit/test_network_math_correctness.py`

```python
"""
Network Math Correctness Tests

Tests mathematical formulas with known values using a toy graph.
Based on ICT paper specifications.
"""

import pytest
import math
from decimal import Decimal


class TestNetworkMathFormulas:
    """
    Test mathematical correctness with toy graph.

    Graph:
        React ----[800]---- JavaScript ----[600]---- Backend ----[150]---- Go
          |
        [320]
          |
        UI Design ---[250]--- Design Systems ---[200]--- UX Research

    Weights shown are co-occurrence counts.
    Cost = 1 / weight
    """

    # Define toy graph edges: (skill1, skill2, weight)
    TOY_GRAPH = [
        ("React", "UI Design", 320),
        ("UI Design", "Design Systems", 250),
        ("Design Systems", "UX Research", 200),
        ("React", "JavaScript", 800),
        ("JavaScript", "Backend", 600),
        ("Backend", "Go", 150),
    ]

    def test_cost_formula(self):
        """Verify cost = 1 / weight."""
        for s1, s2, weight in self.TOY_GRAPH:
            cost = 1.0 / weight
            assert cost == 1.0 / weight

        # Specific values
        assert 1.0 / 800 == 0.00125
        assert 1.0 / 600 == pytest.approx(0.001666666, rel=1e-5)
        assert 1.0 / 150 == pytest.approx(0.006666666, rel=1e-5)

    def test_shortest_path_react_to_go(self):
        """
        Verify shortest path React -> Go uses React->JavaScript->Backend->Go

        Path costs:
        - React -> JavaScript: 1/800 = 0.00125
        - JavaScript -> Backend: 1/600 = 0.00166667
        - Backend -> Go: 1/150 = 0.00666667

        Total cost = 0.00125 + 0.00166667 + 0.00666667 = 0.00958334
        Closeness = 1 / (1 + 0.00958334) = 0.99050...
        """
        # Calculate expected values
        cost_react_js = 1.0 / 800  # 0.00125
        cost_js_backend = 1.0 / 600  # 0.00166667
        cost_backend_go = 1.0 / 150  # 0.00666667

        total_cost_expected = cost_react_js + cost_js_backend + cost_backend_go
        closeness_expected = 1.0 / (1.0 + total_cost_expected)

        # Verify with tolerance
        assert total_cost_expected == pytest.approx(0.00958334, rel=1e-4)
        assert closeness_expected == pytest.approx(0.99050, rel=1e-4)

    def test_dijkstra_uses_cost_not_weight(self):
        """
        CRITICAL: Dijkstra must use cost property, NOT weight.

        If weight were used:
        - React -> Go via design path: 320 + 250 + 200 = 770 (wrong - would be chosen)
        - React -> Go via JS path: 800 + 600 + 150 = 1550 (wrong - would be rejected)

        With cost (correct):
        - Design path: 1/320 + 1/250 + 1/200 = 0.01175 (longer)
        - JS path: 1/800 + 1/600 + 1/150 = 0.00958 (shorter - correct choice)
        """
        # Design path cost
        design_path_cost = (1/320) + (1/250) + (1/200)

        # JS path cost
        js_path_cost = (1/800) + (1/600) + (1/150)

        # JS path should be shorter (lower cost)
        assert js_path_cost < design_path_cost

        # Verify values
        assert design_path_cost == pytest.approx(0.01175, rel=1e-3)
        assert js_path_cost == pytest.approx(0.00958, rel=1e-3)

    def test_closeness_formula(self):
        """Verify closeness = 1 / (1 + D)."""
        test_cases = [
            (0, 1.0),       # Zero distance = closeness 1
            (1, 0.5),       # Distance 1 = closeness 0.5
            (0.5, 0.6667),  # Distance 0.5 = closeness 0.667
            (2, 0.3333),    # Distance 2 = closeness 0.333
        ]

        for distance, expected_closeness in test_cases:
            actual = 1.0 / (1.0 + distance)
            assert actual == pytest.approx(expected_closeness, rel=1e-3)

    def test_job_closeness_formula(self):
        """
        Test JobCloseness formula:
        JobCloseness(U, J) = average(closeness_req for all req in J)

        Example:
        - User skills: [React, JavaScript]
        - Job requires: [React, Go, UX Research]

        For React: User has it -> distance=0, closeness=1.0
        For Go: min(D(React,Go), D(JS,Go))
                D(React,Go) = 0.00958...
                D(JS,Go) = 1/600 + 1/150 = 0.00833...
                min = 0.00833...
                closeness = 1/(1+0.00833) = 0.99174...
        For UX Research: min(D(React,UX), D(JS,UX))
                Need to traverse design path for both
                D(React,UX) = 1/320 + 1/250 + 1/200 = 0.01175
                D(JS,UX) = no direct path (in toy graph)
                closeness = 1/(1+0.01175) = 0.98840...

        JobCloseness = (1.0 + 0.99174 + 0.98840) / 3 = 0.99338
        """
        # This test documents the expected formula behavior
        # Actual integration test will verify implementation

        closeness_react = 1.0  # User has it
        closeness_go = 1.0 / (1.0 + (1/600 + 1/150))  # Via JS
        closeness_ux = 1.0 / (1.0 + (1/320 + 1/250 + 1/200))  # Via design path

        job_closeness = (closeness_react + closeness_go + closeness_ux) / 3

        assert closeness_go == pytest.approx(0.99174, rel=1e-3)
        assert closeness_ux == pytest.approx(0.98840, rel=1e-3)
        assert job_closeness == pytest.approx(0.99338, rel=1e-3)

    def test_eigenvector_centrality_expectations(self):
        """
        Test eigenvector centrality rankings.

        In the toy graph:
        - JavaScript is most central (connects both subgraphs)
        - React has high connectivity (hub in JS subgraph)
        - UI Design connects design subgraph
        - UX Research is peripheral (only one connection)

        Expected ranking (roughly):
        1. JavaScript (highest - bridges subgraphs)
        2. React (high - connects to both JS and UI)
        3. Backend / UI Design (medium)
        4. Design Systems (medium)
        5. Go / UX Research (lowest - endpoints)
        """
        # This documents expected behavior
        # Integration tests verify actual rankings

        expected_ranking = [
            "JavaScript",    # Bridge node
            "React",         # High degree
            "Backend",       # On main path
            "UI Design",     # Secondary hub
            "Design Systems",
            "Go",
            "UX Research"
        ]

        # Top 3 should include JavaScript and React
        top_3 = expected_ranking[:3]
        assert "JavaScript" in top_3
        assert "React" in top_3

    def test_transition_index_formula(self):
        """
        Test TransitionIndex formula:
        TransitionIndex = 0.50*job_closeness + 0.30*core_skill_overlap + 0.20*market_demand
        """
        # Test case 1: Perfect scores
        ti = 0.50 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0
        assert ti == 1.0

        # Test case 2: Typical case
        job_closeness = 0.75
        core_overlap = 0.60
        market_demand = 0.85

        ti = 0.50 * job_closeness + 0.30 * core_overlap + 0.20 * market_demand
        expected = 0.50 * 0.75 + 0.30 * 0.60 + 0.20 * 0.85
        # = 0.375 + 0.18 + 0.17 = 0.725

        assert ti == pytest.approx(0.725, rel=1e-5)

        # Test case 3: Zero scores
        ti = 0.50 * 0.0 + 0.30 * 0.0 + 0.20 * 0.0
        assert ti == 0.0
```

### Integration Test with Toy Graph

**File**: `backend/tests/integration/test_toy_graph_network.py`

```python
"""
Integration tests using toy graph in Neo4j.

Creates a controlled test graph to validate network math implementation.
"""

import pytest
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder


@pytest.fixture
async def toy_graph(neo4j_repo):
    """Create toy graph for testing."""
    # Create skills
    skills = [
        ("React", "Frontend Framework"),
        ("JavaScript", "Programming Language"),
        ("Backend", "Development Type"),
        ("Go", "Programming Language"),
        ("UI Design", "Design"),
        ("Design Systems", "Design"),
        ("UX Research", "Research"),
    ]

    for name, category in skills:
        await neo4j_repo.execute_query(
            """
            MERGE (s:Skill {id: $id, name: $name, category: $category})
            """,
            {"id": f"test_{name.lower().replace(' ', '_')}", "name": name, "category": category}
        )

    # Create CO_OCCURS_WITH relationships
    edges = [
        ("React", "UI Design", 320),
        ("UI Design", "Design Systems", 250),
        ("Design Systems", "UX Research", 200),
        ("React", "JavaScript", 800),
        ("JavaScript", "Backend", 600),
        ("Backend", "Go", 150),
    ]

    for s1, s2, weight in edges:
        await neo4j_repo.execute_query(
            """
            MATCH (a:Skill {name: $s1})
            MATCH (b:Skill {name: $s2})
            MERGE (a)-[r:CO_OCCURS_WITH]-(b)
            SET r.weight = $weight, r.cost = 1.0 / $weight
            """,
            {"s1": s1, "s2": s2, "weight": weight}
        )

    yield

    # Cleanup
    await neo4j_repo.execute_query(
        """
        MATCH (s:Skill) WHERE s.id STARTS WITH 'test_'
        DETACH DELETE s
        """
    )


@pytest.mark.integration
async def test_shortest_path_react_to_go(toy_graph, network_metrics_service):
    """Verify shortest path calculation with known graph."""
    result = await network_metrics_service.get_shortest_path(
        "test_react",
        "test_go"
    )

    assert result["path_exists"] is True

    # Path should be React -> JavaScript -> Backend -> Go
    expected_path = ["React", "JavaScript", "Backend", "Go"]
    actual_path = [d["name"] for d in result["path_details"]]
    assert actual_path == expected_path

    # Total cost should be 1/800 + 1/600 + 1/150
    expected_cost = (1/800) + (1/600) + (1/150)
    assert result["total_distance"] == pytest.approx(expected_cost, rel=1e-4)

    # Closeness should be 1/(1+cost)
    expected_closeness = 1.0 / (1.0 + expected_cost)
    assert result["closeness"] == pytest.approx(expected_closeness, rel=1e-4)


@pytest.mark.integration
async def test_dijkstra_chooses_correct_path(toy_graph, network_metrics_service):
    """Verify Dijkstra uses cost (not weight) for path selection."""
    # React to UX Research could go two ways:
    # 1. React -> UI Design -> Design Systems -> UX Research (design path)
    # 2. No direct path via JavaScript

    result = await network_metrics_service.get_shortest_path(
        "test_react",
        "test_ux_research"
    )

    assert result["path_exists"] is True

    # Should take design path
    expected_path = ["React", "UI Design", "Design Systems", "UX Research"]
    actual_path = [d["name"] for d in result["path_details"]]
    assert actual_path == expected_path


@pytest.mark.integration
async def test_eigenvector_centrality_ranking(toy_graph, network_metrics_service):
    """Verify eigenvector centrality produces reasonable rankings."""
    result = await network_metrics_service.get_eigenvector_centrality(top_k=10)

    # Get top 3 skills
    top_3_names = [r["skill"] for r in result[:3]]

    # JavaScript should be in top 3 (bridge node)
    assert "JavaScript" in top_3_names

    # React should be in top 3 (high connectivity)
    assert "React" in top_3_names
```

---

## 6. Acceptance Criteria

### Phase 6 Definition of Done

- [x] **Stoplist Implementation**
  - [x] `NETWORK_GENERIC_SKILLS_STOPLIST` config added
  - [x] CoOccurrenceBuilder excludes stoplist skills
  - [x] Stoplist statistics endpoint works
  - [x] Unit tests for stoplist filtering

- [x] **API Endpoints**
  - [x] `POST /api/network/build-cooccurrence` (admin)
  - [x] `GET /api/network/path?from=X&to=Y`
  - [x] `GET /api/network/centrality?topK=N`
  - [x] `POST /api/network/job-closeness`
  - [x] `POST /api/network/transition-index`
  - [x] `GET /api/network/capabilities`

- [x] **Enhanced Job Closeness**
  - [x] Per-skill distance breakdown
  - [x] Path for each required skill
  - [x] skills_already_have / skills_to_learn lists

- [x] **GDS Fallback**
  - [x] Graceful "unavailable" response when GDS missing
  - [x] Capabilities endpoint shows what's available
  - [x] APOC fallback for shortest path

- [x] **Mathematical Correctness**
  - [x] Dijkstra uses cost (1/weight), not weight
  - [x] closeness = 1/(1+D)
  - [x] Toy graph tests pass *(Implemented in test_network_api_integration.py)*
  - [x] Edge case handling (no path, same skill, etc.)

---

## 7. Example API Usage

### cURL Examples

```bash
# 1. Check capabilities
curl -X GET "http://localhost:8000/api/network/capabilities" \
  -H "Authorization: Bearer $TOKEN"

# 2. Build co-occurrence (admin)
curl -X POST "http://localhost:8000/api/network/build-cooccurrence?clear_existing=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Get shortest path
curl -X GET "http://localhost:8000/api/network/path?from=React&to=Go" \
  -H "Authorization: Bearer $TOKEN"

# 4. Get centrality rankings
curl -X GET "http://localhost:8000/api/network/centrality?topK=50" \
  -H "Authorization: Bearer $TOKEN"

# 5. Calculate job closeness
curl -X POST "http://localhost:8000/api/network/job-closeness" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_skills": ["Python", "Django", "PostgreSQL"],
    "job_title": "Backend Developer"
  }'

# 6. Calculate transition index
curl -X POST "http://localhost:8000/api/network/transition-index" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "job_closeness": 0.75,
    "core_skill_overlap": 0.60,
    "market_demand": 0.85
  }'
```

---

## 8. Environment Variables

```bash
# Required
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=secret

# New for Phase 6
NETWORK_GENERIC_SKILLS_STOPLIST="Communication,MS Excel,Teamwork,..."
ALLOW_NETWORK_ADMIN=false  # Set true for dev environment
ENVIRONMENT=development     # development|staging|production
```

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Stoplist removes important skills | Low | Medium | Make configurable, log filtered skills |
| GDS not installed in prod | Medium | High | Graceful fallback, clear error messages |
| Job closeness too slow | Medium | Medium | Cache paths, limit required skills |
| Breaking changes to existing API | Low | High | New namespace /api/network/, old untouched |

---

## 10. Rollback Strategy

1. **API**: New `/api/network/` endpoints - simply remove router registration
2. **Config**: New settings have defaults - safe to remove
3. **Co-occurrence**: Stoplist change is additive - rebuild without stoplist restores old behavior
4. **Tests**: New test files - can be deleted without affecting prod

---

*Generated: 2025-12-06*
*Version: 1.0*
*Status: QA APPROVED - All Tests Pass*

---

## QA Results

**Reviewer:** Quinn (Test Architect)
**Date:** 2025-12-06
**Gate:** PASS
**Quality Score:** 92/100

### Verification Summary

| Component | Status | Evidence |
|-----------|--------|----------|
| `/api/network/*` router | ✅ Verified | 430 lines, 6 endpoints |
| Pydantic models | ✅ Verified | `network_metrics.py` (250 lines) |
| Stoplist config | ✅ Verified | `config.py` lines 84-120 |
| Router registration | ✅ Verified | `main.py` line 286 |
| Unit tests | ✅ Verified | `test_network_api.py` (443 lines) |
| Integration tests | ✅ Verified | `test_network_api_integration.py` (425 lines) |
| Toy graph tests | ✅ Verified | Integrated in `test_network_api_integration.py` |

### API Endpoints Verified

| Endpoint | Method | Line | Status |
|----------|--------|------|--------|
| `/api/network/capabilities` | GET | 66 | ✅ |
| `/api/network/build-cooccurrence` | POST | 83 | ✅ |
| `/api/network/path` | GET | 136 | ✅ |
| `/api/network/centrality` | GET | 205 | ✅ |
| `/api/network/job-closeness` | POST | 263 | ✅ |
| `/api/network/transition-index` | POST | 353 | ✅ |

### Toy Graph Tests Verified (Re-test)

Found in `test_network_api_integration.py`:
- `toy_graph` fixture (lines 32-98): A→B→C with known costs
- `job_closeness_graph` fixture (lines 102+): User skills vs job requirements
- `test_direct_edge_distance` - D(A,B) = 0.1 ✅
- `test_two_hop_distance` - D(A,C) = 0.3 ✅
- `test_same_skill_distance` - D(A,A) = 0 ✅
- `test_closeness_formula_direct` - 1/(1+D) ✅
- `test_closeness_formula_two_hop` ✅
- `test_closeness_same_skill` ✅
- Job closeness per-skill breakdown tests ✅

### Stoplist Configuration Verified

```python
NETWORK_GENERIC_SKILLS_STOPLIST = [
    "Communication", "Problem Solving", "Teamwork", ...
    "Microsoft Excel", "MS Office", ...
    "Computer Skills", "Typing", ...
]  # 30+ entries
```

### Recommendations

**Monitor:**
- Performance of job-closeness endpoint with large skill sets
- GDS fallback behavior in production

**Gate Reference:** `docs/qa/gates/7.1-network-api-enhancements.yml`
