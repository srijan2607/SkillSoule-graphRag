"""Unit tests for JobSimilarityBuilder service.

Tests cover:
- build_all() full rebuild workflow
- _clear_existing() relationship deletion
- _compute_and_create() Jaccard similarity calculation
- get_statistics() metrics retrieval
- update_for_job() incremental updates
- get_similar_jobs() query functionality
- create_indexes() index management
- validate_data() data integrity checks
- Edge cases (empty graph, single job, no shared skills)

Reference: Phase 7 - Visible Impact Integration (08-VISIBLE-IMPACT-INTEGRATION.md)
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services.job_similarity_builder import JobSimilarityBuilder


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4jRepository for testing."""
    repo = AsyncMock()
    repo.execute_query = AsyncMock()
    return repo


@pytest.fixture
def job_similarity_builder(mock_neo4j_repo):
    """Create JobSimilarityBuilder instance with mocked dependencies."""
    return JobSimilarityBuilder(mock_neo4j_repo)


@pytest.mark.unit
class TestJobSimilarityBuilderInit:
    """Test JobSimilarityBuilder initialization."""

    def test_init_with_defaults(self, mock_neo4j_repo):
        """Test initialization with default parameters."""
        builder = JobSimilarityBuilder(mock_neo4j_repo)

        assert builder.neo4j_repo == mock_neo4j_repo
        assert builder.min_shared_skills == 3
        assert builder.min_jaccard == 0.2
        assert builder.max_similar_per_job == 20

    def test_init_with_custom_params(self, mock_neo4j_repo):
        """Test initialization with custom parameters."""
        builder = JobSimilarityBuilder(
            mock_neo4j_repo,
            min_shared_skills=5,
            min_jaccard=0.3,
            max_similar_per_job=10
        )

        assert builder.min_shared_skills == 5
        assert builder.min_jaccard == 0.3
        assert builder.max_similar_per_job == 10


@pytest.mark.unit
class TestClearExisting:
    """Test _clear_existing() method."""

    @pytest.mark.asyncio
    async def test_clear_existing_deletes_relationships(self, job_similarity_builder, mock_neo4j_repo):
        """Test _clear_existing() executes delete query and returns count."""
        mock_neo4j_repo.execute_query.return_value = [{"deleted": 100}]

        result = await job_similarity_builder._clear_existing()

        assert result == 100
        mock_neo4j_repo.execute_query.assert_called_once()
        call_args = mock_neo4j_repo.execute_query.call_args
        query = call_args[0][0]
        assert "SIMILAR_JOB" in query
        assert "DELETE" in query

    @pytest.mark.asyncio
    async def test_clear_existing_returns_zero_when_empty(self, job_similarity_builder, mock_neo4j_repo):
        """Test _clear_existing() returns 0 when no relationships exist."""
        mock_neo4j_repo.execute_query.return_value = [{"deleted": 0}]

        result = await job_similarity_builder._clear_existing()

        assert result == 0

    @pytest.mark.asyncio
    async def test_clear_existing_handles_empty_result(self, job_similarity_builder, mock_neo4j_repo):
        """Test _clear_existing() handles empty query result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder._clear_existing()

        assert result == 0


@pytest.mark.unit
class TestComputeAndCreate:
    """Test _compute_and_create() method."""

    @pytest.mark.asyncio
    async def test_compute_and_create_returns_count(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create() returns created relationship count."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 250}]

        result = await job_similarity_builder._compute_and_create()

        assert result == 250

    @pytest.mark.asyncio
    async def test_compute_and_create_passes_thresholds(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create() passes threshold parameters."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]
        job_similarity_builder.min_shared_skills = 5
        job_similarity_builder.min_jaccard = 0.4

        await job_similarity_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('params', {})
        assert params.get("min_shared") == 5
        assert params.get("min_jaccard") == 0.4

    @pytest.mark.asyncio
    async def test_compute_and_create_uses_timeout(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create() sets appropriate timeout for large graphs."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]

        await job_similarity_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        assert call_args[1].get('timeout') == 300.0 or \
               (len(call_args[0]) > 2 and call_args[0][2] == 300.0)

    @pytest.mark.asyncio
    async def test_compute_and_create_query_structure(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create() query matches Jaccard specification."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]

        await job_similarity_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        query = call_args[0][0]

        # Verify query structure per story spec
        assert "MATCH (j1:Job)-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)" in query
        assert "id(j1) < id(j2)" in query  # Prevent duplicates
        assert "jaccard_score" in query
        assert "shared_count" in query
        assert "MERGE (j1)-[r:SIMILAR_JOB]->(j2)" in query

    @pytest.mark.asyncio
    async def test_compute_and_create_handles_empty_result(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create() handles empty result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder._compute_and_create()

        assert result == 0


@pytest.mark.unit
class TestBuildAll:
    """Test build_all() method."""

    @pytest.mark.asyncio
    async def test_build_all_with_clear(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() clears existing relationships when requested."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 50}],  # _clear_existing
            [{"created": 100}],  # _compute_and_create
            [{"total_relationships": 100, "avg_jaccard": 0.45,
              "min_jaccard": 0.2, "max_jaccard": 0.9, "avg_shared_skills": 5.2}]  # get_statistics
        ]

        result = await job_similarity_builder.build_all(clear_existing=True)

        assert result["status"] == "success"
        assert result["relationships_deleted"] == 50
        assert result["relationships_created"] == 100
        assert result["clear_existing"] is True

    @pytest.mark.asyncio
    async def test_build_all_without_clear(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() skips clearing when clear_existing=False."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"created": 25}],  # _compute_and_create
            [{"total_relationships": 125, "avg_jaccard": 0.5,
              "min_jaccard": 0.2, "max_jaccard": 0.95, "avg_shared_skills": 6.0}]  # get_statistics
        ]

        result = await job_similarity_builder.build_all(clear_existing=False)

        assert result["status"] == "success"
        assert "relationships_deleted" not in result
        assert result["relationships_created"] == 25
        assert result["clear_existing"] is False

    @pytest.mark.asyncio
    async def test_build_all_includes_timing(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() includes timing information."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],
            [{"created": 100}],
            [{"total_relationships": 100, "avg_jaccard": 0.4,
              "min_jaccard": 0.2, "max_jaccard": 0.8, "avg_shared_skills": 4.5}]
        ]

        result = await job_similarity_builder.build_all()

        assert "started_at" in result
        assert "completed_at" in result
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_build_all_handles_error(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() handles errors gracefully."""
        mock_neo4j_repo.execute_query.side_effect = Exception("Database connection failed")

        result = await job_similarity_builder.build_all()

        assert result["status"] == "failed"
        assert "error" in result
        assert "Database connection failed" in result["error"]


@pytest.mark.unit
class TestGetStatistics:
    """Test get_statistics() method."""

    @pytest.mark.asyncio
    async def test_get_statistics_returns_metrics(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_statistics() returns all required metrics."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 300,
            "avg_jaccard": 0.55,
            "min_jaccard": 0.2,
            "max_jaccard": 0.95,
            "avg_shared_skills": 6.3
        }]

        result = await job_similarity_builder.get_statistics()

        assert result["total_similar_job_relationships"] == 300
        assert result["average_jaccard_score"] == pytest.approx(0.55)
        assert result["min_jaccard_score"] == pytest.approx(0.2)
        assert result["max_jaccard_score"] == pytest.approx(0.95)
        assert result["average_shared_skills"] == pytest.approx(6.3)

    @pytest.mark.asyncio
    async def test_get_statistics_handles_empty_graph(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_statistics() handles empty graph gracefully."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": None,
            "avg_jaccard": None,
            "min_jaccard": None,
            "max_jaccard": None,
            "avg_shared_skills": None
        }]

        result = await job_similarity_builder.get_statistics()

        assert result["total_similar_job_relationships"] == 0
        assert result["average_jaccard_score"] == 0.0
        assert result["min_jaccard_score"] == 0.0
        assert result["max_jaccard_score"] == 0.0
        assert result["average_shared_skills"] == 0.0

    @pytest.mark.asyncio
    async def test_get_statistics_handles_empty_result(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_statistics() handles empty query result."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder.get_statistics()

        assert result["total_similar_job_relationships"] == 0


@pytest.mark.unit
class TestUpdateForJob:
    """Test update_for_job() method."""

    @pytest.mark.asyncio
    async def test_update_for_job_returns_count(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() returns created relationship count."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 8}]

        result = await job_similarity_builder.update_for_job("job_123")

        assert result["edges_created"] == 8

    @pytest.mark.asyncio
    async def test_update_for_job_passes_parameters(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() passes correct parameters."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 5}]
        job_similarity_builder.min_shared_skills = 4
        job_similarity_builder.min_jaccard = 0.3
        job_similarity_builder.max_similar_per_job = 15

        await job_similarity_builder.update_for_job("job_xyz")

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["job_id"] == "job_xyz"
        assert params["min_shared"] == 4
        assert params["min_jaccard"] == 0.3
        assert params["max_per_job"] == 15

    @pytest.mark.asyncio
    async def test_update_for_job_handles_empty_result(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() handles empty result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder.update_for_job("nonexistent_job")

        assert result["edges_created"] == 0


@pytest.mark.unit
class TestGetSimilarJobs:
    """Test get_similar_jobs() method."""

    @pytest.mark.asyncio
    async def test_get_similar_jobs_returns_list(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_similar_jobs() returns similar job list."""
        mock_neo4j_repo.execute_query.return_value = [
            {"job_id": "job_2", "title": "Python Developer", "company": "Google",
             "location": "Remote", "similarity": 0.85, "shared_skills": 7},
            {"job_id": "job_3", "title": "Backend Engineer", "company": "Amazon",
             "location": "Seattle", "similarity": 0.72, "shared_skills": 5}
        ]

        result = await job_similarity_builder.get_similar_jobs("job_1")

        assert len(result) == 2
        assert result[0]["title"] == "Python Developer"
        assert result[0]["similarity"] == 0.85

    @pytest.mark.asyncio
    async def test_get_similar_jobs_respects_limit(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_similar_jobs() passes limit parameter."""
        mock_neo4j_repo.execute_query.return_value = []

        await job_similarity_builder.get_similar_jobs("job_1", limit=5)

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_similar_jobs_uses_default_limit(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_similar_jobs() uses default limit of 10."""
        mock_neo4j_repo.execute_query.return_value = []

        await job_similarity_builder.get_similar_jobs("job_1")

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["limit"] == 10


@pytest.mark.unit
class TestGetSimilarJobsByTitle:
    """Test get_similar_jobs_by_title() method."""

    @pytest.mark.asyncio
    async def test_get_similar_jobs_by_title_returns_results(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_similar_jobs_by_title() searches by title."""
        mock_neo4j_repo.execute_query.return_value = [
            {"source_job_id": "job_1", "source_job_title": "Backend Developer",
             "job_id": "job_2", "title": "Python Developer", "company": "Google",
             "similarity": 0.75, "shared_skills": 6}
        ]

        result = await job_similarity_builder.get_similar_jobs_by_title("Backend")

        assert len(result) == 1
        assert result[0]["source_job_title"] == "Backend Developer"

    @pytest.mark.asyncio
    async def test_get_similar_jobs_by_title_passes_params(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_similar_jobs_by_title() passes parameters correctly."""
        mock_neo4j_repo.execute_query.return_value = []

        await job_similarity_builder.get_similar_jobs_by_title("Data Scientist", limit=20)

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["title"] == "Data Scientist"
        assert params["limit"] == 20


@pytest.mark.unit
class TestGetJobSimilarityScore:
    """Test get_job_similarity_score() method."""

    @pytest.mark.asyncio
    async def test_get_job_similarity_score_returns_score(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_job_similarity_score() returns similarity details."""
        mock_neo4j_repo.execute_query.return_value = [{
            "similarity": 0.65,
            "shared_skills": 5,
            "computed_at": "2025-12-07T10:00:00Z"
        }]

        result = await job_similarity_builder.get_job_similarity_score("job_1", "job_2")

        assert result["similarity"] == 0.65
        assert result["shared_skills"] == 5

    @pytest.mark.asyncio
    async def test_get_job_similarity_score_returns_none_when_no_relationship(
        self, job_similarity_builder, mock_neo4j_repo
    ):
        """Test get_job_similarity_score() returns None when no relationship exists."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder.get_job_similarity_score("job_1", "job_99")

        assert result is None


@pytest.mark.unit
class TestGetSharedSkillsBetweenJobs:
    """Test get_shared_skills_between_jobs() method."""

    @pytest.mark.asyncio
    async def test_get_shared_skills_returns_list(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_shared_skills_between_jobs() returns skill list."""
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "skill_1", "skill_name": "Python", "centrality": 0.8, "demand_count": 100},
            {"skill_id": "skill_2", "skill_name": "Django", "centrality": 0.6, "demand_count": 50}
        ]

        result = await job_similarity_builder.get_shared_skills_between_jobs("job_1", "job_2")

        assert len(result) == 2
        assert result[0]["skill_name"] == "Python"

    @pytest.mark.asyncio
    async def test_get_shared_skills_handles_no_shared_skills(self, job_similarity_builder, mock_neo4j_repo):
        """Test get_shared_skills_between_jobs() handles empty result."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder.get_shared_skills_between_jobs("job_1", "job_99")

        assert len(result) == 0


@pytest.mark.unit
class TestCreateIndexes:
    """Test create_indexes() method."""

    @pytest.mark.asyncio
    async def test_create_indexes_creates_both_indexes(self, job_similarity_builder, mock_neo4j_repo):
        """Test create_indexes() creates jaccard and shared_count indexes."""
        mock_neo4j_repo.execute_query.return_value = None

        result = await job_similarity_builder.create_indexes()

        assert result["status"] == "success"
        assert "job_similar_jaccard" in result["indexes_created"]
        assert "job_similar_shared" in result["indexes_created"]
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_create_indexes_handles_partial_failure(self, job_similarity_builder, mock_neo4j_repo):
        """Test create_indexes() handles partial failures gracefully."""
        mock_neo4j_repo.execute_query.side_effect = [
            None,
            Exception("Index creation failed")
        ]

        result = await job_similarity_builder.create_indexes()

        assert result["status"] == "partial"
        assert "job_similar_jaccard" in result["indexes_created"]
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_create_indexes_handles_complete_failure(self, job_similarity_builder, mock_neo4j_repo):
        """Test create_indexes() handles all indexes failing."""
        mock_neo4j_repo.execute_query.side_effect = Exception("Database unavailable")

        result = await job_similarity_builder.create_indexes()

        assert result["status"] == "partial"
        assert len(result["indexes_created"]) == 0
        assert len(result["errors"]) == 2


@pytest.mark.unit
class TestValidateData:
    """Test validate_data() method."""

    @pytest.mark.asyncio
    async def test_validate_data_valid_relationships(self, job_similarity_builder, mock_neo4j_repo):
        """Test validate_data() returns valid for correct data."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 200,
            "null_jaccards": 0,
            "null_shareds": 0,
            "invalid_jaccards": 0,
            "invalid_shareds": 0
        }]

        result = await job_similarity_builder.validate_data()

        assert result["is_valid"] is True
        assert result["total_relationships"] == 200
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_data_detects_null_jaccard(self, job_similarity_builder, mock_neo4j_repo):
        """Test validate_data() detects null jaccard_score issues."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 200,
            "null_jaccards": 3,
            "null_shareds": 0,
            "invalid_jaccards": 0,
            "invalid_shareds": 0
        }]

        result = await job_similarity_builder.validate_data()

        assert result["is_valid"] is False
        assert "3 relationships with null jaccard_score" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_invalid_jaccard(self, job_similarity_builder, mock_neo4j_repo):
        """Test validate_data() detects invalid jaccard_score (not 0-1)."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 200,
            "null_jaccards": 0,
            "null_shareds": 0,
            "invalid_jaccards": 2,
            "invalid_shareds": 0
        }]

        result = await job_similarity_builder.validate_data()

        assert result["is_valid"] is False
        assert "2 relationships with invalid jaccard_score" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_multiple_issues(self, job_similarity_builder, mock_neo4j_repo):
        """Test validate_data() reports all issues found."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 200,
            "null_jaccards": 1,
            "null_shareds": 2,
            "invalid_jaccards": 3,
            "invalid_shareds": 4
        }]

        result = await job_similarity_builder.validate_data()

        assert result["is_valid"] is False
        assert len(result["issues"]) == 4

    @pytest.mark.asyncio
    async def test_validate_data_handles_empty_graph(self, job_similarity_builder, mock_neo4j_repo):
        """Test validate_data() handles empty graph gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await job_similarity_builder.validate_data()

        assert result["is_valid"] is True
        assert result["total_relationships"] == 0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases for job similarity building."""

    @pytest.mark.asyncio
    async def test_update_for_job_single_job_no_similar(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() handles job with no similar jobs."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        result = await job_similarity_builder.update_for_job("isolated_job")

        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_update_for_job_below_shared_threshold(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() when shared skills below threshold."""
        # Job shares only 1-2 skills with others (below min_shared_skills=3)
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        result = await job_similarity_builder.update_for_job("low_match_job")

        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_update_for_job_below_jaccard_threshold(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() when Jaccard below threshold."""
        # Jaccard score below min_jaccard=0.2
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        result = await job_similarity_builder.update_for_job("dissimilar_job")

        assert result["edges_created"] == 0

    @pytest.mark.asyncio
    async def test_build_all_empty_graph_no_jobs(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() handles graph with no jobs gracefully."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],  # _clear_existing
            [{"created": 0}],  # _compute_and_create - no jobs
            [{"total_relationships": None, "avg_jaccard": None,
              "min_jaccard": None, "max_jaccard": None, "avg_shared_skills": None}]
        ]

        result = await job_similarity_builder.build_all()

        assert result["status"] == "success"
        assert result["relationships_created"] == 0
        assert result["total_similar_job_relationships"] == 0

    @pytest.mark.asyncio
    async def test_build_all_jobs_with_no_shared_skills(self, job_similarity_builder, mock_neo4j_repo):
        """Test build_all() when no jobs share any skills."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],
            [{"created": 0}],  # No pairs meet threshold
            [{"total_relationships": 0, "avg_jaccard": None,
              "min_jaccard": None, "max_jaccard": None, "avg_shared_skills": None}]
        ]

        result = await job_similarity_builder.build_all()

        assert result["status"] == "success"
        assert result["relationships_created"] == 0


@pytest.mark.unit
class TestCypherQueryCorrectness:
    """Test Cypher query correctness per spec."""

    @pytest.mark.asyncio
    async def test_compute_uses_undirected_matching(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create uses id(j1) < id(j2) to prevent duplicates."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await job_similarity_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        assert "id(j1) < id(j2)" in query

    @pytest.mark.asyncio
    async def test_compute_calculates_jaccard_correctly(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create calculates Jaccard as |A∩B| / |A∪B|."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await job_similarity_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        # Jaccard = shared / (j1_count + j2_count - shared) = shared / union
        assert "toFloat(shared_count) / (j1_count + j2_count - shared_count)" in query

    @pytest.mark.asyncio
    async def test_compute_sets_computed_at(self, job_similarity_builder, mock_neo4j_repo):
        """Test _compute_and_create sets computed_at timestamp."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await job_similarity_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        assert "r.computed_at = datetime()" in query

    @pytest.mark.asyncio
    async def test_update_uses_max_per_job_limit(self, job_similarity_builder, mock_neo4j_repo):
        """Test update_for_job() uses max_similar_per_job limit."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await job_similarity_builder.update_for_job("job_1")

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        assert "LIMIT $max_per_job" in query
