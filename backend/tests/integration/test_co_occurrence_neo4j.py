"""
Integration tests for CoOccurrenceBuilder with real Neo4j database.

Tests actual co-occurrence relationship creation and querying
with seeded Neo4j data.

Reference: Network Math Implementation - Phase 1 (01-DATA-LAYER.md)
"""

import pytest
from app.services.co_occurrence_builder import CoOccurrenceBuilder


# ============================================================================
# Neo4j Test Data Setup
# ============================================================================


@pytest.fixture
async def seeded_neo4j_for_cooccurrence(neo4j_repo):
    """
    Seed Neo4j with test data for co-occurrence testing.

    Creates:
    - 6 Skills (Python, Django, FastAPI, PostgreSQL, Redis, Docker)
    - 4 Jobs with various skill requirements
    - REQUIRES relationships between jobs and skills

    Job-Skill Matrix:
    - Job1 (Backend Dev): Python, Django, PostgreSQL
    - Job2 (Python Dev): Python, FastAPI, PostgreSQL, Redis
    - Job3 (Full Stack): Python, Django, Redis, Docker
    - Job4 (DevOps): Docker, PostgreSQL, Redis

    Expected Co-occurrences (count >= 2):
    - Python-Django: 2 (Job1, Job3)
    - Python-PostgreSQL: 2 (Job1, Job2)
    - Python-Redis: 2 (Job2, Job3)
    - PostgreSQL-Redis: 2 (Job2, Job4)
    - Django-Redis: 1 (Job3) - Below threshold
    """
    async with neo4j_repo.driver.session() as session:
        # Create Skills
        await session.run(
            """
            CREATE (s1:Skill {id: 'skill_python', name: 'Python'})
            CREATE (s2:Skill {id: 'skill_django', name: 'Django'})
            CREATE (s3:Skill {id: 'skill_fastapi', name: 'FastAPI'})
            CREATE (s4:Skill {id: 'skill_postgresql', name: 'PostgreSQL'})
            CREATE (s5:Skill {id: 'skill_redis', name: 'Redis'})
            CREATE (s6:Skill {id: 'skill_docker', name: 'Docker'})

            // Create Jobs
            CREATE (j1:Job {job_id: 'job_001', job_title: 'Backend Developer'})
            CREATE (j2:Job {job_id: 'job_002', job_title: 'Python Developer'})
            CREATE (j3:Job {job_id: 'job_003', job_title: 'Full Stack Developer'})
            CREATE (j4:Job {job_id: 'job_004', job_title: 'DevOps Engineer'})

            // Job1 requirements
            CREATE (j1)-[:REQUIRES]->(s1)
            CREATE (j1)-[:REQUIRES]->(s2)
            CREATE (j1)-[:REQUIRES]->(s4)

            // Job2 requirements
            CREATE (j2)-[:REQUIRES]->(s1)
            CREATE (j2)-[:REQUIRES]->(s3)
            CREATE (j2)-[:REQUIRES]->(s4)
            CREATE (j2)-[:REQUIRES]->(s5)

            // Job3 requirements
            CREATE (j3)-[:REQUIRES]->(s1)
            CREATE (j3)-[:REQUIRES]->(s2)
            CREATE (j3)-[:REQUIRES]->(s5)
            CREATE (j3)-[:REQUIRES]->(s6)

            // Job4 requirements
            CREATE (j4)-[:REQUIRES]->(s4)
            CREATE (j4)-[:REQUIRES]->(s5)
            CREATE (j4)-[:REQUIRES]->(s6)
            """
        )

    yield neo4j_repo

    # Cleanup handled by neo4j_repo fixture


# ============================================================================
# Integration Tests: Build All
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceBuildAllIntegration:
    """Integration tests for build_all() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_build_all_creates_relationships(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() creates CO_OCCURS_WITH relationships."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        result = await builder.build_all(clear_existing=True)

        assert result["status"] == "success"
        assert result["relationships_created"] > 0

        # Verify relationships exist in database
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                "MATCH ()-[r:CO_OCCURS_WITH]-() RETURN count(r)/2 as count"
            )
            record = await verify_result.single()
            assert record["count"] > 0

    @pytest.mark.asyncio
    async def test_build_all_respects_min_weight(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() only creates relationships above min_weight threshold."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # All relationships should have weight >= 2
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                """
                MATCH ()-[r:CO_OCCURS_WITH]-()
                RETURN min(r.weight) as min_weight
                """
            )
            record = await verify_result.single()
            assert record["min_weight"] >= 2

    @pytest.mark.asyncio
    async def test_build_all_sets_weight_correctly(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() sets correct weight values."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # Check Python-Django weight (should be 2: Job1, Job3)
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                """
                MATCH (s1:Skill {id: 'skill_python'})-[r:CO_OCCURS_WITH]-(s2:Skill {id: 'skill_django'})
                RETURN r.weight as weight
                """
            )
            record = await verify_result.single()
            assert record is not None
            assert record["weight"] == 2

    @pytest.mark.asyncio
    async def test_build_all_sets_cost_as_inverse(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() sets cost = 1.0 / weight."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # Check cost is inverse of weight
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                """
                MATCH ()-[r:CO_OCCURS_WITH]-()
                WHERE abs(r.cost - (1.0 / r.weight)) > 0.001
                RETURN count(r) as invalid_costs
                """
            )
            record = await verify_result.single()
            assert record["invalid_costs"] == 0

    @pytest.mark.asyncio
    async def test_build_all_sets_timestamps(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() sets created_at and updated_at timestamps."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # All relationships should have timestamps
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                """
                MATCH ()-[r:CO_OCCURS_WITH]-()
                WHERE r.created_at IS NULL OR r.updated_at IS NULL
                RETURN count(r) as missing_timestamps
                """
            )
            record = await verify_result.single()
            assert record["missing_timestamps"] == 0

    @pytest.mark.asyncio
    async def test_build_all_clears_existing(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() clears existing relationships when requested."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        # First build
        await builder.build_all(clear_existing=True)

        # Get initial count
        stats1 = await builder.get_statistics()
        initial_count = stats1["total_co_occurrence_relationships"]

        # Second build with clear
        result = await builder.build_all(clear_existing=True)

        # Should have same count (not doubled)
        stats2 = await builder.get_statistics()
        assert stats2["total_co_occurrence_relationships"] == initial_count
        assert "relationships_deleted" in result

    @pytest.mark.asyncio
    async def test_build_all_without_clear_merges(self, seeded_neo4j_for_cooccurrence):
        """Test build_all() merges without clear (idempotent)."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        # First build
        await builder.build_all(clear_existing=True)
        stats1 = await builder.get_statistics()

        # Second build without clear
        await builder.build_all(clear_existing=False)
        stats2 = await builder.get_statistics()

        # Should have same count (MERGE is idempotent)
        assert stats2["total_co_occurrence_relationships"] == stats1["total_co_occurrence_relationships"]


# ============================================================================
# Integration Tests: Get Statistics
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceStatisticsIntegration:
    """Integration tests for get_statistics() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_get_statistics_returns_accurate_count(self, seeded_neo4j_for_cooccurrence):
        """Test get_statistics() returns accurate relationship count."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)
        stats = await builder.get_statistics()

        # Verify count matches direct query
        async with neo4j_repo.driver.session() as session:
            verify_result = await session.run(
                "MATCH ()-[r:CO_OCCURS_WITH]-() RETURN count(r)/2 as count"
            )
            record = await verify_result.single()
            assert stats["total_co_occurrence_relationships"] == record["count"]

    @pytest.mark.asyncio
    async def test_get_statistics_empty_graph(self, neo4j_repo):
        """Test get_statistics() handles empty graph."""
        builder = CoOccurrenceBuilder(neo4j_repo)

        stats = await builder.get_statistics()

        assert stats["total_co_occurrence_relationships"] == 0
        assert stats["average_weight"] == 0.0


# ============================================================================
# Integration Tests: Update For Job
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceUpdateForJobIntegration:
    """Integration tests for update_for_job() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_update_for_job_creates_relationships(self, seeded_neo4j_for_cooccurrence):
        """Test update_for_job() creates relationships for specific job."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 1  # Lower threshold for single job

        result = await builder.update_for_job("job_001")

        assert result["relationships_updated"] > 0

    @pytest.mark.asyncio
    async def test_update_for_job_updates_existing(self, seeded_neo4j_for_cooccurrence):
        """Test update_for_job() updates existing relationships correctly."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        # Build all first
        await builder.build_all(clear_existing=True)

        # Get weight before update
        async with neo4j_repo.driver.session() as session:
            before_result = await session.run(
                """
                MATCH (s1:Skill {id: 'skill_python'})-[r:CO_OCCURS_WITH]-(s2:Skill {id: 'skill_django'})
                RETURN r.weight as weight
                """
            )
            before_record = await before_result.single()
            initial_weight = before_record["weight"]

        # Update for job (should maintain same weight)
        await builder.update_for_job("job_001")

        # Weight should remain same
        async with neo4j_repo.driver.session() as session:
            after_result = await session.run(
                """
                MATCH (s1:Skill {id: 'skill_python'})-[r:CO_OCCURS_WITH]-(s2:Skill {id: 'skill_django'})
                RETURN r.weight as weight
                """
            )
            after_record = await after_result.single()
            assert after_record["weight"] == initial_weight


# ============================================================================
# Integration Tests: Get Top Co-occurrences
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceTopCooccurrencesIntegration:
    """Integration tests for get_top_co_occurrences() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_returns_sorted(self, seeded_neo4j_for_cooccurrence):
        """Test get_top_co_occurrences() returns results sorted by weight."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)
        results = await builder.get_top_co_occurrences("skill_python", limit=10)

        # Should return results
        assert len(results) > 0

        # Should be sorted by weight descending
        weights = [r["weight"] for r in results]
        assert weights == sorted(weights, reverse=True)

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_respects_limit(self, seeded_neo4j_for_cooccurrence):
        """Test get_top_co_occurrences() respects limit parameter."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)
        results = await builder.get_top_co_occurrences("skill_python", limit=2)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_unknown_skill(self, seeded_neo4j_for_cooccurrence):
        """Test get_top_co_occurrences() handles unknown skill gracefully."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)

        results = await builder.get_top_co_occurrences("nonexistent_skill")

        assert results == []


# ============================================================================
# Integration Tests: Create Indexes
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceIndexesIntegration:
    """Integration tests for create_indexes() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_create_indexes_succeeds(self, neo4j_repo):
        """Test create_indexes() creates indexes successfully."""
        builder = CoOccurrenceBuilder(neo4j_repo)

        result = await builder.create_indexes()

        # Should succeed or be partial (indexes might already exist)
        assert result["status"] in ["success", "partial"]

    @pytest.mark.asyncio
    async def test_create_indexes_idempotent(self, neo4j_repo):
        """Test create_indexes() is idempotent (can run multiple times)."""
        builder = CoOccurrenceBuilder(neo4j_repo)

        # Run twice
        result1 = await builder.create_indexes()
        result2 = await builder.create_indexes()

        # Both should succeed
        assert result1["status"] in ["success", "partial"]
        assert result2["status"] in ["success", "partial"]


# ============================================================================
# Integration Tests: Validate Data
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceValidateDataIntegration:
    """Integration tests for validate_data() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_validate_data_valid_after_build(self, seeded_neo4j_for_cooccurrence):
        """Test validate_data() returns valid after clean build."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)
        validation = await builder.validate_data()

        assert validation["is_valid"] is True
        assert len(validation["issues"]) == 0

    @pytest.mark.asyncio
    async def test_validate_data_empty_graph(self, neo4j_repo):
        """Test validate_data() handles empty graph."""
        builder = CoOccurrenceBuilder(neo4j_repo)

        validation = await builder.validate_data()

        assert validation["is_valid"] is True
        assert validation["total_relationships"] == 0


# ============================================================================
# Integration Tests: Relationship Properties
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceRelationshipPropertiesIntegration:
    """Integration tests verifying CO_OCCURS_WITH relationship properties."""

    @pytest.mark.asyncio
    async def test_relationship_is_undirected(self, seeded_neo4j_for_cooccurrence):
        """Test CO_OCCURS_WITH relationships are effectively undirected."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # Query both directions should return same relationship
        async with neo4j_repo.driver.session() as session:
            # Direction A -> B
            result1 = await session.run(
                """
                MATCH (s1:Skill {id: 'skill_python'})-[r:CO_OCCURS_WITH]-(s2:Skill {id: 'skill_django'})
                RETURN r.weight as weight
                """
            )
            record1 = await result1.single()

            # Direction B -> A (same query due to undirected pattern)
            result2 = await session.run(
                """
                MATCH (s1:Skill {id: 'skill_django'})-[r:CO_OCCURS_WITH]-(s2:Skill {id: 'skill_python'})
                RETURN r.weight as weight
                """
            )
            record2 = await result2.single()

            # Both queries should return same weight
            assert record1["weight"] == record2["weight"]

    @pytest.mark.asyncio
    async def test_no_duplicate_pairs(self, seeded_neo4j_for_cooccurrence):
        """Test no duplicate (A,B) and (B,A) relationships exist."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        await builder.build_all(clear_existing=True)

        # Check for duplicates
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                """
                MATCH (s1:Skill)-[r:CO_OCCURS_WITH]-(s2:Skill)
                WITH s1.id as a, s2.id as b, count(r) as cnt
                WHERE cnt > 1
                RETURN count(*) as duplicates
                """
            )
            record = await result.single()
            # Each undirected relationship is traversed twice (A-B and B-A)
            # but should only exist once in the database
            assert record["duplicates"] == 0


# ============================================================================
# Integration Tests: Clear Existing
# ============================================================================


@pytest.mark.integration
class TestCoOccurrenceClearExistingIntegration:
    """Integration tests for _clear_existing() with real Neo4j."""

    @pytest.mark.asyncio
    async def test_clear_existing_removes_all(self, seeded_neo4j_for_cooccurrence):
        """Test _clear_existing() removes all CO_OCCURS_WITH relationships."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        # Build relationships
        await builder.build_all(clear_existing=True)

        # Verify relationships exist
        stats_before = await builder.get_statistics()
        assert stats_before["total_co_occurrence_relationships"] > 0

        # Clear
        deleted = await builder._clear_existing()

        # Verify all removed
        stats_after = await builder.get_statistics()
        assert stats_after["total_co_occurrence_relationships"] == 0
        assert deleted > 0

    @pytest.mark.asyncio
    async def test_clear_existing_preserves_other_relationships(self, seeded_neo4j_for_cooccurrence):
        """Test _clear_existing() only removes CO_OCCURS_WITH, not REQUIRES."""
        neo4j_repo = seeded_neo4j_for_cooccurrence
        builder = CoOccurrenceBuilder(neo4j_repo)
        builder.min_weight = 2

        # Build co-occurrence relationships
        await builder.build_all(clear_existing=True)

        # Count REQUIRES before clear
        async with neo4j_repo.driver.session() as session:
            before_result = await session.run(
                "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
            )
            before_record = await before_result.single()
            requires_before = before_record["count"]

        # Clear CO_OCCURS_WITH
        await builder._clear_existing()

        # REQUIRES should still exist
        async with neo4j_repo.driver.session() as session:
            after_result = await session.run(
                "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
            )
            after_record = await after_result.single()
            requires_after = after_record["count"]

        assert requires_after == requires_before
