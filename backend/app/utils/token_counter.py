"""
Token counting utilities for LLM context management.
"""


def count_tokens(text: str) -> int:
    """
    Estimate token count for text using rough heuristic.

    Uses approximation: 1 token ≈ 4 characters for English text.
    This is a conservative estimate suitable for MVP.

    Args:
        text: Input text to count tokens for

    Returns:
        Estimated token count

    Example:
        >>> count_tokens("Hello world")
        3
        >>> count_tokens("A" * 400)
        100
    """
    if not text:
        return 0

    # Conservative estimate: 1 token per 4 characters
    return len(text) // 4


def exceeds_token_limit(text: str, limit: int = 4000) -> bool:
    """
    Check if text exceeds token limit.

    Args:
        text: Text to check
        limit: Token limit (default 4000)

    Returns:
        True if text exceeds limit, False otherwise
    """
    return count_tokens(text) > limit
