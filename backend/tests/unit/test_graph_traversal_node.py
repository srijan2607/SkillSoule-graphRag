"""
Unit tests for Graph Traversal Node.

Tests intent-based graph traversal, query generation, result formatting,
node/relationship extraction, and error handling.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.agents.nodes.graph_traversal import (
    graph_traversal_node,
    generate_traversal_query,
    extract_seed_node_ids,
    format_graph_results
)
from app.agents.graph import GraphRAGState


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_repository():
    """Mock Neo4jRepository for testing."""
    mock_repo = Mock()
    mock_repo.connect = AsyncMock()
    mock_repo.close = AsyncMock()

    # Mock successful traversal query execution
    mock_repo.execute_query = AsyncMock(return_value=[
        {
            "job_node": {
                "job_id": "job-001",
                "job_title": "Senior Python Developer",
                "company_name": "Tech Corp",
                "description": "Looking for Python expert"
            },
            "requires_rel": {
                "type": "REQUIRES",
                "similarity_score": 0.95
            },
            "skill_node": {
                "id": "python-001",
                "name": "Python",
                "description": "Programming language",
                "level": 3
            },
            "category_node": {
                "category_id": "cat-001",
                "category_name": "Programming Languages"
            }
        },
        {
            "job_node": {
                "job_id": "job-002",
                "job_title": "Python Backend Engineer",
                "company_name": "Startup Inc",
                "description": "Backend development"
            },
            "requires_rel": {
                "type": "REQUIRES"
            },
            "skill_node": {
                "id": "fastapi-001",
                "name": "FastAPI",
                "description": "Web framework",
                "level": 2
            }
        }
    ])

    return mock_repo


@pytest.fixture
def sample_vector_results():
    """Sample vector search results to seed traversal."""
    return [
        {
            "id": "job-001",
            "name": "Senior Python Developer",
            "score": 0.92,
            "node_type": "Job"
        },
        {
            "id": "job-002",
            "name": "Python Backend Engineer",
            "score": 0.88,
            "node_type": "Job"
        },
        {
            "id": "job-003",
            "name": "Full Stack Developer",
            "score": 0.85,
            "node_type": "Job"
        }
    ]


@pytest.fixture
def sample_skill_vector_results():
    """Sample skill vector results."""
    return [
        {
            "id": "python-001",
            "name": "Python",
            "score": 0.95,
            "node_type": "Skill"
        },
        {
            "id": "javascript-001",
            "name": "JavaScript",
            "score": 0.87,
            "node_type": "Skill"
        }
    ]


# ============================================================================
# Test generate_traversal_query
# ============================================================================


def test_generate_traversal_query_skill_requirement():
    """Test Cypher query generation for skill_requirement intent."""
    query = generate_traversal_query(
        intent="skill_requirement",
        seed_node_ids=["job-001", "job-002"],
        node_type="Job",
        depth=2
    )

    assert query is not None
    assert "MATCH (j:Job) WHERE j.job_id IN $seed_ids" in query
    assert "REQUIRES" in query
    assert "BELONGS_TO_CATEGORY" in query
    assert "LIMIT 50" in query


def test_generate_traversal_query_career_path():
    """Test Cypher query generation for career_path intent."""
    query = generate_traversal_query(
        intent="career_path",
        seed_node_ids=["python-001"],
        node_type="Skill",
        depth=2
    )

    assert query is not None
    assert "MATCH (s:Skill) WHERE s.id IN $seed_ids" in query
    assert "SIMILAR_TO" in query
    assert "REQUIRES" in query
    assert "LIMIT 50" in query


def test_generate_traversal_query_salary_analysis():
    """Test Cypher query generation for salary_analysis intent."""
    query = generate_traversal_query(
        intent="salary_analysis",
        seed_node_ids=["job-001"],
        node_type="Job",
        depth=2
    )

    assert query is not None
    assert "MATCH (j:Job) WHERE j.job_id IN $seed_ids" in query
    assert "POSTED_BY" in query
    assert "ORDER BY j.max_salary DESC" in query


def test_generate_traversal_query_skill_relationship():
    """Test Cypher query generation for skill_relationship intent."""
    query = generate_traversal_query(
        intent="skill_relationship",
        seed_node_ids=["python-001"],
        node_type="Skill",
        depth=2
    )

    assert query is not None
    assert "MATCH (s:Skill) WHERE s.id IN $seed_ids" in query
    assert "SIMILAR_TO" in query


def test_generate_traversal_query_company_query():
    """Test Cypher query generation for company_query intent."""
    query = generate_traversal_query(
        intent="company_query",
        seed_node_ids=["Google", "Microsoft"],
        node_type="Company",
        depth=2
    )

    assert query is not None
    assert "MATCH (c:Company) WHERE c.company_name IN $seed_ids" in query
    assert "POSTED_BY" in query


def test_generate_traversal_query_unknown_intent():
    """Test query generation returns None for unknown intent."""
    query = generate_traversal_query(
        intent="unknown_intent",
        seed_node_ids=["test-001"],
        node_type="Job",
        depth=2
    )

    assert query is None


def test_generate_traversal_query_empty_seeds():
    """Test query generation returns None for empty seed IDs."""
    query = generate_traversal_query(
        intent="skill_requirement",
        seed_node_ids=[],
        node_type="Job",
        depth=2
    )

    assert query is None


# ============================================================================
# Test extract_seed_node_ids
# ============================================================================


def test_extract_seed_node_ids_success(sample_vector_results):
    """Test successful extraction of seed node IDs."""
    seed_ids, node_type = extract_seed_node_ids(sample_vector_results, top_k=10)

    assert len(seed_ids) == 3
    assert seed_ids == ["job-001", "job-002", "job-003"]
    assert node_type == "Job"


def test_extract_seed_node_ids_top_k_limit(sample_vector_results):
    """Test top_k parameter limits number of seed nodes."""
    seed_ids, node_type = extract_seed_node_ids(sample_vector_results, top_k=2)

    assert len(seed_ids) == 2
    assert seed_ids == ["job-001", "job-002"]


def test_extract_seed_node_ids_empty_results():
    """Test extraction with empty vector results."""
    seed_ids, node_type = extract_seed_node_ids([], top_k=10)

    assert seed_ids == []
    assert node_type == ""


def test_extract_seed_node_ids_missing_id():
    """Test extraction handles missing IDs gracefully."""
    results = [
        {"name": "Test Job", "node_type": "Job"},  # No ID
        {"id": "job-001", "name": "Job 1", "node_type": "Job"}
    ]

    seed_ids, node_type = extract_seed_node_ids(results, top_k=10)

    assert len(seed_ids) == 1
    assert seed_ids == ["job-001"]


# ============================================================================
# Test format_graph_results
# ============================================================================


def test_format_graph_results_nodes_and_relationships():
    """Test formatting of nodes and relationships from raw results."""
    raw_results = [
        {
            "job_node": {
                "job_id": "job-001",
                "job_title": "Python Developer",
                "company_name": "Tech Corp"
            },
            "skill_node": {
                "id": "python-001",
                "name": "Python",
                "level": 3
            },
            "requires_rel": {
                "type": "REQUIRES",
                "similarity_score": 0.95
            }
        }
    ]

    result = format_graph_results(raw_results)

    assert "nodes" in result
    assert "relationships" in result
    assert len(result["nodes"]) == 2  # job_node and skill_node
    assert len(result["relationships"]) == 1  # requires_rel


def test_format_graph_results_deduplication():
    """Test that duplicate nodes are deduplicated."""
    raw_results = [
        {
            "job_node": {
                "job_id": "job-001",
                "job_title": "Python Developer"
            }
        },
        {
            "job_node": {
                "job_id": "job-001",  # Duplicate
                "job_title": "Python Developer"
            }
        }
    ]

    result = format_graph_results(raw_results)

    assert len(result["nodes"]) == 1  # Should be deduplicated


def test_format_graph_results_node_limit():
    """Test 50 node limit enforcement."""
    # Create 60 unique nodes
    raw_results = [
        {
            "skill_node": {
                "id": f"skill-{i:03d}",
                "name": f"Skill {i}"
            }
        }
        for i in range(60)
    ]

    result = format_graph_results(raw_results)

    assert len(result["nodes"]) == 50  # Should be limited to 50


def test_format_graph_results_handles_null_values():
    """Test formatting handles None/null values gracefully."""
    raw_results = [
        {
            "job_node": {
                "job_id": "job-001",
                "job_title": "Developer"
            },
            "category_node": None  # Null value
        }
    ]

    result = format_graph_results(raw_results)

    assert len(result["nodes"]) == 1  # Only job_node, category_node is None


def test_format_graph_results_node_type_inference():
    """Test node type is correctly inferred from key names."""
    raw_results = [
        {
            "skill_node": {"id": "s1", "name": "Python"},
            "job_node": {"job_id": "j1", "job_title": "Developer"},
            "company_node": {"company_name": "Tech Corp"}
        }
    ]

    result = format_graph_results(raw_results)

    node_types = {node["node_type"] for node in result["nodes"]}
    assert "Skill" in node_types
    assert "Job" in node_types
    assert "Company" in node_types


# ============================================================================
# Test graph_traversal_node with various intents
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_node_skill_requirement(
    mock_neo4j_repository,
    sample_vector_results
):
    """Test graph traversal with skill_requirement intent."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="What skills are required for Python developer jobs?",
            user_id="test-user-123",
            vector_results=sample_vector_results,
            intent="skill_requirement",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert "graph_results" in result
        assert "nodes" in result["graph_results"]
        assert "relationships" in result["graph_results"]
        assert result["metadata"]["graph_traversal_completed"] is True
        assert "graph_nodes_count" in result["metadata"]

        # Verify Neo4j repository was called correctly
        mock_neo4j_repository.connect.assert_called_once()
        mock_neo4j_repository.execute_query.assert_called_once()
        mock_neo4j_repository.close.assert_called_once()


@pytest.mark.asyncio
async def test_graph_traversal_node_career_path(
    mock_neo4j_repository,
    sample_skill_vector_results
):
    """Test graph traversal with career_path intent."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="What career paths are available with Python?",
            user_id="test-user-123",
            vector_results=sample_skill_vector_results,
            intent="career_path",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert result["metadata"]["graph_traversal_completed"] is True
        assert result["metadata"]["traversal_intent"] == "career_path"


@pytest.mark.asyncio
async def test_graph_traversal_node_no_vector_results(mock_neo4j_repository):
    """Test traversal skips when no vector results available."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="Test query",
            user_id="test-user-123",
            vector_results=[],  # Empty results
            intent="skill_requirement",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert result["metadata"]["graph_traversal_skipped"] is True
        assert result["metadata"]["skip_reason"] == "no_vector_results"
        assert result["graph_results"] == {"nodes": [], "relationships": []}


@pytest.mark.asyncio
async def test_graph_traversal_node_general_intent(
    mock_neo4j_repository,
    sample_vector_results
):
    """Test traversal skips for general/unknown intents."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="General question",
            user_id="test-user-123",
            vector_results=sample_vector_results,
            intent="general",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert result["metadata"]["graph_traversal_skipped"] is True
        assert result["metadata"]["skip_reason"] == "general_intent"


@pytest.mark.asyncio
async def test_graph_traversal_node_no_seed_ids(mock_neo4j_repository):
    """Test traversal handles case when seed IDs cannot be extracted."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        # Vector results without IDs
        state = GraphRAGState(
            user_query="Test query",
            user_id="test-user-123",
            vector_results=[{"name": "Test", "node_type": "Job"}],  # No ID
            intent="skill_requirement",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert "graph_traversal_error" in result["metadata"]
        assert result["metadata"]["graph_traversal_error"] == "no_seed_ids"


@pytest.mark.asyncio
async def test_graph_traversal_node_unsupported_intent(
    mock_neo4j_repository,
    sample_vector_results
):
    """Test traversal handles unsupported intent types (uses 'unknown' as valid enum value)."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="Test query",
            user_id="test-user-123",
            vector_results=sample_vector_results,
            intent="unknown",  # Use valid 'unknown' intent instead
            metadata={}
        )

        result = await graph_traversal_node(state)

        # For 'unknown' intent, traversal should be skipped
        assert result["metadata"]["graph_traversal_skipped"] is True
        assert result["metadata"]["skip_reason"] == "general_intent"


@pytest.mark.asyncio
async def test_graph_traversal_node_exception_handling(
    mock_neo4j_repository,
    sample_vector_results
):
    """Test traversal handles database errors gracefully."""
    mock_neo4j_repository.execute_query = AsyncMock(
        side_effect=Exception("Database connection failed")
    )

    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="Test query",
            user_id="test-user-123",
            vector_results=sample_vector_results,
            intent="skill_requirement",
            metadata={}
        )

        result = await graph_traversal_node(state)

        assert "graph_traversal_error" in result["metadata"]
        assert "Database connection failed" in result["metadata"]["graph_traversal_error"]
        assert result["graph_results"] == {"nodes": [], "relationships": []}


@pytest.mark.asyncio
async def test_graph_traversal_node_metadata_tracking(
    mock_neo4j_repository,
    sample_vector_results
):
    """Test traversal tracks metadata correctly."""
    with patch(
        "app.agents.nodes.graph_traversal.get_neo4j_repository",
        return_value=mock_neo4j_repository
    ):
        state = GraphRAGState(
            user_query="Test query",
            user_id="test-user-123",
            vector_results=sample_vector_results,
            intent="skill_requirement",
            metadata={"previous_step": "completed"}
        )

        result = await graph_traversal_node(state)

        # Check metadata is preserved and augmented
        assert result["metadata"]["previous_step"] == "completed"
        assert result["metadata"]["graph_traversal_completed"] is True
        assert "graph_nodes_count" in result["metadata"]
        assert "graph_relationships_count" in result["metadata"]
        assert "traversal_intent" in result["metadata"]
        assert "seed_nodes_used" in result["metadata"]
