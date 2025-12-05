"""Integration tests for Skill Graph Construction."""
import pytest
from app.services.skill_graph_service import SkillGraphService
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.config import settings


@pytest.mark.integration
class TestSkillGraphConstruction:
    """Integration tests for end-to-end skill graph creation."""

    @pytest.mark.asyncio
    async def test_end_to_end_skill_graph_creation(self, neo4j_test_db, prisma_test_db):
        """Test complete skill graph creation workflow with real databases."""
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
            "file_name": "test_skills.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 2
        })

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Test data - Two skills with different categories
        skills_data = [
            {
                "ID": "python-001",
                "NAME": "Python",
                "LEVEL": 3,
                "TYPE": "Programming Language",
                "IS_SOFTWARE": False,
                "IS_LANGUAGE": True,
                "DESCRIPTION": "Python is a high-level programming language",
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming",
                "SUBCATEGORY": "SUB001",
                "SUBCATEGORY_NAME": "General Purpose"
            },
            {
                "ID": "javascript-001",
                "NAME": "JavaScript",
                "LEVEL": 3,
                "TYPE": "Programming Language",
                "IS_SOFTWARE": False,
                "IS_LANGUAGE": True,
                "DESCRIPTION": "JavaScript is used for web development",
                "CATEGORY": "CAT001",
                "CATEGORY_NAME": "Programming",
                "SUBCATEGORY": "SUB002",
                "SUBCATEGORY_NAME": "Web Development"
            }
        ]

        # Execute graph creation
        stats = await service.create_skill_graph(skills_data, job_id=job.id)

        # Verify statistics
        assert stats["skills_created"] == 2
        assert stats["categories_created"] >= 1  # At least one unique category
        assert stats["subcategories_created"] >= 2  # Two different subcategories
        assert stats["relationships_created"] >= 4  # 2 skills x 2 relationships minimum
        assert len(stats["errors"]) == 0

        # Verify Skill nodes exist in Neo4j
        async with neo4j_repo.driver.session() as session:
            # Check Python skill
            result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s",
                id="python-001"
            )
            record = await result.single()
            assert record is not None
            skill_node = dict(record["s"])
            assert skill_node["name"] == "python"  # Normalized to lowercase
            assert skill_node["level"] == 3
            assert skill_node["is_language"] is True
            assert len(skill_node["embedding"]) == 384  # 384-dimensional embedding

            # Check JavaScript skill
            result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s",
                id="javascript-001"
            )
            record = await result.single()
            assert record is not None
            skill_node = dict(record["s"])
            assert skill_node["name"] == "javascript"

        # Verify Category node
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH (c:Category {category_id: $id}) RETURN c",
                id="CAT001"
            )
            record = await result.single()
            assert record is not None
            category_node = dict(record["c"])
            assert category_node["category_name"] == "Programming"

        # Verify Subcategory nodes
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH (s:Subcategory) WHERE s.subcategory_id IN $ids RETURN count(s) as count",
                ids=["SUB001", "SUB002"]
            )
            record = await result.single()
            assert record["count"] == 2

        # Verify relationships exist
        async with neo4j_repo.driver.session() as session:
            # Python -> Category relationship
            result = await session.run(
                """
                MATCH (s:Skill {id: 'python-001'})-[r:BELONGS_TO_CATEGORY]->(c:Category {category_id: 'CAT001'})
                RETURN r
                """
            )
            record = await result.single()
            assert record is not None

            # Category -> Subcategory relationship
            result = await session.run(
                """
                MATCH (c:Category {category_id: 'CAT001'})-[r:CONTAINS]->(s:Subcategory {subcategory_id: 'SUB001'})
                RETURN r
                """
            )
            record = await result.single()
            assert record is not None

        # Cleanup
        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_merge_prevents_duplicates_on_reingestion(self, neo4j_test_db, prisma_test_db):
        """Test MERGE upsert prevents duplicate nodes on re-ingestion."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        skill_data = [{
            "ID": "react-001",
            "NAME": "React",
            "DESCRIPTION": "React JavaScript library",
            "LEVEL": 3,
            "TYPE": "Framework",
            "IS_SOFTWARE": True,
            "IS_LANGUAGE": False,
            "CATEGORY": "CAT002",
            "CATEGORY_NAME": "Frontend Frameworks"
        }]

        # Create ingestion job 1
        job1 = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_skills_first.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 1
        })

        # Ingest once
        stats1 = await service.create_skill_graph(skill_data, job_id=job1.id)
        assert stats1["skills_created"] == 1

        # Create ingestion job 2
        job2 = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_skills_second.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 1
        })

        # Ingest again (should update, not duplicate)
        stats2 = await service.create_skill_graph(skill_data, job_id=job2.id)
        assert stats2["skills_created"] == 1

        # Verify only ONE Skill node exists (no duplicates)
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH (s:Skill {id: 'react-001'}) RETURN count(s) as count"
            )
            record = await result.single()
            assert record["count"] == 1  # No duplicates

            # Verify only ONE Category node exists
            result = await session.run(
                "MATCH (c:Category {category_id: 'CAT002'}) RETURN count(c) as count"
            )
            record = await result.single()
            assert record["count"] == 1  # No duplicates

        # Cleanup
        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_batch_transaction_with_1000_skills(self, neo4j_test_db, prisma_test_db):
        """Test 1000-skill batch is processed in single transaction."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        # Create ingestion job
        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_1000_skills.csv",
            "file_size_mb": 1.0,
            "status": "processing",
            "total_records": 1000
        })

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Generate 1000 skills
        skills_data = [
            {
                "ID": f"skill-{i:04d}",
                "NAME": f"Skill {i}",
                "DESCRIPTION": f"Description for skill {i}",
                "LEVEL": (i % 5) + 1,  # Level 1-5
                "TYPE": "Test Type",
                "IS_SOFTWARE": i % 2 == 0,
                "IS_LANGUAGE": i % 2 == 1,
                "CATEGORY": f"CAT{i % 10:03d}",  # 10 categories
                "CATEGORY_NAME": f"Category {i % 10}",
                "SUBCATEGORY": f"SUB{i % 20:03d}",  # 20 subcategories
                "SUBCATEGORY_NAME": f"Subcategory {i % 20}"
            }
            for i in range(1000)
        ]

        # Execute
        import time
        start_time = time.time()
        stats = await service.create_skill_graph(skills_data, job_id=job.id)
        elapsed = time.time() - start_time

        # Verify all skills created
        assert stats["skills_created"] == 1000
        assert len(stats["errors"]) == 0

        # Log performance
        print(f"\n1000 skills processed in {elapsed:.2f}s ({1000/elapsed:.0f} skills/sec)")

        # Verify skills exist in Neo4j
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH (s:Skill) RETURN count(s) as count"
            )
            record = await result.single()
            assert record["count"] == 1000  # Exactly 1000 (clean test database)

        # Cleanup
        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_progress_tracking_updates_ingestion_job(self, neo4j_test_db, prisma_test_db):
        """Test progress tracking updates IngestionJob correctly."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        # Create ingestion job
        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_progress.csv",
            "file_size_mb": 0.5,
            "status": "processing",
            "total_records": 50,
            "processed_records": 0
        })

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Create 50 skills
        skills_data = [
            {
                "ID": f"prog-{i:03d}",
                "NAME": f"Programming Skill {i}",
                "DESCRIPTION": f"Test skill {i}",
                "CATEGORY": "PROG",
                "CATEGORY_NAME": "Programming"
            }
            for i in range(50)
        ]

        # Execute
        await service.create_skill_graph(skills_data, job_id=job.id)

        # Verify IngestionJob was updated with progress
        updated_job = await ingestion_repo.find_by_id(job.id)
        assert updated_job is not None
        assert updated_job.processed_records > 0  # Progress was tracked

        # Cleanup
        await neo4j_repo.close()

    @pytest.mark.asyncio
    async def test_empty_description_gets_zero_vector(self, neo4j_test_db, prisma_test_db):
        """Test skills with no description get zero vector embedding."""
        # Setup services
        embedding_service = EmbeddingService()
        neo4j_repo = Neo4jRepository(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD
        )
        await neo4j_repo.connect()

        ingestion_repo = IngestionRepository(prisma_test_db)

        # Create ingestion job
        job = await ingestion_repo.create({
            "user_id": "test-user",
            "file_type": "skills",
            "file_name": "test_empty_description.csv",
            "file_size_mb": 0.01,
            "status": "processing",
            "total_records": 1
        })

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Skill with no description or wiki extract
        skill_data = [{
            "ID": "empty-001",
            "NAME": "Empty Skill",
            "DESCRIPTION": "",
            "WIKI_EXTRACT": "",
            "CATEGORY": "TEST",
            "CATEGORY_NAME": "Test Category"
        }]

        # Execute
        stats = await service.create_skill_graph(skill_data, job_id=job.id)
        assert stats["skills_created"] == 1

        # Verify zero vector was stored
        async with neo4j_repo.driver.session() as session:
            result = await session.run(
                "MATCH (s:Skill {id: 'empty-001'}) RETURN s.embedding as embedding"
            )
            record = await result.single()
            assert record is not None
            embedding = record["embedding"]
            assert len(embedding) == 384
            assert all(v == 0.0 for v in embedding)  # All zeros

        # Cleanup
        await neo4j_repo.close()
