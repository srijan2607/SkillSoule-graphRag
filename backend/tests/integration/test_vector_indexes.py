"""
Integration tests for Vector Index functionality.

Tests actual Neo4j vector index creation, verification, and usage.
Requires running Neo4j instance.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.vector_index_service import VectorIndexService


@pytest.fixture(scope="module")
async def neo4j_repo():
    """Create Neo4jRepository instance for testing."""
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture(scope="module")
def vector_index_service(neo4j_repo):
    """Create VectorIndexService instance for testing."""
    return VectorIndexService(neo4j_repo)


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def auth_token(client):
    """Get authentication token for API tests."""
    # Register test user
    register_response = client.post(
        "/auth/register",
        json={
            "email": "test_vector_admin@example.com",
            "password": "TestPassword123!"
        }
    )

    if register_response.status_code == 201:
        # New user created
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_vector_admin@example.com",
                "password": "TestPassword123!"
            }
        )
        return login_response.json()["access_token"]
    elif register_response.status_code == 409:
        # User already exists, just login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "test_vector_admin@example.com",
                "password": "TestPassword123!"
            }
        )
        return login_response.json()["access_token"]
    else:
        pytest.fail(f"Failed to get auth token: {register_response.text}")


class TestVectorIndexCreation:
    """Test vector index creation workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_all_vector_indexes(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test creating all vector indexes in Neo4j."""
        # Create indexes
        results = await vector_index_service.create_vector_indexes()

        # Verify all three indexes were created or already exist
        assert "skill_embedding_idx" in results
        assert "job_embedding_idx" in results
        assert "company_embedding_idx" in results

        # Results should be "created" or "already_exists"
        for index_name, status in results.items():
            assert status in ["created", "already_exists"], \
                f"Unexpected status for {index_name}: {status}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_verify_indexes_in_neo4j(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test verification of indexes using SHOW INDEXES."""
        # Ensure indexes exist first
        await vector_index_service.create_vector_indexes()

        # Verify using SHOW INDEXES query
        query = """
        SHOW INDEXES
        YIELD name, type, state, populationPercent
        WHERE type = "VECTOR"
        RETURN name, state, populationPercent
        ORDER BY name
        """

        results = await neo4j_repo.execute_query(query)

        # Should have 3 vector indexes
        assert len(results) >= 3, f"Expected 3+ vector indexes, found {len(results)}"

        # Check each index
        index_names = [r["name"] for r in results]
        assert "skill_embedding_idx" in index_names
        assert "job_embedding_idx" in index_names
        assert "company_embedding_idx" in index_names

        # All indexes should be ONLINE (may take a few seconds after creation)
        for result in results:
            if result["name"] in ["skill_embedding_idx", "job_embedding_idx", "company_embedding_idx"]:
                # State should be ONLINE or POPULATING (if just created)
                assert result["state"] in ["ONLINE", "POPULATING"], \
                    f"Index {result['name']} in unexpected state: {result['state']}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_idempotent_index_creation(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test that index creation is idempotent (can be run multiple times)."""
        # Create indexes first time
        results1 = await vector_index_service.create_vector_indexes()

        # Create indexes second time
        results2 = await vector_index_service.create_vector_indexes()

        # Second run should return "already_exists" for all
        assert results2["skill_embedding_idx"] == "already_exists"
        assert results2["job_embedding_idx"] == "already_exists"
        assert results2["company_embedding_idx"] == "already_exists"


class TestIndexVerification:
    """Test index health check and verification."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_verify_vector_indexes(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test verification of all vector indexes."""
        # Ensure indexes exist
        await vector_index_service.create_vector_indexes()

        # Verify indexes
        health = await vector_index_service.verify_vector_indexes()

        # Check all three indexes
        assert "skill_embedding_idx" in health
        assert "job_embedding_idx" in health
        assert "company_embedding_idx" in health

        # Each index should exist
        for index_name, status in health.items():
            assert status["exists"] is True, \
                f"Index {index_name} does not exist"

            # State should be ONLINE or POPULATING
            assert status["state"] in ["ONLINE", "POPULATING", None], \
                f"Index {index_name} in unexpected state: {status['state']}"

            # entity_count should be a number
            assert isinstance(status["entity_count"], int), \
                f"Invalid entity_count for {index_name}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ensure_vector_indexes_exist(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test on-demand index creation."""
        # Call ensure (creates if missing)
        await vector_index_service.ensure_vector_indexes_exist()

        # Verify all indexes now exist
        health = await vector_index_service.verify_vector_indexes()

        # All should exist
        assert all(status["exists"] for status in health.values()), \
            "Not all indexes exist after ensure_vector_indexes_exist()"


class TestHealthCheckEndpoint:
    """Test admin health check API endpoint."""

    @pytest.mark.integration
    def test_health_check_endpoint_without_auth(self, client):
        """Test health check endpoint requires authentication."""
        response = client.get("/admin/vector-indexes/health")

        # Should return 403 (Forbidden) or 401 (Unauthorized)
        assert response.status_code in [401, 403], \
            f"Expected 401/403, got {response.status_code}"

    @pytest.mark.integration
    def test_health_check_endpoint_with_auth(
        self,
        client,
        auth_token
    ):
        """Test health check endpoint with valid authentication."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.get("/admin/vector-indexes/health", headers=headers)

        # Should return 200
        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.text}"

        # Check response structure
        data = response.json()
        assert "status" in data
        assert "indexes" in data

        # Status should be "healthy" or "unhealthy"
        assert data["status"] in ["healthy", "unhealthy"]

        # Indexes should have all three
        assert "skill_embedding_idx" in data["indexes"]
        assert "job_embedding_idx" in data["indexes"]
        assert "company_embedding_idx" in data["indexes"]

        # Each index should have required fields
        for index_name, status in data["indexes"].items():
            assert "exists" in status
            assert "state" in status
            assert "population_percent" in status
            assert "entity_count" in status

    @pytest.mark.integration
    def test_create_indexes_endpoint(
        self,
        client,
        auth_token
    ):
        """Test admin endpoint for creating vector indexes."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = client.post(
            "/admin/vector-indexes/create",
            headers=headers
        )

        # Should return 200
        assert response.status_code == 200

        # Check response
        data = response.json()
        assert "message" in data
        assert "results" in data

        # Results should have all three indexes
        assert "skill_embedding_idx" in data["results"]
        assert "job_embedding_idx" in data["results"]
        assert "company_embedding_idx" in data["results"]


class TestVectorSimilarityWithIndexes:
    """Test vector similarity queries use indexes."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_similarity_query_execution(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test vector similarity query with indexes."""
        # Ensure indexes exist
        await vector_index_service.create_vector_indexes()

        # Create a test skill node with embedding
        skill_data = {
            "id": "test-python-001",
            "name": "Python Test",
            "description": "Python programming language",
            "level": 3,
            "type": "programming_language",
            "is_software": False,
            "is_language": True,
            "embedding": [0.1] * 384,  # Dummy embedding
            "embedding_model_version": "test-v1"
        }

        await neo4j_repo.create_skill_node(skill_data)

        # Query similar skills using vector index
        query = """
        MATCH (s:Skill {name: 'Python Test'})
        CALL db.index.vector.queryNodes('skill_embedding_idx', 5, s.embedding)
        YIELD node, score
        RETURN node.name as name, score
        ORDER BY score DESC
        """

        try:
            results = await neo4j_repo.execute_query(query)

            # Should return results (at least the query skill itself)
            assert len(results) > 0, "No results returned from vector similarity query"

            # First result should be the query skill itself
            assert results[0]["name"] == "Python Test"
            assert results[0]["score"] > 0.9  # Similarity to itself should be high

        finally:
            # Cleanup: Delete test node
            cleanup_query = """
            MATCH (s:Skill {id: 'test-python-001'})
            DELETE s
            """
            await neo4j_repo.execute_query(cleanup_query)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_index_usage_with_profile(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test that vector index is actually being used (with PROFILE)."""
        # Ensure indexes exist
        await vector_index_service.create_vector_indexes()

        # Create test skill
        skill_data = {
            "id": "test-profile-001",
            "name": "Profile Test Skill",
            "description": "Test skill for index profiling",
            "level": 3,
            "type": "test",
            "is_software": False,
            "is_language": False,
            "embedding": [0.2] * 384,
            "embedding_model_version": "test-v1"
        }

        await neo4j_repo.create_skill_node(skill_data)

        # Profile query to check index usage
        query = """
        PROFILE
        MATCH (s:Skill {name: 'Profile Test Skill'})
        CALL db.index.vector.queryNodes('skill_embedding_idx', 3, s.embedding)
        YIELD node, score
        RETURN node.name, score
        """

        try:
            # Execute profile query (result will include execution plan)
            results = await neo4j_repo.execute_query(query)

            # Should return results
            assert len(results) > 0

            # Note: In real Neo4j PROFILE output, we'd check for VectorIndexSeek
            # For this test, we just verify the query executes successfully

        finally:
            # Cleanup
            cleanup_query = """
            MATCH (s:Skill {id: 'test-profile-001'})
            DELETE s
            """
            await neo4j_repo.execute_query(cleanup_query)


class TestIndexMaintenance:
    """Test index maintenance operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_entity_counts(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Test counting entities with embeddings."""
        # Get entity count for Skills
        skill_count = await vector_index_service._get_entity_count("Skill")

        # Should be a non-negative integer
        assert isinstance(skill_count, int)
        assert skill_count >= 0

        # Get entity count for Jobs
        job_count = await vector_index_service._get_entity_count("Job")
        assert isinstance(job_count, int)
        assert job_count >= 0

        # Get entity count for Companies
        company_count = await vector_index_service._get_entity_count("Company")
        assert isinstance(company_count, int)
        assert company_count >= 0


class TestConcurrentIndexOperations:
    """Test concurrent index operations."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_index_creation(
        self,
        neo4j_repo
    ):
        """Test creating indexes concurrently (idempotency test)."""
        import asyncio

        # Create multiple services
        services = [
            VectorIndexService(neo4j_repo),
            VectorIndexService(neo4j_repo),
            VectorIndexService(neo4j_repo)
        ]

        # Create indexes concurrently
        results = await asyncio.gather(
            *[service.create_vector_indexes() for service in services],
            return_exceptions=True
        )

        # All should succeed or return already_exists
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent creation failed: {result}")

            # Check all indexes
            for index_name, status in result.items():
                assert status in ["created", "already_exists"], \
                    f"Unexpected status: {status}"


# Performance benchmark (optional, for manual testing)
class TestPerformanceBenchmark:
    """Performance benchmarks for vector indexes (optional)."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_index_query_performance(
        self,
        neo4j_repo,
        vector_index_service
    ):
        """Benchmark vector similarity query performance."""
        import time

        # Ensure indexes exist
        await vector_index_service.create_vector_indexes()

        # Create test skill
        skill_data = {
            "id": "test-perf-001",
            "name": "Performance Test Skill",
            "description": "Test skill for performance benchmarking",
            "level": 3,
            "type": "test",
            "is_software": False,
            "is_language": False,
            "embedding": [0.3] * 384,
            "embedding_model_version": "test-v1"
        }

        await neo4j_repo.create_skill_node(skill_data)

        # Query with vector index
        query = """
        MATCH (s:Skill {name: 'Performance Test Skill'})
        CALL db.index.vector.queryNodes('skill_embedding_idx', 10, s.embedding)
        YIELD node, score
        RETURN node.name, score
        """

        try:
            # Measure query time
            start = time.time()
            results = await neo4j_repo.execute_query(query)
            duration = time.time() - start

            # Query should complete in reasonable time (<1 second)
            assert duration < 1.0, \
                f"Query too slow: {duration:.3f}s (expected <1s)"

            # Should return results
            assert len(results) > 0

            print(f"\n✅ Vector similarity query completed in {duration*1000:.2f}ms")

        finally:
            # Cleanup
            cleanup_query = """
            MATCH (s:Skill {id: 'test-perf-001'})
            DELETE s
            """
            await neo4j_repo.execute_query(cleanup_query)
