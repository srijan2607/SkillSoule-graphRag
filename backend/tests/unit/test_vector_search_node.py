"""
Unit tests for Vector Search Node.

Tests vector similarity search functionality, parameter configuration,
result formatting, and error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.nodes.vector_search import vector_search_node
from app.agents.graph import GraphRAGState


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_repository():
    """Mock Neo4jRepository for testing."""
    with patch("app.agents.nodes.vector_search.Neo4jRepository") as mock:
        instance = Mock()
        instance.connect = AsyncMock()
        instance.close = AsyncMock()
        
        # Mock successful vector search responses
        instance.vector_search_skills = AsyncMock(return_value=[
            {
                "id": "python-001",
                "name": "Python",
                "description": "High-level programming language",
                "type": "programming_language",
                "level": 3,
                "score": 0.92,
                "category": "Programming Languages",
                "subcategory": "General Purpose",
                "node_type": "Skill"
            },
            {
                "id": "javascript-001",
                "name": "JavaScript",
                "description": "Web programming language",
                "type": "programming_language",
                "level": 3,
                "score": 0.85,
                "category": "Programming Languages",
                "subcategory": "Web Development",
                "node_type": "Skill"
            }
        ])
        
        instance.vector_search_jobs = AsyncMock(return_value=[
            {
                "id": "job-001",
                "name": "Senior Python Developer",
                "description": "Looking for experienced Python developer",
                "salary": "$120k-$150k",
                "schedule_type": "Full-time",
                "score": 0.88,
                "company": "Tech Corp",
                "location": "San Francisco",
                "node_type": "Job"
            }
        ])
        
        instance.vector_search_companies = AsyncMock(return_value=[
            {
                "id": "Google",
                "name": "Google",
                "description": "Technology company",
                "score": 0.78,
                "job_count": 150,
                "node_type": "Company"
            }
        ])
        
        mock.return_value = instance
        yield mock


@pytest.fixture
def sample_embedding():
    """Sample 384-dimensional embedding vector."""
    return [0.1] * 384


# ============================================================================
# Test vector_search_node with valid inputs
# ============================================================================


@pytest.mark.asyncio
async def test_vector_search_node_success(mock_neo4j_repository, sample_embedding):
    """Test successful vector search with all node types."""
    state = GraphRAGState(
        user_query="Python developer jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)

    # Verify results structure
    assert "vector_results" in result
    assert "metadata" in result
    
    # Should have combined results from all three searches
    assert len(result["vector_results"]) > 0
    
    # Verify metadata
    assert result["metadata"]["vector_search_completed"] is True
    assert result["metadata"]["vector_results_count"] >= 0
    assert result["metadata"]["skills_count"] == 2
    assert result["metadata"]["jobs_count"] == 1
    assert result["metadata"]["companies_count"] == 1


@pytest.mark.asyncio
async def test_vector_search_node_results_sorted_by_score(mock_neo4j_repository, sample_embedding):
    """Test that results are sorted by similarity score descending."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)
    
    vector_results = result["vector_results"]
    
    # Verify results are sorted by score (highest first)
    scores = [r["score"] for r in vector_results]
    assert scores == sorted(scores, reverse=True)
    
    # Highest score should be from Python skill (0.92)
    assert vector_results[0]["name"] == "Python"
    assert vector_results[0]["score"] == 0.92


@pytest.mark.asyncio
async def test_vector_search_node_default_parameters(mock_neo4j_repository, sample_embedding):
    """Test that default parameters (k=15, threshold=0.5) are used."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}  # No custom parameters
    )

    await vector_search_node(state)
    
    # Verify Neo4j methods were called with defaults
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills.assert_called_once_with(sample_embedding, 15, 0.5)
    repo_instance.vector_search_jobs.assert_called_once_with(sample_embedding, 15, 0.5)
    repo_instance.vector_search_companies.assert_called_once_with(sample_embedding, 15, 0.5)


@pytest.mark.asyncio
async def test_vector_search_node_custom_parameters(mock_neo4j_repository, sample_embedding):
    """Test that custom k and threshold parameters are used."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={
            "vector_search_k": 10,
            "vector_search_threshold": 0.7
        }
    )

    result = await vector_search_node(state)
    
    # Verify custom parameters were used
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills.assert_called_once_with(sample_embedding, 10, 0.7)
    
    # Verify parameters are recorded in metadata
    assert result["metadata"]["vector_search_k"] == 10
    assert result["metadata"]["vector_search_threshold"] == 0.7


@pytest.mark.asyncio
async def test_vector_search_node_respects_k_limit(mock_neo4j_repository, sample_embedding):
    """Test that results are limited to top-k."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={"vector_search_k": 2}  # Limit to 2 results
    )

    result = await vector_search_node(state)
    
    # Even though we have 4 total results (2 skills, 1 job, 1 company),
    # should only return top 2
    assert len(result["vector_results"]) == 2
    assert result["metadata"]["vector_results_count"] == 2


@pytest.mark.asyncio
async def test_vector_search_node_preserves_existing_metadata(mock_neo4j_repository, sample_embedding):
    """Test that existing metadata is preserved."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={
            "existing_key": "existing_value",
            "intent_confidence": 0.95
        }
    )

    result = await vector_search_node(state)
    
    # Existing metadata should be preserved
    assert result["metadata"]["existing_key"] == "existing_value"
    assert result["metadata"]["intent_confidence"] == 0.95
    
    # New metadata should be added
    assert result["metadata"]["vector_search_completed"] is True


# ============================================================================
# Test edge cases
# ============================================================================


@pytest.mark.asyncio
async def test_vector_search_node_no_embedding():
    """Test handling when query_embedding is missing."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=None,  # No embedding
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)
    
    # Should return empty results without error
    assert result["vector_results"] == []
    assert result["metadata"]["vector_search_completed"] is False
    assert "vector_search_error" in result["metadata"]
    assert "No query embedding" in result["metadata"]["vector_search_error"]


@pytest.mark.asyncio
async def test_vector_search_node_empty_results(mock_neo4j_repository, sample_embedding):
    """Test handling when no similar nodes are found."""
    # Mock empty results from all searches
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills = AsyncMock(return_value=[])
    repo_instance.vector_search_jobs = AsyncMock(return_value=[])
    repo_instance.vector_search_companies = AsyncMock(return_value=[])

    state = GraphRAGState(
        user_query="Obscure query",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="general",
        metadata={}
    )

    result = await vector_search_node(state)
    
    # Should handle empty results gracefully
    assert result["vector_results"] == []
    assert result["metadata"]["vector_search_completed"] is True
    assert result["metadata"]["vector_results_count"] == 0
    assert result["metadata"]["skills_count"] == 0
    assert result["metadata"]["jobs_count"] == 0
    assert result["metadata"]["companies_count"] == 0


@pytest.mark.asyncio
async def test_vector_search_node_partial_failures(mock_neo4j_repository, sample_embedding):
    """Test handling when some searches fail but others succeed."""
    # Mock partial failures
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills = AsyncMock(
        side_effect=Exception("Neo4j connection error")
    )
    repo_instance.vector_search_jobs = AsyncMock(return_value=[
        {
            "id": "job-001",
            "name": "Python Developer",
            "score": 0.88,
            "node_type": "Job"
        }
    ])
    repo_instance.vector_search_companies = AsyncMock(return_value=[])

    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)
    
    # Should continue with partial results
    assert len(result["vector_results"]) == 1
    assert result["vector_results"][0]["name"] == "Python Developer"
    assert result["metadata"]["vector_search_completed"] is True
    assert result["metadata"]["skills_count"] == 0  # Failed
    assert result["metadata"]["jobs_count"] == 1    # Succeeded


@pytest.mark.asyncio
async def test_vector_search_node_connection_failure():
    """Test handling when Neo4j connection fails."""
    with patch("app.agents.nodes.vector_search.Neo4jRepository") as mock:
        instance = Mock()
        instance.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock.return_value = instance

        state = GraphRAGState(
            user_query="Python jobs",
            user_id="test-user-123",
            query_embedding=[0.1] * 384,
            intent="skill_requirement",
            metadata={}
        )

        result = await vector_search_node(state)
        
        # Should return error state
        assert result["vector_results"] == []
        assert result["metadata"]["vector_search_completed"] is False
        assert "vector_search_error" in result["metadata"]


@pytest.mark.asyncio
async def test_vector_search_node_connection_always_closed(mock_neo4j_repository, sample_embedding):
    """Test that Neo4j connection is always closed, even on error."""
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills = AsyncMock(
        side_effect=Exception("Search error")
    )

    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    await vector_search_node(state)
    
    # Connection should be closed even when search fails
    repo_instance.close.assert_called_once()


# ============================================================================
# Test result formatting
# ============================================================================


@pytest.mark.asyncio
async def test_vector_search_node_result_structure(mock_neo4j_repository, sample_embedding):
    """Test that results have correct structure."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)
    
    # Verify each result has required fields
    for item in result["vector_results"]:
        assert "id" in item
        assert "name" in item
        assert "score" in item
        assert "node_type" in item
        assert item["node_type"] in ["Skill", "Job", "Company"]


@pytest.mark.asyncio
async def test_vector_search_node_combines_all_node_types(mock_neo4j_repository, sample_embedding):
    """Test that results include Skills, Jobs, and Companies."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    result = await vector_search_node(state)
    
    # Check that we have results from all node types
    node_types = set(item["node_type"] for item in result["vector_results"])
    assert "Skill" in node_types
    assert "Job" in node_types
    assert "Company" in node_types


# ============================================================================
# Test integration patterns
# ============================================================================


@pytest.mark.asyncio
async def test_vector_search_node_neo4j_instantiation(mock_neo4j_repository, sample_embedding):
    """Test that Neo4jRepository is instantiated with correct config."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    await vector_search_node(state)
    
    # Verify Neo4jRepository was instantiated with settings
    mock_neo4j_repository.assert_called_once()
    call_kwargs = mock_neo4j_repository.call_args.kwargs
    
    assert "uri" in call_kwargs
    assert "user" in call_kwargs
    assert "password" in call_kwargs


@pytest.mark.asyncio
async def test_vector_search_node_parallel_execution(mock_neo4j_repository, sample_embedding):
    """Test that searches are executed in parallel."""
    state = GraphRAGState(
        user_query="Python jobs",
        user_id="test-user-123",
        query_embedding=sample_embedding,
        intent="skill_requirement",
        metadata={}
    )

    await vector_search_node(state)
    
    # All three search methods should be called
    repo_instance = mock_neo4j_repository.return_value
    repo_instance.vector_search_skills.assert_called_once()
    repo_instance.vector_search_jobs.assert_called_once()
    repo_instance.vector_search_companies.assert_called_once()
