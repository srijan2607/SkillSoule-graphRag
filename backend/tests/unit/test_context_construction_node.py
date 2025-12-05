"""
Unit tests for context construction node.
"""
import pytest
from app.agents.nodes.context_construction import context_construction_node
from app.agents.graph import GraphRAGState


@pytest.mark.asyncio
async def test_context_construction_with_sample_data():
    """Test context formatting with realistic sample data."""
    # Arrange
    state = GraphRAGState(
        user_query="What skills do I need for Data Scientist roles?",
        user_id="test-user-123",
        intent="skill_requirement",
        entities=[
            {"type": "job_role", "value": "Data Scientist"},
            {"type": "skill", "value": "Python"}
        ],
        vector_results=[
            {
                "name": "Python",
                "node_type": "Skill",
                "similarity_score": 0.89,
                "category": "Programming Languages",
                "description": "High-level programming language for data analysis",
                "id": "skill-python-001"
            },
            {
                "name": "Data Science",
                "node_type": "Job",
                "similarity_score": 0.85,
                "company_name": "Google",
                "job_description": "Analyze large datasets to derive insights",
                "id": "job-12345",
                "salary_min": 120000,
                "salary_max": 180000
            }
        ],
        graph_context=[
            {
                "name": "Python",
                "relationships": [
                    {"type": "REQUIRED_BY", "target_name": "Data Scientist", "count": 1234},
                    {"type": "SIMILAR_TO", "target_name": "Machine Learning", "count": 1}
                ]
            }
        ],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    assert "constructed_context" in result
    context = result["constructed_context"]

    # Check all required sections present
    assert "## User Query" in context
    assert "What skills do I need for Data Scientist roles?" in context
    assert "## Top Matching Nodes" in context
    assert "## Related Information" in context
    assert "## Graph Structure" in context

    # Check source citations
    assert "Skill:skill-python-001" in context
    assert "Job:job-12345" in context

    # Check metadata
    assert result["metadata"]["context_construction_completed"] is True
    assert result["metadata"]["context_token_count"] > 0
    assert result["metadata"]["vector_results_count"] == 2
    assert result["metadata"]["graph_nodes_count"] == 1


@pytest.mark.asyncio
async def test_context_construction_with_empty_results():
    """Test graceful handling of empty vector and graph results."""
    # Arrange
    state = GraphRAGState(
        user_query="What is machine learning?",
        user_id="test-user-456",
        intent="general",
        vector_results=[],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    assert "constructed_context" in result
    context = result["constructed_context"]

    # Should still have user query section
    assert "## User Query" in context
    assert "What is machine learning?" in context

    # Should handle empty results gracefully
    assert result["metadata"]["context_construction_completed"] is True
    assert result["metadata"]["vector_results_count"] == 0
    assert result["metadata"]["graph_nodes_count"] == 0


@pytest.mark.asyncio
async def test_token_counting_accuracy():
    """Test token counting is approximately accurate."""
    # Arrange
    state = GraphRAGState(
        user_query="Test query",
        user_id="test-user-789",
        vector_results=[
            {
                "name": f"Skill {i}",
                "node_type": "Skill",
                "similarity_score": 0.8,
                "description": "A" * 100,  # 100 chars
                "id": f"skill-{i}"
            }
            for i in range(5)
        ],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    token_count = result["metadata"]["context_token_count"]
    char_count = result["metadata"]["context_char_count"]

    # Rough check: token count should be ~1/4 of char count
    assert token_count > 0
    assert char_count > 0
    assert abs(token_count - (char_count // 4)) < 50  # Allow 50 token variance


@pytest.mark.asyncio
async def test_truncation_logic_with_large_context():
    """Test truncation when context exceeds 4000 tokens."""
    # Arrange - Create dataset that will exceed 4000 tokens
    # Note: The formatting functions have built-in limits (top 10 vectors, 15 graph nodes, 8 rels/type)
    # To trigger truncation, need MANY relationship types with long names

    large_vector_results = [
        {
            "name": f"Skill_{i:04d}",
            "node_type": "Skill",
            "similarity_score": 0.9 - (i * 0.001),
            "description": "Y" * 500,  # Will be truncated to 150 in formatting
            "category": f"Cat_{i}",
            "id": f"sk-{i:06d}"
        }
        for i in range(100)
    ]

    # Create graph nodes with MANY DIFFERENT relationship types
    # Since formatting shows 8 rels per type, having 100+ types will create large output
    # 100 types * 8 rels/type * 150 chars/rel = 120,000 chars = 30,000 tokens!
    large_graph_context = [
        {
            "name": f"GraphNode_{i:05d}_with_very_long_name_for_padding_purposes",
            "relationships": [
                {
                    # Create unique relationship type for each to bypass the 8-per-type limit
                    "type": f"RELATIONSHIP_TYPE_NUMBER_{i:04d}_{j:04d}_WITH_VERY_LONG_NAME_FOR_SIZE",
                    "target_name": f"TargetNode_{i:05d}_{j:05d}_with_extremely_long_name_for_maximum_character_count_inflation_purposes_adding_more_text",
                    "count": j + 1
                }
                for j in range(20)  # 20 relationships per node, each with unique type
            ]
        }
        for i in range(50)  # 50 nodes
    ]

    state = GraphRAGState(
        user_query="Y" * 2000,  # Very long query
        user_id="test-user-truncation",
        intent="skill_requirement",  # Valid intent
        vector_results=large_vector_results,
        graph_context=large_graph_context,
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    token_count = result["metadata"]["context_token_count"]
    was_truncated = result["metadata"]["context_truncated"]

    # With this much data (1000+ unique relationship types), should definitely be truncated
    assert was_truncated is True, f"Expected truncation but got {token_count} tokens"
    assert token_count <= 4000

    # Should include truncation notice
    assert "*Note: Some graph relationships were truncated" in result["constructed_context"]


@pytest.mark.asyncio
async def test_source_citation_inclusion():
    """Test that source citations are included for traceability."""
    # Arrange
    state = GraphRAGState(
        user_query="Python programming",
        user_id="test-user-cite",
        vector_results=[
            {
                "name": "Python",
                "node_type": "Skill",
                "similarity_score": 0.95,
                "id": "skill-python-123"
            },
            {
                "name": "Software Engineer",
                "node_type": "Job",
                "similarity_score": 0.88,
                "id": "job-se-456"
            }
        ],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Check source citations present
    assert "Source: Skill:skill-python-123" in context
    assert "Source: Job:job-se-456" in context


@pytest.mark.asyncio
async def test_intent_and_entities_in_user_query_section():
    """Test that intent and entities are displayed in user query section."""
    # Arrange
    state = GraphRAGState(
        user_query="What's the average salary for data scientists?",
        user_id="test-user-intent",
        intent="salary_analysis",
        entities=[
            {"type": "job_role", "value": "Data Scientist"},
            {"type": "metric", "value": "salary"}
        ],
        vector_results=[],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Check intent is formatted
    assert "**Intent:** Salary Analysis" in context

    # Check entities are listed
    assert "**Entities:**" in context
    assert "job_role: Data Scientist" in context


@pytest.mark.asyncio
async def test_salary_range_in_graph_structure():
    """Test salary analysis appears in graph structure section."""
    # Arrange
    state = GraphRAGState(
        user_query="Data scientist jobs",
        user_id="test-user-salary",
        vector_results=[
            {
                "name": "Data Scientist - Google",
                "node_type": "Job",
                "similarity_score": 0.9,
                "salary_min": 150000,
                "salary_max": 200000,
                "id": "job-1"
            },
            {
                "name": "Data Scientist - Meta",
                "node_type": "Job",
                "similarity_score": 0.88,
                "salary_min": 140000,
                "salary_max": 190000,
                "id": "job-2"
            }
        ],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Check salary range summary in graph structure
    assert "## Graph Structure" in context
    assert "Salary range:" in context
    assert "average across 2 jobs" in context


@pytest.mark.asyncio
async def test_relationship_grouping():
    """Test relationships are grouped by type in related information."""
    # Arrange
    state = GraphRAGState(
        user_query="Python skills",
        user_id="test-user-rel",
        vector_results=[],
        graph_context=[
            {
                "name": "Python",
                "relationships": [
                    {"type": "REQUIRED_BY", "target_name": "Job A", "count": 1},
                    {"type": "REQUIRED_BY", "target_name": "Job B", "count": 1},
                    {"type": "SIMILAR_TO", "target_name": "Java", "count": 1},
                ]
            }
        ],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Check relationship groups
    assert "**Required By:**" in context
    assert "**Similar To:**" in context
    assert "Python → Job A" in context
    assert "Python → Java" in context


@pytest.mark.asyncio
async def test_error_handling():
    """Test graceful handling of malformed data."""
    # Arrange - Create state with malformed data
    state = GraphRAGState(
        user_query="Test query",
        user_id="test-user-error",
        # Pass malformed data - code should handle gracefully with defaults
        vector_results=[{"invalid": "data"}],  # Missing expected fields
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert - Should not crash, should handle gracefully
    assert "constructed_context" in result
    assert "metadata" in result
    assert result["metadata"]["context_construction_completed"] is True

    # Should still include user query
    assert "Test query" in result["constructed_context"]

    # Should handle missing fields gracefully (use defaults)
    context = result["constructed_context"]
    assert "## User Query" in context
    assert "## Top Matching Nodes" in context  # Should be present even with malformed data


@pytest.mark.asyncio
async def test_top_10_vector_results_only():
    """Test only top 10 vector results are included."""
    # Arrange
    state = GraphRAGState(
        user_query="Skills",
        user_id="test-user-top10",
        vector_results=[
            {
                "name": f"Skill {i}",
                "node_type": "Skill",
                "similarity_score": 0.9 - (i * 0.01),
                "id": f"skill-{i}"
            }
            for i in range(20)  # 20 results
        ],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Check top 10 are present
    for i in range(10):
        assert f"Skill {i}" in context

    # Check 11+ are not present
    for i in range(11, 20):
        assert f"Skill {i}" not in context


@pytest.mark.asyncio
async def test_description_truncation():
    """Test long descriptions are truncated to 150 chars."""
    # Arrange
    long_description = "A" * 300  # 300 char description

    state = GraphRAGState(
        user_query="Test",
        user_id="test-user-desc",
        vector_results=[
            {
                "name": "Test Skill",
                "node_type": "Skill",
                "similarity_score": 0.9,
                "description": long_description,
                "id": "skill-1"
            }
        ],
        graph_context=[],
        metadata={}
    )

    # Act
    result = await context_construction_node(state)

    # Assert
    context = result["constructed_context"]

    # Description should be truncated with ...
    assert "AAA..." in context  # First part of description
    # Full 300 char description should NOT be present
    assert long_description not in context
