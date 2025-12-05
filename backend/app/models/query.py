"""Query API request/response models."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


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
