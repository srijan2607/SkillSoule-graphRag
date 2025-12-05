"""Unit tests for Query API endpoint."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from starlette.requests import Request
from starlette.datastructures import Headers
from app.api.query import ask_question
from app.models.query import QueryRequest, QueryResponse, SourceNode


@pytest.fixture
def mock_request():
    """Create a mock Request object for rate limiter."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/query/ask",
        "headers": Headers({"content-type": "application/json"}).raw,
        "query_string": b"",
        "client": ("127.0.0.1", 8000),
    }
    return Request(scope)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_success(mock_request):
    """Test successful query execution."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    # Mock LangGraph service response
    mock_langgraph_service.execute_query.return_value = {
        "response": "You need Python, SQL, and machine learning skills for Data Scientist roles.",
        "sources": [
            SourceNode(
                node_type="Skill",
                node_id="skill-python-001",
                properties={"name": "Python", "level": 3}
            ),
            SourceNode(
                node_type="Skill",
                node_id="skill-sql-001",
                properties={"name": "SQL", "level": 2}
            )
        ],
        "metadata": {"intent": "skill_requirement"}
    }

    query_data = QueryRequest(query="What skills do I need for Data Scientist roles?")
    current_user_id = "user-123"

    # Act
    result = await ask_question(
        request=mock_request,
        query_data=query_data,
        current_user_id=current_user_id,
        langgraph_service=mock_langgraph_service,
        query_history_repo=mock_query_history_repo
    )

    # Assert
    assert isinstance(result, QueryResponse)
    assert result.query == "What skills do I need for Data Scientist roles?"
    assert "Python" in result.response
    assert len(result.sources) == 2
    assert result.sources[0].node_type == "Skill"
    assert result.sources[0].node_id == "skill-python-001"
    assert result.processing_time_ms > 0
    assert result.metadata["intent"] == "skill_requirement"

    # Verify service calls
    mock_langgraph_service.execute_query.assert_called_once_with(
        query="What skills do I need for Data Scientist roles?",
        user_id="user-123"
    )
    mock_query_history_repo.create_query_history.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_empty_query(mock_request):
    """Test that empty query returns 400 error."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    query_data = QueryRequest(query="   ")  # Whitespace only
    current_user_id = "user-123"

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await ask_question(
            request=mock_request,
            query_data=query_data,
            current_user_id=current_user_id,
            langgraph_service=mock_langgraph_service,
            query_history_repo=mock_query_history_repo
        )

    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()

    # Verify service not called
    mock_langgraph_service.execute_query.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_langgraph_failure(mock_request):
    """Test that LangGraph failure returns 500 error."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    # Mock LangGraph service to raise exception
    mock_langgraph_service.execute_query.side_effect = Exception("Neo4j connection failed")

    query_data = QueryRequest(query="What skills do I need for Data Scientist roles?")
    current_user_id = "user-123"

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await ask_question(
            request=mock_request,
            query_data=query_data,
            current_user_id=current_user_id,
            langgraph_service=mock_langgraph_service,
            query_history_repo=mock_query_history_repo
        )

    assert exc_info.value.status_code == 500
    assert "Failed to process query" in exc_info.value.detail

    # Verify service was called
    mock_langgraph_service.execute_query.assert_called_once()

    # Verify error was logged to database
    mock_query_history_repo.create_query_history.assert_called_once()
    call_args = mock_query_history_repo.create_query_history.call_args
    assert "ERROR" in call_args.kwargs["response_text"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_processing_time_calculated(mock_request):
    """Test that processing time is accurately calculated."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    # Mock LangGraph service with delay
    async def mock_execute(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.1)  # 100ms delay
        return {
            "response": "Test response",
            "sources": [],
            "metadata": {}
        }

    mock_langgraph_service.execute_query = mock_execute

    query_data = QueryRequest(query="Test query")
    current_user_id = "user-123"

    # Act
    result = await ask_question(
        request=mock_request,
        query_data=query_data,
        current_user_id=current_user_id,
        langgraph_service=mock_langgraph_service,
        query_history_repo=mock_query_history_repo
    )

    # Assert
    assert result.processing_time_ms >= 100  # At least 100ms due to sleep
    assert result.processing_time_ms < 200  # Should be less than 200ms


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_logging_failure_doesnt_fail_request(mock_request):
    """Test that query history logging failure doesn't fail the request."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    # Mock successful LangGraph execution
    mock_langgraph_service.execute_query.return_value = {
        "response": "Test response",
        "sources": [],
        "metadata": {}
    }

    # Mock logging failure
    mock_query_history_repo.create_query_history.side_effect = Exception("Database connection failed")

    query_data = QueryRequest(query="Test query")
    current_user_id = "user-123"

    # Act - Should NOT raise exception despite logging failure
    result = await ask_question(
        request=mock_request,
        query_data=query_data,
        current_user_id=current_user_id,
        langgraph_service=mock_langgraph_service,
        query_history_repo=mock_query_history_repo
    )

    # Assert
    assert isinstance(result, QueryResponse)
    assert result.response == "Test response"

    # Verify logging was attempted
    mock_query_history_repo.create_query_history.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_sources_extraction(mock_request):
    """Test that sources are correctly extracted from LangGraph result."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    # Mock LangGraph service with multiple sources
    mock_langgraph_service.execute_query.return_value = {
        "response": "Test response",
        "sources": [
            SourceNode(
                node_type="Skill",
                node_id="skill-001",
                properties={"name": "Python"}
            ),
            SourceNode(
                node_type="Job",
                node_id="job-001",
                properties={"title": "Data Scientist"}
            ),
            SourceNode(
                node_type="Company",
                node_id="company-001",
                properties={"name": "Tech Corp"}
            )
        ],
        "metadata": {}
    }

    query_data = QueryRequest(query="Test query")
    current_user_id = "user-123"

    # Act
    result = await ask_question(
        request=mock_request,
        query_data=query_data,
        current_user_id=current_user_id,
        langgraph_service=mock_langgraph_service,
        query_history_repo=mock_query_history_repo
    )

    # Assert
    assert len(result.sources) == 3
    assert result.sources[0].node_type == "Skill"
    assert result.sources[1].node_type == "Job"
    assert result.sources[2].node_type == "Company"
    assert result.sources[0].properties["name"] == "Python"
    assert result.sources[1].properties["title"] == "Data Scientist"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ask_question_metadata_includes_processing_time(mock_request):
    """Test that metadata includes processing time."""
    # Arrange
    mock_langgraph_service = AsyncMock()
    mock_query_history_repo = AsyncMock()

    mock_langgraph_service.execute_query.return_value = {
        "response": "Test response",
        "sources": [],
        "metadata": {"intent": "skill_requirement"}
    }

    query_data = QueryRequest(query="Test query")
    current_user_id = "user-123"

    # Act
    result = await ask_question(
        request=mock_request,
        query_data=query_data,
        current_user_id=current_user_id,
        langgraph_service=mock_langgraph_service,
        query_history_repo=mock_query_history_repo
    )

    # Assert
    assert "processing_time_ms" in result.metadata
    assert result.metadata["processing_time_ms"] == result.processing_time_ms
    assert "intent" in result.metadata
    assert result.metadata["intent"] == "skill_requirement"
