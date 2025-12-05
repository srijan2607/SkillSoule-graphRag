"""
Unit tests for batch processing functionality.

Tests batch iteration, batch statistics, and batch processor error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.utils.batch_iterator import batch_iterator, calculate_batch_stats
from app.services.batch_processor import BatchProcessor


class TestBatchIterator:
    """Test suite for batch_iterator utility function."""

    def test_batch_iterator_evenly_divisible(self):
        """Test batch iterator with evenly divisible list."""
        items = list(range(1, 11))  # [1, 2, 3, ..., 10]
        batches = list(batch_iterator(items, batch_size=5))

        assert len(batches) == 2
        assert batches[0] == (1, [1, 2, 3, 4, 5])
        assert batches[1] == (2, [6, 7, 8, 9, 10])

    def test_batch_iterator_with_remainder(self):
        """Test batch iterator with remainder."""
        items = list(range(1, 11))  # [1, 2, 3, ..., 10]
        batches = list(batch_iterator(items, batch_size=3))

        assert len(batches) == 4
        assert batches[0] == (1, [1, 2, 3])
        assert batches[1] == (2, [4, 5, 6])
        assert batches[2] == (3, [7, 8, 9])
        assert batches[3] == (4, [10])

    def test_batch_iterator_single_item(self):
        """Test batch iterator with single item."""
        items = [42]
        batches = list(batch_iterator(items, batch_size=10))

        assert len(batches) == 1
        assert batches[0] == (1, [42])

    def test_batch_iterator_empty_list(self):
        """Test batch iterator with empty list."""
        items = []
        batches = list(batch_iterator(items, batch_size=10))

        assert len(batches) == 0

    def test_batch_iterator_batch_size_one(self):
        """Test batch iterator with batch size of 1."""
        items = [1, 2, 3]
        batches = list(batch_iterator(items, batch_size=1))

        assert len(batches) == 3
        assert batches[0] == (1, [1])
        assert batches[1] == (2, [2])
        assert batches[2] == (3, [3])

    def test_batch_iterator_large_batch_size(self):
        """Test batch iterator with batch size larger than list."""
        items = [1, 2, 3]
        batches = list(batch_iterator(items, batch_size=100))

        assert len(batches) == 1
        assert batches[0] == (1, [1, 2, 3])


class TestCalculateBatchStats:
    """Test suite for calculate_batch_stats utility function."""

    def test_calculate_batch_stats_evenly_divisible(self):
        """Test batch statistics with evenly divisible items."""
        stats = calculate_batch_stats(total_items=1000, batch_size=100)

        assert stats["total_batches"] == 10
        assert stats["full_batches"] == 10
        assert stats["last_batch_size"] == 100

    def test_calculate_batch_stats_with_remainder(self):
        """Test batch statistics with remainder."""
        stats = calculate_batch_stats(total_items=1055, batch_size=100)

        assert stats["total_batches"] == 11
        assert stats["full_batches"] == 10
        assert stats["last_batch_size"] == 55

    def test_calculate_batch_stats_single_batch(self):
        """Test batch statistics with single batch."""
        stats = calculate_batch_stats(total_items=50, batch_size=100)

        assert stats["total_batches"] == 1
        assert stats["full_batches"] == 0
        assert stats["last_batch_size"] == 50

    def test_calculate_batch_stats_empty(self):
        """Test batch statistics with zero items."""
        stats = calculate_batch_stats(total_items=0, batch_size=100)

        assert stats["total_batches"] == 0
        assert stats["full_batches"] == 0
        assert stats["last_batch_size"] == 100  # Default when no items


class TestBatchProcessor:
    """Test suite for BatchProcessor service."""

    @pytest.fixture
    def mock_neo4j_repo(self):
        """Create mock Neo4j repository."""
        mock = AsyncMock()
        mock.create_skill_node = AsyncMock()
        mock.create_skill_category_relationship = AsyncMock()
        mock.create_skill_subcategory_relationship = AsyncMock()
        mock.create_job_node = AsyncMock()
        mock.create_job_company_relationship = AsyncMock()
        mock.create_job_location_relationship = AsyncMock()
        mock.create_job_skill_relationships = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        mock = AsyncMock()
        mock.generate_embedding = AsyncMock(return_value={
            "embedding": [0.1] * 384,
            "model_version": "test-model"
        })
        return mock

    @pytest.fixture
    def mock_error_logger(self):
        """Create mock error logging service."""
        mock = AsyncMock()
        mock.log_ingestion_error = AsyncMock()
        return mock

    @pytest.fixture
    def batch_processor(
        self,
        mock_neo4j_repo,
        mock_embedding_service,
        mock_error_logger
    ):
        """Create BatchProcessor instance with mocks."""
        return BatchProcessor(
            neo4j_repo=mock_neo4j_repo,
            embedding_service=mock_embedding_service,
            error_logger=mock_error_logger
        )

    @pytest.mark.asyncio
    async def test_process_skills_batch_success(
        self,
        batch_processor,
        mock_embedding_service,
        mock_neo4j_repo
    ):
        """Test successful skills batch processing."""
        batch = [
            {
                "ID": "skill-001",
                "NAME": "Python",
                "DESCRIPTION": "Programming language",
                "CATEGORY": "programming",
                "SUBCATEGORY": "languages"
            },
            {
                "ID": "skill-002",
                "NAME": "React",
                "DESCRIPTION": "JavaScript library",
                "CATEGORY": "frameworks",
                "SUBCATEGORY": "frontend"
            }
        ]

        result = await batch_processor.process_skills_batch(
            batch=batch,
            job_id="test-job-123",
            batch_number=1,
            start_row=1
        )

        # Verify all records processed successfully
        assert result["processed"] == 2
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

        # Verify embedding service called for each record
        assert mock_embedding_service.generate_embedding.call_count == 2

        # Verify Neo4j operations called for each record
        assert mock_neo4j_repo.create_skill_node.call_count == 2
        assert mock_neo4j_repo.create_skill_category_relationship.call_count == 2
        assert mock_neo4j_repo.create_skill_subcategory_relationship.call_count == 2

    @pytest.mark.asyncio
    async def test_process_skills_batch_with_errors(
        self,
        batch_processor,
        mock_neo4j_repo,
        mock_error_logger
    ):
        """Test skills batch processing with some failures."""
        # Make second record fail
        mock_neo4j_repo.create_skill_node.side_effect = [
            None,  # First succeeds
            Exception("Database connection error"),  # Second fails
            None   # Third succeeds
        ]

        batch = [
            {
                "ID": "skill-001",
                "NAME": "Python",
                "DESCRIPTION": "Programming language",
                "CATEGORY": "programming"
            },
            {
                "ID": "skill-002",
                "NAME": "React",
                "DESCRIPTION": "JavaScript library",
                "CATEGORY": "frameworks"
            },
            {
                "ID": "skill-003",
                "NAME": "Docker",
                "DESCRIPTION": "Containerization",
                "CATEGORY": "devops"
            }
        ]

        result = await batch_processor.process_skills_batch(
            batch=batch,
            job_id="test-job-123",
            batch_number=1,
            start_row=1
        )

        # Verify processing continues after error
        assert result["processed"] == 2
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert "Row 2" in result["errors"][0]

        # Verify error was logged
        assert mock_error_logger.log_ingestion_error.call_count == 1

    @pytest.mark.asyncio
    async def test_process_jobs_batch_success(
        self,
        batch_processor,
        mock_embedding_service,
        mock_neo4j_repo
    ):
        """Test successful jobs batch processing."""
        batch = [
            {
                "Job ID": "job-001",
                "Job Title": "Python Developer",
                "Company Name": "Tech Corp",
                "Location": "New York",
                "Description": "Backend developer role",
                "standardized_skills": ["python", "django", "postgresql"]
            }
        ]

        result = await batch_processor.process_jobs_batch(
            batch=batch,
            job_id="test-job-456",
            batch_number=1,
            start_row=1
        )

        # Verify record processed successfully
        assert result["processed"] == 1
        assert result["failed"] == 0
        assert len(result["errors"]) == 0

        # Verify all Neo4j operations called
        assert mock_neo4j_repo.create_job_node.call_count == 1
        assert mock_neo4j_repo.create_job_company_relationship.call_count == 1
        assert mock_neo4j_repo.create_job_location_relationship.call_count == 1
        assert mock_neo4j_repo.create_job_skill_relationships.call_count == 1

    @pytest.mark.asyncio
    async def test_process_jobs_batch_with_errors(
        self,
        batch_processor,
        mock_neo4j_repo,
        mock_error_logger
    ):
        """Test jobs batch processing with failures."""
        mock_neo4j_repo.create_job_node.side_effect = Exception("Neo4j error")

        batch = [
            {
                "Job ID": "job-001",
                "Job Title": "Developer",
                "Company Name": "Tech Corp",
                "Location": "NYC",
                "Description": "Backend role"
            }
        ]

        result = await batch_processor.process_jobs_batch(
            batch=batch,
            job_id="test-job-456",
            batch_number=1,
            start_row=1
        )

        # Verify error handling
        assert result["processed"] == 0
        assert result["failed"] == 1
        assert len(result["errors"]) == 1

        # Verify error logged
        assert mock_error_logger.log_ingestion_error.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_statistics_tracking(
        self,
        batch_processor,
        mock_neo4j_repo
    ):
        """Test that batch statistics are correctly tracked."""
        # Mix of successes and failures
        mock_neo4j_repo.create_skill_node.side_effect = [
            None,  # Success
            Exception("Error"),  # Failure
            None,  # Success
            Exception("Error"),  # Failure
            None   # Success
        ]

        batch = [
            {"ID": f"skill-{i}", "NAME": f"Skill {i}", "DESCRIPTION": "Test"}
            for i in range(5)
        ]

        result = await batch_processor.process_skills_batch(
            batch=batch,
            job_id="test-job",
            batch_number=1,
            start_row=1
        )

        assert result["processed"] == 3
        assert result["failed"] == 2
        assert len(result["errors"]) == 2
