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
                "general",
                "unknown",
            ]
            for intent in v:
                if intent not in allowed_intents:
                    raise ValueError(f"intent must be one of {allowed_intents}, got: {intent}")
        return v


def create_rag_workflow():
    """
    Create and compile the GraphRAG workflow.

    Returns:
        Compiled StateGraph ready for invocation
    """
    from langgraph.graph import StateGraph, END
    from app.agents.nodes.query_understanding import query_understanding_node
    from app.agents.nodes.vector_search import vector_search_node
    from app.agents.nodes.graph_traversal import graph_traversal_node
    from app.agents.nodes.context_construction import context_construction_node
    from app.agents.nodes.response_generation import response_generation_node

    # Create the state graph
    workflow = StateGraph(GraphRAGState)

    # Add nodes
    workflow.add_node("understand_query", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)
    workflow.add_node("construct_context", context_construction_node)
    workflow.add_node("generate_response", response_generation_node)

    # Define linear flow
    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")
    workflow.add_edge("graph_traversal", "construct_context")
    workflow.add_edge("construct_context", "generate_response")
    workflow.add_edge("generate_response", END)

    # Compile the graph
    return workflow.compile()
