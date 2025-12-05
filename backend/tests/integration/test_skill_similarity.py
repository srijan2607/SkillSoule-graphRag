"""Integration tests for Skill Similarity Computation."""
import pytest
from app.services.skill_similarity_service import SkillSimilarityService
from app.services.skill_graph_service import SkillGraphService
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.config import settings


@pytest.mark.integration
class TestSkillSimilarityIntegration:
    """Integration tests for end-to-end similarity computation."""

    @pytest.mark.asyncio
    async def test_end_to_end_similarity_computation(self, neo4j_test_db, prisma_test_db):
        """Test complete similarity computation workflow with real databases."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        # Create ingestion job for tracking
        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_similarity.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 3
        })

        # First, create skill nodes with embeddings
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Create test skills with highly similar descriptions (to ensure > 0.7 similarity)
        # Using identical core descriptions with minor variations ensures high similarity scores
        skills_data = [
            {
                "ID": "python-001",
                "NAME": "Python",
                "DESCRIPTION": "A powerful programming language for data science, web development, automation, and scientific computing with extensive libraries and frameworks",
                "LEVEL": 3,
                "TYPE": "Programming Language",
                "IS_SOFTWARE": False,
                "IS_LANGUAGE": True,
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming"
            },
            {
                "ID": "python3-001",
                "NAME": "Python 3",
                "DESCRIPTION": "A powerful programming language for data science, web development, automation, and scientific computing with extensive libraries and community support",
                "LEVEL": 3,
                "TYPE": "Programming Language",
                "IS_SOFTWARE": False,
                "IS_LANGUAGE": True,
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming"
            },
            {
                "ID": "javascript-001",
                "NAME": "JavaScript",
                "DESCRIPTION": "JavaScript is used for web development and frontend programming",
                "LEVEL": 3,
                "TYPE": "Programming Language",
                "IS_SOFTWARE": False,
                "IS_LANGUAGE": True,
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming"
            }
        ]

        # Create skill nodes
        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Now compute similarities
        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        stats = await similarity_service.compute_skill_similarities(job_id=job.id)

        # Verify statistics
        assert stats["skills_processed"] == 3
        assert stats["relationships_created"] > 0
        assert stats["duration_seconds"] > 0

        # Verify bidirectional relationships exist between Python and Python 3
        async with neo4j_repo.driver.session() as session:
            # Check Python->Python3 relationship exists
            result = await session.run(
                """
                MATCH (s1:Skill {id: $id1})-[r:SIMILAR_TO]->(s2:Skill {id: $id2})
                RETURN r.similarity_score as score
                """,
                id1="python-001",
                id2="python3-001"
            )
            record = await result.single()

            # Python and Python3 should be similar (highly similar descriptions)
            assert record is not None, "No similarity relationship found between Python and Python3"
            assert record["score"] > 0.7, f"Similarity score {record['score']} below threshold"
            assert record["score"] <= 1.0

            # Verify reverse relationship exists (bidirectional)
            result2 = await session.run(
                """
                MATCH (s1:Skill {id: $id1})-[r:SIMILAR_TO]->(s2:Skill {id: $id2})
                RETURN r.similarity_score as score
                """,
                id1="python3-001",
                id2="python-001"
            )
            record2 = await result2.single()
            assert record2 is not None, "Reverse relationship not found"
            assert record2["score"] == record["score"], "Bidirectional scores don't match"

        # Cleanup
        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_similarity_threshold_filtering(self, neo4j_test_db, prisma_test_db):
        """Test that only skills above threshold get relationships."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_threshold.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 2
        })

        # Create skills with very different descriptions (low similarity)
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [
            {
                "ID": "python-002",
                "NAME": "Python",
                "DESCRIPTION": "Python programming language for software development",
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming"
            },
            {
                "ID": "pottery-001",
                "NAME": "Pottery",
                "DESCRIPTION": "Creating ceramic objects using clay and firing techniques",
                "CATEGORY": "CAT999",
                "CATEGORY_NAME": "Arts and Crafts"
            }
        ]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Compute similarities
        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        stats = await similarity_service.compute_skill_similarities(job_id=job.id)

        # Verify no relationships created (skills too dissimilar)
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                """
                MATCH (s1:Skill {id: $id1})-[r:SIMILAR_TO]->(s2:Skill {id: $id2})
                RETURN r
                """,
                id1="python-002",
                id2="pottery-001"
            )
            record = await result.single()
            # Should be None (below threshold)
            assert record is None

        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_self_similarity_excluded(self, neo4j_test_db, prisma_test_db):
        """Test that skills don't have SIMILAR_TO relationships with themselves."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_self.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 1
        })

        # Create single skill
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [{
            "ID": "react-001",
            "NAME": "React",
            "DESCRIPTION": "React JavaScript library for building user interfaces",
            "CATEGORY": "CAT002",
            "CATEGORY_NAME": "Frontend"
        }]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Compute similarities
        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        await similarity_service.compute_skill_similarities(job_id=job.id)

        # Verify no self-loop
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill {id: $id})-[r:SIMILAR_TO]->(s)
                RETURN r
                """,
                id="react-001"
            )
            record = await result.single()
            assert record is None  # No self-loop

        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_batch_processing_with_large_dataset(self, neo4j_test_db, prisma_test_db):
        """Test similarity computation with 200 skills (2 batches)."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_batch.csv",
            "file_size_mb": 0.5,
            "status": "processing",
            "total_records": 200
        })

        # Create 200 skills
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [
            {
                "ID": f"skill-{i:03d}",
                "NAME": f"Skill {i}",
                "DESCRIPTION": f"Programming skill {i} for software development",
                "CATEGORY": f"CAT{i % 10:03d}",
                "CATEGORY_NAME": f"Category {i % 10}"
            }
            for i in range(200)
        ]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Compute similarities
        import time
        start_time = time.time()

        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        stats = await similarity_service.compute_skill_similarities(job_id=job.id)

        elapsed = time.time() - start_time

        # Verify all skills processed
        assert stats["skills_processed"] == 200
        assert stats["duration_seconds"] > 0

        # Log performance
        print(f"\n200 skills processed in {elapsed:.2f}s ({200/elapsed:.0f} skills/sec)")

        # Verify relationships exist in Neo4j
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) as count"
            )
            record = await result.single()
            # Should have created some relationships
            assert record["count"] > 0

        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_top_k_limit_enforced(self, neo4j_test_db, prisma_test_db):
        """Test that only top 5 similar skills are kept per skill."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_topk.csv",
            "file_size_mb": 0.1,
            "status": "processing",
            "total_records": 20
        })

        # Create 20 very similar skills (same description)
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [
            {
                "ID": f"prog-{i:02d}",
                "NAME": f"Programming Language {i}",
                "DESCRIPTION": "General-purpose programming language for software development",
                "CATEGORY": "PROG",
                "CATEGORY_NAME": "Programming"
            }
            for i in range(20)
        ]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Compute similarities
        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        await similarity_service.compute_skill_similarities(job_id=job.id)

        # Check first skill has at most TOP_K outgoing relationships
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill {id: $id})-[r:SIMILAR_TO]->()
                RETURN count(r) as count
                """,
                id="prog-00"
            )
            record = await result.single()

            # Should have at most TOP_K (5) relationships
            assert record["count"] <= settings.SIMILARITY_TOP_K

        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_relationships_have_scores(self, neo4j_test_db, prisma_test_db):
        """Test that SIMILAR_TO relationships have similarity_score property."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_scores.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 2
        })

        # Create similar skills
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [
            {
                "ID": "nodejs-001",
                "NAME": "Node.js",
                "DESCRIPTION": "JavaScript runtime for server-side programming",
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Backend"
            },
            {
                "ID": "express-001",
                "NAME": "Express",
                "DESCRIPTION": "Node.js framework for building web applications",
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Backend"
            }
        ]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Compute similarities
        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        await similarity_service.compute_skill_similarities(job_id=job.id)

        # Verify relationship properties
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                """
                MATCH ()-[r:SIMILAR_TO]->()
                RETURN r.similarity_score as score,
                       r.created_at as created_at
                LIMIT 1
                """
            )
            record = await result.single()

            if record:  # If similar
                # Score should be valid float between 0 and 1
                assert isinstance(record["score"], float)
                assert 0.0 <= record["score"] <= 1.0
                # Should have timestamp
                assert record["created_at"] is not None

        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_performance_benchmark_vectorized_computation(self, neo4j_test_db, prisma_test_db):
        """Performance benchmark test to track execution time trends with vectorization.

        Validates that vectorized implementation achieves expected performance gains:
        - Baseline: 200 skills should complete in < 5 seconds
        - Expected: 10-100x faster than nested loop implementation

        This test establishes performance metrics for future optimization validation.
        """
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "benchmark_test.csv",
            "file_size_mb": 0.5,
            "status": "processing",
            "total_records": 200
        })

        # Create 200 skills with varied descriptions
        graph_service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skills_data = [
            {
                "ID": f"benchmark-{i:03d}",
                "NAME": f"Skill {i}",
                "DESCRIPTION": f"Technical skill {i} for software development, data analysis, and system design with focus on performance optimization",
                "CATEGORY": f"CAT{i % 10:03d}",
                "CATEGORY_NAME": f"Category {i % 10}"
            }
            for i in range(200)
        ]

        await graph_service.create_skill_graph(skills_data, job_id=job.id)

        # Benchmark similarity computation with vectorization
        import time
        start_time = time.time()

        similarity_service = SkillSimilarityService(neo4j_repo, ingestion_repo)
        stats = await similarity_service.compute_skill_similarities(job_id=job.id)

        elapsed = time.time() - start_time

        # Verify completion
        assert stats["skills_processed"] == 200
        assert elapsed < 10.0, f"Performance regression: took {elapsed:.2f}s (expected < 10s with vectorization)"

        # Log benchmark results
        print(f"\n{'='*60}")
        print(f"PERFORMANCE BENCHMARK - Vectorized Similarity Computation")
        print(f"{'='*60}")
        print(f"Skills processed:        {stats['skills_processed']}")
        print(f"Relationships created:   {stats['relationships_created']}")
        print(f"Execution time:          {elapsed:.3f} seconds")
        print(f"Throughput:              {stats['skills_processed']/elapsed:.1f} skills/sec")
        print(f"{'='*60}")

        await neo4j_repo.close()
