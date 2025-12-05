"""
Unit tests for SkillMatchingService.

Tests the 3-tier skill matching strategy:
1. Exact case-insensitive matching
2. Fuzzy matching with Levenshtein distance
3. Orphan creation for unmatched skills
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.skill_matching_service import SkillMatchingService


@pytest.fixture
def mock_neo4j_repo():
    """Mock Neo4j repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_ingestion_repo():
    """Mock ingestion repository."""
    repo = AsyncMock()
    repo.create_orphan_log = AsyncMock()
    return repo


@pytest.fixture
def skill_matcher(mock_neo4j_repo, mock_ingestion_repo):
    """Create SkillMatchingService instance with mocked dependencies."""
    return SkillMatchingService(mock_neo4j_repo, mock_ingestion_repo)


# ============================================================================
# Exact Match Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_case_insensitive(skill_matcher, mock_neo4j_repo):
    """Test exact matching is case-insensitive."""
    # Setup: Mock Neo4j to return Python skill for exact match
    mock_neo4j_repo.execute_query.return_value = [
        {"id": "python-001", "name": "Python"}
    ]

    # Execute: Match "PYTHON" (uppercase)
    result = await skill_matcher.match_skill("PYTHON", job_id="test-job-1")

    # Verify
    assert result["match_type"] == "exact"
    assert result["matched_name"] == "Python"  # Canonical name preserved
    assert result["confidence"] == 1.0
    assert result["requires_manual_review"] is False
    assert result["fuzzy_candidates"] == []

    # Verify Neo4j query was called with lowercase normalized name
    mock_neo4j_repo.execute_query.assert_called_once()
    call_args = mock_neo4j_repo.execute_query.call_args
    assert call_args[0][1]["normalized_name"] == "python"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_with_whitespace(skill_matcher, mock_neo4j_repo):
    """Test exact matching trims whitespace."""
    mock_neo4j_repo.execute_query.return_value = [
        {"id": "react-001", "name": "React"}
    ]

    result = await skill_matcher.match_skill("  React  ", job_id="test-job-2")

    assert result["match_type"] == "exact"
    assert result["matched_name"] == "React"
    assert result["confidence"] == 1.0

    # Verify normalized name has no whitespace
    call_args = mock_neo4j_repo.execute_query.call_args
    assert call_args[0][1]["normalized_name"] == "react"


# ============================================================================
# Fuzzy Match Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fuzzy_match_typo_correction_distance_1(skill_matcher, mock_neo4j_repo):
    """Test fuzzy matching corrects typos with Levenshtein distance 1."""
    # Setup: No exact match, but skill cache has "Python"
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [{"id": "python-001", "name": "Python", "name_lower": "python"}]  # Cache
    ]

    # Execute: Match "Pyton" (missing 'h')
    result = await skill_matcher.match_skill("Pyton", job_id="test-job-3")

    # Verify
    assert result["match_type"] == "fuzzy"
    assert result["matched_name"] == "Python"
    assert 0.8 <= result["confidence"] <= 0.9  # Distance 1 = confidence 0.9
    assert result["requires_manual_review"] is False
    assert result["fuzzy_candidates"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fuzzy_match_typo_correction_distance_2(skill_matcher, mock_neo4j_repo):
    """Test fuzzy matching corrects typos with Levenshtein distance 2."""
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [{"id": "javascript-001", "name": "JavaScript", "name_lower": "javascript"}]
    ]

    result = await skill_matcher.match_skill("JavaScrit", job_id="test-job-4")

    assert result["match_type"] == "fuzzy"
    assert result["matched_name"] == "JavaScript"
    assert 0.8 <= result["confidence"] <= 0.9  # Distance 2 = confidence 0.8


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fuzzy_match_threshold_exceeded(skill_matcher, mock_neo4j_repo, mock_ingestion_repo):
    """Test fuzzy matching fails when Levenshtein distance > 2."""
    # Setup: No exact match, skill cache has "Python" but distance is 3
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [{"id": "python-001", "name": "Python", "name_lower": "python"}],  # Cache
        [{"id": "orphan-001", "name": "ptn"}]  # Orphan creation
    ]

    # Execute: Match "Ptn" (distance 3 from "Python")
    result = await skill_matcher.match_skill("Ptn", job_id="test-job-5")

    # Verify: Should create orphan (no fuzzy match)
    assert result["match_type"] == "orphan"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ambiguous_fuzzy_match_creates_orphan(skill_matcher, mock_neo4j_repo, mock_ingestion_repo):
    """Test ambiguous fuzzy matches (multiple candidates) create orphan."""
    # Setup: No exact match, but two similar skills within threshold
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [
            {"id": "react-001", "name": "React", "name_lower": "react"},
            {"id": "reactjs-001", "name": "ReactJS", "name_lower": "reactjs"}
        ],  # Cache with two similar skills
        [{"id": "orphan-002", "name": "reactjs"}]  # Orphan creation
    ]

    # Execute: Match "Reactjs" (could be React or ReactJS)
    result = await skill_matcher.match_skill("Reactjs", job_id="test-job-6")

    # Verify: Should create orphan with suggested candidates
    assert result["match_type"] == "orphan"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True
    assert set(result["fuzzy_candidates"]) == {"React", "ReactJS"}

    # Verify orphan was logged
    mock_ingestion_repo.create_orphan_log.assert_called_once()
    call_args = mock_ingestion_repo.create_orphan_log.call_args[1]
    assert call_args["orphan_reason"] == "ambiguous_fuzzy_match"
    assert set(call_args["fuzzy_candidates"]) == {"React", "ReactJS"}


# ============================================================================
# Orphan Creation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orphan_creation_no_match(skill_matcher, mock_neo4j_repo, mock_ingestion_repo):
    """Test orphan creation when no match is found."""
    # Setup: No exact match, empty skill cache
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [],  # Empty cache
        [{"id": "orphan-003", "name": "newframework2025"}]  # Orphan creation
    ]

    # Execute: Match completely unknown skill
    result = await skill_matcher.match_skill("NewFramework2025", job_id="test-job-7")

    # Verify: Orphan created
    assert result["match_type"] == "orphan"
    assert result["matched_name"] == "newframework2025"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True
    assert result["fuzzy_candidates"] == []

    # Verify orphan was logged
    mock_ingestion_repo.create_orphan_log.assert_called_once()
    call_args = mock_ingestion_repo.create_orphan_log.call_args[1]
    assert call_args["skill_name"] == "newframework2025"
    assert call_args["job_id"] == "test-job-7"
    assert call_args["orphan_reason"] == "no_match"
    assert call_args["status"] == "pending_review"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_orphan_creation_skill_name_too_short(skill_matcher, mock_ingestion_repo):
    """Test orphan creation for skill names that are too short."""
    # Setup: Mock orphan creation
    skill_matcher.neo4j_repo.execute_query = AsyncMock(return_value=[
        {"id": "orphan-004", "name": "x"}
    ])

    # Execute: Match single character skill
    result = await skill_matcher.match_skill("X", job_id="test-job-8")

    # Verify: Orphan created with "too_short" reason
    assert result["match_type"] == "orphan"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True

    # Verify orphan reason
    mock_ingestion_repo.create_orphan_log.assert_called_once()
    call_args = mock_ingestion_repo.create_orphan_log.call_args[1]
    assert call_args["orphan_reason"] == "too_short"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deduplication_prevents_duplicates(skill_matcher, mock_neo4j_repo, mock_ingestion_repo):
    """Test MERGE prevents duplicate orphan creation."""
    # First call: Create orphan
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [],  # Empty cache
        [{"id": "orphan-005", "name": "newskill"}],  # First orphan creation
        [],  # No exact match (second call)
        [{"id": "orphan-005", "name": "newskill"}]  # Same orphan ID returned by MERGE
    ]

    result1 = await skill_matcher.match_skill("NewSkill", job_id="job-1")
    assert result1["match_type"] == "orphan"

    # Second call: Should reuse existing orphan (MERGE in Cypher)
    # Cache is already loaded, so no cache refresh query
    result2 = await skill_matcher.match_skill("newskill", job_id="job-2")

    # Verify: Same orphan ID reused
    assert result2["skill_id"] == result1["skill_id"]
    assert result2["match_type"] == "orphan"


# ============================================================================
# Confidence Calculation Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confidence_calculation_distance_1(skill_matcher, mock_neo4j_repo):
    """Test confidence calculation for Levenshtein distance 1."""
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [{"id": "python-001", "name": "Python", "name_lower": "python"}]
    ]

    result = await skill_matcher.match_skill("Pyton", job_id="test-job")

    # Distance 1: confidence = 1.0 - (1 / 10) = 0.9
    assert result["confidence"] == 0.9


@pytest.mark.unit
@pytest.mark.asyncio
async def test_confidence_calculation_distance_2(skill_matcher, mock_neo4j_repo):
    """Test confidence calculation for Levenshtein distance 2."""
    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match
        [{"id": "python-001", "name": "Python", "name_lower": "python"}]
    ]

    # "Pton" is distance 2 from "Python" (missing 'y' and 'h')
    result = await skill_matcher.match_skill("Pton", job_id="test-job")

    # Distance 2: confidence = 1.0 - (2 / 10) = 0.8
    assert result["confidence"] == 0.8


# ============================================================================
# Cache Management Tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skill_cache_refreshed_once(skill_matcher, mock_neo4j_repo, mock_ingestion_repo):
    """Test skill cache is loaded once and reused."""
    # Setup cache data
    cache_data = [
        {"id": "python-001", "name": "Python", "name_lower": "python"},
        {"id": "react-001", "name": "React", "name_lower": "react"}
    ]

    mock_neo4j_repo.execute_query.side_effect = [
        [],  # No exact match (first call)
        cache_data,  # Cache refresh
        [{"id": "orphan-001", "name": "unknownskill1"}],  # Orphan creation
        [],  # No exact match (second call)
        [{"id": "orphan-002", "name": "unknownskill2"}]  # Orphan creation
    ]

    # First match: Cache should be loaded
    await skill_matcher.match_skill("UnknownSkill1", job_id="job-1")

    # Second match: Cache should be reused (no second cache query)
    await skill_matcher.match_skill("UnknownSkill2", job_id="job-2")

    # Verify: execute_query was called 5 times total
    # (2 exact match queries + 1 cache refresh + 2 orphan creations)
    assert mock_neo4j_repo.execute_query.call_count == 5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_manual_cache_refresh(skill_matcher, mock_neo4j_repo):
    """Test manual cache refresh updates cached skills."""
    # Initial cache
    cache_data_old = [
        {"id": "python-001", "name": "Python", "name_lower": "python"}
    ]

    # Updated cache (new skill added)
    cache_data_new = [
        {"id": "python-001", "name": "Python", "name_lower": "python"},
        {"id": "rust-001", "name": "Rust", "name_lower": "rust"}
    ]

    mock_neo4j_repo.execute_query.side_effect = [
        cache_data_old,  # First refresh
        cache_data_new  # Second refresh
    ]

    # First refresh
    await skill_matcher._refresh_skill_cache()
    assert len(skill_matcher._skill_cache) == 1

    # Second refresh (simulate new skill added to Neo4j)
    await skill_matcher._refresh_skill_cache()
    assert len(skill_matcher._skill_cache) == 2
