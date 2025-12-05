"""Unit tests for JWT token utilities."""

import pytest
from datetime import datetime, timedelta
import jwt
from app.utils.jwt import create_access_token, verify_access_token
from app.config import settings


def test_create_access_token():
    """Test JWT token creation with valid user data."""
    user_id = "user-123"
    email = "test@example.com"

    token = create_access_token(user_id, email)

    # Verify token is a string
    assert isinstance(token, str)
    assert len(token) > 0


def test_token_payload_fields():
    """Test JWT token contains correct payload fields."""
    user_id = "user-456"
    email = "user@example.com"

    token = create_access_token(user_id, email)

    # Decode token
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    # Verify payload fields
    assert payload["sub"] == user_id
    assert payload["email"] == email
    assert "iat" in payload  # Issued at
    assert "exp" in payload  # Expiration


def test_token_expiration():
    """Test JWT token expiration set to 24 hours."""
    user_id = "user-789"
    email = "expiry@example.com"

    token = create_access_token(user_id, email)

    # Decode token
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    # Verify expiration (~24 hours)
    exp_time = datetime.fromtimestamp(payload["exp"])
    iat_time = datetime.fromtimestamp(payload["iat"])
    delta = exp_time - iat_time

    # Check expiration matches configured hours
    expected_seconds = settings.JWT_EXPIRATION_HOURS * 3600
    assert abs(delta.total_seconds() - expected_seconds) < 2  # Allow 2 second tolerance


def test_jwt_secret_from_settings():
    """Test JWT secret is loaded from settings."""
    user_id = "test-user"
    email = "settings@example.com"

    token = create_access_token(user_id, email)

    # Token should decode successfully with settings secret
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    assert payload is not None


def test_token_algorithm():
    """Test JWT token uses correct algorithm from settings."""
    user_id = "algo-test"
    email = "algorithm@example.com"

    token = create_access_token(user_id, email)

    # Decode with specified algorithm
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    # Verify algorithm is HS256 (default from settings)
    assert settings.JWT_ALGORITHM == "HS256"
    assert payload["sub"] == user_id


# Tests for verify_access_token


def test_verify_access_token_success():
    """Test token verification with valid token returns user_id."""
    user_id = "user-123"
    email = "test@example.com"

    # Create valid token
    token = create_access_token(user_id, email)

    # Verify token
    extracted_user_id = verify_access_token(token)

    assert extracted_user_id == user_id


def test_verify_access_token_expired():
    """Test token verification with expired token raises ExpiredSignatureError."""
    # Create token with past expiration
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "iat": datetime.utcnow() - timedelta(hours=2),
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    # Should raise ExpiredSignatureError
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_access_token(token)


def test_verify_access_token_invalid_signature():
    """Test token verification with invalid signature raises InvalidTokenError."""
    # Create token with wrong secret
    payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    token = jwt.encode(payload, "wrong-secret", algorithm=settings.JWT_ALGORITHM)

    # Should raise InvalidTokenError
    with pytest.raises(jwt.InvalidTokenError):
        verify_access_token(token)


def test_verify_access_token_malformed():
    """Test token verification with malformed token raises InvalidTokenError."""
    malformed_token = "not.a.valid.token"

    with pytest.raises(jwt.InvalidTokenError):
        verify_access_token(malformed_token)


def test_verify_access_token_missing_user_id():
    """Test token verification with missing user_id in payload raises InvalidTokenError."""
    # Create token without 'sub' field
    payload = {
        "email": "test@example.com",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    with pytest.raises(jwt.InvalidTokenError, match="Missing user ID in token"):
        verify_access_token(token)
