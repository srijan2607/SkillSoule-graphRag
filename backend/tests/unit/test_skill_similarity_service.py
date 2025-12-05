"""Unit tests for SkillSimilarityService."""
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from app.services.skill_similarity_service import SkillSimilarityService
from app.config import settings


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4jRepository for testing."""
    repo = AsyncMock()
    repo.execute_query = AsyncMock()
    repo.transaction = MagicMock()
    return repo


@pytest.fixture
def mock_ingestion_repo():
    """Mock IngestionRepository for testing."""
    return AsyncMock()


@pytest.fixture
def skill_similarity_service(mock_neo4j_repo, mock_ingestion_repo):
    """Create SkillSimilarityService instance with mocked dependencies."""
    return SkillSimilarityService(mock_neo4j_repo, mock_ingestion_repo)


@pytest.mark.unit
class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors_similarity_is_one(self, skill_similarity_service):
        """Test cosine similarity of identical vectors equals 1.0."""
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        assert similarity == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_similarity_is_zero(self, skill_similarity_service):
        """Test cosine similarity of orthogonal vectors equals 0.0."""
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([0.0, 1.0, 0.0])

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_clamped_to_zero(self, skill_similarity_service):
        """Test cosine similarity of opposite vectors is clamped to 0.0."""
        emb1 = np.array([1.0, 0.0, 0.0])
        emb2 = np.array([-1.0, 0.0, 0.0])

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        # Should be clamped to [0, 1] range
        assert 0.0 <= similarity <= 0.1

    def test_zero_vector_returns_zero(self, skill_similarity_service):
        """Test cosine similarity with zero vector returns 0.0."""
        emb1 = np.array([0.0, 0.0, 0.0])
        emb2 = np.array([1.0, 0.0, 0.0])

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        assert similarity == 0.0

    def test_high_dimensional_vectors(self, skill_similarity_service):
        """Test cosine similarity with 384-dimensional vectors."""
        # Create two similar 384-dim vectors
        emb1 = np.random.rand(384)
        emb2 = emb1 + np.random.rand(384) * 0.1  # Similar but not identical

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        # Should be high similarity
        assert 0.8 <= similarity <= 1.0


@pytest.mark.unit
class TestSimilarityFiltering:
    """Test similarity filtering logic."""

    def test_excludes_self_similarity(self, skill_similarity_service):
        """Test that skill does not match itself."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [
            {"skill_id": "1", "embedding": [1.0, 0.0, 0.0]},  # Self
            {"skill_id": "2", "embedding": [0.95, 0.1, 0.0]},  # Similar
        ]

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # Should not include self
        skill_ids = [skill_id for skill_id, _ in similar]
        assert "1" not in skill_ids
        assert "2" in skill_ids

    def test_filters_by_threshold(self, skill_similarity_service):
        """Test that only skills above threshold are returned."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [
            {"skill_id": "1", "embedding": [1.0, 0.0, 0.0]},  # Self (skip)
            {"skill_id": "2", "embedding": [0.95, 0.1, 0.0]},  # High similarity
            {"skill_id": "3", "embedding": [0.0, 1.0, 0.0]},   # Low similarity (< 0.7)
        ]

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # All results should be above threshold
        for _, score in similar:
            assert score > settings.SIMILARITY_THRESHOLD

    def test_returns_top_k_results(self, skill_similarity_service):
        """Test that only top K results are returned."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        # Create 10 similar skills
        all_skills = [{"skill_id": "1", "embedding": [1.0, 0.0, 0.0]}]  # Self
        for i in range(2, 12):  # IDs 2-11
            # Create similar embeddings
            all_skills.append({
                "skill_id": str(i),
                "embedding": [0.9, 0.1 * i / 10, 0.0]
            })

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # Should return at most TOP_K results
        assert len(similar) <= settings.SIMILARITY_TOP_K

    def test_sorted_by_similarity_descending(self, skill_similarity_service):
        """Test that results are sorted by similarity score descending."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [
            {"skill_id": "1", "embedding": [1.0, 0.0, 0.0]},  # Self
            {"skill_id": "2", "embedding": [0.95, 0.1, 0.0]},  # High
            {"skill_id": "3", "embedding": [0.85, 0.2, 0.0]},  # Medium
            {"skill_id": "4", "embedding": [0.75, 0.3, 0.0]},  # Lower
        ]

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # Check descending order
        scores = [score for _, score in similar]
        assert scores == sorted(scores, reverse=True)

    def test_empty_results_when_no_similar_skills(self, skill_similarity_service):
        """Test returns empty list when no skills meet threshold."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [
            {"skill_id": "1", "embedding": [1.0, 0.0, 0.0]},  # Self
            {"skill_id": "2", "embedding": [0.0, 1.0, 0.0]},  # Orthogonal (low sim)
            {"skill_id": "3", "embedding": [0.0, 0.0, 1.0]},  # Orthogonal (low sim)
        ]

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # Should return empty list
        assert len(similar) == 0


@pytest.mark.unit
class TestBidirectionalRelationships:
    """Test bidirectional relationship creation logic."""

    def test_bidirectional_emerges_from_symmetric_similarity(self, skill_similarity_service):
        """Test that bidirectional relationships emerge naturally from processing."""
        # Skill 1 processing
        skill1 = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [
            {"skill_id": "1", "embedding": [1.0, 0.0, 0.0]},  # Self
            {"skill_id": "2", "embedding": [0.95, 0.1, 0.0]},  # Similar
        ]

        # Skill 1 finds skill 2 as similar
        similar_to_1 = skill_similarity_service._find_top_similar_skills(skill1, all_skills)
        relationships_from_1 = [
            {"source_id": "1", "target_id": similar_skill_id, "score": score}
            for similar_skill_id, score in similar_to_1
        ]

        # Skill 2 processing
        skill2 = {
            "skill_id": "2",
            "skill_name": "Java",
            "embedding": [0.95, 0.1, 0.0]
        }

        # Skill 2 finds skill 1 as similar
        similar_to_2 = skill_similarity_service._find_top_similar_skills(skill2, all_skills)
        relationships_from_2 = [
            {"source_id": "2", "target_id": similar_skill_id, "score": score}
            for similar_skill_id, score in similar_to_2
        ]

        # Should have 1->2 from skill 1 processing
        assert len(relationships_from_1) == 1
        assert relationships_from_1[0]["source_id"] == "1"
        assert relationships_from_1[0]["target_id"] == "2"

        # Should have 2->1 from skill 2 processing (bidirectional)
        assert len(relationships_from_2) == 1
        assert relationships_from_2[0]["source_id"] == "2"
        assert relationships_from_2[0]["target_id"] == "1"

        # Scores should be identical (cosine similarity is symmetric)
        assert relationships_from_1[0]["score"] == pytest.approx(relationships_from_2[0]["score"])


@pytest.mark.unit
@pytest.mark.asyncio
class TestBatchProcessing:
    """Test batch processing logic."""

    async def test_fetch_all_skill_embeddings(self, skill_similarity_service, mock_neo4j_repo):
        """Test fetching all skill embeddings from Neo4j."""
        # Mock data
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": "1", "skill_name": "Python", "embedding": [0.1] * 384},
            {"skill_id": "2", "skill_name": "Java", "embedding": [0.2] * 384}
        ]

        # Execute
        skills = await skill_similarity_service._fetch_all_skill_embeddings()

        # Verify
        assert len(skills) == 2
        assert skills[0]["skill_id"] == "1"
        assert skills[1]["skill_id"] == "2"
        assert len(skills[0]["embedding"]) == 384

    async def test_empty_database_returns_empty_list(self, skill_similarity_service, mock_neo4j_repo):
        """Test handling of empty database."""
        # Mock empty response
        mock_neo4j_repo.execute_query.return_value = []

        # Execute
        result = await skill_similarity_service.compute_skill_similarities(job_id="test-job")

        # Verify
        assert result["skills_processed"] == 0
        assert result["relationships_created"] == 0
        assert result["duration_seconds"] == 0

    async def test_process_similarity_batch_creates_relationships(
        self,
        skill_similarity_service,
        mock_neo4j_repo
    ):
        """Test batch processing creates correct number of relationships."""
        batch = [{"skill_id": "1", "embedding": np.array([1.0, 0.0, 0.0])}]
        all_skills = [
            {"skill_id": "1", "embedding": np.array([1.0, 0.0, 0.0])},
            {"skill_id": "2", "embedding": np.array([0.95, 0.1, 0.0])}  # Similar
        ]

        # Mock transaction
        mock_session = AsyncMock()
        mock_tx = AsyncMock()
        mock_session.begin_transaction.return_value = mock_tx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_neo4j_repo.transaction.return_value = mock_session

        # Execute
        relationships_count = await skill_similarity_service._process_similarity_batch(
            batch,
            all_skills,
            job_id="test-job"
        )

        # Should create 1 relationship (unidirectional: 1->2)
        # The reverse relationship (2->1) will be created when skill 2 is processed
        assert relationships_count == 1


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_single_skill_no_matches(self, skill_similarity_service):
        """Test behavior with only one skill in database."""
        skill = {
            "skill_id": "1",
            "skill_name": "Python",
            "embedding": [1.0, 0.0, 0.0]
        }

        all_skills = [{"skill_id": "1", "embedding": [1.0, 0.0, 0.0]}]  # Only self

        similar = skill_similarity_service._find_top_similar_skills(skill, all_skills)

        # Should return empty (self excluded)
        assert len(similar) == 0

    def test_all_zero_embeddings(self, skill_similarity_service):
        """Test handling of zero embeddings."""
        emb1 = np.array([0.0, 0.0, 0.0])
        emb2 = np.array([0.0, 0.0, 0.0])

        similarity = skill_similarity_service._compute_cosine_similarity(emb1, emb2)

        # Should return 0.0 (avoid division by zero)
        assert similarity == 0.0
