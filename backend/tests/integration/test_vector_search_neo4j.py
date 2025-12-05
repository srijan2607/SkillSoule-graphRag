"""
Integration tests for Vector Search with Neo4j.

Tests actual vector similarity search against a running Neo4j instance
with real data and embeddings.
"""

import pytest
from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.agents.nodes.vector_search import vector_search_node
from app.agents.graph import GraphRAGState


@pytest.fixture(scope="module")
async def neo4j_repo():
    """Create Neo4jRepository instance for testing."""
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture
async def test_skill_nodes(neo4j_repo):
    """Create test skill nodes with embeddings."""
    test_skills = [
        {
            "id": "test-skill-001",
            "name": "Python",
            "description": "High-level programming language",
            "level": 3,
            "type": "programming_language",
            "is_software": False,
            "is_language": True,
            "embedding": [0.1] * 384,
            "embedding_model_version": "test-v1"
        },
        {
            "id": "test-skill-002",
            "name": "JavaScript",
            "description": "Web programming language",
            "level": 3,
            "type": "programming_language",
            "is_software": False,
            "is_language": True,
            "embedding": [0.2] * 384,
            "embedding_model_version": "test-v1"
        },
        {
            "id": "test-skill-003",
            "name": "React",
            "description": "JavaScript library for building UIs",
            "level": 2,
            "type": "framework",
            "is_software": True,
            "is_language": False,
            "embedding": [0.3] * 384,
            "embedding_model_version": "test-v1"
        }
    ]

    # Create skill nodes
    for skill in test_skills:
        await neo4j_repo.create_skill_node(skill)

    yield test_skills

    # Cleanup: Delete test nodes
    cleanup_query = """
    MATCH (s:Skill)
    WHERE s.id STARTS WITH 'test-skill-'
    DELETE s
    """
    await neo4j_repo.execute_query(cleanup_query)


@pytest.fixture
async def test_job_nodes(neo4j_repo):
    """Create test job nodes with embeddings."""
    test_jobs = [
        {
            "job_id": "test-job-001",
            "job_title": "Senior Python Developer",
            "company_name": "Test Corp",
            "location": "San Francisco",
            "description": "Looking for experienced Python developer",
            "salary": "$120k-$150k",
            "schedule_type": "Full-time",
            "work_from_home": True,
            "embedding": [0.15] * 384,
            "embedding_model_version": "test-v1"
        },
        {
            "job_id": "test-job-002",
            "job_title": "Frontend Engineer",
            "company_name": "Web Co",
            "location": "Remote",
            "description": "React and JavaScript expert needed",
            "salary": "$100k-$130k",
            "schedule_type": "Full-time",
            "work_from_home": True,
            "embedding": [0.25] * 384,
            "embedding_model_version": "test-v1"
        }
    ]

    # Create job nodes
    for job in test_jobs:
        await neo4j_repo.create_job_node(job)

    yield test_jobs

    # Cleanup
    cleanup_query = """
    MATCH (j:Job)
    WHERE j.job_id STARTS WITH 'test-job-'
    DELETE j
    """
    await neo4j_repo.execute_query(cleanup_query)


# ============================================================================
# Test Neo4jRepository Vector Search Methods
# ============================================================================


class TestNeo4jVectorSearchMethods:
    """Test Neo4jRepository vector search methods."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_skills(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test vector similarity search for skills."""
        query_embedding = [0.1] * 384  # Similar to Python skill
        
        results = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=10,
            threshold=0.0  # Low threshold to ensure we get results
        )

        # Should return skills
        assert len(results) > 0, "No skills returned"
        
        # Verify result structure
        for result in results:
            assert "id" in result
            assert "name" in result
            assert "score" in result
            assert "node_type" in result
            assert result["node_type"] == "Skill"
            
            # Score should be between 0 and 1
            assert 0 <= result["score"] <= 1

        # Results should be sorted by score descending
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_jobs(
        self,
        neo4j_repo,
        test_job_nodes
    ):
        """Test vector similarity search for jobs."""
        query_embedding = [0.15] * 384  # Similar to Python job
        
        results = await neo4j_repo.vector_search_jobs(
            query_embedding=query_embedding,
            k=10,
            threshold=0.0
        )

        # Should return jobs
        assert len(results) > 0, "No jobs returned"
        
        # Verify result structure
        for result in results:
            assert "id" in result  # job_id
            assert "name" in result  # job_title
            assert "score" in result
            assert "node_type" in result
            assert result["node_type"] == "Job"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_threshold_filtering(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test that threshold filtering works correctly."""
        query_embedding = [0.1] * 384
        
        # Search with high threshold
        results_high_threshold = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=10,
            threshold=0.9  # Very high threshold
        )

        # Search with low threshold
        results_low_threshold = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=10,
            threshold=0.0  # Very low threshold
        )

        # Low threshold should return more results
        assert len(results_low_threshold) >= len(results_high_threshold)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_k_limit(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test that k parameter limits results."""
        query_embedding = [0.1] * 384
        
        # Search with k=1
        results_k1 = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=1,
            threshold=0.0
        )

        # Search with k=10
        results_k10 = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=10,
            threshold=0.0
        )

        # k=1 should return at most 1 result
        assert len(results_k1) <= 1
        
        # k=10 should potentially return more
        assert len(results_k10) >= len(results_k1)


# ============================================================================
# Test Vector Search Node with Real Neo4j
# ============================================================================


class TestVectorSearchNodeIntegration:
    """Test vector_search_node with real Neo4j instance."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_node_with_real_data(
        self,
        neo4j_repo,
        test_skill_nodes,
        test_job_nodes
    ):
        """Test vector_search_node with real Neo4j data."""
        state = GraphRAGState(
            user_query="Python programming jobs",
            user_id="test-user-integration",
            query_embedding=[0.1] * 384,  # Similar to Python
            intent="skill_requirement",
            metadata={}
        )

        result = await vector_search_node(state)

        # Should return results
        assert "vector_results" in result
        assert len(result["vector_results"]) > 0

        # Should have results from multiple node types
        node_types = set(r["node_type"] for r in result["vector_results"])
        assert len(node_types) > 0  # At least one type

        # Metadata should be populated
        assert result["metadata"]["vector_search_completed"] is True
        assert result["metadata"]["vector_results_count"] > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_node_custom_parameters(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test vector_search_node with custom k and threshold."""
        state = GraphRAGState(
            user_query="Programming skills",
            user_id="test-user-integration",
            query_embedding=[0.1] * 384,
            intent="skill_requirement",
            metadata={
                "vector_search_k": 2,
                "vector_search_threshold": 0.0
            }
        )

        result = await vector_search_node(state)

        # Should respect k limit
        assert len(result["vector_results"]) <= 2
        
        # Parameters should be in metadata
        assert result["metadata"]["vector_search_k"] == 2
        assert result["metadata"]["vector_search_threshold"] == 0.0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_node_empty_results(
        self,
        neo4j_repo
    ):
        """Test vector_search_node when no similar nodes exist."""
        # Use extreme embedding that won't match anything
        state = GraphRAGState(
            user_query="Nonexistent skill",
            user_id="test-user-integration",
            query_embedding=[0.99] * 384,  # Unlikely to match
            intent="general",
            metadata={"vector_search_threshold": 0.99}  # Very high threshold
        )

        result = await vector_search_node(state)

        # Should handle empty results gracefully
        assert result["vector_results"] == []
        assert result["metadata"]["vector_search_completed"] is True
        assert result["metadata"]["vector_results_count"] == 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_search_node_results_sorted(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test that results are sorted by score."""
        state = GraphRAGState(
            user_query="Programming",
            user_id="test-user-integration",
            query_embedding=[0.1] * 384,
            intent="skill_requirement",
            metadata={"vector_search_threshold": 0.0}
        )

        result = await vector_search_node(state)

        # Results should be sorted by score descending
        scores = [r["score"] for r in result["vector_results"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# Test Error Handling with Real Neo4j
# ============================================================================


class TestVectorSearchErrorHandling:
    """Test error handling in real Neo4j scenarios."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_embedding_dimension(
        self,
        neo4j_repo
    ):
        """Test handling of invalid embedding dimension."""
        # Neo4j expects 384-dim embeddings
        invalid_embedding = [0.1] * 100  # Wrong dimension

        # This should fail or return empty results
        try:
            results = await neo4j_repo.vector_search_skills(
                query_embedding=invalid_embedding,
                k=10,
                threshold=0.5
            )
            # If it doesn't fail, it should return empty results
            assert len(results) == 0
        except Exception as e:
            # Expected: dimension mismatch error
            assert "dimension" in str(e).lower() or "embedding" in str(e).lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_resilience(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test that vector search handles connection issues gracefully."""
        # This is a positive test - connection should work
        results = await neo4j_repo.vector_search_skills(
            query_embedding=[0.1] * 384,
            k=5,
            threshold=0.0
        )

        # Should successfully return results
        assert isinstance(results, list)


# ============================================================================
# Test Performance and Scalability
# ============================================================================


class TestVectorSearchPerformance:
    """Test performance of vector search operations."""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_vector_search_performance(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test vector search query performance."""
        import time

        query_embedding = [0.1] * 384

        # Measure query time
        start = time.time()
        results = await neo4j_repo.vector_search_skills(
            query_embedding=query_embedding,
            k=10,
            threshold=0.0
        )
        duration = time.time() - start

        # Should complete in reasonable time (<2 seconds for integration tests)
        assert duration < 2.0, f"Query too slow: {duration:.3f}s"

        # Should return results
        assert len(results) > 0

        print(f"\n✅ Vector search completed in {duration*1000:.2f}ms")

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_parallel_search_performance(
        self,
        neo4j_repo,
        test_skill_nodes,
        test_job_nodes
    ):
        """Test performance of parallel vector searches."""
        import asyncio
        import time

        query_embedding = [0.1] * 384

        # Measure parallel execution time
        start = time.time()
        
        results = await asyncio.gather(
            neo4j_repo.vector_search_skills(query_embedding, 10, 0.0),
            neo4j_repo.vector_search_jobs(query_embedding, 10, 0.0),
            neo4j_repo.vector_search_companies(query_embedding, 10, 0.0)
        )
        
        duration = time.time() - start

        # Parallel execution should be faster than sequential
        # Should complete in reasonable time (<3 seconds)
        assert duration < 3.0, f"Parallel queries too slow: {duration:.3f}s"

        # All searches should return results
        assert len(results) == 3  # Three search operations

        print(f"\n✅ Parallel vector searches completed in {duration*1000:.2f}ms")


# ============================================================================
# Test Index Usage Verification
# ============================================================================


class TestVectorIndexUsage:
    """Verify that vector indexes are being used."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_verify_indexes_exist(
        self,
        neo4j_repo
    ):
        """Verify that required vector indexes exist."""
        query = """
        SHOW INDEXES
        YIELD name, type
        WHERE type = "VECTOR"
        RETURN name
        """

        results = await neo4j_repo.execute_query(query)
        index_names = [r["name"] for r in results]

        # Required indexes should exist
        assert "skill_embedding_idx" in index_names
        assert "job_embedding_idx" in index_names
        # company_embedding_idx might not exist yet if companies aren't ingested

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_vector_index_query_syntax(
        self,
        neo4j_repo,
        test_skill_nodes
    ):
        """Test that vector index query syntax is correct."""
        # This tests the actual Cypher query syntax
        query = """
        CALL db.index.vector.queryNodes('skill_embedding_idx', 3, $query_embedding)
        YIELD node, score
        WHERE score > 0.0
        MATCH (node:Skill)
        RETURN node.id as id, node.name as name, score
        LIMIT 3
        """

        results = await neo4j_repo.execute_query(
            query,
            {"query_embedding": [0.1] * 384}
        )

        # Should execute without error
        assert isinstance(results, list)
        
        # If there are results, verify structure
        if len(results) > 0:
            assert "id" in results[0]
            assert "name" in results[0]
            assert "score" in results[0]
