"""
Unit tests for EmbeddingService.

Tests single text embedding, batch embedding, empty text handling,
retry logic, and singleton pattern.

Story 3.1: Embedding Generation Service
"""

import pytest
from unittest.mock import Mock, patch
from app.services.embedding_service import EmbeddingService
import numpy as np


@pytest.mark.unit
async def test_generate_embedding_single_text():
    """Test single text embedding generation."""
    service = EmbeddingService()

    result = await service.generate_embedding("Python programming language")

    assert "embedding" in result
    assert "model_version" in result
    assert "generated_at" in result
    assert len(result["embedding"]) == 384
    assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"
    assert all(isinstance(x, float) for x in result["embedding"])


@pytest.mark.unit
async def test_empty_text_returns_zero_vector():
    """Test empty text returns zero vector."""
    service = EmbeddingService()

    # Test empty string
    result1 = await service.generate_embedding("")
    assert result1["embedding"] == [0.0] * 384

    # Test whitespace only
    result2 = await service.generate_embedding("   ")
    assert result2["embedding"] == [0.0] * 384


@pytest.mark.unit
async def test_none_text_returns_zero_vector():
    """Test None text returns zero vector."""
    service = EmbeddingService()

    result = await service.generate_embedding(None)
    assert result["embedding"] == [0.0] * 384
    assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"
    assert result["generated_at"] is not None


@pytest.mark.unit
async def test_batch_embedding_generation():
    """Test batch embedding generation."""
    service = EmbeddingService()

    texts = [
        "Python programming",
        "JavaScript development",
        "Machine learning",
        ""  # Empty text
    ]

    results = await service.generate_batch_embeddings(texts)

    assert len(results) == 4

    # First 3 should have non-zero embeddings
    for i in range(3):
        assert len(results[i]["embedding"]) == 384
        assert results[i]["embedding"] != [0.0] * 384
        assert results[i]["model_version"] == "all-MiniLM-L6-v2:2024-01"

    # Last one (empty text) should be zero vector
    assert results[3]["embedding"] == [0.0] * 384


@pytest.mark.unit
async def test_batch_with_mixed_empty_texts():
    """Test batch processing with mixed empty and valid texts."""
    service = EmbeddingService()

    texts = [
        "",
        "Valid text",
        "   ",  # Whitespace
        "Another valid text",
        None
    ]

    results = await service.generate_batch_embeddings(texts)

    assert len(results) == 5

    # Empty texts should have zero vectors
    assert results[0]["embedding"] == [0.0] * 384
    assert results[2]["embedding"] == [0.0] * 384
    assert results[4]["embedding"] == [0.0] * 384

    # Valid texts should have non-zero embeddings
    assert results[1]["embedding"] != [0.0] * 384
    assert results[3]["embedding"] != [0.0] * 384


@pytest.mark.unit
async def test_batch_empty_list():
    """Test batch embedding with empty list."""
    service = EmbeddingService()

    results = await service.generate_batch_embeddings([])

    assert results == []


@pytest.mark.unit
async def test_singleton_pattern():
    """Test service uses singleton pattern."""
    service1 = EmbeddingService()
    service2 = EmbeddingService()

    # Both instances should be the same object
    assert service1 is service2

    # Model should be loaded only once
    assert service1._model is service2._model


@pytest.mark.unit
async def test_retry_logic_with_mock_failure():
    """Test retry logic with exponential backoff."""
    service = EmbeddingService()

    # Create mock embeddings for success case
    mock_embeddings = np.array([[0.1, 0.2, 0.3] + [0.0] * 381])

    with patch.object(service._model, 'encode') as mock_encode, \
         patch('asyncio.sleep') as mock_sleep:

        # Mock encode to fail twice, succeed on third attempt
        mock_encode.side_effect = [
            Exception("Network error"),  # Attempt 1
            Exception("Timeout"),         # Attempt 2
            mock_embeddings               # Attempt 3 - success
        ]

        # Should succeed after 2 retries
        result = await service._generate_with_retry(["test text"])

        # Verify retries occurred
        assert mock_encode.call_count == 3
        assert mock_sleep.call_count == 2

        # Verify backoff times
        assert mock_sleep.call_args_list[0][0][0] == 1  # First retry: 1s
        assert mock_sleep.call_args_list[1][0][0] == 2  # Second retry: 2s


@pytest.mark.unit
async def test_retry_exhaustion_raises_error():
    """Test that retry logic raises error after max retries."""
    service = EmbeddingService()

    with patch.object(service._model, 'encode') as mock_encode, \
         patch('asyncio.sleep') as mock_sleep:

        # Mock encode to always fail
        mock_encode.side_effect = Exception("Persistent error")

        # Should raise RuntimeError after 3 failed attempts
        with pytest.raises(RuntimeError) as exc_info:
            await service._generate_with_retry(["test text"])

        assert "Failed to generate embeddings after 3 retries" in str(exc_info.value)
        assert mock_encode.call_count == 3
        assert mock_sleep.call_count == 2  # Sleeps on first 2 failures


@pytest.mark.unit
async def test_embedding_dimensions_validation():
    """Test that embedding dimensions are validated."""
    service = EmbeddingService()

    # Mock embeddings with wrong dimensions
    wrong_dim_embeddings = np.array([[0.1] * 512])  # Wrong: 512 instead of 384

    with patch.object(service._model, 'encode') as mock_encode, \
         patch('asyncio.sleep'):

        mock_encode.return_value = wrong_dim_embeddings

        # Should raise RuntimeError after exhausting retries
        with pytest.raises(RuntimeError) as exc_info:
            await service._generate_with_retry(["test text"])

        # Original error should be ValueError about dimensions
        assert "Invalid embedding dimensions" in str(exc_info.value.__cause__)


@pytest.mark.unit
async def test_model_version_metadata():
    """Test that model version metadata is included in results."""
    service = EmbeddingService()

    # Single embedding
    single_result = await service.generate_embedding("Test text")
    assert single_result["model_version"] == "all-MiniLM-L6-v2:2024-01"

    # Batch embeddings
    batch_results = await service.generate_batch_embeddings(["Test 1", "Test 2"])
    for result in batch_results:
        assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"


@pytest.mark.unit
async def test_generated_at_timestamp():
    """Test that generated_at timestamp is included."""
    service = EmbeddingService()

    result = await service.generate_embedding("Test text")

    assert "generated_at" in result
    assert result["generated_at"] is not None


@pytest.mark.unit
async def test_custom_batch_size():
    """Test custom batch size parameter."""
    service = EmbeddingService()

    texts = [f"Text {i}" for i in range(100)]

    with patch.object(service._model, 'encode', wraps=service._model.encode) as mock_encode:
        await service.generate_batch_embeddings(texts, batch_size=64)

        # Should be called with batch_size=64
        assert any(
            call[1].get('batch_size') == 64
            for call in mock_encode.call_args_list
        )


@pytest.mark.unit
async def test_large_batch_processing():
    """Test processing large batch of texts."""
    service = EmbeddingService()

    # Create 100 texts
    texts = [f"Test text number {i}" for i in range(100)]

    results = await service.generate_batch_embeddings(texts)

    assert len(results) == 100
    # All should have valid embeddings
    for result in results:
        assert len(result["embedding"]) == 384
        assert result["embedding"] != [0.0] * 384
