"""Integration tests for Skills API with real database connections.

Tests cover end-to-end API flows with actual Neo4j graph data.

Reference: Network Math Implementation - Phase 3 (03-API-LAYER.md)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.middleware.auth import get_current_user
from app.dependencies import get_network_metrics_service
from app.services.network_metrics_service import NetworkMetricsService
from app.repositories.neo4j_repository import Neo4jRepository


@pytest.fixture
def authenticated_client():
    """Create test client with authentication override."""
    async def override_get_current_user():
        return "test-user-123"

    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def seeded_client(neo4j_repo: Neo4jRepository):
    """
    Create test client with seeded Neo4j data.

    Seeds a small test graph with skills, jobs, and CO_OCCURS_WITH relationships.
    """
    # Seed test data
    skills = [
        ("test_s1", "Python"),
        ("test_s2", "Django"),
        ("test_s3", "Flask"),
        ("test_s4", "JavaScript"),
        ("test_s5", "React"),
    ]

    for skill_id, name in skills:
        await neo4j_repo.execute_query(
            "CREATE (s:Skill {id: $id, name: $name})",
            {"id": skill_id, "name": name}
        )

    # Create jobs
    jobs = [
        ("test_j1", "Backend Developer"),
        ("test_j2", "Frontend Developer"),
    ]

    for job_id, title in jobs:
        await neo4j_repo.execute_query(
            "CREATE (j:Job {job_id: $job_id, job_title: $title})",
            {"job_id": job_id, "title": title}
        )

    # Create REQUIRES relationships
    await neo4j_repo.execute_query(
        """
        MATCH (j:Job {job_id: 'test_j1'})
        MATCH (s:Skill) WHERE s.id IN ['test_s1', 'test_s2', 'test_s3']
        CREATE (j)-[:REQUIRES]->(s)
        """
    )

    await neo4j_repo.execute_query(
        """
        MATCH (j:Job {job_id: 'test_j2'})
        MATCH (s:Skill) WHERE s.id IN ['test_s4', 'test_s5']
        CREATE (j)-[:REQUIRES]->(s)
        """
    )

    # Create CO_OCCURS_WITH relationships
    co_occurrences = [
        ("test_s1", "test_s2", 10),
        ("test_s1", "test_s3", 8),
        ("test_s2", "test_s3", 6),
        ("test_s4", "test_s5", 15),
        ("test_s1", "test_s4", 3),  # Bridge
    ]

    for s1, s2, weight in co_occurrences:
        cost = 1.0 / weight
        await neo4j_repo.execute_query(
            """
            MATCH (skill1:Skill {id: $s1})
            MATCH (skill2:Skill {id: $s2})
            CREATE (skill1)-[:CO_OCCURS_WITH {weight: $weight, cost: $cost}]->(skill2)
            """,
            {"s1": s1, "s2": s2, "weight": weight, "cost": cost}
        )

    # Create service with seeded repo
    service = NetworkMetricsService(neo4j_repo)

    async def override_get_current_user():
        return "test-user-123"

    async def override_get_metrics_service():
        return service

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_network_metrics_service] = override_get_metrics_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# =============================================================================
# SHORTEST PATH INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestShortestPathIntegration:
    """Integration tests for shortest path API."""

    @pytest.mark.asyncio
    async def test_shortest_path_connected_skills(self, seeded_client):
        """Test shortest path between connected skills."""
        response = seeded_client.post(
            "/api/skills/path",
            json={"skill_id_1": "test_s1", "skill_id_2": "test_s2"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is True
        assert data["closeness"] > 0
        assert "test_s1" in data["path"]
        assert "test_s2" in data["path"]

    @pytest.mark.asyncio
    async def test_shortest_path_same_skill(self, seeded_client):
        """Test shortest path for same skill returns optimized result."""
        response = seeded_client.post(
            "/api/skills/path",
            json={"skill_id_1": "test_s1", "skill_id_2": "test_s1"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is True
        assert data["total_distance"] == 0.0
        assert data["closeness"] == 1.0
        assert data["algorithm"] == "same_skill"

    @pytest.mark.asyncio
    async def test_shortest_path_get_endpoint(self, seeded_client):
        """Test GET endpoint for shortest path."""
        response = seeded_client.get("/api/skills/path/test_s1/test_s2")

        assert response.status_code == 200
        data = response.json()
        assert data["path_exists"] is True


# =============================================================================
# CLOSENESS INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestClosenessIntegration:
    """Integration tests for closeness API."""

    @pytest.mark.asyncio
    async def test_closeness_connected_skills(self, seeded_client):
        """Test closeness between connected skills."""
        response = seeded_client.post(
            "/api/skills/closeness",
            json={"skill_id_1": "test_s1", "skill_id_2": "test_s2"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skill_id_1"] == "test_s1"
        assert data["skill_id_2"] == "test_s2"
        assert 0 < data["closeness"] <= 1
        assert data["distance"] >= 0

    @pytest.mark.asyncio
    async def test_job_closeness(self, seeded_client):
        """Test job closeness calculation."""
        response = seeded_client.post(
            "/api/skills/closeness/job",
            json={"job_id": "test_j1"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test_j1"
        assert data["skill_count"] == 3  # Python, Django, Flask
        assert data["pair_count"] == 3  # 3 pairs from 3 skills


# =============================================================================
# CENTRALITY INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestCentralityIntegration:
    """Integration tests for centrality API."""

    @pytest.mark.asyncio
    async def test_centrality_rankings(self, seeded_client):
        """Test centrality rankings returns ordered skills."""
        response = seeded_client.get("/api/skills/centrality?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert data["count"] <= 5
        assert data["algorithm"] in ["eigenvector_gds", "weighted_degree_fallback"]

        # Verify ordering (descending by score)
        if len(data["skills"]) > 1:
            scores = [s["centrality_score"] for s in data["skills"]]
            assert scores == sorted(scores, reverse=True)


# =============================================================================
# TRANSITION INDEX INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestTransitionIndexIntegration:
    """Integration tests for transition index API."""

    @pytest.mark.asyncio
    async def test_transition_index(self, seeded_client):
        """Test transition index calculation."""
        response = seeded_client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["test_s1"],
                "target_job_id": "test_j1"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert 0 <= data["transition_index"] <= 1
        assert "details" in data

    @pytest.mark.asyncio
    async def test_transition_with_overlap(self, seeded_client):
        """Test transition index with skill overlap."""
        response = seeded_client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["test_s1", "test_s2"],  # 2 of 3 required skills
                "target_job_id": "test_j1"
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Should have ~0.67 overlap (2/3)
        assert data["core_skill_overlap"] > 0.5


# =============================================================================
# SKILL METRICS INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestSkillMetricsIntegration:
    """Integration tests for skill metrics API."""

    @pytest.mark.asyncio
    async def test_skill_metrics(self, seeded_client):
        """Test skill metrics returns co-occurrence data."""
        response = seeded_client.get("/api/skills/metrics/test_s1")

        assert response.status_code == 200
        data = response.json()
        assert data["skill_id"] == "test_s1"
        assert data["skill_name"] == "Python"
        assert data["co_occurrence_count"] > 0


# =============================================================================
# ERROR HANDLING INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    @pytest.mark.asyncio
    async def test_nonexistent_skill_metrics(self, seeded_client):
        """Test error handling for non-existent skill."""
        response = seeded_client.get("/api/skills/metrics/nonexistent-skill")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_nonexistent_job_closeness(self, seeded_client):
        """Test error handling for non-existent job."""
        response = seeded_client.post(
            "/api/skills/closeness/job",
            json={"job_id": "nonexistent-job"}
        )

        # Should return 200 with 0 values, or 404 depending on implementation
        assert response.status_code in [200, 404]
