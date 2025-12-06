"""Unit tests for NetworkMetricsService.

Tests cover:
- Shortest path calculations (GDS, APOC, BFS fallback)
- Closeness calculations (skill-to-skill, job closeness)
- Eigenvector centrality (GDS and fallback)
- TransitionIndex calculation
- Caching behavior
- Fallback chain verification

Reference: Network Math Implementation - Phase 2 (02-SERVICES-LAYER.md)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.network_metrics_service import NetworkMetricsService


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4jRepository for testing."""
    repo = AsyncMock()
    repo.execute_query = AsyncMock()
    return repo


@pytest.fixture
def network_metrics_service(mock_neo4j_repo):
    """Create NetworkMetricsService instance with mocked dependencies."""
    with patch('app.services.network_metrics_service.settings') as mock_settings:
        mock_settings.NETWORK_CACHE_TTL = 3600
        mock_settings.NETWORK_DIJKSTRA_TIMEOUT = 5.0
        mock_settings.NETWORK_MAX_JOB_COUNT = 1000
        service = NetworkMetricsService(mock_neo4j_repo)
    return service


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

@pytest.mark.unit
class TestNetworkMetricsServiceInit:
    """Test NetworkMetricsService initialization."""

    def test_init_with_defaults(self, mock_neo4j_repo):
        """Test initialization uses settings with safe defaults."""
        with patch('app.services.network_metrics_service.settings') as mock_settings:
            mock_settings.NETWORK_CACHE_TTL = 7200
            mock_settings.NETWORK_DIJKSTRA_TIMEOUT = 10.0
            mock_settings.NETWORK_MAX_JOB_COUNT = 2000
            service = NetworkMetricsService(mock_neo4j_repo)

            assert service.neo4j_repo == mock_neo4j_repo
            assert service.cache_ttl == 7200
            assert service.dijkstra_timeout == 10.0
            assert service._gds_available is None

    def test_init_with_missing_settings_uses_defaults(self, mock_neo4j_repo):
        """Test initialization falls back to defaults if settings missing."""
        with patch('app.services.network_metrics_service.settings') as mock_settings:
            # Remove attributes to simulate missing settings
            type(mock_settings).NETWORK_CACHE_TTL = property(lambda s: (_ for _ in ()).throw(AttributeError()))
            type(mock_settings).NETWORK_DIJKSTRA_TIMEOUT = property(lambda s: (_ for _ in ()).throw(AttributeError()))

            service = NetworkMetricsService(mock_neo4j_repo)

            # Should use defaults
            assert service.cache_ttl == 3600  # Default
            assert service.dijkstra_timeout == 5.0  # Default


# =============================================================================
# GDS AVAILABILITY TESTS
# =============================================================================

@pytest.mark.unit
class TestGDSAvailability:
    """Test GDS library availability checking."""

    @pytest.mark.asyncio
    async def test_check_gds_available_when_installed(self, network_metrics_service, mock_neo4j_repo):
        """Test check_gds_available returns True when GDS is installed."""
        mock_neo4j_repo.execute_query.return_value = [{"version": "2.5.0"}]

        result = await network_metrics_service.check_gds_available()

        assert result is True
        assert network_metrics_service._gds_available is True

    @pytest.mark.asyncio
    async def test_check_gds_available_when_not_installed(self, network_metrics_service, mock_neo4j_repo):
        """Test check_gds_available returns False when GDS is not installed."""
        mock_neo4j_repo.execute_query.side_effect = Exception("GDS not found")

        result = await network_metrics_service.check_gds_available()

        assert result is False
        assert network_metrics_service._gds_available is False

    @pytest.mark.asyncio
    async def test_check_gds_available_caches_result(self, network_metrics_service, mock_neo4j_repo):
        """Test GDS availability is cached after first check."""
        mock_neo4j_repo.execute_query.return_value = [{"version": "2.5.0"}]

        # First call
        result1 = await network_metrics_service.check_gds_available()

        # Second call - should not query Neo4j again
        result2 = await network_metrics_service.check_gds_available()

        assert result1 is True
        assert result2 is True
        # Should only be called once due to caching
        assert mock_neo4j_repo.execute_query.call_count == 1


# =============================================================================
# SHORTEST PATH TESTS
# =============================================================================

@pytest.mark.unit
class TestShortestPath:
    """Test get_shortest_path method."""

    @pytest.mark.asyncio
    async def test_same_skill_returns_immediate_result(self, network_metrics_service, mock_neo4j_repo):
        """Test shortest path for same skill returns distance=0, closeness=1.0."""
        result = await network_metrics_service.get_shortest_path("skill_1", "skill_1")

        assert result["path_exists"] is True
        assert result["total_distance"] == 0.0
        assert result["closeness"] == 1.0
        assert result["path"] == ["skill_1"]
        assert result["algorithm"] == "same_skill"
        # Should not query Neo4j
        mock_neo4j_repo.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_shortest_path_uses_gds_when_available(self, network_metrics_service, mock_neo4j_repo):
        """Test shortest path uses GDS Dijkstra when available."""
        # GDS is available
        network_metrics_service._gds_available = True

        mock_neo4j_repo.execute_query.return_value = [{
            "totalCost": 0.5,
            "path_ids": ["skill_1", "skill_2", "skill_3"],
            "path_names": ["Python", "Django", "Flask"]
        }]

        result = await network_metrics_service.get_shortest_path("skill_1", "skill_3")

        assert result["path_exists"] is True
        assert result["total_distance"] == 0.5
        assert result["closeness"] == pytest.approx(1.0 / (1.0 + 0.5))  # 0.667
        assert result["path"] == ["skill_1", "skill_2", "skill_3"]
        assert result["algorithm"] == "gds_dijkstra"

    @pytest.mark.asyncio
    async def test_shortest_path_no_path_found(self, network_metrics_service, mock_neo4j_repo):
        """Test shortest path when no path exists between skills."""
        network_metrics_service._gds_available = False

        # APOC fails
        mock_neo4j_repo.execute_query.side_effect = [
            Exception("APOC not available"),  # APOC fails
            []  # BFS returns empty
        ]

        result = await network_metrics_service.get_shortest_path("skill_1", "skill_99")

        assert result["path_exists"] is False
        assert result["total_distance"] == float('inf')
        assert result["closeness"] == 0.0
        assert result["path"] == []
        assert result["algorithm"] == "no_path"


# =============================================================================
# FALLBACK CHAIN TESTS
# =============================================================================

@pytest.mark.unit
class TestFallbackChain:
    """Test GDS → APOC → BFS fallback chain."""

    @pytest.mark.asyncio
    async def test_fallback_from_gds_to_apoc(self, network_metrics_service, mock_neo4j_repo):
        """Test fallback from GDS to APOC when GDS fails."""
        network_metrics_service._gds_available = True

        # GDS fails, APOC succeeds
        mock_neo4j_repo.execute_query.side_effect = [
            Exception("GDS query failed"),  # GDS fails
            [{  # APOC succeeds
                "totalCost": 0.3,
                "path_ids": ["skill_1", "skill_2"],
                "path_names": ["Python", "Django"]
            }]
        ]

        result = await network_metrics_service.get_shortest_path("skill_1", "skill_2")

        assert result["path_exists"] is True
        assert result["algorithm"] == "apoc_dijkstra"

    @pytest.mark.asyncio
    async def test_fallback_from_apoc_to_bfs(self, network_metrics_service, mock_neo4j_repo):
        """Test fallback from APOC to BFS when APOC not available."""
        network_metrics_service._gds_available = False

        # APOC fails, BFS succeeds
        mock_neo4j_repo.execute_query.side_effect = [
            Exception("APOC not available"),  # APOC fails
            [{  # BFS succeeds
                "totalCost": 0.4,
                "path_ids": ["skill_1", "skill_3"],
                "path_names": ["Python", "Flask"]
            }]
        ]

        result = await network_metrics_service.get_shortest_path("skill_1", "skill_3")

        assert result["path_exists"] is True
        assert result["algorithm"] == "bfs_fallback"

    @pytest.mark.asyncio
    async def test_complete_fallback_chain_gds_to_bfs(self, network_metrics_service, mock_neo4j_repo):
        """Test complete fallback chain: GDS → APOC → BFS."""
        network_metrics_service._gds_available = True

        # GDS fails, APOC fails, BFS succeeds
        mock_neo4j_repo.execute_query.side_effect = [
            Exception("GDS failed"),  # GDS fails (in _dijkstra_gds)
            Exception("APOC failed"),  # APOC fails (in _dijkstra_native)
            [{  # BFS succeeds
                "totalCost": 0.6,
                "path_ids": ["skill_1", "skill_4", "skill_2"],
                "path_names": ["Python", "JavaScript", "React"]
            }]
        ]

        result = await network_metrics_service.get_shortest_path("skill_1", "skill_2")

        assert result["path_exists"] is True
        assert result["algorithm"] == "bfs_fallback"
        assert len(result["path"]) == 3


# =============================================================================
# CLOSENESS CALCULATION TESTS
# =============================================================================

@pytest.mark.unit
class TestClosenessCalculation:
    """Test closeness calculation methods."""

    @pytest.mark.asyncio
    async def test_get_skill_closeness(self, network_metrics_service, mock_neo4j_repo):
        """Test get_skill_closeness returns correct value."""
        network_metrics_service._gds_available = False
        mock_neo4j_repo.execute_query.side_effect = [
            Exception("APOC not available"),
            [{
                "totalCost": 1.0,  # Distance of 1
                "path_ids": ["skill_1", "skill_2"],
                "path_names": ["Python", "Django"]
            }]
        ]

        closeness = await network_metrics_service.get_skill_closeness("skill_1", "skill_2")

        # closeness = 1 / (1 + D) = 1 / (1 + 1) = 0.5
        assert closeness == pytest.approx(0.5)

    @pytest.mark.asyncio
    async def test_get_job_closeness_empty_job(self, network_metrics_service, mock_neo4j_repo):
        """Test job closeness for job with no skills."""
        mock_neo4j_repo.execute_query.return_value = [{"skill_ids": [], "skill_names": []}]

        result = await network_metrics_service.get_job_closeness("job_123")

        assert result["job_id"] == "job_123"
        assert result["job_closeness"] == 0.0
        assert result["skill_count"] == 0
        assert result["pair_count"] == 0

    @pytest.mark.asyncio
    async def test_get_job_closeness_single_skill(self, network_metrics_service, mock_neo4j_repo):
        """Test job closeness for job with single skill."""
        mock_neo4j_repo.execute_query.return_value = [{
            "skill_ids": ["skill_1"],
            "skill_names": ["Python"]
        }]

        result = await network_metrics_service.get_job_closeness("job_123")

        assert result["job_closeness"] == 1.0  # Single skill = perfect closeness
        assert result["skill_count"] == 1
        assert result["pair_count"] == 0

    @pytest.mark.asyncio
    async def test_get_job_closeness_multiple_skills(self, network_metrics_service, mock_neo4j_repo):
        """Test job closeness for job with multiple skills."""
        # First query returns job skills
        # Subsequent queries return path results for each pair
        network_metrics_service._gds_available = False

        mock_neo4j_repo.execute_query.side_effect = [
            [{"skill_ids": ["s1", "s2", "s3"], "skill_names": ["A", "B", "C"]}],
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s1", "s2"], "path_names": ["A", "B"]}],  # s1-s2
            Exception("APOC"), [{"totalCost": 1.0, "path_ids": ["s1", "s3"], "path_names": ["A", "C"]}],  # s1-s3
            Exception("APOC"), [{"totalCost": 0.3, "path_ids": ["s2", "s3"], "path_names": ["B", "C"]}],  # s2-s3
        ]

        result = await network_metrics_service.get_job_closeness("job_123")

        assert result["skill_count"] == 3
        assert result["pair_count"] == 3  # 3 pairs: (s1,s2), (s1,s3), (s2,s3)
        assert result["job_closeness"] > 0.0


# =============================================================================
# EIGENVECTOR CENTRALITY TESTS
# =============================================================================

@pytest.mark.unit
class TestEigenvectorCentrality:
    """Test eigenvector centrality methods."""

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_uses_cache(self, network_metrics_service, mock_neo4j_repo):
        """Test eigenvector centrality returns cached result when valid."""
        # Pre-populate cache
        cached_data = [
            {"skill_id": "s1", "skill_name": "Python", "centrality_score": 0.95},
            {"skill_id": "s2", "skill_name": "Django", "centrality_score": 0.85}
        ]
        cache_key = "eigenvector_100"
        network_metrics_service._centrality_cache[cache_key] = (cached_data, datetime.utcnow())

        result = await network_metrics_service.get_eigenvector_centrality(limit=100, use_cache=True)

        assert result == cached_data
        # Should not query Neo4j
        mock_neo4j_repo.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_ignores_expired_cache(self, network_metrics_service, mock_neo4j_repo):
        """Test eigenvector centrality ignores expired cache."""
        network_metrics_service._gds_available = False

        # Pre-populate with expired cache
        cached_data = [{"skill_id": "old", "skill_name": "Old", "centrality_score": 0.5}]
        cache_key = "eigenvector_100"
        expired_time = datetime.utcnow() - timedelta(seconds=network_metrics_service.cache_ttl + 100)
        network_metrics_service._centrality_cache[cache_key] = (cached_data, expired_time)

        # Mock fallback query
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "new", "skill_name": "New", "centrality_score": 0.9}
        ]

        result = await network_metrics_service.get_eigenvector_centrality(limit=100, use_cache=True)

        assert result[0]["skill_id"] == "new"
        mock_neo4j_repo.execute_query.assert_called()

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_bypass_cache(self, network_metrics_service, mock_neo4j_repo):
        """Test eigenvector centrality bypasses cache when use_cache=False."""
        network_metrics_service._gds_available = False

        # Pre-populate cache
        cached_data = [{"skill_id": "cached", "skill_name": "Cached", "centrality_score": 0.5}]
        cache_key = "eigenvector_100"
        network_metrics_service._centrality_cache[cache_key] = (cached_data, datetime.utcnow())

        # Mock fresh query
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "fresh", "skill_name": "Fresh", "centrality_score": 0.99}
        ]

        result = await network_metrics_service.get_eigenvector_centrality(limit=100, use_cache=False)

        assert result[0]["skill_id"] == "fresh"

    @pytest.mark.asyncio
    async def test_eigenvector_fallback_weighted_degree(self, network_metrics_service, mock_neo4j_repo):
        """Test eigenvector falls back to weighted degree when GDS unavailable."""
        network_metrics_service._gds_available = False

        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "s1", "skill_name": "Python", "centrality_score": 15.5},
            {"skill_id": "s2", "skill_name": "Django", "centrality_score": 12.3}
        ]

        result = await network_metrics_service.get_eigenvector_centrality(limit=10, use_cache=False)

        assert len(result) == 2
        assert result[0]["skill_id"] == "s1"
        assert result[0]["centrality_score"] == 15.5


# =============================================================================
# TRANSITION INDEX TESTS
# =============================================================================

@pytest.mark.unit
class TestTransitionIndex:
    """Test TransitionIndex calculation."""

    @pytest.mark.asyncio
    async def test_transition_index_formula(self, network_metrics_service, mock_neo4j_repo):
        """Test TransitionIndex uses correct formula weights."""
        network_metrics_service._gds_available = False

        # Setup: target job has skills s3, s4
        # Source skills: s1, s2 (no overlap)
        mock_neo4j_repo.execute_query.side_effect = [
            [{"target_skills": ["s3", "s4"]}],  # Target job skills
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s1", "s3"], "path_names": []}],  # s1-s3
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s1", "s4"], "path_names": []}],  # s1-s4
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s2", "s3"], "path_names": []}],  # s2-s3
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s2", "s4"], "path_names": []}],  # s2-s4
            [{"job_count": 500}]  # Market demand
        ]

        result = await network_metrics_service.calculate_transition_index(
            source_skills=["s1", "s2"],
            target_job_id="job_123"
        )

        # avg_closeness = 1/(1+0.5) = 0.667 for all 4 pairs
        # core_skill_overlap = 0/2 = 0 (no overlap)
        # market_demand = 500/1000 = 0.5
        # TransitionIndex = 0.50*0.667 + 0.30*0 + 0.20*0.5 = 0.333 + 0 + 0.1 = 0.433

        assert result["transition_index"] == pytest.approx(0.433, rel=0.1)
        assert result["avg_closeness"] == pytest.approx(0.667, rel=0.01)
        assert result["core_skill_overlap"] == 0.0
        assert result["market_demand"] == 0.5

    @pytest.mark.asyncio
    async def test_transition_index_with_skill_overlap(self, network_metrics_service, mock_neo4j_repo):
        """Test TransitionIndex with overlapping skills."""
        network_metrics_service._gds_available = False

        # Source: s1, s2; Target: s2, s3 (s2 overlaps)
        mock_neo4j_repo.execute_query.side_effect = [
            [{"target_skills": ["s2", "s3"]}],  # Target job skills
            Exception("APOC"), [{"totalCost": 0.0, "path_ids": ["s1", "s2"], "path_names": []}],  # s1-s2 (very close)
            Exception("APOC"), [{"totalCost": 1.0, "path_ids": ["s1", "s3"], "path_names": []}],  # s1-s3
            # s2-s2 is same skill (skipped)
            Exception("APOC"), [{"totalCost": 0.5, "path_ids": ["s2", "s3"], "path_names": []}],  # s2-s3
            [{"job_count": 100}]  # Market demand
        ]

        result = await network_metrics_service.calculate_transition_index(
            source_skills=["s1", "s2"],
            target_job_id="job_456"
        )

        # core_skill_overlap = 1/2 = 0.5 (s2 is in both)
        assert result["core_skill_overlap"] == 0.5
        assert result["details"]["overlapping_skills"] == ["s2"]
        assert result["details"]["skills_to_learn"] == ["s3"]

    @pytest.mark.asyncio
    async def test_transition_index_empty_target_job(self, network_metrics_service, mock_neo4j_repo):
        """Test TransitionIndex returns 0 for job with no skills."""
        mock_neo4j_repo.execute_query.return_value = [{"target_skills": []}]

        result = await network_metrics_service.calculate_transition_index(
            source_skills=["s1", "s2"],
            target_job_id="empty_job"
        )

        assert result["transition_index"] == 0.0
        assert "error" in result["details"]

    @pytest.mark.asyncio
    async def test_transition_index_empty_source_skills(self, network_metrics_service, mock_neo4j_repo):
        """Test TransitionIndex returns 0 for empty source skills."""
        mock_neo4j_repo.execute_query.return_value = [{"target_skills": ["s1", "s2"]}]

        result = await network_metrics_service.calculate_transition_index(
            source_skills=[],
            target_job_id="job_123"
        )

        assert result["transition_index"] == 0.0
        assert "error" in result["details"]


# =============================================================================
# SKILL METRICS TESTS
# =============================================================================

@pytest.mark.unit
class TestSkillMetrics:
    """Test get_skill_metrics method."""

    @pytest.mark.asyncio
    async def test_get_skill_metrics_success(self, network_metrics_service, mock_neo4j_repo):
        """Test get_skill_metrics returns comprehensive data."""
        mock_neo4j_repo.execute_query.side_effect = [
            [{
                "skill_id": "s1",
                "skill_name": "Python",
                "co_occurrence_count": 150,
                "total_weight": 5000,
                "avg_weight": 33.3
            }],
            [
                {"id": "s2", "name": "Django", "weight": 100},
                {"id": "s3", "name": "Flask", "weight": 80}
            ]
        ]

        result = await network_metrics_service.get_skill_metrics("s1")

        assert result["skill_id"] == "s1"
        assert result["skill_name"] == "Python"
        assert result["co_occurrence_count"] == 150
        assert result["total_weight"] == 5000
        assert len(result["top_co_occurring"]) == 2

    @pytest.mark.asyncio
    async def test_get_skill_metrics_not_found(self, network_metrics_service, mock_neo4j_repo):
        """Test get_skill_metrics handles non-existent skill."""
        mock_neo4j_repo.execute_query.return_value = []

        result = await network_metrics_service.get_skill_metrics("non_existent")

        assert "error" in result


# =============================================================================
# CACHE MANAGEMENT TESTS
# =============================================================================

@pytest.mark.unit
class TestCacheManagement:
    """Test cache management functionality."""

    def test_clear_cache(self, network_metrics_service):
        """Test clear_cache removes all cached data."""
        # Pre-populate cache
        network_metrics_service._centrality_cache["key1"] = ([], datetime.utcnow())
        network_metrics_service._centrality_cache["key2"] = ([], datetime.utcnow())

        network_metrics_service.clear_cache()

        assert len(network_metrics_service._centrality_cache) == 0

    def test_cache_size_limit(self, network_metrics_service):
        """Test cache respects max_cache_size."""
        # Verify max_cache_size exists
        assert hasattr(network_metrics_service, 'max_cache_size')
        assert network_metrics_service.max_cache_size > 0
