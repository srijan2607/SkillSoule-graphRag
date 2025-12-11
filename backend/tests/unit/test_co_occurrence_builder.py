"""Unit tests for CoOccurrenceBuilder service.

Tests cover:
- build_all() full rebuild workflow
- _clear_existing() relationship deletion
- _compute_and_create() co-occurrence calculation
- get_statistics() metrics retrieval
- update_for_job() incremental updates
- get_top_co_occurrences() query functionality
- create_indexes() index management
- validate_data() data integrity checks

Reference: Network Math Implementation - Phase 1 (01-DATA-LAYER.md)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.co_occurrence_builder import CoOccurrenceBuilder


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4jRepository for testing."""
    repo = AsyncMock()
    repo.execute_query = AsyncMock()
    return repo


@pytest.fixture
def co_occurrence_builder(mock_neo4j_repo):
    """Create CoOccurrenceBuilder instance with mocked dependencies."""
    with patch('app.services.co_occurrence_builder.settings') as mock_settings:
        mock_settings.NETWORK_MIN_CO_OCCURRENCE = 2
        builder = CoOccurrenceBuilder(mock_neo4j_repo)
    return builder


@pytest.mark.unit
class TestCoOccurrenceBuilderInit:
    """Test CoOccurrenceBuilder initialization."""

    def test_init_with_default_min_weight(self, mock_neo4j_repo):
        """Test initialization uses settings for min_weight."""
        with patch('app.services.co_occurrence_builder.settings') as mock_settings:
            mock_settings.NETWORK_MIN_CO_OCCURRENCE = 3
            builder = CoOccurrenceBuilder(mock_neo4j_repo)

            assert builder.neo4j_repo == mock_neo4j_repo
            assert builder.min_weight == 3

    def test_init_with_missing_setting_uses_default(self, mock_neo4j_repo):
        """Test initialization falls back to default if setting missing."""
        with patch('app.services.co_occurrence_builder.settings') as mock_settings:
            # Simulate missing attribute
            delattr(mock_settings, 'NETWORK_MIN_CO_OCCURRENCE')
            builder = CoOccurrenceBuilder(mock_neo4j_repo)

            assert builder.min_weight == 2  # Default fallback


@pytest.mark.unit
class TestClearExisting:
    """Test _clear_existing() method."""

    @pytest.mark.asyncio
    async def test_clear_existing_deletes_relationships(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _clear_existing() executes delete query and returns count."""
        mock_neo4j_repo.execute_query.return_value = [{"deleted": 150}]

        result = await co_occurrence_builder._clear_existing()

        assert result == 150
        mock_neo4j_repo.execute_query.assert_called_once()
        call_args = mock_neo4j_repo.execute_query.call_args
        query = call_args[0][0]
        # Verify undirected relationship pattern is used
        assert "CO_OCCURS_WITH" in query
        assert "-[r:CO_OCCURS_WITH]-" in query or "()-[r:CO_OCCURS_WITH]-()" in query

    @pytest.mark.asyncio
    async def test_clear_existing_returns_zero_when_empty(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _clear_existing() returns 0 when no relationships exist."""
        mock_neo4j_repo.execute_query.return_value = [{"deleted": 0}]

        result = await co_occurrence_builder._clear_existing()

        assert result == 0

    @pytest.mark.asyncio
    async def test_clear_existing_handles_empty_result(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _clear_existing() handles empty query result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await co_occurrence_builder._clear_existing()

        assert result == 0


@pytest.mark.unit
class TestComputeAndCreate:
    """Test _compute_and_create() method."""

    @pytest.mark.asyncio
    async def test_compute_and_create_returns_count(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create() returns created relationship count."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 500}]

        result = await co_occurrence_builder._compute_and_create()

        assert result == 500

    @pytest.mark.asyncio
    async def test_compute_and_create_passes_min_weight(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create() passes min_weight parameter."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]
        co_occurrence_builder.min_weight = 5

        await co_occurrence_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get('params', {})
        assert params.get("min_weight") == 5

    @pytest.mark.asyncio
    async def test_compute_and_create_uses_timeout(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create() sets appropriate timeout for large graphs."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]

        await co_occurrence_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        # Check timeout is passed (300 seconds for large graphs)
        assert call_args[1].get('timeout') == 300.0 or \
               (len(call_args[0]) > 2 and call_args[0][2] == 300.0)

    @pytest.mark.asyncio
    async def test_compute_and_create_query_structure(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create() query matches specification."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 100}]

        await co_occurrence_builder._compute_and_create()

        call_args = mock_neo4j_repo.execute_query.call_args
        query = call_args[0][0]

        # Verify query structure per 01-DATA-LAYER.md spec
        assert "MATCH (j:Job)-[:REQUIRES]->(s1:Skill)" in query
        assert "MATCH (j)-[:REQUIRES]->(s2:Skill)" in query
        assert "WHERE id(s1) < id(s2)" in query  # Prevent duplicates
        assert "count(DISTINCT j)" in query  # Count jobs
        assert "MERGE (s1)-[r:CO_OCCURS_WITH]-(s2)" in query  # Undirected
        assert "r.weight = weight" in query
        assert "r.cost = 1.0 / weight" in query

    @pytest.mark.asyncio
    async def test_compute_and_create_handles_empty_result(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create() handles empty result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await co_occurrence_builder._compute_and_create()

        assert result == 0


@pytest.mark.unit
class TestBuildAll:
    """Test build_all() method."""

    @pytest.mark.asyncio
    async def test_build_all_with_clear(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() clears existing relationships when requested."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 100}],  # _clear_existing
            [{"created": 200}],  # _compute_and_create
            [{"total_relationships": 200, "avg_weight": 3.5,
              "min_weight": 2, "max_weight": 10}]  # get_statistics
        ]

        result = await co_occurrence_builder.build_all(clear_existing=True)

        assert result["status"] == "success"
        assert result["relationships_deleted"] == 100
        assert result["relationships_created"] == 200
        assert result["clear_existing"] is True

    @pytest.mark.asyncio
    async def test_build_all_without_clear(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() skips clearing when clear_existing=False."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"created": 50}],  # _compute_and_create
            [{"total_relationships": 250, "avg_weight": 4.0,
              "min_weight": 2, "max_weight": 12}]  # get_statistics
        ]

        result = await co_occurrence_builder.build_all(clear_existing=False)

        assert result["status"] == "success"
        assert "relationships_deleted" not in result
        assert result["relationships_created"] == 50
        assert result["clear_existing"] is False

    @pytest.mark.asyncio
    async def test_build_all_includes_timing(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() includes timing information."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],
            [{"created": 100}],
            [{"total_relationships": 100, "avg_weight": 2.5,
              "min_weight": 2, "max_weight": 5}]
        ]

        result = await co_occurrence_builder.build_all()

        assert "started_at" in result
        assert "completed_at" in result
        assert "duration_seconds" in result
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_build_all_handles_error(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() handles errors gracefully."""
        mock_neo4j_repo.execute_query.side_effect = Exception("Database connection failed")

        result = await co_occurrence_builder.build_all()

        assert result["status"] == "failed"
        assert "error" in result
        assert "Database connection failed" in result["error"]


@pytest.mark.unit
class TestGetStatistics:
    """Test get_statistics() method."""

    @pytest.mark.asyncio
    async def test_get_statistics_returns_metrics(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_statistics() returns all required metrics."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "avg_weight": 4.2,
            "min_weight": 2,
            "max_weight": 25
        }]

        result = await co_occurrence_builder.get_statistics()

        assert result["total_co_occurrence_relationships"] == 500
        assert result["average_weight"] == pytest.approx(4.2)
        assert result["min_weight"] == 2
        assert result["max_weight"] == 25

    @pytest.mark.asyncio
    async def test_get_statistics_handles_empty_graph(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_statistics() handles empty graph gracefully."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": None,
            "avg_weight": None,
            "min_weight": None,
            "max_weight": None
        }]

        result = await co_occurrence_builder.get_statistics()

        assert result["total_co_occurrence_relationships"] == 0
        assert result["average_weight"] == 0.0
        assert result["min_weight"] == 0
        assert result["max_weight"] == 0

    @pytest.mark.asyncio
    async def test_get_statistics_handles_empty_result(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_statistics() handles empty query result."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await co_occurrence_builder.get_statistics()

        assert result["total_co_occurrence_relationships"] == 0


@pytest.mark.unit
class TestUpdateForJob:
    """Test update_for_job() method."""

    @pytest.mark.asyncio
    async def test_update_for_job_returns_count(self, co_occurrence_builder, mock_neo4j_repo):
        """Test update_for_job() returns updated relationship count."""
        mock_neo4j_repo.execute_query.return_value = [{"updated": 15}]

        result = await co_occurrence_builder.update_for_job("job_123")

        assert result["relationships_updated"] == 15

    @pytest.mark.asyncio
    async def test_update_for_job_passes_parameters(self, co_occurrence_builder, mock_neo4j_repo):
        """Test update_for_job() passes correct parameters."""
        mock_neo4j_repo.execute_query.return_value = [{"updated": 10}]
        co_occurrence_builder.min_weight = 3

        await co_occurrence_builder.update_for_job("job_xyz")

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["job_id"] == "job_xyz"
        assert params["min_weight"] == 3

    @pytest.mark.asyncio
    async def test_update_for_job_handles_empty_result(self, co_occurrence_builder, mock_neo4j_repo):
        """Test update_for_job() handles empty result gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await co_occurrence_builder.update_for_job("nonexistent_job")

        assert result["relationships_updated"] == 0


@pytest.mark.unit
class TestGetTopCoOccurrences:
    """Test get_top_co_occurrences() method."""

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_returns_list(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_top_co_occurrences() returns skill list."""
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "skill_2", "skill_name": "Django", "weight": 50, "cost": 0.02},
            {"skill_id": "skill_3", "skill_name": "FastAPI", "weight": 30, "cost": 0.033}
        ]

        result = await co_occurrence_builder.get_top_co_occurrences("skill_1")

        assert len(result) == 2
        assert result[0]["skill_name"] == "Django"
        assert result[0]["weight"] == 50

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_respects_limit(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_top_co_occurrences() passes limit parameter."""
        mock_neo4j_repo.execute_query.return_value = []

        await co_occurrence_builder.get_top_co_occurrences("skill_1", limit=5)

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_uses_default_limit(self, co_occurrence_builder, mock_neo4j_repo):
        """Test get_top_co_occurrences() uses default limit of 10."""
        mock_neo4j_repo.execute_query.return_value = []

        await co_occurrence_builder.get_top_co_occurrences("skill_1")

        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["limit"] == 10


@pytest.mark.unit
class TestCreateIndexes:
    """Test create_indexes() method."""

    @pytest.mark.asyncio
    async def test_create_indexes_creates_both_indexes(self, co_occurrence_builder, mock_neo4j_repo):
        """Test create_indexes() creates weight and cost indexes."""
        mock_neo4j_repo.execute_query.return_value = None

        result = await co_occurrence_builder.create_indexes()

        assert result["status"] == "success"
        assert "skill_cooccurs_weight" in result["indexes_created"]
        assert "skill_cooccurs_cost" in result["indexes_created"]
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_create_indexes_handles_partial_failure(self, co_occurrence_builder, mock_neo4j_repo):
        """Test create_indexes() handles partial failures gracefully."""
        # First call succeeds, second fails
        mock_neo4j_repo.execute_query.side_effect = [
            None,
            Exception("Index creation failed")
        ]

        result = await co_occurrence_builder.create_indexes()

        assert result["status"] == "partial"
        assert "skill_cooccurs_weight" in result["indexes_created"]
        assert len(result["errors"]) == 1

    @pytest.mark.asyncio
    async def test_create_indexes_handles_complete_failure(self, co_occurrence_builder, mock_neo4j_repo):
        """Test create_indexes() handles all indexes failing."""
        mock_neo4j_repo.execute_query.side_effect = Exception("Database unavailable")

        result = await co_occurrence_builder.create_indexes()

        assert result["status"] == "partial"
        assert len(result["indexes_created"]) == 0
        assert len(result["errors"]) == 2


@pytest.mark.unit
class TestValidateData:
    """Test validate_data() method."""

    @pytest.mark.asyncio
    async def test_validate_data_valid_relationships(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() returns valid for correct data."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 0,
            "null_costs": 0,
            "invalid_weights": 0,
            "invalid_costs": 0
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is True
        assert result["total_relationships"] == 500
        assert len(result["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_data_detects_null_weights(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() detects null weight issues."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 5,
            "null_costs": 0,
            "invalid_weights": 0,
            "invalid_costs": 0
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is False
        assert "5 relationships with null weight" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_null_costs(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() detects null cost issues."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 0,
            "null_costs": 3,
            "invalid_weights": 0,
            "invalid_costs": 0
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is False
        assert "3 relationships with null cost" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_invalid_weights(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() detects invalid weight (<1) issues."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 0,
            "null_costs": 0,
            "invalid_weights": 2,
            "invalid_costs": 0
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is False
        assert "2 relationships with invalid weight (<1)" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_invalid_costs(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() detects invalid cost (<=0) issues."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 0,
            "null_costs": 0,
            "invalid_weights": 0,
            "invalid_costs": 4
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is False
        assert "4 relationships with invalid cost (<=0)" in result["issues"]

    @pytest.mark.asyncio
    async def test_validate_data_detects_multiple_issues(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() reports all issues found."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 500,
            "null_weights": 2,
            "null_costs": 3,
            "invalid_weights": 1,
            "invalid_costs": 4
        }]

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is False
        assert len(result["issues"]) == 4

    @pytest.mark.asyncio
    async def test_validate_data_handles_empty_graph(self, co_occurrence_builder, mock_neo4j_repo):
        """Test validate_data() handles empty graph gracefully."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await co_occurrence_builder.validate_data()

        assert result["is_valid"] is True
        assert result["total_relationships"] == 0


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases for co-occurrence building."""

    @pytest.mark.asyncio
    async def test_update_for_job_empty_job_no_skills(self, co_occurrence_builder, mock_neo4j_repo):
        """Test update_for_job() handles job with no skills (empty job)."""
        # Job exists but has no REQUIRES relationships - returns 0 updates
        mock_neo4j_repo.execute_query.return_value = [{"updated": 0}]

        result = await co_occurrence_builder.update_for_job("job_with_no_skills")

        assert result["relationships_updated"] == 0
        # Verify query was executed with correct job_id
        call_args = mock_neo4j_repo.execute_query.call_args
        params = call_args[0][1]
        assert params["job_id"] == "job_with_no_skills"

    @pytest.mark.asyncio
    async def test_update_for_job_single_skill_job(self, co_occurrence_builder, mock_neo4j_repo):
        """Test update_for_job() handles job with only one skill (no pairs possible)."""
        # Job has only one skill, so id(s1) < id(s2) constraint can't be satisfied
        # Result should be 0 co-occurrences
        mock_neo4j_repo.execute_query.return_value = [{"updated": 0}]

        result = await co_occurrence_builder.update_for_job("job_single_skill")

        assert result["relationships_updated"] == 0

    @pytest.mark.asyncio
    async def test_build_all_empty_graph_no_jobs(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() handles graph with no jobs gracefully."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],  # _clear_existing - no existing relationships
            [{"created": 0}],  # _compute_and_create - no jobs to process
            [{"total_relationships": None, "avg_weight": None,
              "min_weight": None, "max_weight": None}]  # get_statistics - empty stats
        ]

        result = await co_occurrence_builder.build_all()

        assert result["status"] == "success"
        assert result["relationships_deleted"] == 0
        assert result["relationships_created"] == 0
        assert result["total_co_occurrence_relationships"] == 0

    @pytest.mark.asyncio
    async def test_build_all_all_single_skill_jobs(self, co_occurrence_builder, mock_neo4j_repo):
        """Test build_all() when all jobs have only single skills (no pairs)."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{"deleted": 0}],  # _clear_existing
            [{"created": 0}],  # _compute_and_create - no pairs found
            [{"total_relationships": 0, "avg_weight": None,
              "min_weight": None, "max_weight": None}]  # get_statistics
        ]

        result = await co_occurrence_builder.build_all()

        assert result["status"] == "success"
        assert result["relationships_created"] == 0

    @pytest.mark.asyncio
    async def test_stoplist_filtering_excludes_generic_skills(self, mock_neo4j_repo):
        """Test that stoplist skills are properly excluded from co-occurrence."""
        with patch('app.services.co_occurrence_builder.settings') as mock_settings:
            mock_settings.NETWORK_MIN_CO_OCCURRENCE = 2
            mock_settings.NETWORK_GENERIC_SKILLS_STOPLIST = [
                "Communication", "Teamwork", "MS Excel"
            ]
            builder = CoOccurrenceBuilder(mock_neo4j_repo)

            # Verify stoplist is normalized
            assert builder._is_stoplist_skill("communication")
            assert builder._is_stoplist_skill("COMMUNICATION")
            assert builder._is_stoplist_skill("Communication")
            assert builder._is_stoplist_skill("teamwork")
            assert builder._is_stoplist_skill("MS Excel")
            assert builder._is_stoplist_skill("ms excel")

            # Non-stoplist skills should pass
            assert not builder._is_stoplist_skill("Python")
            assert not builder._is_stoplist_skill("JavaScript")
            assert not builder._is_stoplist_skill("Django")


@pytest.mark.unit
class TestCypherQueryCorrectness:
    """Test Cypher query correctness per spec."""

    @pytest.mark.asyncio
    async def test_clear_uses_undirected_pattern(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _clear_existing uses undirected relationship pattern."""
        mock_neo4j_repo.execute_query.return_value = [{"deleted": 0}]

        await co_occurrence_builder._clear_existing()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        # Should NOT have directed pattern like ->() or <-()
        assert "->(" not in query.replace("->()", "").replace("]->(", "")
        assert "-[r:CO_OCCURS_WITH]-" in query

    @pytest.mark.asyncio
    async def test_compute_sets_cost_as_inverse_weight(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create sets cost = 1.0 / weight."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await co_occurrence_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        assert "r.cost = 1.0 / weight" in query

    @pytest.mark.asyncio
    async def test_compute_prevents_duplicate_pairs(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create prevents duplicate skill pairs."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await co_occurrence_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        # Uses id(s1) < id(s2) to prevent both (A,B) and (B,A)
        assert "id(s1) < id(s2)" in query

    @pytest.mark.asyncio
    async def test_compute_sets_timestamps(self, co_occurrence_builder, mock_neo4j_repo):
        """Test _compute_and_create sets created_at and updated_at."""
        mock_neo4j_repo.execute_query.return_value = [{"created": 0}]

        await co_occurrence_builder._compute_and_create()

        query = mock_neo4j_repo.execute_query.call_args[0][0]
        assert "r.created_at = datetime()" in query
        assert "r.updated_at = datetime()" in query
