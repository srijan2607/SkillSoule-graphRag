"""Integration tests for authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_success(test_db):
    """Test POST /auth/register with valid data returns 201."""
    # Arrange
    user_data = {
        "email": "newuser@example.com",
        "password": "password123"
    }

    # Act
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_duplicate_email(test_db):
    """Test POST /auth/register with duplicate email returns 409."""
    # Arrange - Register first user
    user_data = {
        "email": "duplicate@example.com",
        "password": "password123"
    }
    client.post("/auth/register", json=user_data)

    # Act - Try to register same email again
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 409
    data = response.json()
    assert data["detail"] == "Email already exists"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_invalid_email(test_db):
    """Test POST /auth/register with invalid email returns 422."""
    # Arrange
    user_data = {
        "email": "not-an-email",
        "password": "password123"
    }

    # Act
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_password_too_short(test_db):
    """Test POST /auth/register with short password returns 422."""
    # Arrange
    user_data = {
        "email": "test@example.com",
        "password": "short"
    }

    # Act
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_user_created_in_db(test_db, prisma_client):
    """Test that registered user is actually created in database."""
    # Arrange
    user_data = {
        "email": "dbtest@example.com",
        "password": "password123"
    }

    # Act
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Verify in database
    user = await prisma_client.user.find_unique(where={"id": user_id})
    assert user is not None
    assert user.email == "dbtest@example.com"
    assert user.password_hash is not None
    assert user.password_hash != "password123"  # Password should be hashed


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_endpoint_password_not_exposed(test_db):
    """Test that password is not exposed in API response."""
    # Arrange
    user_data = {
        "email": "secure@example.com",
        "password": "supersecret123"
    }

    # Act
    response = client.post("/auth/register", json=user_data)

    # Assert
    assert response.status_code == 201
    data = response.json()

    # Verify password fields are not in response
    assert "password" not in data
    assert "password_hash" not in data

    # Verify only expected fields are present
    expected_fields = {"id", "email", "created_at"}
    assert set(data.keys()) == expected_fields


# Login Integration Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_endpoint_success(test_db):
    """Test POST /auth/login with valid credentials returns 200 with token."""
    # Arrange - Register a user first
    register_data = {
        "email": "logintest@example.com",
        "password": "password123"
    }
    client.post("/auth/register", json=register_data)

    # Act - Login with valid credentials
    login_data = {
        "email": "logintest@example.com",
        "password": "password123"
    }
    response = client.post("/auth/login", json=login_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert isinstance(data["token"], str)
    assert len(data["token"]) > 0
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "logintest@example.com"
    assert "id" in data["user"]
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_endpoint_nonexistent_email(test_db):
    """Test POST /auth/login with non-existent email returns 401."""
    # Arrange
    login_data = {
        "email": "nonexistent@example.com",
        "password": "password123"
    }

    # Act
    response = client.post("/auth/login", json=login_data)

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_endpoint_wrong_password(test_db):
    """Test POST /auth/login with wrong password returns 401."""
    # Arrange - Register a user first
    register_data = {
        "email": "wrongpass@example.com",
        "password": "correctpassword"
    }
    client.post("/auth/register", json=register_data)

    # Act - Login with wrong password
    login_data = {
        "email": "wrongpass@example.com",
        "password": "wrongpassword"
    }
    response = client.post("/auth/login", json=login_data)

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid email or password"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_endpoint_token_is_valid_jwt(test_db):
    """Test that returned token is a valid JWT."""
    # Arrange - Register and login
    register_data = {
        "email": "jwttest@example.com",
        "password": "password123"
    }
    reg_response = client.post("/auth/register", json=register_data)
    user_id = reg_response.json()["id"]

    login_data = {
        "email": "jwttest@example.com",
        "password": "password123"
    }
    login_response = client.post("/auth/login", json=login_data)

    # Assert
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    # Decode and verify JWT token
    import jwt
    from app.config import settings

    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    assert payload["sub"] == user_id
    assert payload["email"] == "jwttest@example.com"
    assert "iat" in payload
    assert "exp" in payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_endpoint_user_info_matches(test_db):
    """Test that user info in response matches registered user."""
    # Arrange - Register a user
    register_data = {
        "email": "matchtest@example.com",
        "password": "password123"
    }
    reg_response = client.post("/auth/register", json=register_data)
    registered_user = reg_response.json()

    # Act - Login
    login_data = {
        "email": "matchtest@example.com",
        "password": "password123"
    }
    login_response = client.post("/auth/login", json=login_data)

    # Assert - User info matches
    assert login_response.status_code == 200
    login_user = login_response.json()["user"]

    assert login_user["id"] == registered_user["id"]
    assert login_user["email"] == registered_user["email"]
    assert login_user["created_at"] == registered_user["created_at"]
