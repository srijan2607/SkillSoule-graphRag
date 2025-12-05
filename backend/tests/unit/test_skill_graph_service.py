"""Unit tests for SkillGraphService."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.skill_graph_service import SkillGraphService


class TestEmbeddingTextSelection:
    """Test embedding text selection logic."""

    def test_primary_description_field(self):
        """Test DESCRIPTION field is used when present (primary source)."""
        service = SkillGraphService(None, None, None)

        skill_row = {
            "ID": "1",
            "DESCRIPTION": "Python is a programming language",
            "WIKI_EXTRACT": "Python wiki text"
        }

        result = service._get_embedding_text(skill_row)
        assert result == "Python is a programming language"

    def test_secondary_wiki_extract_field(self):
        """Test WIKI_EXTRACT is used when DESCRIPTION is empty (secondary source)."""
        service = SkillGraphService(None, None, None)

        skill_row = {
            "ID": "2",
            "DESCRIPTION": "",
            "WIKI_EXTRACT": "Python wiki text"
        }

        result = service._get_embedding_text(skill_row)
        assert result == "Python wiki text"

    def test_empty_string_fallback(self):
        """Test empty string is returned when both fields are empty."""
        service = SkillGraphService(None, None, None)

        skill_row = {
            "ID": "3",
            "DESCRIPTION": "",
            "WIKI_EXTRACT": ""
        }

        result = service._get_embedding_text(skill_row)
        assert result == ""

    def test_whitespace_handling(self):
        """Test whitespace-only strings are treated as empty."""
        service = SkillGraphService(None, None, None)

        skill_row = {
            "ID": "4",
            "DESCRIPTION": "   ",
            "WIKI_EXTRACT": "Valid extract"
        }

        result = service._get_embedding_text(skill_row)
        assert result == "Valid extract"


class TestBatchProcessingLogic:
    """Test batch processing and transaction logic."""

    @pytest.mark.asyncio
    async def test_batch_size_calculation(self):
        """Test batch processing divides skills correctly."""
        # Mock dependencies
        embedding_service = AsyncMock()
        neo4j_repo = MagicMock()
        ingestion_repo = AsyncMock()

        # Setup mock driver and session
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        # New pattern: begin_transaction() returns awaitable that gives tx object
        mock_session.begin_transaction = AsyncMock(return_value=mock_tx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        neo4j_repo.driver = MagicMock()
        neo4j_repo.driver.session = MagicMock(return_value=mock_session)

        # Mock embedding service
        embedding_service.generate_batch_embeddings = AsyncMock(
            return_value=[
                {"embedding": [0.1] * 384, "model_version": "v1"}
                for _ in range(1000)
            ]
        )

        # Mock transaction methods
        mock_tx.run = AsyncMock()
        mock_tx.commit = AsyncMock()
        mock_tx.rollback = AsyncMock()

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Create 2500 skills (should create 3 batches: 1000, 1000, 500)
        skills_data = [
            {
                "ID": str(i),
                "NAME": f"Skill-{i}",
                "DESCRIPTION": f"Description for skill {i}"
            }
            for i in range(2500)
        ]

        # Process
        stats = await service.create_skill_graph(skills_data, job_id="test-job")

        # Verify batching - should have called session 3 times (3 batches)
        assert neo4j_repo.driver.session.call_count == 3
        assert stats["skills_created"] == 2500
        assert stats["errors"] == []

    @pytest.mark.asyncio
    async def test_batch_progress_tracking(self):
        """Test progress is updated after each batch."""
        # Mock dependencies
        embedding_service = AsyncMock()
        neo4j_repo = MagicMock()
        ingestion_repo = AsyncMock()

        # Setup mock driver and session
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        # New pattern: begin_transaction() returns awaitable that gives tx object
        mock_session.begin_transaction = AsyncMock(return_value=mock_tx)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        neo4j_repo.driver = MagicMock()
        neo4j_repo.driver.session = MagicMock(return_value=mock_session)

        # Mock embedding service
        embedding_service.generate_batch_embeddings = AsyncMock(
            return_value=[
                {"embedding": [0.1] * 384, "model_version": "v1"}
                for _ in range(100)
            ]
        )

        # Mock transaction methods
        mock_tx.run = AsyncMock()
        mock_tx.commit = AsyncMock()
        mock_tx.rollback = AsyncMock()

        service = SkillGraphService(embedding_service, neo4j_repo, ingestion_repo)

        # Create 150 skills (2 batches with BATCH_SIZE=1000, but will be 1 batch for 150 items)
        skills_data = [
            {
                "ID": str(i),
                "NAME": f"Skill-{i}",
                "DESCRIPTION": "Test"
            }
            for i in range(150)
        ]

        await service.create_skill_graph(skills_data, job_id="test-job-123")

        # Verify progress was updated
        ingestion_repo.update_progress.assert_called()


class TestSkillNodeCreation:
    """Test Skill node creation with all properties."""

    @pytest.mark.asyncio
    async def test_skill_node_merge_properties(self):
        """Test Skill node is created with all CSV properties."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        skill_row = {
            "ID": "python-001",
            "NAME": "Python",
            "LEVEL": 3,
            "TYPE": "programming_language",
            "IS_SOFTWARE": False,
            "IS_LANGUAGE": True,
            "DESCRIPTION": "High-level programming language",
            "VERSION": "3.11",
            "LATEST_VERSION": "3.12",
            "WIKI_LINK": "https://en.wikipedia.org/wiki/Python",
            "WIKI_EXTRACT": "Python is a language..."
        }

        embedding_data = {
            "embedding": [0.1] * 384,
            "model_version": "all-MiniLM-L6-v2:2024-01"
        }

        await service._create_skill_node(mock_tx, skill_row, embedding_data)

        # Verify MERGE query was executed
        mock_tx.run.assert_called_once()

        # Verify query parameters
        call_args = mock_tx.run.call_args
        assert call_args.kwargs["id"] == "python-001"
        assert call_args.kwargs["name"] == "Python"
        assert call_args.kwargs["level"] == 3
        assert call_args.kwargs["type"] == "programming_language"
        assert call_args.kwargs["is_software"] is False
        assert call_args.kwargs["is_language"] is True
        assert call_args.kwargs["embedding"] == [0.1] * 384
        assert call_args.kwargs["embedding_model_version"] == "all-MiniLM-L6-v2:2024-01"

    @pytest.mark.asyncio
    async def test_description_source_tracking(self):
        """Test description_source metadata is set correctly."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        # Case 1: Description source is CSV
        skill_with_description = {
            "ID": "1",
            "NAME": "Skill1",
            "DESCRIPTION": "From CSV",
            "WIKI_EXTRACT": ""
        }

        embedding_data = {"embedding": [0.1] * 384, "model_version": "v1"}

        await service._create_skill_node(mock_tx, skill_with_description, embedding_data)

        call_args = mock_tx.run.call_args
        assert call_args.kwargs["description_source"] == "csv_description"

        # Case 2: Description source is WIKI_EXTRACT
        mock_tx.reset_mock()

        skill_with_wiki = {
            "ID": "2",
            "NAME": "Skill2",
            "DESCRIPTION": "",
            "WIKI_EXTRACT": "From Wikipedia"
        }

        await service._create_skill_node(mock_tx, skill_with_wiki, embedding_data)

        call_args = mock_tx.run.call_args
        assert call_args.kwargs["description_source"] == "wiki_extract"


class TestCategorySubcategoryCreation:
    """Test Category and Subcategory node creation."""

    @pytest.mark.asyncio
    async def test_category_upsert_logic(self):
        """Test Category node uses MERGE to prevent duplicates."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        await service._create_category_node(
            mock_tx,
            category_id="CAT001",
            category_name="Programming"
        )

        mock_tx.run.assert_called_once()

        # Verify MERGE query contains ON CREATE and ON MATCH
        call_args = mock_tx.run.call_args
        query = call_args.args[0]
        assert "MERGE" in query
        assert "ON CREATE SET" in query
        assert "ON MATCH SET" in query
        assert call_args.kwargs["category_id"] == "CAT001"
        assert call_args.kwargs["category_name"] == "Programming"

    @pytest.mark.asyncio
    async def test_subcategory_upsert_logic(self):
        """Test Subcategory node uses MERGE to prevent duplicates."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        await service._create_subcategory_node(
            mock_tx,
            subcategory_id="SUB001",
            subcategory_name="Web Development"
        )

        mock_tx.run.assert_called_once()

        # Verify MERGE query
        call_args = mock_tx.run.call_args
        query = call_args.args[0]
        assert "MERGE" in query
        assert "ON CREATE SET" in query
        assert "ON MATCH SET" in query
        assert call_args.kwargs["subcategory_id"] == "SUB001"
        assert call_args.kwargs["subcategory_name"] == "Web Development"


class TestRelationshipCreation:
    """Test relationship creation logic."""

    @pytest.mark.asyncio
    async def test_all_relationships_created(self):
        """Test all three relationship types are created when both category and subcategory present."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        rel_count = await service._create_skill_relationships(
            mock_tx,
            skill_id="skill-001",
            category_id="CAT001",
            subcategory_id="SUB001"
        )

        # Should create 3 relationships:
        # 1. Skill -> Category
        # 2. Skill -> Subcategory
        # 3. Category -> Subcategory
        assert rel_count == 3
        assert mock_tx.run.call_count == 3

    @pytest.mark.asyncio
    async def test_partial_relationships(self):
        """Test only relevant relationships created when category/subcategory missing."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        # Only category provided
        rel_count = await service._create_skill_relationships(
            mock_tx,
            skill_id="skill-001",
            category_id="CAT001",
            subcategory_id=None
        )

        assert rel_count == 1  # Only Skill -> Category
        assert mock_tx.run.call_count == 1

    @pytest.mark.asyncio
    async def test_no_relationships_when_both_missing(self):
        """Test no relationships created when both category and subcategory are None."""
        service = SkillGraphService(None, None, None)

        mock_tx = AsyncMock()

        rel_count = await service._create_skill_relationships(
            mock_tx,
            skill_id="skill-001",
            category_id=None,
            subcategory_id=None
        )

        assert rel_count == 0
        assert mock_tx.run.call_count == 0
