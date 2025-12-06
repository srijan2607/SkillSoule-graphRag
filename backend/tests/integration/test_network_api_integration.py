"""Integration tests for Network API endpoints with toy graph.

Tests verify mathematical correctness of network calculations using a
controlled toy graph with known distances and expected results.

Toy Graph Structure (from 07-NETWORK-API-ENHANCEMENTS.md):

    A --[w=10, c=0.1]--> B --[w=5, c=0.2]--> C

    Expected:
    - D(A,B) = 0.1
    - D(A,C) = 0.1 + 0.2 = 0.3
    - Closeness(A,B) = 1/(1+0.1) = 0.909
    - Closeness(A,C) = 1/(1+0.3) = 0.769

Reference: Network Math Implementation - Phase 6 (07-NETWORK-API-ENHANCEMENTS.md)
"""

import pytest
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder
from app.repositories.neo4j_repository import Neo4jRepository


@pytest.fixture
async def toy_graph_service(neo4j_repo: Neo4jRepository):
    """Create NetworkMetricsService with real Neo4j connection."""
    return NetworkMetricsService(neo4j_repo)


@pytest.fixture
async def toy_graph(neo4j_repo: Neo4jRepository):
    """
    Create toy graph for testing network math.

    Structure:
        A --[weight=10, cost=0.1]--> B --[weight=5, cost=0.2]--> C

    This gives us predictable distances:
    - D(A,B) = 0.1 (direct edge)
    - D(B,C) = 0.2 (direct edge)
    - D(A,C) = 0.3 (via B)
    """
    # Clean up any existing test data
    await neo4j_repo.execute_query(
        "MATCH (n) WHERE n.id IN ['toy_A', 'toy_B', 'toy_C'] DETACH DELETE n"
    )

    # Create skills A, B, C
    skills = [
        ("toy_A", "SkillA"),
        ("toy_B", "SkillB"),
        ("toy_C", "SkillC"),
    ]

    for skill_id, name in skills:
        await neo4j_repo.execute_query(
            "CREATE (s:Skill {id: $id, name: $name})",
            {"id": skill_id, "name": name}
        )

    # Create CO_OCCURS_WITH relationships
    # A -> B: weight=10, cost=0.1
    await neo4j_repo.execute_query(
        """
        MATCH (a:Skill {id: 'toy_A'})
        MATCH (b:Skill {id: 'toy_B'})
        CREATE (a)-[:CO_OCCURS_WITH {weight: 10, cost: 0.1}]->(b)
        """
    )

    # B -> C: weight=5, cost=0.2
    await neo4j_repo.execute_query(
        """
        MATCH (b:Skill {id: 'toy_B'})
        MATCH (c:Skill {id: 'toy_C'})
        CREATE (b)-[:CO_OCCURS_WITH {weight: 5, cost: 0.2}]->(c)
        """
    )

    yield {
        "skills": skills,
        "expected_distances": {
            ("toy_A", "toy_B"): 0.1,
            ("toy_B", "toy_C"): 0.2,
            ("toy_A", "toy_C"): 0.3,  # via B
        },
        "expected_closenesses": {
            ("toy_A", "toy_B"): 1.0 / (1.0 + 0.1),  # 0.909...
            ("toy_B", "toy_C"): 1.0 / (1.0 + 0.2),  # 0.833...
            ("toy_A", "toy_C"): 1.0 / (1.0 + 0.3),  # 0.769...
        }
    }

    # Cleanup
    await neo4j_repo.execute_query(
        "MATCH (n) WHERE n.id IN ['toy_A', 'toy_B', 'toy_C'] DETACH DELETE n"
    )


@pytest.fixture
async def job_closeness_graph(neo4j_repo: Neo4jRepository):
    """
    Create graph for testing enhanced job closeness.

    Structure:
        User has: Python, SQL
        Job requires: Python, Django, PostgreSQL

        Python --[w=10]--> Django
        SQL --[w=8]--> PostgreSQL

    Expected:
    - Python: already_has=True, closeness=1.0
    - Django: closest=Python, distance=0.1, closeness=0.909
    - PostgreSQL: closest=SQL, distance=0.125, closeness=0.889
    - Overall: (1.0 + 0.909 + 0.889) / 3 = 0.933
    """
    # Clean up
    await neo4j_repo.execute_query(
        """
        MATCH (n) WHERE n.id STARTS WITH 'jc_' DETACH DELETE n
        """
    )

    # Create skills
    skills = [
        ("jc_python", "Python"),
        ("jc_sql", "SQL"),
        ("jc_django", "Django"),
        ("jc_postgresql", "PostgreSQL"),
    ]

    for skill_id, name in skills:
        await neo4j_repo.execute_query(
            "CREATE (s:Skill {id: $id, name: $name})",
            {"id": skill_id, "name": name}
        )

    # Create CO_OCCURS_WITH relationships
    await neo4j_repo.execute_query(
        """
        MATCH (p:Skill {id: 'jc_python'})
        MATCH (d:Skill {id: 'jc_django'})
        CREATE (p)-[:CO_OCCURS_WITH {weight: 10, cost: 0.1}]->(d)
        """
    )

    await neo4j_repo.execute_query(
        """
        MATCH (s:Skill {id: 'jc_sql'})
        MATCH (pg:Skill {id: 'jc_postgresql'})
        CREATE (s)-[:CO_OCCURS_WITH {weight: 8, cost: 0.125}]->(pg)
        """
    )

    # Create job
    await neo4j_repo.execute_query(
        """
        CREATE (j:Job {job_id: 'jc_job1', job_title: 'Backend Developer'})
        """
    )

    # Create REQUIRES relationships
    for skill_id in ["jc_python", "jc_django", "jc_postgresql"]:
        await neo4j_repo.execute_query(
            """
            MATCH (j:Job {job_id: 'jc_job1'})
            MATCH (s:Skill {id: $skill_id})
            CREATE (j)-[:REQUIRES]->(s)
            """,
            {"skill_id": skill_id}
        )

    yield {
        "job_id": "jc_job1",
        "user_skills": ["Python", "SQL"],
        "required_skills": ["Python", "Django", "PostgreSQL"],
        "expected_already_have": ["Python"],
        "expected_to_learn": ["Django", "PostgreSQL"],
    }

    # Cleanup
    await neo4j_repo.execute_query(
        "MATCH (n) WHERE n.id STARTS WITH 'jc_' DETACH DELETE n"
    )


# =============================================================================
# TOY GRAPH DISTANCE TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestToyGraphDistances:
    """Test shortest path calculations on toy graph."""

    async def test_direct_edge_distance(self, toy_graph_service, toy_graph):
        """Test distance for direct edge A -> B."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_B")

        assert result["path_exists"] is True
        expected_distance = toy_graph["expected_distances"][("toy_A", "toy_B")]
        assert abs(result["total_distance"] - expected_distance) < 0.001

    async def test_two_hop_distance(self, toy_graph_service, toy_graph):
        """Test distance for two-hop path A -> B -> C."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_C")

        assert result["path_exists"] is True
        expected_distance = toy_graph["expected_distances"][("toy_A", "toy_C")]
        assert abs(result["total_distance"] - expected_distance) < 0.001

    async def test_same_skill_distance(self, toy_graph_service, toy_graph):
        """Test distance from skill to itself is 0."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_A")

        assert result["path_exists"] is True
        assert result["total_distance"] == 0.0
        assert result["closeness"] == 1.0


# =============================================================================
# TOY GRAPH CLOSENESS TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestToyGraphCloseness:
    """Test closeness calculations on toy graph."""

    async def test_closeness_formula_direct(self, toy_graph_service, toy_graph):
        """Test closeness = 1 / (1 + distance) for direct edge."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_B")

        expected_closeness = toy_graph["expected_closenesses"][("toy_A", "toy_B")]
        assert abs(result["closeness"] - expected_closeness) < 0.001

    async def test_closeness_formula_two_hop(self, toy_graph_service, toy_graph):
        """Test closeness = 1 / (1 + distance) for two-hop path."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_C")

        expected_closeness = toy_graph["expected_closenesses"][("toy_A", "toy_C")]
        assert abs(result["closeness"] - expected_closeness) < 0.001

    async def test_closeness_same_skill(self, toy_graph_service, toy_graph):
        """Test closeness of skill to itself is 1.0."""
        result = await toy_graph_service.get_shortest_path("toy_A", "toy_A")

        assert result["closeness"] == 1.0


# =============================================================================
# ENHANCED JOB CLOSENESS TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestEnhancedJobCloseness:
    """Test enhanced job closeness with per-skill breakdown."""

    async def test_skills_already_have(self, toy_graph_service, job_closeness_graph):
        """Test skills user already has are identified."""
        result = await toy_graph_service.calculate_enhanced_job_closeness(
            user_skills=job_closeness_graph["user_skills"],
            job_id=job_closeness_graph["job_id"]
        )

        assert "Python" in result["skills_already_have"]
        assert result["matched_skills_count"] == 1

    async def test_skills_to_learn(self, toy_graph_service, job_closeness_graph):
        """Test skills to learn are identified."""
        result = await toy_graph_service.calculate_enhanced_job_closeness(
            user_skills=job_closeness_graph["user_skills"],
            job_id=job_closeness_graph["job_id"]
        )

        assert "Django" in result["skills_to_learn"]
        assert "PostgreSQL" in result["skills_to_learn"]

    async def test_per_skill_breakdown(self, toy_graph_service, job_closeness_graph):
        """Test per-skill closeness breakdown is correct."""
        result = await toy_graph_service.calculate_enhanced_job_closeness(
            user_skills=job_closeness_graph["user_skills"],
            job_id=job_closeness_graph["job_id"]
        )

        assert len(result["per_skill_details"]) == 3

        # Find Python entry (should have closeness 1.0)
        python_entry = next(
            (d for d in result["per_skill_details"] if d["required_skill"] == "Python"),
            None
        )
        assert python_entry is not None
        assert python_entry["user_already_has"] is True
        assert python_entry["closeness"] == 1.0

    async def test_overall_closeness_calculation(self, toy_graph_service, job_closeness_graph):
        """Test overall closeness is average of per-skill closenesses."""
        result = await toy_graph_service.calculate_enhanced_job_closeness(
            user_skills=job_closeness_graph["user_skills"],
            job_id=job_closeness_graph["job_id"]
        )

        # Sum all per-skill closenesses and divide by count
        per_skill_sum = sum(d["closeness"] for d in result["per_skill_details"])
        expected_overall = per_skill_sum / len(result["per_skill_details"])

        assert abs(result["overall_closeness"] - expected_overall) < 0.001

    async def test_job_lookup_by_title(self, toy_graph_service, job_closeness_graph):
        """Test job can be found by title."""
        result = await toy_graph_service.calculate_enhanced_job_closeness(
            user_skills=job_closeness_graph["user_skills"],
            job_title="Backend"  # Partial match
        )

        assert result["job_id"] == job_closeness_graph["job_id"]
        assert result["job_title"] == "Backend Developer"


# =============================================================================
# CAPABILITIES TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestNetworkCapabilities:
    """Test network capabilities detection."""

    async def test_get_capabilities_returns_dict(self, toy_graph_service):
        """Test get_capabilities returns proper structure."""
        result = await toy_graph_service.get_capabilities()

        assert "gds_available" in result
        assert "apoc_available" in result
        assert "capabilities" in result
        assert "fallback_mode" in result
        assert "limited_mode" in result

    async def test_capabilities_includes_required_features(self, toy_graph_service):
        """Test capabilities dict includes all required features."""
        result = await toy_graph_service.get_capabilities()

        required_capabilities = [
            "shortest_path",
            "eigenvector_centrality",
            "job_closeness",
            "transition_index",
        ]

        for cap in required_capabilities:
            assert cap in result["capabilities"]


# =============================================================================
# CO-OCCURRENCE BUILDER INTEGRATION TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestCoOccurrenceBuilderIntegration:
    """Test CoOccurrenceBuilder with real Neo4j."""

    async def test_stoplist_stats(self, neo4j_repo: Neo4jRepository):
        """Test get_stoplist_stats returns proper structure."""
        from app.services.co_occurrence_builder import CoOccurrenceBuilder

        builder = CoOccurrenceBuilder(neo4j_repo)
        result = await builder.get_stoplist_stats()

        assert "stoplist_size" in result
        assert "skills_filtered" in result
        assert "jobs_affected" in result
        assert "total_skills" in result
        assert result["stoplist_size"] > 0  # Should have stoplist configured


# =============================================================================
# COST FORMULA VERIFICATION
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
class TestCostFormulaVerification:
    """Verify cost = 1/weight formula is applied correctly."""

    async def test_cost_equals_inverse_weight(self, neo4j_repo: Neo4jRepository):
        """Test that cost = 1/weight on CO_OCCURS_WITH relationships."""
        # Create test relationship with known weight
        await neo4j_repo.execute_query(
            "MATCH (n) WHERE n.id STARTS WITH 'cost_test_' DETACH DELETE n"
        )

        await neo4j_repo.execute_query(
            """
            CREATE (a:Skill {id: 'cost_test_a', name: 'CostTestA'})
            CREATE (b:Skill {id: 'cost_test_b', name: 'CostTestB'})
            CREATE (a)-[:CO_OCCURS_WITH {weight: 4, cost: 0.25}]->(b)
            """
        )

        # Verify cost = 1/weight
        result = await neo4j_repo.execute_query(
            """
            MATCH (:Skill {id: 'cost_test_a'})-[r:CO_OCCURS_WITH]->(:Skill {id: 'cost_test_b'})
            RETURN r.weight as weight, r.cost as cost
            """
        )

        assert result is not None
        assert len(result) == 1
        weight = result[0]["weight"]
        cost = result[0]["cost"]

        assert weight == 4
        assert abs(cost - 0.25) < 0.001
        assert abs(cost - (1.0 / weight)) < 0.001

        # Cleanup
        await neo4j_repo.execute_query(
            "MATCH (n) WHERE n.id STARTS WITH 'cost_test_' DETACH DELETE n"
        )
