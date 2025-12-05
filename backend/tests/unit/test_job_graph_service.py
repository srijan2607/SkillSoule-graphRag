"""Unit tests for JobGraphService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.job_graph_service import JobGraphService


class MockEmbeddingService:
    """Mock EmbeddingService for testing."""

    async def generate_batch_embeddings(self, texts):
        """Return mock embeddings."""
        return [
            {
                "embedding": [0.1] * 384,
                "model_version": "all-MiniLM-L6-v2"
            }
            for _ in texts
        ]


class MockNeo4jRepo:
    """Mock Neo4jRepository for testing."""

    def __init__(self):
        self.driver = MagicMock()
        self.session = AsyncMock()
        self.tx = AsyncMock()

        # Setup transaction
        self.tx.run = AsyncMock()
        self.tx.commit = AsyncMock()
        self.tx.rollback = AsyncMock()

        # Setup session
        self.session.begin_transaction = AsyncMock(return_value=self.tx)
        self.session.__aenter__ = AsyncMock(return_value=self.session)
        self.session.__aexit__ = AsyncMock()

        # Setup driver
        self.driver.session = MagicMock(return_value=self.session)


class MockIngestionRepo:
    """Mock IngestionRepository for testing."""

    def __init__(self):
        self.update_progress_called = False

    async def update_progress(self, job_id, processed_records, total_records):
        """Mock update progress."""
        self.update_progress_called = True


@pytest.mark.unit
class TestJobGraphService:
    """Test suite for JobGraphService."""

    def setup_method(self):
        """Setup test fixtures."""
        self.embedding_service = MockEmbeddingService()
        self.neo4j_repo = MockNeo4jRepo()
        self.ingestion_repo = MockIngestionRepo()
        self.service = JobGraphService(
            self.embedding_service,
            self.neo4j_repo,
            self.ingestion_repo
        )

    def test_get_job_embedding_text_primary(self):
        """Test embedding text selection - primary Job Description."""
        job = {
            "Job ID": "1",
            "Job Description": "Python developer with 3 years experience",
            "Description": "Other description"
        }
        result = self.service._get_job_embedding_text(job)
        assert result == "Python developer with 3 years experience"

    def test_get_job_embedding_text_fallback(self):
        """Test embedding text selection - fallback to Description."""
        job = {
            "Job ID": "2",
            "Job Description": "",
            "Description": "Java developer position"
        }
        result = self.service._get_job_embedding_text(job)
        assert result == "Java developer position"

    def test_get_job_embedding_text_empty(self):
        """Test embedding text selection - empty when neither present."""
        job = {
            "Job ID": "3",
            "Job Description": "",
            "Description": ""
        }
        result = self.service._get_job_embedding_text(job)
        assert result == ""

    def test_get_job_embedding_text_whitespace_only(self):
        """Test embedding text selection - whitespace treated as empty."""
        job = {
            "Job ID": "4",
            "Job Description": "   ",
            "Description": "  \n  "
        }
        result = self.service._get_job_embedding_text(job)
        assert result == ""

    def test_get_job_embedding_text_missing_fields(self):
        """Test embedding text selection - missing fields handled gracefully."""
        job = {"Job ID": "5"}
        result = self.service._get_job_embedding_text(job)
        assert result == ""

    @pytest.mark.asyncio
    async def test_create_job_node_all_fields(self):
        """Test job node creation includes all 30 CSV fields."""
        job_row = {
            "Job ID": "job-123",
            "Job Title": "Senior Python Developer",
            "Location": "Bangalore",
            "District": "Bangalore Urban",
            "Via": "LinkedIn",
            "Salary": "15-20 LPA",
            "Minimum Salary": 1500000,
            "Maximum Salary": 2000000,
            "Mean Salary": 1750000,
            "Unit of Measure": "per annum",
            "Schedule Type": "Full-time",
            "Work From Home": 1,
            "Posted At": "2025-10-23T10:00:00",
            "Description": "Short description",
            "Job Description": "Full job description text",
            "Apply Options": "Apply on company website",
            "Exact Matched Company": 1,
            "NCO_Code_algo": "2512.10",
            "Description Token Count": 50,
            "Company Description Token Count": 100,
            "Job Description Token Count": 200
        }
        embedding_data = {
            "embedding": [0.1] * 384,
            "model_version": "all-MiniLM-L6-v2"
        }

        mock_tx = AsyncMock()
        await self.service._create_job_node(mock_tx, job_row, embedding_data)

        # Verify tx.run was called
        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        # Verify all fields are passed
        assert call_args[1]["job_id"] == "job-123"
        assert call_args[1]["job_title"] == "Senior Python Developer"
        assert call_args[1]["location"] == "Bangalore"
        assert call_args[1]["district"] == "Bangalore Urban"
        assert call_args[1]["via"] == "LinkedIn"
        assert call_args[1]["salary"] == "15-20 LPA"
        assert call_args[1]["min_salary"] == 1500000
        assert call_args[1]["max_salary"] == 2000000
        assert call_args[1]["mean_salary"] == 1750000
        assert call_args[1]["salary_unit"] == "per annum"
        assert call_args[1]["schedule_type"] == "Full-time"
        assert call_args[1]["work_from_home"] is True
        assert call_args[1]["description"] == "Short description"
        assert call_args[1]["job_description"] == "Full job description text"
        assert call_args[1]["apply_options"] == "Apply on company website"
        assert call_args[1]["exact_matched_company"] is True
        assert call_args[1]["nco_code"] == "2512.10"
        assert call_args[1]["description_token_count"] == 50
        assert call_args[1]["company_description_token_count"] == 100
        assert call_args[1]["job_description_token_count"] == 200
        assert call_args[1]["embedding"] == [0.1] * 384
        assert call_args[1]["embedding_model_version"] == "all-MiniLM-L6-v2"

    @pytest.mark.asyncio
    async def test_create_job_node_null_fields(self):
        """Test job node creation handles NULL fields gracefully."""
        job_row = {
            "Job ID": "job-456",
            "Job Title": "Developer",
            # All other fields missing/NULL
        }
        embedding_data = {
            "embedding": [0.1] * 384,
            "model_version": "all-MiniLM-L6-v2"
        }

        mock_tx = AsyncMock()
        # Should not raise exception
        await self.service._create_job_node(mock_tx, job_row, embedding_data)

        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        # Verify required fields are present
        assert call_args[1]["job_id"] == "job-456"
        assert call_args[1]["job_title"] == "Developer"

        # Verify NULL fields are None
        assert call_args[1]["location"] is None
        assert call_args[1]["district"] is None
        assert call_args[1]["salary"] is None

    @pytest.mark.asyncio
    async def test_create_company_node_with_embedding(self):
        """Test company node creation with embedding."""
        job_row = {
            "Company Name": "Tech Corp",
            "CIN": "U72900KA2020PTC123456",
            "Company Description": "Leading tech company",
            "CompanyIndustrialClassification": "Information Technology",
            "NIC_Code_algo": "62.01",
            "nic_code_2_2008": "6201"
        }
        embedding_data = {
            "embedding": [0.2] * 384,
            "model_version": "all-MiniLM-L6-v2"
        }

        mock_tx = AsyncMock()
        await self.service._create_company_node(mock_tx, job_row, embedding_data)

        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        assert call_args[1]["company_name"] == "Tech Corp"
        assert call_args[1]["cin"] == "U72900KA2020PTC123456"
        assert call_args[1]["company_description"] == "Leading tech company"
        assert call_args[1]["embedding"] == [0.2] * 384

    @pytest.mark.asyncio
    async def test_create_company_node_without_embedding(self):
        """Test company node creation without embedding (NULL description)."""
        job_row = {
            "Company Name": "Startup Inc",
            "Company Description": None
        }
        embedding_data = None

        mock_tx = AsyncMock()
        await self.service._create_company_node(mock_tx, job_row, embedding_data)

        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        assert call_args[1]["company_name"] == "Startup Inc"
        assert call_args[1]["embedding"] is None
        assert call_args[1]["embedding_model_version"] is None

    @pytest.mark.asyncio
    async def test_create_location_node(self):
        """Test location node creation."""
        mock_tx = AsyncMock()
        await self.service._create_location_node(mock_tx, "Mumbai", "Mumbai Suburban")

        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        assert call_args[1]["location_name"] == "Mumbai"
        assert call_args[1]["district"] == "Mumbai Suburban"

    @pytest.mark.asyncio
    async def test_create_location_node_null_district(self):
        """Test location node creation with NULL district."""
        mock_tx = AsyncMock()
        await self.service._create_location_node(mock_tx, "Delhi", None)

        assert mock_tx.run.called
        call_args = mock_tx.run.call_args

        assert call_args[1]["location_name"] == "Delhi"
        assert call_args[1]["district"] is None

    @pytest.mark.asyncio
    async def test_create_job_relationships_all(self):
        """Test creating both job relationships."""
        mock_tx = AsyncMock()
        result = await self.service._create_job_relationships(
            mock_tx,
            "job-123",
            "Tech Corp",
            "Bangalore"
        )

        assert result == 2  # Both relationships created
        assert mock_tx.run.call_count == 2

    @pytest.mark.asyncio
    async def test_create_job_relationships_company_only(self):
        """Test creating only company relationship."""
        mock_tx = AsyncMock()
        result = await self.service._create_job_relationships(
            mock_tx,
            "job-123",
            "Tech Corp",
            None
        )

        assert result == 1  # Only company relationship
        assert mock_tx.run.call_count == 1

    @pytest.mark.asyncio
    async def test_create_job_relationships_location_only(self):
        """Test creating only location relationship."""
        mock_tx = AsyncMock()
        result = await self.service._create_job_relationships(
            mock_tx,
            "job-123",
            None,
            "Bangalore"
        )

        assert result == 1  # Only location relationship
        assert mock_tx.run.call_count == 1

    @pytest.mark.asyncio
    async def test_create_job_relationships_none(self):
        """Test no relationships when both NULL."""
        mock_tx = AsyncMock()
        result = await self.service._create_job_relationships(
            mock_tx,
            "job-123",
            None,
            None
        )

        assert result == 0  # No relationships
        assert mock_tx.run.call_count == 0

    @pytest.mark.asyncio
    async def test_create_job_graph_single_batch(self):
        """Test job graph creation with single batch (< 1000 jobs)."""
        jobs_data = [
            {
                "Job ID": f"job-{i}",
                "Job Title": f"Developer {i}",
                "Job Description": f"Description {i}",
                "Company Name": f"Company {i}",
                "Company Description": f"Company desc {i}",
                "Location": f"City {i}"
            }
            for i in range(10)
        ]

        stats = await self.service.create_job_graph(jobs_data, "test-job-id")

        assert stats["jobs_created"] == 10
        assert stats["companies_created"] == 10
        assert stats["locations_created"] == 10
        assert len(stats["errors"]) == 0

    @pytest.mark.asyncio
    async def test_create_job_graph_handles_errors(self):
        """Test job graph creation handles individual job errors gracefully."""
        jobs_data = [
            {
                "Job ID": "job-1",
                "Job Title": "Developer",
                "Job Description": "Good description",
                "Company Name": "Company A",
                "Company Description": "Company desc",
                "Location": "City A"
            }
        ]

        # Make transaction raise error
        self.neo4j_repo.tx.run = AsyncMock(side_effect=Exception("Database error"))

        stats = await self.service.create_job_graph(jobs_data, "test-job-id")

        # Should capture error but not crash
        assert len(stats["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
