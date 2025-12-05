"""Pytest configuration and fixtures for testing."""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from prisma import Prisma
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def prisma_client() -> AsyncGenerator[Prisma, None]:
    """
    Provide a Prisma client for testing.

    Connects to test database and ensures clean state.
    """
    client = Prisma()
    await client.connect()

    yield client

    # Cleanup: Delete all test data (order matters - delete child records first)
    try:
        await client.ingestionjob.delete_many()
        await client.user.delete_many()
    except Exception:
        pass

    await client.disconnect()


@pytest.fixture
async def test_db(prisma_client: Prisma) -> AsyncGenerator[Prisma, None]:
    """
    Provide a clean test database for each test.

    Ensures database is empty before test runs.
    """
    # Clean database before test
    try:
        await prisma_client.ingestionjob.delete_many()
        await prisma_client.user.delete_many()
    except Exception:
        pass

    yield prisma_client

    # Clean database after test
    try:
        await prisma_client.ingestionjob.delete_many()
        await prisma_client.user.delete_many()
    except Exception:
        pass


@pytest.fixture
async def prisma_test_db(prisma_client: Prisma) -> AsyncGenerator[Prisma, None]:
    """
    Alias for test_db fixture for integration tests.

    Provides a clean Prisma database with automatic cleanup.
    Creates a test user for foreign key constraints.
    """
    # Clean database before test
    try:
        await prisma_client.orphanskilllog.delete_many()
        await prisma_client.queryhistory.delete_many()
        await prisma_client.ingestionjob.delete_many()
        await prisma_client.user.delete_many()
    except Exception:
        pass

    # Create test user for foreign key constraints
    try:
        await prisma_client.user.create(data={
            "id": "test-user",
            "email": "test@example.com",
            "password_hash": "hashed_password"
        })
    except Exception:
        pass

    yield prisma_client

    # Clean database after test
    try:
        await prisma_client.orphanskilllog.delete_many()
        await prisma_client.queryhistory.delete_many()
        await prisma_client.ingestionjob.delete_many()
        await prisma_client.user.delete_many()
    except Exception:
        pass


@pytest.fixture
async def neo4j_test_db() -> AsyncGenerator[Neo4jRepository, None]:
    """
    Provide a Neo4j test database with automatic cleanup.

    Cleans all test data before and after each test to ensure isolation.
    """
    neo4j_repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await neo4j_repo.connect()

    # Clean database before test
    async with neo4j_repo.driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    yield neo4j_repo

    # Clean database after test
    async with neo4j_repo.driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await neo4j_repo.close()


@pytest.fixture
async def neo4j_repo() -> AsyncGenerator[Neo4jRepository, None]:
    """
    Alias for neo4j_test_db fixture for integration tests.

    Provides a clean Neo4j database with automatic cleanup.
    """
    neo4j_repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await neo4j_repo.connect()

    # Clean database before test
    async with neo4j_repo.driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    yield neo4j_repo

    # Clean database after test
    async with neo4j_repo.driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await neo4j_repo.close()


@pytest.fixture
async def ingestion_repo(prisma_client: Prisma) -> IngestionRepository:
    """
    Provide an IngestionRepository for testing.

    Uses the prisma_client fixture to ensure clean database state.
    """
    return IngestionRepository(db=prisma_client)


@pytest.fixture
def auth_token() -> str:
    """
    Provide a test JWT authentication token.

    Returns:
        str: Test JWT token for authenticated endpoints
    """
    # For testing purposes, return a mock token
    # In actual implementation, this would be a valid JWT signed with test key
    return "test_jwt_token_for_testing"


@pytest.fixture
def test_user_id() -> str:
    """
    Provide a consistent test user ID for tests.

    Returns:
        str: Test user ID
    """
    return "test-user-123"


@pytest.fixture
async def test_client():
    """
    Provide a FastAPI test client for API integration tests.

    Returns:
        TestClient: FastAPI test client with dependency overrides
    """
    from fastapi.testclient import TestClient
    from app.main import app
    from app.middleware.auth import get_current_user

    # Override authentication dependency for testing
    async def override_get_current_user():
        return "test-user-123"

    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    # Clean up dependency overrides
    app.dependency_overrides.clear()
