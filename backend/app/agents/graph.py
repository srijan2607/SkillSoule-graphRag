"""
LangGraph workflow definition for GraphRAG query pipeline.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, ConfigDict


class GraphRAGState(BaseModel):
    """
    State schema for the GraphRAG workflow.

    Tracks the progression of a user query through the RAG pipeline:
    QueryUnderstanding → VectorSearch → GraphTraversal → ContextConstruction → ResponseGeneration
    """

    model_config = ConfigDict(
        extra="forbid",  # Catch field name typos immediately
        validate_assignment=True,  # Validate on state updates
    )

    # Required fields
    user_query: str = Field(..., description="Original user query text")
    user_id: str = Field(..., description="ID of user making the query")

    # Optional fields - populated by workflow nodes
    query_embedding: Optional[List[float]] = Field(
        default=None, description="Embedding vector for the user query (384-dim)"
    )
    intent: Optional[str] = Field(
        default=None, description="Primary classified query intent (backward compatibility)"
    )
    intents: Optional[List[str]] = Field(
        default=None, description="All detected query intents for multi-intent support"
    )
    entities: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Extracted entities from query (skills, jobs, locations, etc.)"
    )
    vector_results: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Results from Neo4j vector similarity search"
    )
    graph_context: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Results from Neo4j graph traversal (relationships, neighbors)"
    )
    network_enrichment: Optional[Dict[str, Any]] = Field(
        default=None, description="Network metrics enrichment (skill paths, centrality, job similarity) - Story 7.4"
    )
    constructed_context: Optional[str] = Field(
        default=None, description="Formatted context string for LLM prompt"
    )
    final_response: Optional[str] = Field(default=None, description="Generated response from LLM")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata (execution times, confidence scores, etc.)",
    )

    @field_validator("user_query")
    @classmethod
    def validate_user_query_not_empty(cls, v: str) -> str:
        """Ensure user query is not empty."""
        if not v or not v.strip():
            raise ValueError("user_query cannot be empty")
        return v.strip()

    # Transition-specific fields (Phase 4)
    transition_path: Optional[Dict[str, Any]] = Field(
        default=None, description="Transition path analysis results"
    )
    source_skills: Optional[List[str]] = Field(
        default=None, description="Source skill IDs for transition"
    )
    target_skills: Optional[List[str]] = Field(
        default=None, description="Target skill IDs for transition"
    )
    closeness_score: Optional[float] = Field(
        default=None, description="Closeness score for transition path"
    )
    transition_index: Optional[float] = Field(
        default=None, description="Composite transition index score"
    )

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v: Optional[str]) -> Optional[str]:
        """Validate intent is one of the allowed values."""
        if v is not None:
            allowed_intents = [
                "skill_requirement",
                "career_path",
                "salary_analysis",
                "skill_relationship",
                "company_query",
                "transition_path",
                "career_transition",  # NEW - Story 7.4
                "skill_bridge",  # NEW - Story 7.4
                "skill_importance",  # NEW - Story 7.4
                "job_similarity",  # NEW - Story 7.4
                "general",
                "unknown",
            ]
            if v not in allowed_intents:
                raise ValueError(f"intent must be one of {allowed_intents}, got: {v}")
        return v

    @field_validator("intents")
    @classmethod
    def validate_intents(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate all intents are allowed values."""
        if v is not None:
            allowed_intents = [
                "skill_requirement",
                "career_path",
                "salary_analysis",
                "skill_relationship",
                "company_query",
                "transition_path",
                "career_transition",  # NEW - Story 7.4
                "skill_bridge",  # NEW - Story 7.4
                "skill_importance",  # NEW - Story 7.4
                "job_similarity",  # NEW - Story 7.4
                "general",
                "unknown",
            ]
            for intent in v:
                if intent not in allowed_intents:
                    raise ValueError(f"intent must be one of {allowed_intents}, got: {intent}")
        return v


def _should_run_transition_metrics(state: GraphRAGState) -> str:
    """
    Routing function to determine if transition_metrics node should run.

    Args:
        state: Current graph state

    Returns:
        "transition_metrics" if transition_path intent detected, else "network_enrichment"
    """
    intents = state.intents or [state.intent] if state.intent else []
    if "transition_path" in intents:
        return "transition_metrics"
    return "network_enrichment"


def create_rag_workflow():
    """
    Create and compile the GraphRAG workflow.

    Story 7.4 Update: Added network_enrichment node after graph_traversal
    to provide network metrics (skill paths, centrality, job similarity).

    Flow:
        understand_query → vector_search → graph_traversal
            → [if transition_path] → transition_metrics → network_enrichment
            → [else] → network_enrichment
        → construct_context → generate_response → END

    Returns:
        Compiled StateGraph ready for invocation
    """
    from langgraph.graph import StateGraph, END
    from app.agents.nodes.query_understanding import query_understanding_node
    from app.agents.nodes.vector_search import vector_search_node
    from app.agents.nodes.graph_traversal import graph_traversal_node
    from app.agents.nodes.transition_metrics import transition_metrics_node
    from app.agents.nodes.network_enrichment import network_enrichment_node  # Story 7.4
    from app.agents.nodes.context_construction import context_construction_node
    from app.agents.nodes.response_generation import response_generation_node

    # Create the state graph
    workflow = StateGraph(GraphRAGState)

    # Add nodes
    workflow.add_node("understand_query", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)
    workflow.add_node("transition_metrics", transition_metrics_node)  # Phase 4
    workflow.add_node("network_enrichment", network_enrichment_node)  # Story 7.4
    workflow.add_node("construct_context", context_construction_node)
    workflow.add_node("generate_response", response_generation_node)

    # Define flow with conditional routing for transition queries
    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")

    # Conditional edge - route to transition_metrics or network_enrichment
    workflow.add_conditional_edges(
        "graph_traversal",
        _should_run_transition_metrics,
        {
            "transition_metrics": "transition_metrics",
            "network_enrichment": "network_enrichment"  # Story 7.4
        }
    )

    # Transition metrics flows to network enrichment
    workflow.add_edge("transition_metrics", "network_enrichment")  # Story 7.4

    # Network enrichment flows to context construction
    workflow.add_edge("network_enrichment", "construct_context")  # Story 7.4

    # Continue with response generation
    workflow.add_edge("construct_context", "generate_response")
    workflow.add_edge("generate_response", END)

    # Compile the graph
    return workflow.compile()
