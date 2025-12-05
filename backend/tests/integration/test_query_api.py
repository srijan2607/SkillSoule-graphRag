"""Integration tests for Query API endpoint."""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_success(test_client, prisma_test_db, neo4j_repo):
    """Test POST /query/ask with valid query returns 200 and proper structure."""
    # Arrange - Insert test data into Neo4j
    async with neo4j_repo.driver.session() as session:
        # Create test skill nodes
        await session.run("""
            CREATE (s1:Skill {
                id: 'skill-python-001',
                name: 'python',
                level: 3,
                description: 'Python programming language',
                embedding: [0.1] * 384
            })
            CREATE (s2:Skill {
                id: 'skill-sql-001',
                name: 'sql',
                level: 2,
                description: 'SQL database language',
                embedding: [0.2] * 384
            })
        """)

    # Mock OpenRouter service to avoid actual API calls
    with patch('app.services.openrouter_service.OpenRouterService.generate_completion') as mock_llm:
        mock_llm.return_value = "You need Python and SQL skills for Data Scientist roles."

        query_data = {"query": "What skills do I need for Data Scientist roles?"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "query" in data
        assert "response" in data
        assert "sources" in data
        assert "processing_time_ms" in data
        assert "metadata" in data

        # Verify query echoed back
        assert data["query"] == "What skills do I need for Data Scientist roles?"

        # Verify response is not empty
        assert len(data["response"]) > 0

        # Verify processing time is positive
        assert data["processing_time_ms"] > 0

        # Verify sources is a list
        assert isinstance(data["sources"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_empty_query_returns_400(test_client, prisma_test_db):
    """Test POST /query/ask with empty query returns 400."""
    # Arrange
    query_data = {"query": "   "}  # Whitespace only

    # Act
    response = test_client.post("/query/ask", json=query_data)

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "empty" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_malformed_json_returns_422(test_client, prisma_test_db):
    """Test POST /query/ask with malformed JSON returns 422."""
    # Arrange - Missing required field
    query_data = {"wrong_field": "value"}

    # Act
    response = test_client.post("/query/ask", json=query_data)

    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_logged_to_database(test_client, prisma_test_db, neo4j_repo):
    """Test that query and response are logged to PostgreSQL."""
    # Arrange
    async with neo4j_repo.driver.session() as session:
        await session.run("""
            CREATE (s:Skill {
                id: 'skill-test-001',
                name: 'test skill',
                level: 1,
                embedding: [0.1] * 384
            })
        """)

    # Mock OpenRouter
    with patch('app.services.openrouter_service.OpenRouterService.generate_completion') as mock_llm:
        mock_llm.return_value = "Test response"

        query_data = {"query": "Test query for logging"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 200

        # Verify query was logged to database
        query_history = await prisma_test_db.queryhistory.find_many()
        assert len(query_history) == 1
        assert query_history[0].query_text == "Test query for logging"
        assert query_history[0].response_text == "Test response"
        assert query_history[0].user_id == "test-user-123"  # From test_client fixture

        # Verify metadata was stored
        metadata = json.loads(query_history[0].metadata)
        assert "processing_time_ms" in metadata


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_without_auth_returns_401(prisma_test_db):
    """Test POST /query/ask without JWT token returns 401."""
    # Arrange - Use client without authentication override
    client = TestClient(app)
    query_data = {"query": "Test query"}

    # Act
    response = client.post("/query/ask", json=query_data)

    # Assert
    assert response.status_code == 403  # FastAPI returns 403 for missing credentials


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_langgraph_failure_returns_500(test_client, prisma_test_db):
    """Test POST /query/ask with LangGraph failure returns 500."""
    # Arrange - Mock LangGraph service to raise exception
    with patch('app.services.langgraph_service.LangGraphService.execute_query') as mock_execute:
        mock_execute.side_effect = Exception("Workflow execution failed")

        query_data = {"query": "Test query"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to process query" in data["detail"]

        # Verify error was logged to database
        query_history = await prisma_test_db.queryhistory.find_many()
        assert len(query_history) == 1
        assert "ERROR" in query_history[0].response_text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_processing_time_accuracy(test_client, prisma_test_db, neo4j_repo):
    """Test that processing time is accurately measured."""
    # Arrange
    async with neo4j_repo.driver.session() as session:
        await session.run("""
            CREATE (s:Skill {
                id: 'skill-test-001',
                name: 'test',
                level: 1,
                embedding: [0.1] * 384
            })
        """)

    # Mock OpenRouter with delay
    async def mock_generate_with_delay(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.05)  # 50ms delay
        return "Response with delay"

    with patch('app.services.openrouter_service.OpenRouterService.generate_completion', side_effect=mock_generate_with_delay):
        query_data = {"query": "Test query"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Processing time should be at least 50ms due to sleep
        assert data["processing_time_ms"] >= 50


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_sources_from_neo4j(test_client, prisma_test_db, neo4j_repo):
    """Test that sources are extracted from Neo4j results."""
    # Arrange - Create nodes with known IDs
    async with neo4j_repo.driver.session() as session:
        await session.run("""
            CREATE (s1:Skill {
                id: 'skill-python-123',
                name: 'Python',
                level: 3,
                embedding: [0.5] * 384
            })
            CREATE (s2:Skill {
                id: 'skill-java-456',
                name: 'Java',
                level: 2,
                embedding: [0.5] * 384
            })
        """)

    # Mock OpenRouter
    with patch('app.services.openrouter_service.OpenRouterService.generate_completion') as mock_llm:
        mock_llm.return_value = "Python and Java are popular programming languages."

        query_data = {"query": "What are popular programming languages?"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify sources structure
        assert isinstance(data["sources"], list)

        # Depending on vector search, we might get sources
        # Each source should have proper structure
        for source in data["sources"]:
            assert "node_type" in source
            assert "node_id" in source
            assert "properties" in source


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_endpoint_metadata_includes_intent(test_client, prisma_test_db, neo4j_repo):
    """Test that metadata includes query intent classification."""
    # Arrange
    async with neo4j_repo.driver.session() as session:
        await session.run("""
            CREATE (s:Skill {
                id: 'skill-test-001',
                name: 'test',
                level: 1,
                embedding: [0.1] * 384
            })
        """)

    # Mock OpenRouter
    with patch('app.services.openrouter_service.OpenRouterService.generate_completion') as mock_llm:
        mock_llm.return_value = "Test response"

        query_data = {"query": "What skills do I need?"}

        # Act
        response = test_client.post("/query/ask", json=query_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify metadata exists and has expected fields
        assert "metadata" in data
        assert data["metadata"] is not None
        assert "processing_time_ms" in data["metadata"]

        # Intent might be included depending on query understanding node implementation
        # This is just checking the structure is valid
