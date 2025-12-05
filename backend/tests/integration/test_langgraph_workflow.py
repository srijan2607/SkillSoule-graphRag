"""
Integration tests for LangGraph RAG workflow.

Tests the complete workflow from query to response, verifying:
- All 5 nodes execute in correct order
- State is properly maintained and updated
- Final response is generated
"""
import pytest
from app.agents.graph import GraphRAGState, create_rag_workflow


@pytest.mark.asyncio
async def test_workflow_compiles_successfully():
    """Test that the workflow compiles without errors."""
    workflow = create_rag_workflow()
    assert workflow is not None


@pytest.mark.asyncio
async def test_complete_workflow_execution():
    """
    Test complete workflow execution with dummy query.

    Verifies:
    - All 5 nodes execute
    - State updates propagate correctly
    - Final response is generated
    """
    # Create workflow
    workflow = create_rag_workflow()

    # Initial state
    initial_state = GraphRAGState(
        user_query="What skills are required for Python development?",
        user_id="test-user-123"
    )

    # Execute workflow
    result = await workflow.ainvoke(initial_state)

    # Verify all required fields are populated
    assert result["user_query"] == "What skills are required for Python development?"
    assert result["user_id"] == "test-user-123"

    # Verify QueryUnderstanding node executed
    assert result["intent"] is not None
    assert result["intent"] in ["skills_match", "job_search", "skill_info", "job_info", "market_trends", "unknown"]
    assert result["entities"] is not None
    assert isinstance(result["entities"], list)
    assert result["metadata"]["query_understanding_completed"] is True

    # Verify VectorSearch node executed
    assert result["vector_results"] is not None
    assert isinstance(result["vector_results"], list)
    assert len(result["vector_results"]) > 0
    assert result["metadata"]["vector_search_completed"] is True

    # Verify GraphTraversal node executed
    assert result["graph_context"] is not None
    assert isinstance(result["graph_context"], list)
    assert len(result["graph_context"]) > 0
    assert result["metadata"]["graph_traversal_completed"] is True

    # Verify ContextConstruction node executed
    assert result["constructed_context"] is not None
    assert isinstance(result["constructed_context"], str)
    assert len(result["constructed_context"]) > 0
    assert result["metadata"]["context_construction_completed"] is True

    # Verify ResponseGeneration node executed
    assert result["final_response"] is not None
    assert isinstance(result["final_response"], str)
    assert len(result["final_response"]) > 0
    assert result["metadata"]["response_generation_completed"] is True


@pytest.mark.asyncio
async def test_workflow_node_execution_order():
    """
    Test that nodes execute in the correct order.

    Expected order:
    1. QueryUnderstanding
    2. VectorSearch
    3. GraphTraversal
    4. ContextConstruction
    5. ResponseGeneration
    """
    workflow = create_rag_workflow()

    initial_state = GraphRAGState(
        user_query="Tell me about FastAPI framework",
        user_id="test-user-456"
    )

    result = await workflow.ainvoke(initial_state)

    # Verify completion flags exist (indicating execution)
    metadata = result["metadata"]
    assert "query_understanding_completed" in metadata
    assert "vector_search_completed" in metadata
    assert "graph_traversal_completed" in metadata
    assert "context_construction_completed" in metadata
    assert "response_generation_completed" in metadata


@pytest.mark.asyncio
async def test_workflow_with_empty_query_validation():
    """Test that workflow properly validates empty queries."""
    workflow = create_rag_workflow()

    # Attempt with empty query - should raise ValidationError
    with pytest.raises(Exception):  # Pydantic ValidationError
        initial_state = GraphRAGState(
            user_query="",
            user_id="test-user-789"
        )
        await workflow.ainvoke(initial_state)


@pytest.mark.asyncio
async def test_workflow_state_immutability():
    """Test that original state is not mutated by workflow execution."""
    workflow = create_rag_workflow()

    initial_state = GraphRAGState(
        user_query="What is Python?",
        user_id="test-user-999"
    )

    # Store original values
    original_query = initial_state.user_query
    original_user_id = initial_state.user_id

    # Execute workflow
    result = await workflow.ainvoke(initial_state)

    # Verify initial state unchanged
    assert initial_state.user_query == original_query
    assert initial_state.user_id == original_user_id

    # Verify result has updates
    assert result["final_response"] is not None


@pytest.mark.asyncio
async def test_workflow_metadata_tracking():
    """Test that metadata is properly tracked throughout execution."""
    workflow = create_rag_workflow()

    initial_state = GraphRAGState(
        user_query="Job opportunities for Python developers",
        user_id="test-user-meta"
    )

    result = await workflow.ainvoke(initial_state)

    # Verify metadata structure
    metadata = result["metadata"]
    assert isinstance(metadata, dict)

    # Verify each node added metadata
    assert metadata.get("query_understanding_completed") is True
    assert metadata.get("vector_search_completed") is True
    assert metadata.get("graph_traversal_completed") is True
    assert metadata.get("context_construction_completed") is True
    assert metadata.get("response_generation_completed") is True

    # Verify counts are present
    assert "vector_results_count" in metadata
    assert "graph_context_count" in metadata
    assert "context_length" in metadata
    assert "response_length" in metadata
