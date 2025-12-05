"""
Unit tests for response_generation_node.

Tests LLM response generation with mocked OpenRouterService.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.nodes.response_generation import (
    response_generation_node,
    _build_user_prompt,
    SYSTEM_PROMPT,
)
from app.agents.graph import GraphRAGState


@pytest.fixture
def sample_state():
    """Create sample GraphRAGState for testing."""
    return GraphRAGState(
        user_query="What skills are needed for Python developer jobs?",
        user_id="test-user-123",
        constructed_context="Job: Python Developer\nSkills: Python, Django, FastAPI\nSalary: $120k",
        metadata={"test": "value"},
    )


class TestBuildUserPrompt:
    """Test user prompt construction."""

    def test_build_user_prompt_basic(self):
        """Test basic prompt construction."""
        context = "Test context"
        query = "Test query"

        result = _build_user_prompt(context, query)

        assert "Test context" in result
        assert "Test query" in result
        assert "Context from Knowledge Graph" in result
        assert "User Question" in result

    def test_build_user_prompt_empty_context(self):
        """Test prompt with empty context."""
        result = _build_user_prompt("", "What are Python skills?")

        assert "What are Python skills?" in result
        assert "Context from Knowledge Graph:" in result

    def test_build_user_prompt_long_context(self):
        """Test prompt with long context."""
        context = "Long context " * 100
        query = "Test query"

        result = _build_user_prompt(context, query)

        assert len(result) > len(context)
        assert query in result


class TestResponseGenerationNodeSuccess:
    """Test successful response generation."""

    @pytest.mark.asyncio
    async def test_successful_generation(self, sample_state):
        """Test successful LLM response generation."""
        mock_result = {
            "text": "Based on the graph, Python developers need Python, Django, and FastAPI skills.",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 500,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            result = await response_generation_node(sample_state)

            # Verify response
            assert "final_response" in result
            assert result["final_response"] == mock_result["text"]

            # Verify metadata
            assert result["metadata"]["response_generation_completed"] is True
            assert result["metadata"]["llm_tokens_used"] == 150
            assert result["metadata"]["llm_latency_ms"] == 500
            assert result["metadata"]["llm_retry_count"] == 0

            # Verify service was called correctly
            mock_service.generate_completion.assert_called_once()
            call_kwargs = mock_service.generate_completion.call_args.kwargs
            assert call_kwargs["max_tokens"] == 500
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_retries"] == 3

    @pytest.mark.asyncio
    async def test_system_prompt_included(self, sample_state):
        """Test that system prompt is passed to LLM."""
        mock_result = {
            "text": "Test response",
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 300,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            await response_generation_node(sample_state)

            # Verify system prompt was passed
            call_kwargs = mock_service.generate_completion.call_args.kwargs
            assert "system_prompt" in call_kwargs
            assert "skills and job market analysis" in call_kwargs["system_prompt"]

    @pytest.mark.asyncio
    async def test_context_included_in_prompt(self, sample_state):
        """Test that context is included in user prompt."""
        mock_result = {
            "text": "Test response",
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 300,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            await response_generation_node(sample_state)

            # Verify context was included
            call_kwargs = mock_service.generate_completion.call_args.kwargs
            assert "user_prompt" in call_kwargs
            assert sample_state.constructed_context in call_kwargs["user_prompt"]
            assert sample_state.user_query in call_kwargs["user_prompt"]


class TestResponseGenerationNodeRetry:
    """Test retry logic and error handling."""

    @pytest.mark.asyncio
    async def test_successful_after_retries(self, sample_state):
        """Test successful generation after retries."""
        mock_result = {
            "text": "Response after retries",
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 800,
            "retry_count": 2,  # Succeeded on 3rd attempt
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            result = await response_generation_node(sample_state)

            # Verify response
            assert result["final_response"] == "Response after retries"
            assert result["metadata"]["llm_retry_count"] == 2

    @pytest.mark.asyncio
    async def test_all_retries_fail(self, sample_state):
        """Test error handling when all retries fail."""
        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.side_effect = Exception("API timeout")
            mock_service_class.return_value = mock_service

            result = await response_generation_node(sample_state)

            # Verify error response
            assert "final_response" in result
            assert "Unable to generate response" in result["final_response"]
            assert result["metadata"]["response_generation_failed"] is True
            assert "response_generation_error" in result["metadata"]


class TestResponseGenerationNodeEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_empty_context(self):
        """Test with empty context."""
        state = GraphRAGState(
            user_query="What is Python?",
            user_id="test-user-123",
            constructed_context="",
            metadata={},
        )

        mock_result = {
            "text": "Python is a programming language.",
            "usage": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 300,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            result = await response_generation_node(state)

            # Should still work with empty context
            assert result["final_response"] == mock_result["text"]

    @pytest.mark.asyncio
    async def test_none_context(self):
        """Test with None context."""
        state = GraphRAGState(
            user_query="What is Python?",
            user_id="test-user-123",
            constructed_context=None,
            metadata={},
        )

        mock_result = {
            "text": "Python is a programming language.",
            "usage": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 300,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            result = await response_generation_node(state)

            # Should handle None context gracefully
            assert result["final_response"] == mock_result["text"]

    @pytest.mark.asyncio
    async def test_unexpected_error(self, sample_state):
        """Test handling of unexpected errors."""
        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            # Simulate error in service initialization
            mock_service_class.side_effect = RuntimeError("Unexpected error")

            result = await response_generation_node(sample_state)

            # Should return error response
            assert "final_response" in result
            assert "error" in result["final_response"].lower()
            assert result["metadata"]["response_generation_failed"] is True

    @pytest.mark.asyncio
    async def test_metadata_preserved(self, sample_state):
        """Test that existing metadata is preserved."""
        sample_state.metadata = {
            "existing_key": "existing_value",
            "another_key": 123,
        }

        mock_result = {
            "text": "Test response",
            "usage": {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "latency_ms": 300,
            "retry_count": 0,
        }

        with patch("app.agents.nodes.response_generation.OpenRouterService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.generate_completion.return_value = mock_result
            mock_service_class.return_value = mock_service

            result = await response_generation_node(sample_state)

            # Verify existing metadata preserved
            assert result["metadata"]["existing_key"] == "existing_value"
            assert result["metadata"]["another_key"] == 123
            # And new metadata added
            assert result["metadata"]["response_generation_completed"] is True
