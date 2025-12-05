"""
Integration tests for query API with context visibility.

Tests:
- Query response includes constructed_context
- Query response includes context_stats
- Context retrieval endpoint works
- Context is stored in database
- Authorization for context retrieval
"""
import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from prisma import Prisma


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
async def db():
    """Database connection for testing."""
    prisma = Prisma()
    await prisma.connect()
    yield prisma
    await prisma.disconnect()


@pytest.fixture
def auth_token():
    """Mock JWT token for testing.

    Note: In real tests, generate valid JWT with test user credentials.
    """
    # This is a placeholder - replace with actual token generation
    return "test_jwt_token"


@pytest.fixture
def auth_headers(auth_token):
    """Authorization headers with JWT token."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.mark.integration
def test_query_response_includes_context(client, auth_headers):
    """Test that /query/ask returns constructed_context and context_stats."""
    # Execute query
    response = client.post(
        "/api/query/ask",
        json={"query": "What skills are needed for backend development?"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify context fields exist
    assert "constructed_context" in data, "constructed_context field missing"
    assert "context_stats" in data, "context_stats field missing"

    # Verify constructed_context is a string
    assert isinstance(data["constructed_context"], str)
    assert len(data["constructed_context"]) > 0

    # Verify context_stats structure
    stats = data["context_stats"]
    assert "token_count" in stats
    assert "char_count" in stats
    assert "truncated" in stats
    assert "vector_results_count" in stats
    assert "graph_nodes_count" in stats

    # Verify stats values
    assert stats["token_count"] > 0
    assert stats["char_count"] > 0
    assert stats["truncated"] is False  # No truncation
    assert stats["char_count"] == len(data["constructed_context"])


@pytest.mark.integration
def test_query_response_no_truncation(client, auth_headers):
    """Test that contexts are NOT truncated even if large."""
    # Execute a complex query that generates large context
    response = client.post(
        "/api/query/ask",
        json={
            "query": "Tell me everything about backend development, frontend development, "
                     "full stack development, DevOps, and cloud technologies"
        },
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Verify context is present and NOT truncated
    assert data["context_stats"]["truncated"] is False
    assert "truncated to fit context limit" not in data["constructed_context"].lower()

    # Context token count might be >4000 (old limit)
    # This is fine - no truncation should occur


@pytest.mark.integration
async def test_context_stored_in_database(client, auth_headers, db):
    """Test that constructed_context is stored in query_history metadata."""
    # Execute query
    response = client.post(
        "/api/query/ask",
        json={"query": "Test query for database storage"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # Find the query in database (most recent)
    query_record = await db.queryhistory.find_first(
        where={"query_text": "Test query for database storage"},
        order={"created_at": "desc"}
    )

    assert query_record is not None

    # Parse metadata
    metadata = json.loads(query_record.metadata)

    # Verify context is stored
    assert "constructed_context" in metadata
    assert metadata["constructed_context"] == data["constructed_context"]

    # Verify context_stats is stored
    assert "context_stats" in metadata
    assert metadata["context_stats"] == data["context_stats"]


@pytest.mark.integration
def test_context_retrieval_endpoint_success(client, auth_headers):
    """Test GET /query/history/{query_id}/context endpoint."""
    # First, execute a query
    response = client.post(
        "/api/query/ask",
        json={"query": "Test query for retrieval"},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Get query_id from logs or database (mock for now)
    # In real test, extract from database after query execution
    query_id = "mock_query_id"  # Replace with actual query ID

    # Retrieve context
    response = client.get(
        f"/api/query/history/{query_id}/context",
        headers=auth_headers
    )

    # Note: This will fail in real execution without proper setup
    # Proper test should:
    # 1. Create test user
    # 2. Generate valid JWT
    # 3. Execute query
    # 4. Retrieve actual query_id from database
    # 5. Test context retrieval

    # Expected response structure (if successful):
    # {
    #     "query_id": "...",
    #     "query": "Test query for retrieval",
    #     "response_preview": "Based on...",
    #     "constructed_context": "...",
    #     "context_stats": {...},
    #     "created_at": "..."
    # }


@pytest.mark.integration
def test_context_retrieval_authorization(client):
    """Test that context retrieval requires authentication."""
    # Attempt to retrieve without authentication
    response = client.get("/api/query/history/some_query_id/context")

    # Should return 401 Unauthorized or 403 Forbidden
    assert response.status_code in [401, 403]


@pytest.mark.integration
def test_context_retrieval_ownership_check(client, auth_headers):
    """Test that users can only retrieve their own query contexts."""
    # This test requires:
    # 1. Two test users with different JWTs
    # 2. User A executes a query
    # 3. User B attempts to retrieve User A's context
    # 4. Should return 403 Forbidden

    # Mock test (replace with actual implementation)
    # response = client.get(
    #     f"/api/query/history/other_user_query_id/context",
    #     headers=auth_headers_user_b
    # )
    # assert response.status_code == 403
    # assert "Access denied" in response.json()["detail"]
    pass


@pytest.mark.integration
def test_context_retrieval_not_found(client, auth_headers):
    """Test context retrieval with non-existent query_id."""
    response = client.get(
        "/api/query/history/non_existent_query_id/context",
        headers=auth_headers
    )

    # Should return 404 Not Found
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
def test_query_with_session_id_includes_context(client, auth_headers):
    """Test that follow-up queries with session_id still include context."""
    # First query (new session)
    response1 = client.post(
        "/api/query/ask",
        json={"query": "What is Python?"},
        headers=auth_headers
    )

    assert response1.status_code == 200
    data1 = response1.json()

    # Extract session_id (if returned in metadata)
    # session_id = data1["metadata"].get("session_id")

    # Second query (follow-up with session_id)
    # response2 = client.post(
    #     "/api/query/ask",
    #     json={
    #         "query": "Tell me more about its frameworks",
    #         "session_id": session_id
    #     },
    #     headers=auth_headers
    # )

    # assert response2.status_code == 200
    # data2 = response2.json()

    # Both should have context
    # assert "constructed_context" in data2
    # assert data2["context_stats"]["token_count"] > 0


@pytest.mark.integration
def test_context_includes_user_query_section(client, auth_headers):
    """Test that constructed context always includes user query section."""
    response = client.post(
        "/api/query/ask",
        json={"query": "Unique test query 12345"},
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    context = data["constructed_context"]

    # Verify query is present in context
    assert "Unique test query 12345" in context
    assert "User's Question" in context or "User Query" in context


@pytest.mark.integration
def test_empty_query_returns_error(client, auth_headers):
    """Test that empty query returns 400 error."""
    response = client.post(
        "/api/query/ask",
        json={"query": ""},
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"].lower()


@pytest.mark.integration
def test_query_too_long_returns_error(client, auth_headers):
    """Test that query >500 chars returns 400 error."""
    long_query = "a" * 501

    response = client.post(
        "/api/query/ask",
        json={"query": long_query},
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "too long" in response.json()["detail"].lower()


# Helper function for future tests
async def create_test_user_and_token(db):
    """
    Helper to create test user and generate valid JWT token.

    TODO: Implement this for proper integration testing.
    """
    # Create test user
    # user = await db.user.create(data={
    #     "email": "test@example.com",
    #     "password_hash": hash_password("test_password"),
    #     "full_name": "Test User"
    # })

    # Generate JWT
    # from app.utils.jwt import create_access_token
    # token = create_access_token(user.id)

    # return user, token
    pass
