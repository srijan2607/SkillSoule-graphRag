"""Unit tests for authentication middleware."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.security import HTTPAuthorizationCredentials
import jwt

from app.middleware.auth import get_current_user
from app.exceptions import AuthenticationError


@pytest.mark.asyncio
async def test_get_current_user_success():
    """Test middleware with valid token returns user_id."""
    # Mock credentials
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="valid.jwt.token"
    )

    # Mock verify_access_token to return user_id
    with patch('app.middleware.auth.verify_access_token', return_value="user-123"):
        # Call middleware
        user_id = await get_current_user(credentials)

        assert user_id == "user-123"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    """Test middleware with expired token raises AuthenticationError."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="expired.jwt.token"
    )

    # Mock verify_access_token to raise ExpiredSignatureError
    with patch(
        'app.middleware.auth.verify_access_token',
        side_effect=jwt.ExpiredSignatureError("Signature has expired")
    ):
        # Should raise AuthenticationError with "Token expired" message
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials)

        assert "Token expired" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """Test middleware with invalid token raises AuthenticationError."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.jwt.token"
    )

    # Mock verify_access_token to raise InvalidTokenError
    with patch(
        'app.middleware.auth.verify_access_token',
        side_effect=jwt.InvalidTokenError("Invalid token")
    ):
        # Should raise AuthenticationError with "Invalid token" message
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials)

        assert "Invalid token" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_malformed_token():
    """Test middleware with malformed token raises AuthenticationError."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="malformed.token"
    )

    # Mock verify_access_token to raise InvalidTokenError
    with patch(
        'app.middleware.auth.verify_access_token',
        side_effect=jwt.InvalidTokenError("Not enough segments")
    ):
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials)

        assert "Invalid token" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_unexpected_error():
    """Test middleware with unexpected error raises AuthenticationError."""
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="some.token"
    )

    # Mock verify_access_token to raise unexpected exception
    with patch(
        'app.middleware.auth.verify_access_token',
        side_effect=Exception("Unexpected error")
    ):
        # Should raise AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            await get_current_user(credentials)

        assert "Authentication failed" in str(exc_info.value.detail)
        assert exc_info.value.status_code == 401
