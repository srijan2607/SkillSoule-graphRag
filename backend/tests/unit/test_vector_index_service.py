"""
Unit tests for VectorIndexService.

Tests vector index creation, verification, and management functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.vector_index_service import VectorIndexService


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4jRepository for testing."""
    repo = AsyncMock()
    repo.execute_query = AsyncMock()
    return repo


@pytest.fixture
def vector_index_service(mock_neo4j_repo):
    """Create VectorIndexService instance with mocked repository."""
    return VectorIndexService(mock_neo4j_repo)


class TestVectorIndexCreation:
    """Test vector index creation functionality."""

    @pytest.mark.asyncio
    async def test_create_vector_indexes_all_new(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test creating all vector indexes when none exist."""
        # Mock _index_exists to return False (indexes don't exist)
        vector_index_service._index_exists = AsyncMock(return_value=False)

        # Mock _create_vector_index
        vector_index_service._create_vector_index = AsyncMock()

        # Create indexes
        results = await vector_index_service.create_vector_indexes()

        # Verify all three indexes were created
        assert len(results) == 3
        assert results["skill_embedding_idx"] == "created"
        assert results["job_embedding_idx"] == "created"
        assert results["company_embedding_idx"] == "created"

        # Verify _create_vector_index was called 3 times
        assert vector_index_service._create_vector_index.call_count == 3

    @pytest.mark.asyncio
    async def test_create_vector_indexes_already_exist(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test idempotency when indexes already exist."""
        # Mock _index_exists to return True (indexes exist)
        vector_index_service._index_exists = AsyncMock(return_value=True)

        # Mock _create_vector_index (should not be called)
        vector_index_service._create_vector_index = AsyncMock()

        # Create indexes
        results = await vector_index_service.create_vector_indexes()

        # Verify all three indexes marked as already_exists
        assert len(results) == 3
        assert results["skill_embedding_idx"] == "already_exists"
        assert results["job_embedding_idx"] == "already_exists"
        assert results["company_embedding_idx"] == "already_exists"

        # Verify _create_vector_index was NOT called
        assert vector_index_service._create_vector_index.call_count == 0

    @pytest.mark.asyncio
    async def test_create_vector_indexes_partial_exist(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test creating indexes when some already exist."""
        # Mock _index_exists with different responses
        def index_exists_side_effect(index_name):
            if index_name == "skill_embedding_idx":
                return True  # Already exists
            else:
                return False  # Doesn't exist

        vector_index_service._index_exists = AsyncMock(
            side_effect=index_exists_side_effect
        )

        # Mock _create_vector_index
        vector_index_service._create_vector_index = AsyncMock()

        # Create indexes
        results = await vector_index_service.create_vector_indexes()

        # Verify results
        assert results["skill_embedding_idx"] == "already_exists"
        assert results["job_embedding_idx"] == "created"
        assert results["company_embedding_idx"] == "created"

        # Verify _create_vector_index was called 2 times (not for skill)
        assert vector_index_service._create_vector_index.call_count == 2

    @pytest.mark.asyncio
    async def test_create_vector_indexes_error_handling(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test error handling during index creation."""
        # Mock _index_exists to return False
        vector_index_service._index_exists = AsyncMock(return_value=False)

        # Mock _create_vector_index to raise error for one index
        def create_index_side_effect(name, label, prop):
            if name == "job_embedding_idx":
                raise Exception("Index creation failed")

        vector_index_service._create_vector_index = AsyncMock(
            side_effect=create_index_side_effect
        )

        # Create indexes
        results = await vector_index_service.create_vector_indexes()

        # Verify error is captured
        assert results["skill_embedding_idx"] == "created"
        assert "error:" in results["job_embedding_idx"]
        assert results["company_embedding_idx"] == "created"


class TestIndexVerification:
    """Test index verification and health check functionality."""

    @pytest.mark.asyncio
    async def test_verify_vector_indexes_all_healthy(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test verification when all indexes are healthy."""
        # Mock _get_index_status
        async def get_index_status_mock(index_name):
            return {
                "state": "ONLINE",
                "populationPercent": 100.0
            }

        vector_index_service._get_index_status = AsyncMock(
            side_effect=get_index_status_mock
        )

        # Mock _get_entity_count
        async def get_entity_count_mock(label):
            counts = {
                "Skill": 15234,
                "Job": 42108,
                "Company": 5832
            }
            return counts.get(label, 0)

        vector_index_service._get_entity_count = AsyncMock(
            side_effect=get_entity_count_mock
        )

        # Verify indexes
        health = await vector_index_service.verify_vector_indexes()

        # Check all indexes
        assert health["skill_embedding_idx"]["exists"] is True
        assert health["skill_embedding_idx"]["state"] == "ONLINE"
        assert health["skill_embedding_idx"]["population_percent"] == 100.0
        assert health["skill_embedding_idx"]["entity_count"] == 15234

        assert health["job_embedding_idx"]["exists"] is True
        assert health["job_embedding_idx"]["state"] == "ONLINE"
        assert health["job_embedding_idx"]["entity_count"] == 42108

        assert health["company_embedding_idx"]["exists"] is True
        assert health["company_embedding_idx"]["state"] == "ONLINE"
        assert health["company_embedding_idx"]["entity_count"] == 5832

    @pytest.mark.asyncio
    async def test_verify_vector_indexes_not_found(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test verification when indexes don't exist."""
        # Mock _get_index_status to return None (index not found)
        vector_index_service._get_index_status = AsyncMock(return_value=None)

        # Mock _get_entity_count
        vector_index_service._get_entity_count = AsyncMock(return_value=0)

        # Verify indexes
        health = await vector_index_service.verify_vector_indexes()

        # Check all indexes marked as not existing
        for index_name in ["skill_embedding_idx", "job_embedding_idx", "company_embedding_idx"]:
            assert health[index_name]["exists"] is False
            assert health[index_name]["state"] is None
            assert health[index_name]["population_percent"] is None

    @pytest.mark.asyncio
    async def test_verify_vector_indexes_populating(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test verification when indexes are still populating."""
        # Mock _get_index_status with POPULATING state
        async def get_index_status_mock(index_name):
            return {
                "state": "POPULATING",
                "populationPercent": 65.5
            }

        vector_index_service._get_index_status = AsyncMock(
            side_effect=get_index_status_mock
        )

        vector_index_service._get_entity_count = AsyncMock(return_value=5000)

        # Verify indexes
        health = await vector_index_service.verify_vector_indexes()

        # Check indexes are in POPULATING state
        assert health["skill_embedding_idx"]["state"] == "POPULATING"
        assert health["skill_embedding_idx"]["population_percent"] == 65.5


class TestEnsureIndexesExist:
    """Test on-demand index creation."""

    @pytest.mark.asyncio
    async def test_ensure_vector_indexes_exist_creates_missing(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test that missing indexes are created."""
        # Mock _index_exists to return False
        vector_index_service._index_exists = AsyncMock(return_value=False)

        # Mock _create_vector_index
        vector_index_service._create_vector_index = AsyncMock()

        # Ensure indexes exist
        await vector_index_service.ensure_vector_indexes_exist()

        # Verify all indexes were checked and created
        assert vector_index_service._index_exists.call_count == 3
        assert vector_index_service._create_vector_index.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_vector_indexes_exist_skips_existing(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test that existing indexes are not recreated."""
        # Mock _index_exists to return True
        vector_index_service._index_exists = AsyncMock(return_value=True)

        # Mock _create_vector_index
        vector_index_service._create_vector_index = AsyncMock()

        # Ensure indexes exist
        await vector_index_service.ensure_vector_indexes_exist()

        # Verify indexes were checked but not created
        assert vector_index_service._index_exists.call_count == 3
        assert vector_index_service._create_vector_index.call_count == 0


class TestIndexRebuild:
    """Test index rebuild functionality."""

    @pytest.mark.asyncio
    async def test_rebuild_index_if_corrupted_healthy(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test rebuild skips healthy indexes."""
        # Mock _get_index_status with ONLINE state
        vector_index_service._get_index_status = AsyncMock(
            return_value={
                "state": "ONLINE",
                "populationPercent": 100.0
            }
        )

        # Rebuild
        result = await vector_index_service.rebuild_index_if_corrupted(
            "skill_embedding_idx"
        )

        # Verify rebuild was skipped
        assert result["action"] == "skip"
        assert result["reason"] == "index_healthy"
        assert result["new_state"] == "ONLINE"

    @pytest.mark.asyncio
    async def test_rebuild_index_if_corrupted_failed_state(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test rebuild recreates corrupted indexes."""
        # Mock _get_index_status with FAILED state initially
        call_count = 0

        async def get_index_status_mock(index_name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"state": "FAILED", "populationPercent": 0.0}
            else:
                return {"state": "ONLINE", "populationPercent": 100.0}

        vector_index_service._get_index_status = AsyncMock(
            side_effect=get_index_status_mock
        )

        # Mock _create_vector_index
        vector_index_service._create_vector_index = AsyncMock()

        # Rebuild
        result = await vector_index_service.rebuild_index_if_corrupted(
            "skill_embedding_idx"
        )

        # Verify rebuild was performed
        assert result["action"] == "rebuild"
        assert "corrupted_state" in result["reason"]
        assert result["new_state"] == "ONLINE"

        # Verify drop and recreate were called
        assert mock_neo4j_repo.execute_query.call_count >= 1  # DROP query
        assert vector_index_service._create_vector_index.call_count == 1

    @pytest.mark.asyncio
    async def test_rebuild_index_if_corrupted_not_found(
        self,
        vector_index_service,
        mock_neo4j_repo
    ):
        """Test rebuild skips when index not found."""
        # Mock _get_index_status to return None
        vector_index_service._get_index_status = AsyncMock(return_value=None)

        # Rebuild
        result = await vector_index_service.rebuild_index_if_corrupted(
            "skill_embedding_idx"
        )

        # Verify rebuild was skipped
        assert result["action"] == "skip"
        assert result["reason"] == "index_not_found"


class TestIndexConstants:
    """Test VectorIndexService configuration constants."""

    def test_embedding_dimensions(self, vector_index_service):
        """Test embedding dimensions constant."""
        assert vector_index_service.EMBEDDING_DIMENSIONS == 384

    def test_similarity_function(self, vector_index_service):
        """Test similarity function constant."""
        assert vector_index_service.SIMILARITY_FUNCTION == "cosine"

    def test_vector_indexes_definitions(self, vector_index_service):
        """Test vector index definitions."""
        indexes = vector_index_service.VECTOR_INDEXES

        # Verify count
        assert len(indexes) == 3

        # Verify structure
        index_names = [idx["name"] for idx in indexes]
        assert "skill_embedding_idx" in index_names
        assert "job_embedding_idx" in index_names
        assert "company_embedding_idx" in index_names

        # Verify each definition has required fields
        for idx in indexes:
            assert "name" in idx
            assert "node_label" in idx
            assert "property" in idx
            assert idx["property"] == "embedding"
