"""
Unit tests for Query Understanding Node.

Tests intent classification, entity extraction, and embedding generation.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.nodes.query_understanding import (
    query_understanding_node,
    detect_intent,
    extract_entities,
)
from app.agents.graph import GraphRAGState


# ============================================================================
# Test detect_intent function
# ============================================================================


def test_detect_intent_skill_requirement():
    """Test detection of skill requirement intent."""
    queries = [
        "What skills do I need for data science?",
        "Skills needed for frontend developer",
        "What should I learn to become a backend engineer?",
        "Skills required for AWS certification",
    ]
    for query in queries:
        assert detect_intent(query) == "skill_requirement"


def test_detect_intent_career_path():
    """Test detection of career path intent."""
    queries = [
        "How to transition from frontend to backend?",
        "Career path to become a machine learning engineer",
        "How to switch to data science?",
        "Roadmap to get into DevOps",
    ]
    for query in queries:
        assert detect_intent(query) == "career_path"


def test_detect_intent_salary_analysis():
    """Test detection of salary analysis intent."""
    queries = [
        "What is the salary for Python developers?",
        "How much do data scientists earn?",
        "High-paying tech jobs in 2024",
        "Compensation for software engineers at Google",
    ]
    for query in queries:
        assert detect_intent(query) == "salary_analysis"


def test_detect_intent_skill_relationship():
    """Test detection of skill relationship intent."""
    queries = [
        "What skills are similar to Python?",
        "Alternatives to React framework",
        "Python versus Java for backend",
        "Skills related to machine learning",
    ]
    for query in queries:
        assert detect_intent(query) == "skill_relationship"


def test_detect_intent_company_query():
    """Test detection of company query intent."""
    queries = [
        "Which companies hire Python developers?",
        "Companies that use React",
        "Employers looking for data scientists",
        "Organizations hiring for DevOps",
    ]
    for query in queries:
        assert detect_intent(query) == "company_query"


def test_detect_intent_general():
    """Test detection of general intent (default)."""
    queries = [
        "Tell me about programming",
        "What is artificial intelligence?",
        "Explain cloud computing",
        "Random query with no specific keywords",
    ]
    for query in queries:
        assert detect_intent(query) == "general"


def test_detect_intent_case_insensitive():
    """Test that intent detection is case-insensitive."""
    queries = ["WHAT SKILLS DO I NEED?", "what skills do i need?", "What Skills Do I Need?"]
    for query in queries:
        assert detect_intent(query) == "skill_requirement"


# ============================================================================
# Test extract_entities function
# ============================================================================


def test_extract_entities_programming_languages():
    """Test extraction of programming language entities."""
    query = "I know Python and JavaScript, learning TypeScript"
    entities = extract_entities(query)

    skill_values = [e["value"] for e in entities if e["type"] == "skill"]
    assert "python" in skill_values
    assert "javascript" in skill_values
    assert "typescript" in skill_values

    # Check confidence scores
    for entity in entities:
        assert 0.0 <= entity["confidence"] <= 1.0


def test_extract_entities_frameworks():
    """Test extraction of framework entities."""
    query = "Looking for React and Django developers"
    entities = extract_entities(query)

    skill_values = [e["value"] for e in entities if e["type"] == "skill"]
    assert "react" in skill_values
    assert "django" in skill_values


def test_extract_entities_databases():
    """Test extraction of database technology entities."""
    query = "Experience with PostgreSQL and MongoDB required"
    entities = extract_entities(query)

    skill_values = [e["value"] for e in entities if e["type"] == "skill"]
    assert "postgresql" in skill_values
    assert "mongodb" in skill_values


def test_extract_entities_cloud_tools():
    """Test extraction of cloud and DevOps tool entities."""
    query = "Need AWS and Docker experience"
    entities = extract_entities(query)

    skill_values = [e["value"] for e in entities if e["type"] == "skill"]
    assert "aws" in skill_values
    assert "docker" in skill_values


def test_extract_entities_job_titles():
    """Test extraction of job title entities."""
    query = "Looking for software engineer and data scientist roles"
    entities = extract_entities(query)

    job_values = [e["value"] for e in entities if e["type"] == "job"]
    assert "software engineer" in job_values
    assert "data scientist" in job_values


def test_extract_entities_companies():
    """Test extraction of company name entities."""
    query = "Apply to Google, Amazon, and Microsoft"
    entities = extract_entities(query)

    company_values = [e["value"] for e in entities if e["type"] == "company"]
    assert "google" in company_values
    assert "amazon" in company_values
    assert "microsoft" in company_values

    # Companies should have high confidence
    for entity in [e for e in entities if e["type"] == "company"]:
        assert entity["confidence"] >= 0.9


def test_extract_entities_deduplication():
    """Test that duplicate entities are removed."""
    query = "Python Python Python"
    entities = extract_entities(query)

    # Should only have one Python entity
    python_entities = [e for e in entities if e["value"] == "python"]
    assert len(python_entities) == 1


def test_extract_entities_empty_query():
    """Test extraction from empty or whitespace-only query."""
    assert extract_entities("") == []
    assert extract_entities("   ") == []
    assert extract_entities("Random text with no entities") == []


def test_extract_entities_mixed_case():
    """Test that entity extraction is case-insensitive."""
    query = "PYTHON and Python and python"
    entities = extract_entities(query)

    # Should only have one Python entity (deduplicated)
    assert len(entities) == 1
    assert entities[0]["value"] == "python"


# ============================================================================
# Test query_understanding_node function
# ============================================================================


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for testing."""
    with patch("app.agents.nodes.query_understanding.EmbeddingService") as mock:
        instance = Mock()
        instance.generate_embedding = AsyncMock(
            return_value={
                "embedding": [0.1] * 384,
                "model_version": "all-MiniLM-L6-v2:2024-01",
                "generated_at": "2024-10-24T00:00:00Z",
            }
        )
        mock.return_value = instance
        yield mock


@pytest.mark.asyncio
async def test_query_understanding_node_skill_requirement(mock_embedding_service):
    """Test node with skill requirement query."""
    state = GraphRAGState(
        user_query="What skills do I need for machine learning?",
        user_id="test-user-123",
        metadata={},
    )

    result = await query_understanding_node(state)

    assert "query_embedding" in result
    assert len(result["query_embedding"]) == 384
    assert result["intent"] == "skill_requirement"
    assert "entities" in result
    assert result["metadata"]["query_understanding_completed"] is True
    assert result["metadata"]["intent_confidence"] == 1.0


@pytest.mark.asyncio
async def test_query_understanding_node_career_path(mock_embedding_service):
    """Test node with career path query."""
    state = GraphRAGState(
        user_query="How to transition from data analyst to data scientist?",
        user_id="test-user-123",
        metadata={},
    )

    result = await query_understanding_node(state)

    assert result["intent"] == "career_path"
    assert "query_embedding" in result
    assert result["metadata"]["query_understanding_completed"] is True


@pytest.mark.asyncio
async def test_query_understanding_node_salary_analysis(mock_embedding_service):
    """Test node with salary analysis query."""
    state = GraphRAGState(
        user_query="What is the average salary for Python developers?",
        user_id="test-user-123",
        metadata={},
    )

    result = await query_understanding_node(state)

    assert result["intent"] == "salary_analysis"
    # Should extract "python" as entity
    skill_entities = [e for e in result["entities"] if e["type"] == "skill"]
    assert any(e["value"] == "python" for e in skill_entities)


@pytest.mark.asyncio
async def test_query_understanding_node_skill_relationship(mock_embedding_service):
    """Test node with skill relationship query."""
    state = GraphRAGState(
        user_query="What are alternatives to React?", user_id="test-user-123", metadata={}
    )

    result = await query_understanding_node(state)

    assert result["intent"] == "skill_relationship"
    # Should extract "react" as entity
    skill_entities = [e for e in result["entities"] if e["type"] == "skill"]
    assert any(e["value"] == "react" for e in skill_entities)


@pytest.mark.asyncio
async def test_query_understanding_node_company_query(mock_embedding_service):
    """Test node with company query."""
    state = GraphRAGState(
        user_query="Which companies hire Python developers?", user_id="test-user-123", metadata={}
    )

    result = await query_understanding_node(state)

    assert result["intent"] == "company_query"
    # Should extract "python" as skill entity
    skill_entities = [e for e in result["entities"] if e["type"] == "skill"]
    assert any(e["value"] == "python" for e in skill_entities)


@pytest.mark.asyncio
async def test_query_understanding_node_general_intent(mock_embedding_service):
    """Test node with general query (no specific intent)."""
    state = GraphRAGState(
        user_query="Tell me about programming", user_id="test-user-123", metadata={}
    )

    result = await query_understanding_node(state)

    assert result["intent"] == "general"
    assert "query_embedding" in result
    assert result["metadata"]["query_understanding_completed"] is True


@pytest.mark.asyncio
async def test_query_understanding_node_multiple_entities(mock_embedding_service):
    """Test node extracts multiple entities correctly."""
    state = GraphRAGState(
        user_query="Looking for Python and React jobs at Google",
        user_id="test-user-123",
        metadata={},
    )

    result = await query_understanding_node(state)

    entities = result["entities"]
    entity_values = [e["value"] for e in entities]

    assert "python" in entity_values
    assert "react" in entity_values
    assert "google" in entity_values
    assert result["metadata"]["entities_count"] == 3


@pytest.mark.asyncio
async def test_query_understanding_node_preserves_existing_metadata(mock_embedding_service):
    """Test that node preserves existing metadata in state."""
    state = GraphRAGState(
        user_query="What skills do I need?",
        user_id="test-user-123",
        metadata={"existing_key": "existing_value"},
    )

    result = await query_understanding_node(state)

    assert result["metadata"]["existing_key"] == "existing_value"
    assert result["metadata"]["query_understanding_completed"] is True


@pytest.mark.asyncio
async def test_query_understanding_node_error_handling():
    """Test node handles embedding service errors gracefully."""
    with patch("app.agents.nodes.query_understanding.EmbeddingService") as mock:
        instance = Mock()
        instance.generate_embedding = AsyncMock(side_effect=Exception("Embedding error"))
        mock.return_value = instance

        state = GraphRAGState(user_query="Test query", user_id="test-user-123", metadata={})

        result = await query_understanding_node(state)

        # Should return fallback values
        assert result["intent"] == "unknown"
        assert result["query_embedding"] == [0.0] * 384
        assert result["entities"] == []
        assert result["metadata"]["query_understanding_completed"] is False
        assert "query_understanding_error" in result["metadata"]


@pytest.mark.asyncio
async def test_query_understanding_node_embedding_service_called(mock_embedding_service):
    """Test that EmbeddingService is instantiated and called correctly."""
    state = GraphRAGState(user_query="Test query", user_id="test-user-123", metadata={})

    await query_understanding_node(state)

    # Verify EmbeddingService was instantiated
    mock_embedding_service.assert_called_once()

    # Verify generate_embedding was called with correct query
    instance = mock_embedding_service.return_value
    instance.generate_embedding.assert_called_once_with("Test query")


@pytest.mark.asyncio
async def test_query_understanding_node_returns_correct_structure(mock_embedding_service):
    """Test that node returns all required fields."""
    state = GraphRAGState(user_query="What skills do I need?", user_id="test-user-123", metadata={})

    result = await query_understanding_node(state)

    # Verify all required fields are present
    assert "query_embedding" in result
    assert "intent" in result
    assert "entities" in result
    assert "metadata" in result

    # Verify metadata subfields
    assert "query_understanding_completed" in result["metadata"]
    assert "intent_confidence" in result["metadata"]
    assert "embedding_model" in result["metadata"]
    assert "entities_count" in result["metadata"]


# ============================================================================
# Integration-style tests (without mocking EmbeddingService)
# ============================================================================


@pytest.mark.asyncio
async def test_query_understanding_node_real_embedding_generation():
    """
    Integration test with real EmbeddingService.

    Note: This test loads the actual sentence-transformers model.
    It may be slow on first run (model download).
    """
    state = GraphRAGState(
        user_query="Python programming for data science", user_id="test-user-123", metadata={}
    )

    result = await query_understanding_node(state)

    # Verify embedding is real (not all zeros)
    assert result["query_embedding"] != [0.0] * 384
    assert len(result["query_embedding"]) == 384

    # Verify embedding values are reasonable
    for val in result["query_embedding"]:
        assert -1.0 <= val <= 1.0

    # Verify intent and entities
    assert result["intent"] in [
        "skill_requirement",
        "career_path",
        "salary_analysis",
        "skill_relationship",
        "company_query",
        "general",
    ]

    # Should extract "python" as entity
    entity_values = [e["value"] for e in result["entities"]]
    assert "python" in entity_values
