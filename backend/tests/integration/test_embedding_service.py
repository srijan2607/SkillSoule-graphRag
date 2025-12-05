"""
Integration tests for EmbeddingService.

Tests model loading, end-to-end workflows, performance benchmarks,
and real-world data validation.

Story 3.1: Embedding Generation Service
"""

import pytest
import time
from app.services.embedding_service import EmbeddingService


@pytest.mark.integration
async def test_model_initialization_performance():
    """Test that model loads successfully within acceptable time."""
    start_time = time.time()

    service = EmbeddingService()

    load_time = time.time() - start_time

    # Model should load within 10 seconds on first initialization
    assert load_time < 10.0, f"Model took {load_time:.2f}s to load (expected < 10s)"

    # Verify model is loaded
    assert service._model is not None
    assert service.CURRENT_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
    assert service.EMBEDDING_DIMENSIONS == 384


@pytest.mark.integration
async def test_singleton_pattern_model_reuse():
    """Test that singleton pattern ensures model is loaded only once."""
    # First instantiation
    start_time = time.time()
    service1 = EmbeddingService()
    first_load_time = time.time() - start_time

    # Second instantiation (should reuse model)
    start_time = time.time()
    service2 = EmbeddingService()
    second_load_time = time.time() - start_time

    # Same instance
    assert service1 is service2

    # Same model
    assert service1._model is service2._model

    # Second instantiation should be nearly instant (< 0.1s)
    assert second_load_time < 0.1, f"Second instantiation took {second_load_time:.2f}s (should reuse model)"


@pytest.mark.integration
async def test_end_to_end_embedding_workflow():
    """Test complete embedding generation workflow."""
    service = EmbeddingService()

    # Test real skill descriptions
    test_skills = [
        "Python programming language with expertise in data structures and algorithms",
        "JavaScript full-stack development using React and Node.js",
        "Machine learning and deep learning with TensorFlow and PyTorch",
        "Database design and optimization for PostgreSQL and MongoDB",
        "Cloud infrastructure management on AWS and Azure"
    ]

    # Generate embeddings
    results = await service.generate_batch_embeddings(test_skills)

    # Verify results
    assert len(results) == 5

    for i, result in enumerate(results):
        # Check structure
        assert "embedding" in result
        assert "model_version" in result
        assert "generated_at" in result

        # Check embedding properties
        assert len(result["embedding"]) == 384
        assert all(isinstance(x, float) for x in result["embedding"])

        # Non-zero embeddings (valid semantic content)
        assert result["embedding"] != [0.0] * 384

        # Check metadata
        assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"
        assert result["generated_at"] is not None


@pytest.mark.integration
async def test_semantic_similarity_validation():
    """Test that semantically similar texts produce similar embeddings."""
    service = EmbeddingService()

    # Similar skills should have similar embeddings
    similar_skills = [
        "Python programming and software development",
        "Python coding and application development",
    ]

    # Dissimilar skill
    dissimilar_skill = "Graphic design using Adobe Creative Suite"

    # Generate embeddings
    result1 = await service.generate_embedding(similar_skills[0])
    result2 = await service.generate_embedding(similar_skills[1])
    result3 = await service.generate_embedding(dissimilar_skill)

    # Calculate cosine similarities
    def cosine_similarity(vec1, vec2):
        """Calculate cosine similarity between two vectors."""
        import numpy as np
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    similarity_similar = cosine_similarity(result1["embedding"], result2["embedding"])
    similarity_dissimilar = cosine_similarity(result1["embedding"], result3["embedding"])

    # Similar texts should have higher similarity (> 0.7)
    assert similarity_similar > 0.7, f"Similar texts similarity: {similarity_similar:.3f} (expected > 0.7)"

    # Dissimilar texts should have lower similarity (< 0.6)
    assert similarity_dissimilar < 0.6, f"Dissimilar texts similarity: {similarity_dissimilar:.3f} (expected < 0.6)"


@pytest.mark.integration
async def test_batch_processing_performance():
    """Test batch processing performance with 100 texts."""
    service = EmbeddingService()

    # Generate 100 test texts
    test_texts = [
        f"Skill description number {i}: expertise in technology and development"
        for i in range(100)
    ]

    # Measure batch processing time
    start_time = time.time()
    results = await service.generate_batch_embeddings(test_texts)
    elapsed_time = time.time() - start_time

    # Verify results
    assert len(results) == 100

    # All should have valid embeddings
    for result in results:
        assert len(result["embedding"]) == 384
        assert result["embedding"] != [0.0] * 384
        assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"

    # Calculate performance
    embeddings_per_second = 100 / elapsed_time

    # Should process at least 50 embeddings/second on CPU
    # (Story requirement: >50 embeddings/sec)
    assert embeddings_per_second > 50, \
        f"Performance: {embeddings_per_second:.1f} embeddings/sec (expected > 50)"

    print(f"\nPerformance: {embeddings_per_second:.1f} embeddings/second")
    print(f"Total time: {elapsed_time:.2f}s for 100 texts")


@pytest.mark.integration
async def test_large_batch_with_mixed_content():
    """Test large batch with mixed valid and empty texts."""
    service = EmbeddingService()

    # Create mixed batch (80 valid, 20 empty)
    mixed_texts = []
    for i in range(100):
        if i % 5 == 0:  # Every 5th is empty
            mixed_texts.append("")
        else:
            mixed_texts.append(f"Skill description {i}")

    # Process batch
    results = await service.generate_batch_embeddings(mixed_texts)

    # Verify all results
    assert len(results) == 100

    # Count zero and non-zero embeddings
    zero_count = sum(1 for r in results if r["embedding"] == [0.0] * 384)
    non_zero_count = sum(1 for r in results if r["embedding"] != [0.0] * 384)

    assert zero_count == 20, f"Expected 20 zero vectors, got {zero_count}"
    assert non_zero_count == 80, f"Expected 80 non-zero vectors, got {non_zero_count}"


@pytest.mark.integration
async def test_real_csv_data_simulation():
    """Test with realistic skill data from CSV processing scenario."""
    service = EmbeddingService()

    # Simulate real skill descriptions from CSV
    real_skills = [
        "Python programming with Django and Flask frameworks",
        "React and TypeScript for frontend development",
        "AWS cloud architecture and DevOps practices",
        "Data analysis using pandas and NumPy",
        "Machine learning model training and deployment",
        "",  # Empty skill (edge case in CSV)
        "   ",  # Whitespace only (another edge case)
        "PostgreSQL database administration and optimization",
        None,  # None value (CSV parsing edge case)
        "Agile project management and team leadership"
    ]

    # Process all skills
    results = await service.generate_batch_embeddings(real_skills)

    # Verify results
    assert len(results) == 10

    # Check empty/None handling (indices 5, 6, 8)
    assert results[5]["embedding"] == [0.0] * 384  # Empty string
    assert results[6]["embedding"] == [0.0] * 384  # Whitespace
    assert results[8]["embedding"] == [0.0] * 384  # None

    # Check valid embeddings (all others)
    for idx in [0, 1, 2, 3, 4, 7, 9]:
        assert results[idx]["embedding"] != [0.0] * 384
        assert len(results[idx]["embedding"]) == 384
        assert results[idx]["model_version"] == "all-MiniLM-L6-v2:2024-01"


@pytest.mark.integration
async def test_custom_batch_size_performance():
    """Test custom batch size parameter affects performance."""
    service = EmbeddingService()

    # Generate 64 test texts
    test_texts = [f"Test text {i}" for i in range(64)]

    # Test with batch_size=32 (default)
    start_time = time.time()
    results_32 = await service.generate_batch_embeddings(test_texts, batch_size=32)
    time_32 = time.time() - start_time

    # Test with batch_size=64
    start_time = time.time()
    results_64 = await service.generate_batch_embeddings(test_texts, batch_size=64)
    time_64 = time.time() - start_time

    # Both should produce correct results
    assert len(results_32) == 64
    assert len(results_64) == 64

    # Larger batch size should be faster or similar
    # (Not enforcing strict performance, just checking functionality)
    print(f"\nBatch size 32: {time_32:.2f}s")
    print(f"Batch size 64: {time_64:.2f}s")


@pytest.mark.integration
async def test_model_version_consistency():
    """Test that model version remains consistent across operations."""
    service = EmbeddingService()

    # Generate various embeddings
    single_result = await service.generate_embedding("Test")
    batch_results = await service.generate_batch_embeddings(["Test 1", "Test 2", ""])

    # All should have same model version
    expected_version = "all-MiniLM-L6-v2:2024-01"

    assert single_result["model_version"] == expected_version
    for result in batch_results:
        assert result["model_version"] == expected_version


@pytest.mark.integration
async def test_empty_batch_handling():
    """Test edge case of empty batch."""
    service = EmbeddingService()

    # Empty list
    results = await service.generate_batch_embeddings([])
    assert results == []

    # All empty texts
    results = await service.generate_batch_embeddings(["", "   ", None])
    assert len(results) == 3
    for result in results:
        assert result["embedding"] == [0.0] * 384


@pytest.mark.integration
async def test_timestamp_generation():
    """Test that timestamps are generated and reasonable."""
    service = EmbeddingService()

    from datetime import datetime, timedelta, UTC

    # Generate embedding
    before = datetime.now(UTC)
    result = await service.generate_embedding("Test")
    after = datetime.now(UTC)

    # Timestamp should be between before and after
    generated_at = result["generated_at"]
    assert before <= generated_at <= after + timedelta(seconds=1)
