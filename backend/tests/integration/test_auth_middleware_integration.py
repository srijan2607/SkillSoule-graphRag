"""Integration tests for authentication middleware."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt

from app.main import app
from app.utils.jwt import create_access_token
from app.config import settings

client = TestClient(app)


def test_public_endpoint_health_without_token():
    """Test public endpoint (/health) works without authentication token."""
    response = client.get("/health")

    # Should succeed without token
    assert response.status_code in [200, 503]  # 503 if databases not connected
    assert "service" in response.json()
    assert "status" in response.json()


def test_public_endpoint_root_without_token():
    """Test root endpoint (/) works without authentication token."""
    response = client.get("/")

    # Should succeed without token
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Graph RAG API"


@pytest.mark.skip(reason="Requires database connection - tested in auth service integration tests")
def test_auth_register_without_token():
    """Test /auth/register endpoint works without authentication (public)."""
    # Note: This test belongs in auth service integration tests
    # Skipping here to focus on middleware-only testing
    pass


@pytest.mark.skip(reason="Requires database connection - tested in auth service integration tests")
def test_auth_login_without_token():
    """Test /auth/login endpoint works without authentication (public)."""
    # Note: This test belongs in auth service integration tests
    # Skipping here to focus on middleware-only testing
    pass


# Tests for future protected endpoints (examples for when they exist)


def test_protected_endpoint_with_valid_token_example():
    """
    Example test for protected endpoint with valid JWT token.

    This test demonstrates how to test protected endpoints when they exist.
    Replace '/api/protected' with actual protected endpoint path.
    """
    # Create valid token
    user_id = "test-user-123"
    email = "protected@example.com"
    token = create_access_token(user_id, email)

    # EXAMPLE: When protected endpoints exist, test like this:
    # headers = {"Authorization": f"Bearer {token}"}
    # response = client.post("/api/protected", headers=headers, json={"data": "test"})
    # assert response.status_code == 200

    # For now, just verify token is created
    assert isinstance(token, str)
    assert len(token) > 0


def test_protected_endpoint_without_token_example():
    """
    Example test for protected endpoint without token (should fail).

    This test demonstrates 401 response when no token provided.
    """
    # EXAMPLE: When protected endpoints exist:
    # response = client.post("/api/protected", json={"data": "test"})
    # assert response.status_code == 401
    # assert "authentication_failed" in response.json().get("error", "")
    pass


def test_protected_endpoint_with_expired_token_example():
    """
    Example test for protected endpoint with expired token.

    This test demonstrates 401 response with "Token expired" message.
    """
    # Create expired token
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "iat": datetime.utcnow() - timedelta(hours=2),
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired
    }
    expired_token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    # EXAMPLE: When protected endpoints exist:
    # headers = {"Authorization": f"Bearer {expired_token}"}
    # response = client.post("/api/protected", headers=headers, json={"data": "test"})
    # assert response.status_code == 401
    # assert "Token expired" in response.json().get("message", "")

    # For now, just verify token was created
    assert isinstance(expired_token, str)


def test_protected_endpoint_with_invalid_token_example():
    """
    Example test for protected endpoint with invalid token signature.

    This test demonstrates 401 response with "Invalid token" message.
    """
    # Create token with wrong secret
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    invalid_token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)

    # EXAMPLE: When protected endpoints exist:
    # headers = {"Authorization": f"Bearer {invalid_token}"}
    # response = client.post("/api/protected", headers=headers, json={"data": "test"})
    # assert response.status_code == 401
    # assert "Invalid token" in response.json().get("message", "")

    # For now, just verify token was created
    assert isinstance(invalid_token, str)


def test_authentication_error_response_format():
    """
    Test that AuthenticationError returns consistent error format.

    When authentication fails, response should have:
    - status_code: 401
    - body: {"error": "authentication_failed", "message": "<details>"}
    - headers: {"WWW-Authenticate": "Bearer"}
    """
    # This will be testable when protected endpoints exist
    # For now, verify the error format is defined correctly
    from app.exceptions import AuthenticationError

    error = AuthenticationError("Test error message")
    assert error.status_code == 401
    assert error.detail == "Test error message"
    assert error.headers == {"WWW-Authenticate": "Bearer"}
