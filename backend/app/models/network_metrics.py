"""
Pydantic models for network metrics API.

Reference: Network Math Implementation - Phase 2 (02-SERVICES-LAYER.md)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class PathNode(BaseModel):
    """A node in a skill path."""
    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")


class ShortestPathRequest(BaseModel):
    """Request for shortest path between skills."""
    skill_id_1: str = Field(..., description="Source skill ID")
    skill_id_2: str = Field(..., description="Target skill ID")


class ShortestPathResponse(BaseModel):
    """Response for shortest path query."""
    path_exists: bool = Field(..., description="Whether a path was found")
    total_distance: float = Field(..., description="Total cost/distance of path")
    closeness: float = Field(..., ge=0.0, le=1.0, description="Closeness score (1/(1+D))")
    path: List[str] = Field(default_factory=list, description="List of skill IDs in path")
    path_details: List[PathNode] = Field(default_factory=list, description="Detailed path nodes")
    algorithm: str = Field(..., description="Algorithm used for pathfinding")


class ClosenessRequest(BaseModel):
    """Request for closeness calculation."""
    skill_id_1: str = Field(..., description="First skill ID")
    skill_id_2: str = Field(..., description="Second skill ID")


class ClosenessResponse(BaseModel):
    """Response for closeness calculation."""
    skill_id_1: str = Field(..., description="First skill ID")
    skill_id_2: str = Field(..., description="Second skill ID")
    closeness: float = Field(..., ge=0.0, le=1.0, description="Closeness score (0-1)")
    distance: float = Field(..., description="Dijkstra distance")


class JobClosenessRequest(BaseModel):
    """Request for job closeness calculation."""
    job_id: str = Field(..., description="Job ID")


class JobClosenessResponse(BaseModel):
    """Response for job closeness calculation."""
    job_id: str = Field(..., description="Job ID")
    job_closeness: float = Field(..., ge=0.0, le=1.0, description="Average closeness of skill pairs")
    skill_count: int = Field(..., ge=0, description="Number of skills in job")
    pair_count: int = Field(..., ge=0, description="Number of skill pairs analyzed")
    skills: List[str] = Field(default_factory=list, description="List of skill IDs")


class CentralitySkill(BaseModel):
    """A skill with its centrality score."""
    skill_id: str = Field(..., description="Skill ID")
    skill_name: str = Field(..., description="Skill name")
    centrality_score: float = Field(..., ge=0.0, description="Eigenvector centrality score")


class CentralityListRequest(BaseModel):
    """Request for centrality list."""
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of skills to return")
    use_cache: bool = Field(True, description="Whether to use cached results")


class CentralityListResponse(BaseModel):
    """Response for centrality list query."""
    skills: List[CentralitySkill] = Field(default_factory=list, description="Skills ranked by centrality")
    count: int = Field(..., description="Number of skills returned")
    algorithm: str = Field("eigenvector", description="Centrality algorithm used")


class TransitionRequest(BaseModel):
    """Request for transition index calculation."""
    source_skills: List[str] = Field(..., min_length=1, description="Current skill IDs")
    target_job_id: str = Field(..., description="Target job ID")


class TransitionDetails(BaseModel):
    """Details of transition analysis."""
    source_skills_count: int = Field(..., description="Number of source skills")
    target_skills_count: int = Field(..., description="Number of target job skills")
    overlapping_skills: List[str] = Field(default_factory=list, description="Skills in both sets")
    skills_to_learn: List[str] = Field(default_factory=list, description="Skills needed but not had")
    jobs_with_target_skills: int = Field(..., description="Market demand indicator")


class TransitionResponse(BaseModel):
    """Response for transition index calculation."""
    transition_index: float = Field(..., ge=0.0, le=1.0, description="Composite transition score")
    avg_closeness: float = Field(..., ge=0.0, le=1.0, description="Average closeness component (50%)")
    core_skill_overlap: float = Field(..., ge=0.0, le=1.0, description="Skill overlap component (30%)")
    market_demand: float = Field(..., ge=0.0, le=1.0, description="Market demand component (20%)")
    details: TransitionDetails = Field(..., description="Detailed transition analysis")


class CoOccurringSkill(BaseModel):
    """A skill that co-occurs with the queried skill."""
    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")
    weight: int = Field(..., description="Co-occurrence weight (number of jobs)")


class SkillMetricsRequest(BaseModel):
    """Request for skill metrics."""
    skill_id: str = Field(..., description="Skill ID")


class SkillMetricsResponse(BaseModel):
    """Comprehensive metrics for a single skill."""
    skill_id: str = Field(..., description="Skill ID")
    skill_name: str = Field(..., description="Skill name")
    co_occurrence_count: int = Field(..., ge=0, description="Number of co-occurring skills")
    total_weight: int = Field(..., ge=0, description="Sum of all co-occurrence weights")
    avg_weight: float = Field(..., ge=0.0, description="Average co-occurrence weight")
    top_co_occurring: List[CoOccurringSkill] = Field(
        default_factory=list,
        description="Top co-occurring skills"
    )


class NetworkStatsResponse(BaseModel):
    """Network-wide statistics."""
    total_skills: int = Field(..., description="Total number of skills in network")
    total_co_occurrences: int = Field(..., description="Total CO_OCCURS_WITH relationships")
    avg_connections_per_skill: float = Field(..., description="Average connections per skill")
    max_weight: int = Field(..., description="Maximum co-occurrence weight")
    avg_weight: float = Field(..., description="Average co-occurrence weight")
    gds_available: bool = Field(..., description="Whether GDS is available")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    skill_id: Optional[str] = Field(None, description="Related skill ID if applicable")


# =============================================================================
# NEW NETWORK API MODELS (Phase 6)
# =============================================================================

class SkillDetail(BaseModel):
    """Detail about a skill in path."""
    id: str = Field(..., description="Skill ID")
    name: str = Field(..., description="Skill name")
    category: Optional[str] = Field(None, description="Skill category")


class PathResponse(BaseModel):
    """Response for shortest path endpoint (/api/network/path)."""
    total_cost: float = Field(..., description="Sum of edge costs along path")
    closeness: float = Field(..., ge=0.0, le=1.0, description="1 / (1 + total_cost)")
    path_skill_names: List[str] = Field(default_factory=list, description="Ordered skill names in path")
    path_details: List[SkillDetail] = Field(default_factory=list, description="Full details for each skill")
    algorithm: str = Field(default="unknown", description="Algorithm used for pathfinding")


class SkillCentrality(BaseModel):
    """Single skill with centrality score."""
    skill: str = Field(..., description="Skill name")
    skill_id: str = Field(..., description="Skill ID")
    score: float = Field(..., ge=0.0, description="Centrality score")


class CentralityResponse(BaseModel):
    """Response for centrality endpoint (/api/network/centrality)."""
    skills: List[SkillCentrality] = Field(default_factory=list, description="Skills ranked by centrality")
    total_returned: int = Field(..., ge=0, description="Number of skills returned")
    algorithm: str = Field(default="eigenvector_gds", description="Algorithm used")


class EnhancedJobClosenessRequest(BaseModel):
    """Request for enhanced job closeness calculation (/api/network/job-closeness)."""
    user_skills: List[str] = Field(..., min_length=1, description="User's current skills")
    job_id: Optional[str] = Field(None, description="Specific job ID")
    job_title: Optional[str] = Field(None, description="Job title to search")


class PerSkillCloseness(BaseModel):
    """Closeness detail for a single required skill."""
    required_skill: str = Field(..., description="Name of the required skill")
    closest_user_skill: str = Field(..., description="User skill closest to this requirement")
    distance: float = Field(..., description="Dijkstra distance (-1 if unreachable)")
    closeness: float = Field(..., ge=0.0, le=1.0, description="1 / (1 + distance)")
    path: List[str] = Field(default_factory=list, description="Path from user skill to required")
    user_already_has: bool = Field(default=False, description="Whether user already has this skill")


class EnhancedJobClosenessResponse(BaseModel):
    """Enhanced response for job closeness calculation with per-skill breakdown."""
    job_id: Optional[str] = Field(None, description="Job ID if available")
    job_title: str = Field(..., description="Job title")
    overall_closeness: float = Field(..., ge=0.0, le=1.0, description="Average closeness across all required skills")
    per_skill_details: List[PerSkillCloseness] = Field(default_factory=list, description="Breakdown per required skill")
    skills_already_have: List[str] = Field(default_factory=list, description="User skills matching job requirements")
    skills_to_learn: List[str] = Field(default_factory=list, description="Job requirements user doesn't have")
    required_skills_count: int = Field(..., ge=0, description="Total required skills for job")
    matched_skills_count: int = Field(..., ge=0, description="Skills user already has")


class TransitionIndexDirectRequest(BaseModel):
    """Request for transition index calculation with pre-computed values."""
    job_closeness: float = Field(..., ge=0, le=1, description="From job-closeness endpoint")
    core_skill_overlap: float = Field(..., ge=0, le=1, description="% of core skills user has")
    market_demand: float = Field(..., ge=0, le=1, description="Market demand score (0-1)")


class TransitionIndexDirectResponse(BaseModel):
    """Response for transition index calculation."""
    transition_index: float = Field(..., ge=0.0, le=1.0, description="Combined heuristic score (0-1)")
    interpretation: str = Field(..., description="Human-readable assessment")
    breakdown: Dict[str, float] = Field(..., description="Component contributions")
    weights: Dict[str, float] = Field(..., description="Formula weights used")
    note: str = Field(..., description="Disclaimer about heuristic nature")


class BuildCooccurrenceResponse(BaseModel):
    """Response for admin build endpoint (/api/network/build-cooccurrence)."""
    status: str = Field(..., description="Build status (success/failed)")
    relationships_created: int = Field(..., ge=0, description="Number of relationships created")
    relationships_deleted: int = Field(default=0, ge=0, description="Number of relationships deleted")
    duration_seconds: float = Field(..., ge=0, description="Build duration in seconds")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Build statistics")
    stoplist_stats: Dict[str, Any] = Field(default_factory=dict, description="Stoplist impact statistics")


class GDSUnavailableResponse(BaseModel):
    """Response when GDS is not installed."""
    available: bool = Field(default=False, description="Always false for this response")
    message: str = Field(..., description="Explanation of unavailability")
    suggestion: str = Field(..., description="What user can do")


class NetworkCapabilities(BaseModel):
    """Available network math capabilities based on installed plugins."""
    gds_available: bool = Field(..., description="Whether GDS is installed")
    gds_version: Optional[str] = Field(None, description="GDS version if available")
    apoc_available: bool = Field(..., description="Whether APOC is available")
    capabilities: Dict[str, bool] = Field(..., description="Feature availability map")
    fallback_mode: bool = Field(..., description="Using APOC instead of GDS")
    limited_mode: bool = Field(..., description="Neither GDS nor APOC available")
