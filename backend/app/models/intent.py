"""
Intent analysis models for deep query understanding.

Supports multi-layer intent classification with semantic analysis,
entity extraction, and transparent reasoning trails.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from datetime import datetime


class Entity(BaseModel):
    """
    Extracted entity from user query with provenance tracking.

    Entities can be extracted through multiple strategies:
    - exact_match: Token found directly in graph
    - fuzzy_match: Levenshtein distance match with known entities
    - semantic_match: Embedding similarity to graph entities
    - contextual_expansion: Inferred from graph relationships
    """

    type: str = Field(..., description="Entity type: skill, job, company, location, etc.")
    value: str = Field(..., description="Entity value/name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    source: str = Field(
        ...,
        description="Extraction method: exact_match, fuzzy_match, semantic_match, contextual_expansion",
    )
    graph_node_id: Optional[str] = Field(
        default=None, description="Neo4j node ID if entity exists in graph"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional entity metadata"
    )


class QueryExecutionStep(BaseModel):
    """
    Individual step in query execution plan.

    Each step represents a specific query (Neo4j vector, Cypher, SQL)
    with transparent reasoning about why it was chosen.
    """

    step_number: int = Field(..., description="Execution order (1-indexed)")
    query_type: str = Field(
        ..., description="Query type: neo4j_vector, neo4j_cypher, sql_aggregation"
    )
    intent: str = Field(..., description="Intent this step addresses")
    reasoning: str = Field(..., description="Why this query step is needed")
    expected_outcome: str = Field(..., description="What we expect to find")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Query parameters"
    )
    alternatives_considered: List[str] = Field(
        default_factory=list, description="Alternative query approaches considered"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in query choice"
    )


class QueryExecutionPlan(BaseModel):
    """
    Complete query execution plan with multiple steps.

    Represents the strategy for answering a user query through
    a series of graph/database operations.
    """

    steps: List[QueryExecutionStep] = Field(..., description="Ordered execution steps")
    total_estimated_time_ms: float = Field(
        default=0.0, description="Estimated total execution time"
    )
    complexity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Query complexity (0=simple, 1=very complex)",
    )
    requires_multi_hop: bool = Field(
        default=False, description="Whether graph traversal requires multiple hops"
    )


class ReasoningStep(BaseModel):
    """
    Individual reasoning step in decision-making process.

    Provides transparency into how the system arrived at conclusions.
    """

    step: int = Field(..., description="Step number in reasoning chain")
    decision: str = Field(..., description="What was decided")
    rationale: str = Field(..., description="Why this decision was made")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in decision")
    alternatives_considered: List[str] = Field(
        default_factory=list, description="Alternative decisions considered"
    )
    data_used: List[str] = Field(
        default_factory=list, description="What data informed this decision"
    )


class IntentAnalysisResult(BaseModel):
    """
    Complete result of multi-layer intent analysis.

    Combines syntactic, semantic, and entity-informed analysis
    to deeply understand user query intent.
    """

    # Primary intent classification
    primary_intent: str = Field(..., description="Primary detected intent")
    primary_confidence: float = Field(..., ge=0.0, le=1.0, description="Primary intent confidence")

    # Multi-intent support
    secondary_intents: List[Tuple[str, float]] = Field(
        default_factory=list,
        description="Secondary intents with confidence scores [(intent, confidence), ...]",
    )

    # All detected intents (for backward compatibility and filtering)
    all_intents: List[str] = Field(default_factory=list, description="All detected intent types")

    # Extracted entities
    entities: List[Entity] = Field(default_factory=list, description="Extracted entities")

    # Query execution plan
    query_plan: QueryExecutionPlan = Field(..., description="Planned query execution strategy")

    # Reasoning transparency
    reasoning_trail: List[ReasoningStep] = Field(
        default_factory=list, description="Transparent decision-making trail"
    )

    # Metadata
    analysis_time_ms: float = Field(default=0.0, description="Time taken for analysis")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Layer-specific results (for debugging)
    syntactic_intents: List[str] = Field(
        default_factory=list, description="Intents from syntactic analysis (Layer 1)"
    )
    semantic_intents: List[Tuple[str, float]] = Field(
        default_factory=list, description="Intents from semantic analysis (Layer 2)"
    )


class IntentArchetype(BaseModel):
    """
    Canonical query examples for each intent type.

    Used for semantic intent classification via embedding similarity.
    """

    intent_type: str = Field(..., description="Intent type identifier")
    canonical_queries: List[str] = Field(..., description="Example queries for this intent")
    embedding: Optional[List[float]] = Field(
        default=None, description="Precomputed embedding (384-dim)"
    )
    keywords: List[str] = Field(default_factory=list, description="Key indicator words")
    confidence_threshold: float = Field(
        default=0.7, description="Minimum similarity score for this intent"
    )


class ExecutedQuery(BaseModel):
    """
    Record of executed query with monitoring integration.

    Captured from monitoring system for transparency.
    """

    query_id: str = Field(..., description="Unique query identifier")
    query_text: str = Field(..., description="Actual query text (Cypher/SQL)")
    query_type: str = Field(
        ..., description="Query type: neo4j_vector, neo4j_cypher, sql_aggregation"
    )
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    execution_time_ms: float = Field(..., description="Actual execution time")
    result_count: int = Field(..., description="Number of results returned")
    status: str = Field(..., description="Status: success, error, timeout")
    reasoning: str = Field(..., description="Why this query was chosen")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueryResponse(BaseModel):
    """
    Structured query response with full transparency.

    Complete response including intent analysis, executed queries,
    results, and metadata for user-facing display.
    """

    # Intent Analysis Results
    intent_analysis: IntentAnalysisResult

    # Query Execution Details
    executed_queries: List[ExecutedQuery] = Field(
        default_factory=list, description="All queries executed"
    )

    # Data Results (Structured)
    primary_findings: Dict[str, Any] = Field(
        default_factory=dict, description="Main answer data"
    )
    supporting_data: Dict[str, Any] = Field(
        default_factory=dict, description="Context and relationships"
    )

    # Metadata & Transparency
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall result confidence")
    data_limitations: List[str] = Field(
        default_factory=list, description="What data is missing or uncertain"
    )

    # Performance Metrics
    total_time_ms: float = Field(..., description="Total query processing time")
    breakdown_ms: Dict[str, float] = Field(
        default_factory=dict, description="Per-stage timing breakdown"
    )
    nodes_accessed: int = Field(default=0, description="Graph nodes accessed")
    relationships_traversed: int = Field(default=0, description="Graph relationships traversed")
    cache_hit_rate: float = Field(default=0.0, description="Cache hit rate (0.0-1.0)")

    # Human-Readable Response (Generated from structured data)
    formatted_response: str = Field(..., description="Markdown-formatted response for display")

    # Sources
    sources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Source nodes cited in response"
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)
