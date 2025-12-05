"""
Unit tests for context construction node.

Tests:
- Context building without truncation
- Token counting
- Context stats generation
- Section formatting
- Large context handling (>4000 tokens)
"""
import pytest
from app.agents.nodes.context_construction import context_construction_node
from app.agents.graph import GraphRAGState
from app.utils.metrics import QueryMetrics


@pytest.fixture
def sample_vector_results():
    """Sample vector search results."""
    return [
        {
            "node_type": "Skill",
            "id": "skill_1",
            "name": "Python",
            "score": 0.95,
            "properties": {
                "description": "High-level programming language",
                "category": "Programming Language"
            }
        },
        {
            "node_type": "Job",
            "id": "job_1",
            "name": "Backend Developer",
            "score": 0.92,
            "properties": {
                "company_name": "Google",
                "salary_min": 1200000,
                "salary_max": 1800000
            }
        }
    ]


@pytest.fixture
def sample_graph_context():
    """Sample graph traversal results."""
    return [
        {
            "node_type": "Skill",
            "id": "skill_2",
            "name": "Django",
            "properties": {"description": "Python web framework"}
        },
        {
            "type": "REQUIRES",
            "properties": {"importance": "critical"}
        },
        {
            "node_type": "Job",
            "id": "job_2",
            "name": "Python Developer",
            "properties": {"company_name": "Amazon"}
        }
    ]


@pytest.mark.asyncio
async def test_context_construction_basic(sample_vector_results, sample_graph_context):
    """Test basic context construction without truncation."""
    # Create state
    metrics = QueryMetrics(
        query_id="test_1",
        user_id="user_1",
        query_text="What skills are needed?"
    )

    state = GraphRAGState(
        user_query="What skills are needed for backend development?",
        user_id="user_1",
        intent="skill_requirement",
        intents=["skill_requirement"],
        entities=[],
        vector_results=sample_vector_results,
        graph_context=sample_graph_context,
        metadata={
            "metrics": metrics,
            "session_id": "session_1"
        }
    )

    # Execute node
    result = await context_construction_node(state)

    # Assertions
    assert "constructed_context" in result
    assert result["constructed_context"] is not None
    assert len(result["constructed_context"]) > 0

    # Check metadata
    assert result["metadata"]["context_construction_completed"] is True
    assert result["metadata"]["context_token_count"] > 0
    assert result["metadata"]["context_char_count"] > 0
    assert result["metadata"]["context_truncated"] is False  # No truncation
    assert result["metadata"]["vector_results_count"] == 2
    assert result["metadata"]["graph_nodes_count"] == 3


@pytest.mark.asyncio
async def test_context_construction_no_truncation_for_large_context():
    """Test that large contexts (>4000 tokens) are NOT truncated."""
    # Create large mock data
    large_vector_results = [
        {
            "node_type": "Skill",
            "id": f"skill_{i}",
            "name": f"Skill {i}",
            "score": 0.9 - (i * 0.01),
            "properties": {
                "description": f"Description for skill {i} " * 20  # Make it long
            }
        }
        for i in range(50)  # 50 skills with long descriptions
    ]

    large_graph_context = [
        {
            "node_type": "Job",
            "id": f"job_{i}",
            "name": f"Job Position {i}",
            "properties": {
                "company_name": f"Company {i}",
                "description": f"Long job description " * 30
            }
        }
        for i in range(100)  # 100 jobs with long descriptions
    ]

    metrics = QueryMetrics(
        query_id="test_2",
        user_id="user_1",
        query_text="Complex query"
    )

    state = GraphRAGState(
        user_query="Tell me everything about backend, frontend, and full stack development",
        user_id="user_1",
        intent="skill_requirement",
        intents=["skill_requirement", "career_path"],
        entities=[],
        vector_results=large_vector_results,
        graph_context=large_graph_context,
        metadata={"metrics": metrics}
    )

    # Execute node
    result = await context_construction_node(state)

    # Assertions
    assert "constructed_context" in result
    context = result["constructed_context"]
    token_count = result["metadata"]["context_token_count"]

    # Context should be large and NOT truncated
    assert token_count > 4000  # Should exceed old limit
    assert result["metadata"]["context_truncated"] is False
    assert "truncated" not in context.lower() or "no truncation" in context.lower()

    # All data should be present (no progressive truncation)
    assert len(context) > 10000  # Large context


@pytest.mark.asyncio
async def test_context_stats_accuracy():
    """Test that context_stats are accurately calculated."""
    vector_results = [
        {"node_type": "Skill", "id": "s1", "name": "Python", "score": 0.9, "properties": {}}
    ]
    graph_context = [
        {"node_type": "Job", "id": "j1", "name": "Developer", "properties": {}}
    ]

    metrics = QueryMetrics(
        query_id="test_3",
        user_id="user_1",
        query_text="Test query"
    )

    state = GraphRAGState(
        user_query="Test query for stats",
        user_id="user_1",
        intent="general",
        intents=["general"],
        entities=[],
        vector_results=vector_results,
        graph_context=graph_context,
        metadata={"metrics": metrics}
    )

    result = await context_construction_node(state)

    # Check stats
    metadata = result["metadata"]
    context = result["constructed_context"]

    assert metadata["context_token_count"] > 0
    assert metadata["context_char_count"] == len(context)
    assert metadata["vector_results_count"] == len(vector_results)
    assert metadata["graph_nodes_count"] == len(graph_context)


@pytest.mark.asyncio
async def test_context_with_empty_results():
    """Test context construction with empty vector/graph results."""
    metrics = QueryMetrics(
        query_id="test_4",
        user_id="user_1",
        query_text="Query with no results"
    )

    state = GraphRAGState(
        user_query="What is the meaning of life?",
        user_id="user_1",
        intent="general",
        intents=["general"],
        entities=[],
        vector_results=[],  # Empty
        graph_context=[],   # Empty
        metadata={"metrics": metrics}
    )

    result = await context_construction_node(state)

    # Should still construct context with query section
    assert "constructed_context" in result
    assert "What is the meaning of life?" in result["constructed_context"]
    assert result["metadata"]["context_token_count"] > 0
    assert result["metadata"]["vector_results_count"] == 0
    assert result["metadata"]["graph_nodes_count"] == 0


@pytest.mark.asyncio
async def test_context_includes_graph_statistics_header():
    """Test that context includes graph statistics header when graph data exists."""
    vector_results = [{"node_type": "Skill", "id": "s1", "name": "Python", "score": 0.9, "properties": {}}]
    graph_context = [
        {"node_type": "Skill", "id": "s2", "name": "Django", "properties": {}},
        {"type": "REQUIRES", "properties": {}}
    ]

    metrics = QueryMetrics(query_id="test_5", user_id="user_1", query_text="Test")

    state = GraphRAGState(
        user_query="Test query",
        user_id="user_1",
        intent="skill_requirement",
        intents=["skill_requirement"],
        entities=[],
        vector_results=vector_results,
        graph_context=graph_context,
        metadata={"metrics": metrics}
    )

    result = await context_construction_node(state)
    context = result["constructed_context"]

    # Check for graph statistics header
    assert "KNOWLEDGE GRAPH ANALYSIS RESULTS" in context
    assert "Vector Search:" in context
    assert "Graph Traversal:" in context
    assert "initial matches found" in context


@pytest.mark.asyncio
async def test_context_with_multi_intents():
    """Test context construction with multiple detected intents."""
    vector_results = [{"node_type": "Skill", "id": "s1", "name": "Python", "score": 0.9, "properties": {}}]
    graph_context = [{"node_type": "Job", "id": "j1", "name": "Developer", "properties": {}}]

    metrics = QueryMetrics(query_id="test_6", user_id="user_1", query_text="Multi-intent")

    state = GraphRAGState(
        user_query="What skills and salaries for backend jobs?",
        user_id="user_1",
        intent="skill_requirement",  # Backward compat
        intents=["skill_requirement", "salary_analysis"],  # Multi-intent
        entities=[],
        vector_results=vector_results,
        graph_context=graph_context,
        metadata={"metrics": metrics}
    )

    result = await context_construction_node(state)
    context = result["constructed_context"]

    # Check multi-intent support
    assert "skill requirements" in context.lower() or "exploring skill" in context.lower()
    # Context should acknowledge multiple focus areas


@pytest.mark.asyncio
async def test_context_error_handling():
    """Test error handling in context construction."""
    # Missing required fields should be handled gracefully
    state = GraphRAGState(
        user_query="Test",
        user_id="user_1",
        metadata={}  # No metrics
    )

    result = await context_construction_node(state)

    # Should return error context but not raise exception
    assert "constructed_context" in result
    # Error context should include the query
    assert "Test" in result["constructed_context"]
