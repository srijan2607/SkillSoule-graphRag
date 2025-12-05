"""
Unit tests for token counting utilities.
"""
import pytest
from app.utils.token_counter import count_tokens, exceeds_token_limit


def test_count_tokens_empty_string():
    """Test token counting with empty string."""
    assert count_tokens("") == 0
    assert count_tokens(None) == 0


def test_count_tokens_short_text():
    """Test token counting with short text."""
    # "Hello world" = 11 chars = ~2-3 tokens
    assert count_tokens("Hello world") == 2


def test_count_tokens_exact_multiple():
    """Test token counting with exact multiple of 4 chars."""
    # 400 chars = 100 tokens
    text = "A" * 400
    assert count_tokens(text) == 100


def test_count_tokens_approximation():
    """Test token counting approximation is reasonable."""
    # Realistic sentence
    text = "The quick brown fox jumps over the lazy dog"
    token_count = count_tokens(text)

    # Should be roughly len(text) / 4
    expected = len(text) // 4
    assert token_count == expected


def test_count_tokens_large_text():
    """Test token counting with large text."""
    # 16000 chars = 4000 tokens (context limit)
    text = "A" * 16000
    assert count_tokens(text) == 4000


def test_exceeds_token_limit_under_limit():
    """Test exceeds_token_limit returns False when under limit."""
    # 3000 chars = 750 tokens (under 4000 limit)
    text = "A" * 3000
    assert exceeds_token_limit(text, limit=4000) is False


def test_exceeds_token_limit_at_limit():
    """Test exceeds_token_limit returns False when exactly at limit."""
    # 16000 chars = 4000 tokens (exactly at limit)
    text = "A" * 16000
    assert exceeds_token_limit(text, limit=4000) is False


def test_exceeds_token_limit_over_limit():
    """Test exceeds_token_limit returns True when over limit."""
    # 20000 chars = 5000 tokens (over 4000 limit)
    text = "A" * 20000
    assert exceeds_token_limit(text, limit=4000) is True


def test_exceeds_token_limit_custom_limit():
    """Test exceeds_token_limit with custom limit."""
    # 2000 chars = 500 tokens
    text = "A" * 2000

    assert exceeds_token_limit(text, limit=600) is False
    assert exceeds_token_limit(text, limit=400) is True


def test_exceeds_token_limit_empty_string():
    """Test exceeds_token_limit with empty string."""
    assert exceeds_token_limit("", limit=4000) is False
    assert exceeds_token_limit(None, limit=4000) is False
