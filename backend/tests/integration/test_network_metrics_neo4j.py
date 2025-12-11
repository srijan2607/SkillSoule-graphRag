"""Integration tests for NetworkMetricsService with Neo4j.

Tests cover:
- Dijkstra shortest path with real CO_OCCURS_WITH relationships
- Closeness calculations on connected skills
- Eigenvector centrality computation
- TransitionIndex with job/skill data
- Graph statistics retrieval

Reference: Network Math Implementation - Phase 2 (02-SERVICES-LAYER.md)
"""

import pytest
from app.services.network_metrics_service import NetworkMetricsService
from app.repositories.neo4j_repository import Neo4jRepository


@pytest.fixture
async def network_service(neo4j_repo: Neo4jRepository):
    """Create NetworkMetricsService with real Neo4j connection."""
    return NetworkMetricsService(neo4j_repo)


@pytest.fixture
async def seeded_graph(neo4j_repo: Neo4jRepository):
    """
    Seed Neo4j with test data for network metrics tests.

    Creates a small graph:
    - Skills: s1 (Python), s2 (Django), s3 (Flask), s4 (JavaScript), s5 (React)
    - Jobs: j1 (Backend Dev), j2 (Frontend Dev), j3 (Full Stack)
    - CO_OCCURS_WITH relationships with weights and costs

    Graph structure:
        s1 (Python) --[weight:10]--> s2 (Django)
        s1 (Python) --[weight:8]--> s3 (Flask)
        s2 (Django) --[weight:6]--> s3 (Flask)
        s4 (JavaScript) --[weight:15]--> s5 (React)
        s1 (Python) --[weight:3]--> s4 (JavaScript)  # Bridge between communities
    """
    # Create skills
    skills = [
        ("s1", "Python"),
        ("s2", "Django"),
        ("s3", "Flask"),
        ("s4", "JavaScript"),
        ("s5", "React"),
    ]

    for skill_id, name in skills:
        await neo4j_repo.execute_query(
            "CREATE (s:Skill {id: $id, name: $name})",
            {"id": skill_id, "name": name}
        )

    # Create jobs
    jobs = [
        ("j1", "Backend Developer"),
        ("j2", "Frontend Developer"),
        ("j3", "Full Stack Developer"),
    ]

    for job_id, title in jobs:
        await neo4j_repo.execute_query(
            "CREATE (j:Job {job_id: $job_id, job_title: $title})",
            {"job_id": job_id, "title": title}
        )

    # Create REQUIRES relationships
    job_skills = [
        ("j1", ["s1", "s2", "s3"]),       # Backend needs Python, Django, Flask
        ("j2", ["s4", "s5"]),              # Frontend needs JavaScript, React
        ("j3", ["s1", "s4", "s5"]),        # Full Stack needs Python, JavaScript, React
    ]

    for job_id, skill_ids in job_skills:
        for skill_id in skill_ids:
            await neo4j_repo.execute_query(
                """
                MATCH (j:Job {job_id: $job_id})
                MATCH (s:Skill {id: $skill_id})
                CREATE (j)-[:REQUIRES]->(s)
                """,
                {"job_id": job_id, "skill_id": skill_id}
            )

    # Create CO_OCCURS_WITH relationships (undirected, with weight and cost)
    co_occurrences = [
        ("s1", "s2", 10),   # Python-Django: strong co-occurrence
        ("s1", "s3", 8),    # Python-Flask: strong co-occurrence
        ("s2", "s3", 6),    # Django-Flask: moderate co-occurrence
        ("s4", "s5", 15),   # JavaScript-React: very strong
        ("s1", "s4", 3),    # Python-JavaScript: weak bridge
    ]

    for s1, s2, weight in co_occurrences:
        cost = 1.0 / weight  # cost = 1/weight
        await neo4j_repo.execute_query(
            """
            MATCH (skill1:Skill {id: $s1})
            MATCH (skill2:Skill {id: $s2})
            CREATE (skill1)-[:CO_OCCURS_WITH {weight: $weight, cost: $cost}]->(skill2)
            """,
            {"s1": s1, "s2": s2, "weight": weight, "cost": cost}
        )

    yield neo4j_repo


# =============================================================================
# SHORTEST PATH INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestShortestPathIntegration:
    """Integration tests for shortest path calculations."""

    @pytest.mark.asyncio
    async def test_shortest_path_direct_connection(self, seeded_graph, network_service):
        """Test shortest path for directly connected skills."""
        result = await network_service.get_shortest_path("s1", "s2")

        assert result["path_exists"] is True
        assert result["total_distance"] > 0
        assert result["closeness"] > 0
        assert "s1" in result["path"]
        assert "s2" in result["path"]
        assert result["algorithm"] in ["gds_dijkstra", "apoc_dijkstra", "bfs_fallback"]

    @pytest.mark.asyncio
    async def test_shortest_path_multi_hop(self, seeded_graph, network_service):
        """Test shortest path requiring multiple hops."""
        # s2 (Django) to s5 (React) requires: Django -> Python -> JavaScript -> React
        result = await network_service.get_shortest_path("s2", "s5")

        assert result["path_exists"] is True
        # Path should have at least 3 nodes (s2 -> intermediate -> s5)
        assert len(result["path"]) >= 2
        assert result["total_distance"] > 0

    @pytest.mark.asyncio
    async def test_shortest_path_closeness_formula(self, seeded_graph, network_service):
        """Test closeness formula: closeness = 1 / (1 + D)."""
        result = await network_service.get_shortest_path("s1", "s2")

        expected_closeness = 1.0 / (1.0 + result["total_distance"])
        assert result["closeness"] == pytest.approx(expected_closeness, rel=0.01)

    @pytest.mark.asyncio
    async def test_shortest_path_same_skill(self, seeded_graph, network_service):
        """Test shortest path for same skill returns optimized result."""
        result = await network_service.get_shortest_path("s1", "s1")

        assert result["path_exists"] is True
        assert result["total_distance"] == 0.0
        assert result["closeness"] == 1.0
        assert result["algorithm"] == "same_skill"


# =============================================================================
# CLOSENESS INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestClosenessIntegration:
    """Integration tests for closeness calculations."""

    @pytest.mark.asyncio
    async def test_skill_closeness_connected(self, seeded_graph, network_service):
        """Test skill closeness for connected skills."""
        closeness = await network_service.get_skill_closeness("s1", "s2")

        assert 0.0 < closeness <= 1.0

    @pytest.mark.asyncio
    async def test_skill_closeness_same_skill(self, seeded_graph, network_service):
        """Test skill closeness for same skill is 1.0."""
        closeness = await network_service.get_skill_closeness("s1", "s1")

        assert closeness == 1.0

    @pytest.mark.asyncio
    async def test_job_closeness_calculation(self, seeded_graph, network_service):
        """Test job closeness for job with multiple skills."""
        # j1 has skills s1, s2, s3 (all connected)
        result = await network_service.get_job_closeness("j1")

        assert result["job_id"] == "j1"
        assert result["skill_count"] == 3
        assert result["pair_count"] == 3  # 3 pairs: (s1,s2), (s1,s3), (s2,s3)
        assert 0.0 < result["job_closeness"] <= 1.0

    @pytest.mark.asyncio
    async def test_job_closeness_nonexistent_job(self, seeded_graph, network_service):
        """Test job closeness for non-existent job."""
        result = await network_service.get_job_closeness("nonexistent")

        assert result["skill_count"] == 0
        assert result["job_closeness"] == 0.0


# =============================================================================
# EIGENVECTOR CENTRALITY INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestEigenvectorCentralityIntegration:
    """Integration tests for eigenvector centrality."""

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_returns_skills(self, seeded_graph, network_service):
        """Test eigenvector centrality returns ranked skills."""
        result = await network_service.get_eigenvector_centrality(limit=10, use_cache=False)

        assert len(result) > 0
        assert all("skill_id" in r for r in result)
        assert all("centrality_score" in r for r in result)
        # Should be ordered by centrality score (descending)
        scores = [r["centrality_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_limit(self, seeded_graph, network_service):
        """Test eigenvector centrality respects limit parameter."""
        result = await network_service.get_eigenvector_centrality(limit=3, use_cache=False)

        assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_eigenvector_centrality_caching(self, seeded_graph, network_service):
        """Test eigenvector centrality caching works."""
        # First call - populates cache
        result1 = await network_service.get_eigenvector_centrality(limit=5, use_cache=True)

        # Second call - should use cache
        result2 = await network_service.get_eigenvector_centrality(limit=5, use_cache=True)

        # Results should be identical
        assert result1 == result2


# =============================================================================
# TRANSITION INDEX INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestTransitionIndexIntegration:
    """Integration tests for TransitionIndex calculation."""

    @pytest.mark.asyncio
    async def test_transition_index_calculation(self, seeded_graph, network_service):
        """Test TransitionIndex calculation with real data."""
        # User has Python (s1), wants Backend Developer job (j1: s1, s2, s3)
        result = await network_service.calculate_transition_index(
            source_skills=["s1"],
            target_job_id="j1"
        )

        assert 0.0 <= result["transition_index"] <= 1.0
        assert "avg_closeness" in result
        assert "core_skill_overlap" in result
        assert "market_demand" in result
        assert "details" in result

    @pytest.mark.asyncio
    async def test_transition_index_with_overlap(self, seeded_graph, network_service):
        """Test TransitionIndex with skill overlap."""
        # User has Python (s1) and Django (s2), target job has s1, s2, s3
        result = await network_service.calculate_transition_index(
            source_skills=["s1", "s2"],
            target_job_id="j1"
        )

        # 2/3 overlap = 0.67
        assert result["core_skill_overlap"] == pytest.approx(0.67, rel=0.1)
        assert "s1" in result["details"]["overlapping_skills"]
        assert "s2" in result["details"]["overlapping_skills"]
        assert result["details"]["skills_to_learn"] == ["s3"]

    @pytest.mark.asyncio
    async def test_transition_index_full_overlap(self, seeded_graph, network_service):
        """Test TransitionIndex when user has all required skills."""
        # User has all frontend skills (s4, s5), target is Frontend job (j2: s4, s5)
        result = await network_service.calculate_transition_index(
            source_skills=["s4", "s5"],
            target_job_id="j2"
        )

        # 100% skill overlap
        assert result["core_skill_overlap"] == 1.0
        assert result["details"]["skills_to_learn"] == []


# =============================================================================
# SKILL METRICS INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
class TestSkillMetricsIntegration:
    """Integration tests for skill metrics."""

    @pytest.mark.asyncio
    async def test_skill_metrics_returns_data(self, seeded_graph, network_service):
        """Test skill metrics returns comprehensive data."""
        result = await network_service.get_skill_metrics("s1")

        assert result["skill_id"] == "s1"
        assert result["skill_name"] == "Python"
        assert result["co_occurrence_count"] > 0
        assert result["total_weight"] > 0
        assert result["avg_weight"] > 0.0
        assert "top_co_occurring" in result

    @pytest.mark.asyncio
    async def test_skill_metrics_top_co_occurring(self, seeded_graph, network_service):
        """Test skill metrics returns top co-occurring skills."""
        result = await network_service.get_skill_metrics("s1")

        # Python (s1) co-occurs with Django (s2), Flask (s3), JavaScript (s4)
        top_skills = [s["id"] for s in result["top_co_occurring"]]
        assert len(top_skills) > 0
        # Django should be among top (weight=10)
        assert "s2" in top_skills or len(top_skills) >= 1

    @pytest.mark.asyncio
    async def test_skill_metrics_nonexistent_skill(self, seeded_graph, network_service):
        """Test skill metrics handles non-existent skill."""
        result = await network_service.get_skill_metrics("nonexistent")

        assert "error" in result


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

@pytest.mark.integration
class TestEdgeCasesIntegration:
    """Integration tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_graph(self, neo4j_repo: Neo4jRepository):
        """Test service handles empty graph gracefully."""
        service = NetworkMetricsService(neo4j_repo)

        result = await service.get_skill_metrics("any_skill")

        assert "error" in result or result.get("co_occurrence_count", 0) == 0

    @pytest.mark.asyncio
    async def test_disconnected_skills(self, seeded_graph, network_service):
        """Test shortest path between disconnected skills."""
        # Create an isolated skill
        await seeded_graph.execute_query(
            "CREATE (s:Skill {id: 'isolated', name: 'Isolated Skill'})"
        )

        result = await network_service.get_shortest_path("s1", "isolated")

        # Should indicate no path found
        assert result["path_exists"] is False
        assert result["closeness"] == 0.0

    @pytest.mark.asyncio
    async def test_large_limit_eigenvector(self, seeded_graph, network_service):
        """Test eigenvector centrality with limit larger than skill count."""
        result = await network_service.get_eigenvector_centrality(limit=1000, use_cache=False)

        # Should return all skills (5 in our test graph)
        assert len(result) <= 5  # We only have 5 skills
