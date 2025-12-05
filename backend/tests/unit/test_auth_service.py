"""Unit tests for AuthService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserResponse, UserLogin
from datetime import datetime


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_success():
    """Test successful user registration."""
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.find_by_email.return_value = None  # No existing user
    mock_user = MagicMock()
    mock_user.id = "test-uuid-123"
    mock_user.email = "test@example.com"
    mock_user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_repo.create.return_value = mock_user

    service = AuthService(mock_repo)
    user_data = UserCreate(email="test@example.com", password="password123")

    # Act
    result = await service.register_user(user_data)

    # Assert
    assert result.email == "test@example.com"
    assert result.id == "test-uuid-123"
    mock_repo.find_by_email.assert_called_once_with("test@example.com")
    mock_repo.create.assert_called_once()
    # Verify password was hashed (not plain text)
    call_args = mock_repo.create.call_args[0][0]  # First positional argument
    assert "password_hash" in call_args
    assert call_args["password_hash"] != "password123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_duplicate_email():
    """Test registration fails with duplicate email."""
    # Arrange
    mock_repo = AsyncMock()
    existing_user = MagicMock()
    existing_user.email = "test@example.com"
    mock_repo.find_by_email.return_value = existing_user

    service = AuthService(mock_repo)
    user_data = UserCreate(email="test@example.com", password="password123")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await service.register_user(user_data)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Email already exists"
    mock_repo.find_by_email.assert_called_once_with("test@example.com")
    mock_repo.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_password_hashing():
    """Test that password is hashed using bcrypt."""
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.find_by_email.return_value = None
    mock_user = MagicMock()
    mock_user.id = "test-uuid-123"
    mock_user.email = "test@example.com"
    mock_user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_repo.create.return_value = mock_user

    service = AuthService(mock_repo)
    user_data = UserCreate(email="test@example.com", password="mypassword")

    # Act
    await service.register_user(user_data)

    # Assert
    call_args = mock_repo.create.call_args[0][0]  # First positional argument
    password_hash = call_args["password_hash"]

    # Verify it's a bcrypt hash (starts with $2b$)
    assert password_hash.startswith("$2b$")
    assert password_hash != "mypassword"


@pytest.mark.unit
def test_user_create_validation_email():
    """Test email validation in UserCreate model."""
    # Valid email
    user = UserCreate(email="valid@example.com", password="password123")
    assert user.email == "valid@example.com"

    # Invalid email - should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        UserCreate(email="invalid-email", password="password123")


@pytest.mark.unit
def test_user_create_validation_password_length():
    """Test password length validation."""
    # Valid password (8 characters)
    user = UserCreate(email="test@example.com", password="12345678")
    assert user.password == "12345678"

    # Invalid password (too short)
    with pytest.raises(Exception):  # Pydantic validation error
        UserCreate(email="test@example.com", password="short")


# Login Tests

@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_success():
    """Test successful login returns token and user info."""
    # Arrange
    mock_repo = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "test-uuid-123"
    mock_user.email = "test@example.com"
    mock_user.password_hash = "$2b$12$somehash"  # Mock bcrypt hash
    mock_user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_repo.find_by_email.return_value = mock_user

    service = AuthService(mock_repo)
    credentials = UserLogin(email="test@example.com", password="password123")

    # Mock password verification and JWT creation
    with patch("app.services.auth_service.verify_password", return_value=True):
        with patch("app.services.auth_service.create_access_token", return_value="mock-jwt-token"):
            # Act
            result = await service.login_user(credentials)

            # Assert
            assert result.token == "mock-jwt-token"
            assert result.token_type == "bearer"
            assert result.user.email == "test@example.com"
            assert result.user.id == "test-uuid-123"
            mock_repo.find_by_email.assert_called_once_with("test@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_nonexistent_email():
    """Test login with non-existent email returns 401."""
    # Arrange
    mock_repo = AsyncMock()
    mock_repo.find_by_email.return_value = None  # User not found

    service = AuthService(mock_repo)
    credentials = UserLogin(email="nonexistent@example.com", password="password123")

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await service.login_user(credentials)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid email or password"
    mock_repo.find_by_email.assert_called_once_with("nonexistent@example.com")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_wrong_password():
    """Test login with wrong password returns 401."""
    # Arrange
    mock_repo = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "test-uuid-123"
    mock_user.email = "test@example.com"
    mock_user.password_hash = "$2b$12$somehash"
    mock_user.created_at = datetime(2025, 1, 1, 0, 0, 0)
    mock_repo.find_by_email.return_value = mock_user

    service = AuthService(mock_repo)
    credentials = UserLogin(email="test@example.com", password="wrongpassword")

    # Mock password verification to fail
    with patch("app.services.auth_service.verify_password", return_value=False):
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service.login_user(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid email or password"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_error_messages_same():
    """Test both error cases return same message to prevent email enumeration."""
    mock_repo = AsyncMock()
    service = AuthService(mock_repo)

    # Test 1: Non-existent email
    mock_repo.find_by_email.return_value = None
    credentials1 = UserLogin(email="nonexistent@example.com", password="password123")

    try:
        await service.login_user(credentials1)
    except HTTPException as e:
        error_msg_1 = e.detail

    # Test 2: Wrong password
    mock_user = MagicMock()
    mock_user.password_hash = "$2b$12$somehash"
    mock_repo.find_by_email.return_value = mock_user
    credentials2 = UserLogin(email="exists@example.com", password="wrongpassword")

    with patch("app.services.auth_service.verify_password", return_value=False):
        try:
            await service.login_user(credentials2)
        except HTTPException as e:
            error_msg_2 = e.detail

    # Assert both messages are identical
    assert error_msg_1 == error_msg_2 == "Invalid email or password"
