"""Query API request/response models."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class SkillPathResult(BaseModel):
    """Result of skill path calculation."""

    from_skill: str = Field(..., description="Starting skill in the path")
    to_skill: str = Field(..., description="Target skill in the path")
    path: List[str] = Field(..., description="Ordered list of skills in the path")
    total_cost: float = Field(..., description="Sum of edge costs in the path")
    closeness: float = Field(..., description="Closeness metric: 1 / (1 + total_cost)")


class SimilarJobResult(BaseModel):
    """Result of job similarity lookup."""

    job_id: str = Field(..., description="Unique job identifier")
    job_title: str = Field(..., description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    jaccard_score: float = Field(..., description="Jaccard similarity score (0.0 - 1.0)")
    shared_skills: List[str] = Field(default_factory=list, description="Skills shared with query context")


class TopSkillResult(BaseModel):
    """Skill ranked by importance metrics."""

    skill_name: str = Field(..., description="Skill name")
    canonical_name: str = Field(..., description="Canonical skill name")
    centrality: float = Field(..., description="Eigenvector centrality (0.0 - 1.0)")
    demand_count: int = Field(..., description="Number of jobs requiring this skill")


class NetworkInsights(BaseModel):
    """Network-based insights from graph analysis."""

    skill_paths: List[SkillPathResult] = Field(
        default_factory=list,
        description="Skill bridge paths for career transitions"
    )
    similar_jobs: List[SimilarJobResult] = Field(
        default_factory=list,
        description="Similar job opportunities based on skill overlap"
    )
    top_skills: List[TopSkillResult] = Field(
        default_factory=list,
        description="Top skills ranked by centrality and demand"
    )
    transition_feasibility: Optional[float] = Field(
        None,
        description="Overall career transition feasibility score (0.0 - 1.0)"
    )
    graph_stats: Optional[Dict[str, Any]] = Field(
        None,
        description="Graph analysis statistics (nodes, edges, etc.)"
    )


class QueryRequest(BaseModel):
    """Request model for natural language query with validation."""

    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="User's natural language query (3-500 characters)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for tracking query processing in real-time"
    )


class SourceNode(BaseModel):
    """Source node from knowledge graph cited in response."""

    node_type: str = Field(..., description="Type of node (Skill, Job, Company, etc.)")
    node_id: str = Field(..., description="Unique identifier of the node")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")


class QueryResponse(BaseModel):
    """Response model for query execution results."""

    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response from RAG workflow")
    sources: List[SourceNode] = Field(
        default_factory=list,
        description="List of source nodes cited in response"
    )
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (intent, confidence, etc.)"
    )
    constructed_context: Optional[str] = Field(
        default=None,
        description="Full context string passed to LLM (for debugging/transparency)"
    )
    context_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context statistics (token_count, char_count, sections)"
    )
    network_insights: Optional[NetworkInsights] = Field(
        default=None,
        description="Network-based insights from graph analysis (nullable)"
    )
