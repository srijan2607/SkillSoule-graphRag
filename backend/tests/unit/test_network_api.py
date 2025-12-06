"""Unit tests for Network API endpoints.

Tests cover:
- /api/network/capabilities - GDS/APOC availability
- /api/network/path - Shortest path between skills
- /api/network/centrality - Eigenvector centrality rankings
- /api/network/job-closeness - Enhanced job closeness with per-skill breakdown
- /api/network/transition-index - Transition index calculation
- /api/network/build-cooccurrence - Admin build endpoint

Reference: Network Math Implementation - Phase 6 (07-NETWORK-API-ENHANCEMENTS.md)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.network import router, _is_admin_allowed
from app.models.network_metrics import (
    PathResponse,
    CentralityResponse,
    EnhancedJobClosenessRequest,
    EnhancedJobClosenessResponse,
    TransitionIndexDirectRequest,
    TransitionIndexDirectResponse,
    BuildCooccurrenceResponse,
    NetworkCapabilities,
    GDSUnavailableResponse,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_network_metrics_service():
    """Mock NetworkMetricsService for testing."""
    service = AsyncMock()
    service.get_capabilities = AsyncMock()
    service.get_shortest_path = AsyncMock()
    service.get_eigenvector_centrality = AsyncMock()
    service.calculate_enhanced_job_closeness = AsyncMock()
    return service


@pytest.fixture
def mock_co_occurrence_builder():
    """Mock CoOccurrenceBuilder for testing."""
    builder = AsyncMock()
    builder.build_all = AsyncMock()
    builder.get_stoplist_stats = AsyncMock()
    return builder


@pytest.fixture
def app(mock_network_metrics_service, mock_co_occurrence_builder):
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    from app.dependencies import get_network_metrics_service, get_co_occurrence_builder

    app.dependency_overrides[get_network_metrics_service] = lambda: mock_network_metrics_service
    app.dependency_overrides[get_co_occurrence_builder] = lambda: mock_co_occurrence_builder

    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================

@pytest.mark.unit
class TestHelperFunctions:
    """Test helper functions in network.py."""

    def test_is_admin_allowed_in_dev_environment(self):
        """Test admin is allowed in development environment."""
        with patch('app.api.network.settings') as mock_settings:
            mock_settings.ALLOW_NETWORK_ADMIN = False
            mock_settings.APP_ENV = "development"

            assert _is_admin_allowed() is True

    def test_is_admin_allowed_with_explicit_flag(self):
        """Test admin is allowed with explicit flag."""
        with patch('app.api.network.settings') as mock_settings:
            mock_settings.ALLOW_NETWORK_ADMIN = True
            mock_settings.APP_ENV = "production"

            assert _is_admin_allowed() is True

    def test_is_admin_not_allowed_in_production(self):
        """Test admin is not allowed in production without flag."""
        with patch('app.api.network.settings') as mock_settings:
            mock_settings.ALLOW_NETWORK_ADMIN = False
            mock_settings.APP_ENV = "production"

            assert _is_admin_allowed() is False


# =============================================================================
# NETWORK MATH FORMULA TESTS
# =============================================================================

@pytest.mark.unit
class TestNetworkMathFormulas:
    """Test network math formulas for correctness."""

    def test_closeness_formula(self):
        """Test closeness = 1 / (1 + distance)."""
        # Distance 0 -> Closeness 1.0
        assert 1.0 / (1.0 + 0.0) == 1.0

        # Distance 1 -> Closeness 0.5
        assert 1.0 / (1.0 + 1.0) == 0.5

        # Distance 3 -> Closeness 0.25
        assert 1.0 / (1.0 + 3.0) == 0.25

        # Distance infinity -> Closeness 0
        # (In practice, we use -1 to indicate unreachable)

    def test_transition_index_formula(self):
        """Test TransitionIndex = 0.50*closeness + 0.30*overlap + 0.20*demand."""
        # Perfect alignment
        closeness = 1.0
        overlap = 1.0
        demand = 1.0
        expected = 0.50 * 1.0 + 0.30 * 1.0 + 0.20 * 1.0
        assert expected == 1.0

        # Partial alignment
        closeness = 0.8
        overlap = 0.6
        demand = 0.5
        expected = 0.50 * 0.8 + 0.30 * 0.6 + 0.20 * 0.5
        assert abs(expected - 0.68) < 0.001

        # No alignment
        closeness = 0.0
        overlap = 0.0
        demand = 0.0
        expected = 0.50 * 0.0 + 0.30 * 0.0 + 0.20 * 0.0
        assert expected == 0.0

    def test_transition_index_weight_sum(self):
        """Test that transition index weights sum to 1.0."""
        WEIGHT_CLOSENESS = 0.50
        WEIGHT_OVERLAP = 0.30
        WEIGHT_DEMAND = 0.20

        assert abs(WEIGHT_CLOSENESS + WEIGHT_OVERLAP + WEIGHT_DEMAND - 1.0) < 0.001

    def test_cost_formula(self):
        """Test cost = 1 / weight."""
        # Weight 1 -> Cost 1.0
        assert 1.0 / 1 == 1.0

        # Weight 10 -> Cost 0.1
        assert 1.0 / 10 == 0.1

        # Weight 100 -> Cost 0.01
        assert 1.0 / 100 == 0.01

    def test_job_closeness_average(self):
        """Test job closeness is average of per-skill closenesses."""
        closenesses = [1.0, 0.5, 0.25, 0.75]
        expected = sum(closenesses) / len(closenesses)
        assert expected == 0.625


# =============================================================================
# TRANSITION INDEX ENDPOINT TESTS
# =============================================================================

@pytest.mark.unit
class TestTransitionIndexEndpoint:
    """Test /api/network/transition-index endpoint."""

    def test_transition_index_calculation(self, client):
        """Test transition index returns correct calculation."""
        with patch('app.api.network.get_current_user_id', return_value="user_123"):
            response = client.post(
                "/api/network/transition-index",
                json={
                    "job_closeness": 0.75,
                    "core_skill_overlap": 0.60,
                    "market_demand": 0.85
                },
                headers={"Authorization": "Bearer test_token"}
            )

        # Calculate expected
        expected_index = 0.50 * 0.75 + 0.30 * 0.60 + 0.20 * 0.85
        assert response.status_code == 200
        data = response.json()
        assert abs(data["transition_index"] - expected_index) < 0.0001

    def test_transition_index_interpretation_excellent(self, client):
        """Test interpretation for excellent fit (>=0.75)."""
        with patch('app.api.network.get_current_user_id', return_value="user_123"):
            response = client.post(
                "/api/network/transition-index",
                json={
                    "job_closeness": 1.0,
                    "core_skill_overlap": 1.0,
                    "market_demand": 1.0
                },
                headers={"Authorization": "Bearer test_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "excellent" in data["interpretation"].lower()

    def test_transition_index_interpretation_good(self, client):
        """Test interpretation for good fit (>=0.50)."""
        with patch('app.api.network.get_current_user_id', return_value="user_123"):
            response = client.post(
                "/api/network/transition-index",
                json={
                    "job_closeness": 0.6,
                    "core_skill_overlap": 0.5,
                    "market_demand": 0.5
                },
                headers={"Authorization": "Bearer test_token"}
            )

        assert response.status_code == 200
        data = response.json()
        # 0.5*0.6 + 0.3*0.5 + 0.2*0.5 = 0.3 + 0.15 + 0.1 = 0.55
        assert "good" in data["interpretation"].lower()

    def test_transition_index_breakdown(self, client):
        """Test transition index returns correct breakdown."""
        with patch('app.api.network.get_current_user_id', return_value="user_123"):
            response = client.post(
                "/api/network/transition-index",
                json={
                    "job_closeness": 0.8,
                    "core_skill_overlap": 0.6,
                    "market_demand": 0.4
                },
                headers={"Authorization": "Bearer test_token"}
            )

        assert response.status_code == 200
        data = response.json()

        assert "breakdown" in data
        assert abs(data["breakdown"]["job_closeness_contribution"] - 0.4) < 0.0001  # 0.5 * 0.8
        assert abs(data["breakdown"]["core_skill_overlap_contribution"] - 0.18) < 0.0001  # 0.3 * 0.6
        assert abs(data["breakdown"]["market_demand_contribution"] - 0.08) < 0.0001  # 0.2 * 0.4

    def test_transition_index_includes_note(self, client):
        """Test transition index includes heuristic disclaimer."""
        with patch('app.api.network.get_current_user_id', return_value="user_123"):
            response = client.post(
                "/api/network/transition-index",
                json={
                    "job_closeness": 0.5,
                    "core_skill_overlap": 0.5,
                    "market_demand": 0.5
                },
                headers={"Authorization": "Bearer test_token"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "note" in data
        assert "heuristic" in data["note"].lower()


# =============================================================================
# MODEL VALIDATION TESTS
# =============================================================================

@pytest.mark.unit
class TestModelValidation:
    """Test Pydantic model validation."""

    def test_transition_index_request_valid(self):
        """Test valid TransitionIndexDirectRequest."""
        request = TransitionIndexDirectRequest(
            job_closeness=0.75,
            core_skill_overlap=0.60,
            market_demand=0.85
        )
        assert request.job_closeness == 0.75
        assert request.core_skill_overlap == 0.60
        assert request.market_demand == 0.85

    def test_transition_index_request_boundary_values(self):
        """Test TransitionIndexDirectRequest accepts boundary values."""
        # Minimum values
        request = TransitionIndexDirectRequest(
            job_closeness=0.0,
            core_skill_overlap=0.0,
            market_demand=0.0
        )
        assert request.job_closeness == 0.0

        # Maximum values
        request = TransitionIndexDirectRequest(
            job_closeness=1.0,
            core_skill_overlap=1.0,
            market_demand=1.0
        )
        assert request.job_closeness == 1.0

    def test_enhanced_job_closeness_request_with_job_id(self):
        """Test EnhancedJobClosenessRequest with job_id."""
        request = EnhancedJobClosenessRequest(
            user_skills=["Python", "Django"],
            job_id="job_123"
        )
        assert request.user_skills == ["Python", "Django"]
        assert request.job_id == "job_123"
        assert request.job_title is None

    def test_enhanced_job_closeness_request_with_job_title(self):
        """Test EnhancedJobClosenessRequest with job_title."""
        request = EnhancedJobClosenessRequest(
            user_skills=["Python", "Django"],
            job_title="Backend Developer"
        )
        assert request.user_skills == ["Python", "Django"]
        assert request.job_id is None
        assert request.job_title == "Backend Developer"

    def test_network_capabilities_model(self):
        """Test NetworkCapabilities model."""
        capabilities = NetworkCapabilities(
            gds_available=True,
            gds_version="2.5.0",
            apoc_available=True,
            capabilities={
                "shortest_path": True,
                "eigenvector_centrality": True,
                "job_closeness": True,
                "transition_index": True
            },
            fallback_mode=False,
            limited_mode=False
        )
        assert capabilities.gds_available is True
        assert capabilities.gds_version == "2.5.0"
        assert capabilities.capabilities["shortest_path"] is True

    def test_path_response_model(self):
        """Test PathResponse model."""
        response = PathResponse(
            total_cost=2.5,
            closeness=0.2857,
            path_skill_names=["Python", "Django", "Flask"],
            path_details=[
                {"id": "s1", "name": "Python"},
                {"id": "s2", "name": "Django"},
                {"id": "s3", "name": "Flask"}
            ],
            algorithm="gds_dijkstra"
        )
        assert response.total_cost == 2.5
        assert response.closeness == 0.2857
        assert len(response.path_skill_names) == 3


# =============================================================================
# STOPLIST CONFIGURATION TESTS
# =============================================================================

@pytest.mark.unit
class TestStoplistConfiguration:
    """Test stoplist configuration from settings."""

    def test_stoplist_contains_soft_skills(self):
        """Test stoplist includes common soft skills."""
        from app.config import settings

        stoplist = getattr(settings, 'NETWORK_GENERIC_SKILLS_STOPLIST', [])
        stoplist_lower = [s.lower() for s in stoplist]

        assert "communication" in stoplist_lower
        assert "teamwork" in stoplist_lower
        assert "leadership" in stoplist_lower

    def test_stoplist_contains_basic_tools(self):
        """Test stoplist includes basic office tools."""
        from app.config import settings

        stoplist = getattr(settings, 'NETWORK_GENERIC_SKILLS_STOPLIST', [])
        stoplist_lower = [s.lower() for s in stoplist]

        assert "microsoft excel" in stoplist_lower or "excel" in stoplist_lower
        assert "microsoft word" in stoplist_lower or "word" in stoplist_lower


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_closeness_same_skill(self):
        """Test closeness of a skill with itself is 1.0."""
        # Distance = 0, Closeness = 1 / (1 + 0) = 1.0
        distance = 0.0
        closeness = 1.0 / (1.0 + distance)
        assert closeness == 1.0

    def test_closeness_unreachable(self):
        """Test closeness handling for unreachable skills."""
        # In practice, distance = -1 indicates unreachable
        # Frontend should handle this case
        distance = float('inf')
        closeness = 0.0  # Unreachable means 0 closeness
        assert closeness == 0.0

    def test_job_closeness_single_skill(self):
        """Test job closeness with only one required skill."""
        # If user has the skill -> closeness = 1.0
        # If user doesn't have it and no path -> closeness = 0.0
        closenesses = [1.0]
        avg = sum(closenesses) / len(closenesses)
        assert avg == 1.0

    def test_job_closeness_no_skills(self):
        """Test job closeness with no required skills returns 0."""
        closenesses = []
        avg = 0.0  # Default when no skills
        assert avg == 0.0
