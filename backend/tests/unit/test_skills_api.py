"""Unit tests for Skills API endpoints.

Tests cover:
- Shortest path endpoints (POST and GET)
- Closeness endpoints (skill and job)
- Centrality rankings endpoint
- Transition index endpoint
- Skill metrics endpoint
- Admin endpoints (rebuild and stats)

Reference: Network Math Implementation - Phase 3 (03-API-LAYER.md)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.api.skills import router
from app.middleware.auth import get_current_user
from app.dependencies import get_network_metrics_service, get_co_occurrence_builder


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_metrics_service():
    """Create a mock NetworkMetricsService."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_co_occurrence_builder():
    """Create a mock CoOccurrenceBuilder."""
    builder = AsyncMock()
    return builder


@pytest.fixture
def app_with_mocks(mock_metrics_service, mock_co_occurrence_builder):
    """Create a FastAPI test app with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)

    # Override dependencies
    async def override_get_current_user():
        return "test-user-123"

    async def override_get_metrics_service():
        return mock_metrics_service

    async def override_get_builder():
        return mock_co_occurrence_builder

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_network_metrics_service] = override_get_metrics_service
    app.dependency_overrides[get_co_occurrence_builder] = override_get_builder

    return app


@pytest.fixture
def client(app_with_mocks):
    """Create test client."""
    return TestClient(app_with_mocks)


# =============================================================================
# SHORTEST PATH TESTS
# =============================================================================

class TestShortestPathEndpoints:
    """Tests for shortest path endpoints."""

    def test_shortest_path_post_success(self, client, mock_metrics_service):
        """Test POST /api/skills/path returns valid response."""
        mock_metrics_service.get_shortest_path.return_value = {
            "path_exists": True,
            "total_distance": 0.15,
            "closeness": 0.87,
            "path": ["python-001", "django-001", "rest-api-001"],
            "path_details": [
                {"id": "python-001", "name": "Python"},
                {"id": "django-001", "name": "Django"},
                {"id": "rest-api-001", "name": "REST APIs"}
            ],
            "algorithm": "gds_dijkstra"
        }

        response = client.post(
            "/api/skills/path",
            json={"skill_id_1": "python-001", "skill_id_2": "rest-api-001"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is True
        assert data["closeness"] == 0.87
        assert data["algorithm"] == "gds_dijkstra"
        assert len(data["path"]) == 3

    def test_shortest_path_post_no_path(self, client, mock_metrics_service):
        """Test POST /api/skills/path when no path exists."""
        mock_metrics_service.get_shortest_path.return_value = {
            "path_exists": False,
            "total_distance": float("inf"),
            "closeness": 0.0,
            "path": [],
            "path_details": [],
            "algorithm": "bfs_fallback"
        }

        response = client.post(
            "/api/skills/path",
            json={"skill_id_1": "isolated-001", "skill_id_2": "isolated-002"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is False
        assert data["closeness"] == 0.0

    def test_shortest_path_get_success(self, client, mock_metrics_service):
        """Test GET /api/skills/path/{s1}/{s2} returns valid response."""
        mock_metrics_service.get_shortest_path.return_value = {
            "path_exists": True,
            "total_distance": 0.1,
            "closeness": 0.91,
            "path": ["python-001", "django-001"],
            "path_details": [
                {"id": "python-001", "name": "Python"},
                {"id": "django-001", "name": "Django"}
            ],
            "algorithm": "gds_dijkstra"
        }

        response = client.get("/api/skills/path/python-001/django-001")

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is True
        assert data["closeness"] == 0.91

    def test_shortest_path_service_error(self, client, mock_metrics_service):
        """Test error handling when service raises exception."""
        mock_metrics_service.get_shortest_path.side_effect = Exception("Database error")

        response = client.post(
            "/api/skills/path",
            json={"skill_id_1": "python-001", "skill_id_2": "django-001"}
        )

        assert response.status_code == 500
        assert "Failed to calculate path" in response.json()["detail"]


# =============================================================================
# CLOSENESS TESTS
# =============================================================================

class TestClosenessEndpoints:
    """Tests for closeness endpoints."""

    def test_closeness_success(self, client, mock_metrics_service):
        """Test POST /api/skills/closeness returns valid response."""
        mock_metrics_service.get_shortest_path.return_value = {
            "path_exists": True,
            "total_distance": 0.2,
            "closeness": 0.83,
            "path": ["s1", "s2"],
            "path_details": [],
            "algorithm": "gds_dijkstra"
        }

        response = client.post(
            "/api/skills/closeness",
            json={"skill_id_1": "s1", "skill_id_2": "s2"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skill_id_1"] == "s1"
        assert data["skill_id_2"] == "s2"
        assert data["closeness"] == 0.83
        assert data["distance"] == 0.2

    def test_job_closeness_success(self, client, mock_metrics_service):
        """Test POST /api/skills/closeness/job returns valid response."""
        mock_metrics_service.get_job_closeness.return_value = {
            "job_id": "job-123",
            "job_closeness": 0.75,
            "skill_count": 5,
            "pair_count": 10,
            "skills": ["s1", "s2", "s3", "s4", "s5"]
        }

        response = client.post(
            "/api/skills/closeness/job",
            json={"job_id": "job-123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "job-123"
        assert data["job_closeness"] == 0.75
        assert data["skill_count"] == 5
        assert data["pair_count"] == 10

    def test_job_closeness_not_found(self, client, mock_metrics_service):
        """Test job closeness with non-existent job."""
        mock_metrics_service.get_job_closeness.return_value = {
            "error": "Job not found"
        }

        response = client.post(
            "/api/skills/closeness/job",
            json={"job_id": "nonexistent"}
        )

        assert response.status_code == 404
        assert "Job not found" in response.json()["detail"]

    def test_job_closeness_get_success(self, client, mock_metrics_service):
        """Test GET /api/skills/closeness/job/{job_id} returns valid response."""
        mock_metrics_service.get_job_closeness.return_value = {
            "job_id": "job-123",
            "job_closeness": 0.80,
            "skill_count": 3,
            "pair_count": 3,
            "skills": ["s1", "s2", "s3"]
        }

        response = client.get("/api/skills/closeness/job/job-123")

        assert response.status_code == 200
        data = response.json()
        assert data["job_closeness"] == 0.80


# =============================================================================
# CENTRALITY TESTS
# =============================================================================

class TestCentralityEndpoints:
    """Tests for centrality endpoints."""

    def test_centrality_rankings_success(self, client, mock_metrics_service):
        """Test GET /api/skills/centrality returns ranked skills."""
        mock_metrics_service.get_eigenvector_centrality.return_value = [
            {"skill_id": "python-001", "skill_name": "Python", "centrality_score": 0.95},
            {"skill_id": "sql-001", "skill_name": "SQL", "centrality_score": 0.89},
            {"skill_id": "js-001", "skill_name": "JavaScript", "centrality_score": 0.87}
        ]
        mock_metrics_service.check_gds_available.return_value = True

        response = client.get("/api/skills/centrality?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["algorithm"] == "eigenvector_gds"
        assert len(data["skills"]) == 3
        # Verify ordering preserved
        assert data["skills"][0]["skill_name"] == "Python"
        assert data["skills"][0]["centrality_score"] == 0.95

    def test_centrality_rankings_fallback(self, client, mock_metrics_service):
        """Test centrality uses fallback when GDS unavailable."""
        mock_metrics_service.get_eigenvector_centrality.return_value = [
            {"skill_id": "python-001", "skill_name": "Python", "centrality_score": 0.90}
        ]
        mock_metrics_service.check_gds_available.return_value = False

        response = client.get("/api/skills/centrality")

        assert response.status_code == 200
        data = response.json()
        assert data["algorithm"] == "weighted_degree_fallback"

    def test_centrality_limit_validation(self, client, mock_metrics_service):
        """Test limit parameter validation."""
        # Test limit too high (max 500)
        response = client.get("/api/skills/centrality?limit=1000")
        assert response.status_code == 422  # Validation error

        # Test limit too low (min 1)
        response = client.get("/api/skills/centrality?limit=0")
        assert response.status_code == 422


# =============================================================================
# TRANSITION INDEX TESTS
# =============================================================================

class TestTransitionIndexEndpoints:
    """Tests for transition index endpoints."""

    def test_transition_index_success(self, client, mock_metrics_service):
        """Test POST /api/skills/transition returns valid response."""
        mock_metrics_service.calculate_transition_index.return_value = {
            "transition_index": 0.72,
            "avg_closeness": 0.68,
            "core_skill_overlap": 0.40,
            "market_demand": 0.85,
            "details": {
                "source_skills_count": 3,
                "target_skills_count": 5,
                "overlapping_skills": ["python-001", "sql-001"],
                "skills_to_learn": ["tensorflow-001", "pytorch-001", "kubernetes-001"],
                "jobs_with_target_skills": 850
            }
        }

        response = client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["python-001", "sql-001", "pandas-001"],
                "target_job_id": "ml-engineer-123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["transition_index"] <= 1
        assert data["transition_index"] == 0.72
        assert data["avg_closeness"] == 0.68
        assert data["core_skill_overlap"] == 0.40
        assert data["market_demand"] == 0.85
        assert "details" in data
        assert len(data["details"]["overlapping_skills"]) == 2
        assert len(data["details"]["skills_to_learn"]) == 3

    def test_transition_index_empty_skills(self, client, mock_metrics_service):
        """Test transition index with empty source skills."""
        response = client.post(
            "/api/skills/transition",
            json={
                "source_skills": [],
                "target_job_id": "job-123"
            }
        )

        # Pydantic validation should reject empty list
        assert response.status_code == 422

    def test_transition_index_job_not_found(self, client, mock_metrics_service):
        """Test transition index with non-existent job."""
        mock_metrics_service.calculate_transition_index.return_value = {
            "transition_index": 0.0,
            "avg_closeness": 0.0,
            "core_skill_overlap": 0.0,
            "market_demand": 0.0,
            "details": {
                "error": "Job not found"
            }
        }

        response = client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["python-001"],
                "target_job_id": "nonexistent"
            }
        )

        assert response.status_code == 404


# =============================================================================
# SKILL METRICS TESTS
# =============================================================================

class TestSkillMetricsEndpoints:
    """Tests for skill metrics endpoints."""

    def test_skill_metrics_success(self, client, mock_metrics_service):
        """Test GET /api/skills/metrics/{skill_id} returns valid response."""
        mock_metrics_service.get_skill_metrics.return_value = {
            "skill_id": "python-001",
            "skill_name": "Python",
            "co_occurrence_count": 150,
            "total_weight": 4500,
            "avg_weight": 30.0,
            "top_co_occurring": [
                {"id": "django-001", "name": "Django", "weight": 120},
                {"id": "flask-001", "name": "Flask", "weight": 95},
                {"id": "sql-001", "name": "SQL", "weight": 85}
            ]
        }

        response = client.get("/api/skills/metrics/python-001")

        assert response.status_code == 200
        data = response.json()
        assert data["skill_id"] == "python-001"
        assert data["skill_name"] == "Python"
        assert data["co_occurrence_count"] == 150
        assert data["avg_weight"] == 30.0
        assert len(data["top_co_occurring"]) == 3

    def test_skill_metrics_not_found(self, client, mock_metrics_service):
        """Test skill metrics with non-existent skill."""
        mock_metrics_service.get_skill_metrics.return_value = {
            "error": "Skill not found"
        }

        response = client.get("/api/skills/metrics/nonexistent")

        assert response.status_code == 404
        assert "Skill not found" in response.json()["detail"]


# =============================================================================
# ADMIN ENDPOINT TESTS
# =============================================================================

class TestAdminEndpoints:
    """Tests for admin endpoints."""

    def test_rebuild_co_occurrence_success(self, client, mock_co_occurrence_builder):
        """Test POST /api/skills/admin/rebuild-cooccurrence returns valid response."""
        mock_co_occurrence_builder.build_all.return_value = {
            "status": "completed",
            "relationships_created": 5000,
            "duration_seconds": 45.2,
            "total_co_occurrence_relationships": 5000,
            "average_weight": 12.5,
            "min_weight": 2,
            "max_weight": 250
        }

        response = client.post(
            "/api/skills/admin/rebuild-cooccurrence?clear_existing=true&min_weight=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["relationships_created"] == 5000
        assert data["statistics"]["avg_weight"] == 12.5

    def test_rebuild_co_occurrence_sets_min_weight(self, client, mock_co_occurrence_builder):
        """Test rebuild sets min_weight on builder."""
        mock_co_occurrence_builder.build_all.return_value = {
            "status": "completed",
            "relationships_created": 100
        }

        response = client.post(
            "/api/skills/admin/rebuild-cooccurrence?min_weight=5"
        )

        assert response.status_code == 200
        # Verify min_weight was set
        assert mock_co_occurrence_builder.min_weight == 5

    def test_co_occurrence_stats_success(self, client, mock_co_occurrence_builder):
        """Test GET /api/skills/admin/cooccurrence-stats returns valid response."""
        mock_co_occurrence_builder.get_statistics.return_value = {
            "total_skills": 500,
            "total_co_occurrences": 15000,
            "avg_weight": 8.5,
            "max_weight": 300,
            "min_weight": 1
        }

        response = client.get("/api/skills/admin/cooccurrence-stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_skills"] == 500
        assert data["total_co_occurrences"] == 15000


# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

class TestAuthentication:
    """Tests for authentication requirements."""

    def test_endpoints_require_auth(self):
        """Test that all endpoints require authentication."""
        # Create app WITHOUT auth override
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        # All endpoints should return 403 (no credentials)
        endpoints = [
            ("POST", "/api/skills/path", {"skill_id_1": "s1", "skill_id_2": "s2"}),
            ("GET", "/api/skills/path/s1/s2", None),
            ("POST", "/api/skills/closeness", {"skill_id_1": "s1", "skill_id_2": "s2"}),
            ("POST", "/api/skills/closeness/job", {"job_id": "j1"}),
            ("GET", "/api/skills/closeness/job/j1", None),
            ("GET", "/api/skills/centrality", None),
            ("POST", "/api/skills/transition", {"source_skills": ["s1"], "target_job_id": "j1"}),
            ("GET", "/api/skills/metrics/s1", None),
            ("POST", "/api/skills/admin/rebuild-cooccurrence", None),
            ("GET", "/api/skills/admin/cooccurrence-stats", None),
        ]

        for method, url, json_data in endpoints:
            if method == "GET":
                response = client.get(url)
            else:
                response = client.post(url, json=json_data)

            # Should be 403 Forbidden (no auth header)
            assert response.status_code == 403, f"{method} {url} should require auth"
