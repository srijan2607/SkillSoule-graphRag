"""
Integration tests for response_generation_node with real OpenRouter API.

These tests make actual API calls to OpenRouter.
Use pytest markers to skip if API key is not available.
"""

import pytest
import os
from app.agents.nodes.response_generation import response_generation_node
from app.agents.graph import GraphRAGState
from app.services.openrouter_service import OpenRouterService


# Skip all tests if OPENROUTER_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set - skipping OpenRouter integration tests",
)


@pytest.fixture
def sample_state():
    """Create sample GraphRAGState with realistic context."""
    return GraphRAGState(
        user_query="What skills are needed for Python developer jobs?",
        user_id="test-user-integration",
        constructed_context="""## Job: Senior Python Developer
- Company: Tech Corp
- Salary: $120,000
- Required Skills: Python, Django, FastAPI, PostgreSQL
- Nice to have: Docker, AWS, React

## Related Skills:
- Python: High-level programming language
- Django: Web framework for Python
- FastAPI: Modern async web framework
- PostgreSQL: Relational database""",
        metadata={"query_type": "skill_requirements"},
    )


class TestOpenRouterServiceIntegration:
    """Test OpenRouterService with real API calls."""

    @pytest.mark.asyncio
    async def test_generate_completion_real_api(self):
        """Test real OpenRouter API call."""
        service = OpenRouterService()

        system_prompt = "You are a helpful assistant."
        user_prompt = "Say 'Hello' in exactly one word."

        result = await service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=10,
            temperature=0.7,
            max_retries=3,
        )

        # Verify response structure
        assert "text" in result
        assert "usage" in result
        assert "model" in result
        assert "latency_ms" in result
        assert "retry_count" in result

        # Verify response content
        assert len(result["text"]) > 0
        assert result["usage"]["total_tokens"] > 0
        assert result["latency_ms"] > 0
        assert result["retry_count"] >= 0

        print(f"\n✅ Real API Response: {result['text']}")
        print(f"✅ Tokens used: {result['usage']['total_tokens']}")
        print(f"✅ Latency: {result['latency_ms']}ms")

    @pytest.mark.asyncio
    async def test_generate_completion_with_context(self):
        """Test API call with realistic context."""
        service = OpenRouterService()

        system_prompt = """You are a helpful AI assistant specialized in skills analysis.
Answer based on the provided context."""

        user_prompt = """## Context:
Job Title: Python Developer
Required Skills: Python, Django, FastAPI

## Question:
What are the main skills needed?

## Answer:
"""

        result = await service.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=100,
            temperature=0.7,
            max_retries=3,
        )

        # Verify response
        assert len(result["text"]) > 0
        assert "python" in result["text"].lower() or "django" in result["text"].lower()

        print(f"\n✅ Context-based response: {result['text'][:200]}...")


class TestResponseGenerationNodeIntegration:
    """Test response_generation_node with real API."""

    @pytest.mark.asyncio
    async def test_node_real_api_call(self, sample_state):
        """Test node with real OpenRouter API."""
        result = await response_generation_node(sample_state)

        # Verify response structure
        assert "final_response" in result
        assert "metadata" in result

        # Verify response content
        assert len(result["final_response"]) > 0
        assert result["metadata"]["response_generation_completed"] is True

        # Verify LLM metadata
        assert "llm_tokens_used" in result["metadata"]
        assert "llm_latency_ms" in result["metadata"]
        assert "llm_model" in result["metadata"]
        assert result["metadata"]["llm_tokens_used"] > 0
        assert result["metadata"]["llm_latency_ms"] > 0

        print(f"\n✅ Generated response: {result['final_response'][:300]}...")
        print(f"✅ Tokens used: {result['metadata']['llm_tokens_used']}")
        print(f"✅ Latency: {result['metadata']['llm_latency_ms']}ms")
        print(f"✅ Retries: {result['metadata']['llm_retry_count']}")

    @pytest.mark.asyncio
    async def test_node_with_short_context(self):
        """Test node with minimal context."""
        state = GraphRAGState(
            user_query="What is Python?",
            user_id="test-user-integration",
            constructed_context="Python: A high-level programming language.",
            metadata={},
        )

        result = await response_generation_node(state)

        # Verify response
        assert result["final_response"]
        assert len(result["final_response"]) > 0
        assert result["metadata"]["response_generation_completed"] is True

        print(f"\n✅ Short context response: {result['final_response']}")

    @pytest.mark.asyncio
    async def test_node_with_empty_context(self):
        """Test node with empty context (should still work)."""
        state = GraphRAGState(
            user_query="Explain Python programming language",
            user_id="test-user-integration",
            constructed_context="",
            metadata={},
        )

        result = await response_generation_node(state)

        # Verify response (LLM should handle empty context gracefully)
        assert result["final_response"]
        assert len(result["final_response"]) > 0

        print(f"\n✅ Empty context response: {result['final_response']}")

    @pytest.mark.asyncio
    async def test_node_metadata_tracking(self, sample_state):
        """Test that metadata is properly tracked."""
        sample_state.metadata = {
            "existing_key": "existing_value",
            "query_type": "test",
        }

        result = await response_generation_node(sample_state)

        # Verify existing metadata preserved
        assert result["metadata"]["existing_key"] == "existing_value"
        assert result["metadata"]["query_type"] == "test"

        # Verify new metadata added
        assert result["metadata"]["response_generation_completed"] is True
        assert result["metadata"]["llm_tokens_used"] > 0
        assert result["metadata"]["llm_latency_ms"] > 0
        assert result["metadata"]["response_length"] > 0

        print(f"\n✅ Metadata tracking verified")
        print(f"   - Existing metadata preserved")
        print(f"   - LLM metadata added: {result['metadata']['llm_tokens_used']} tokens")


class TestOpenRouterServiceRetryLogic:
    """Test retry logic with real API (use with caution - may cause rate limits)."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_successful_retry_behavior(self):
        """
        Test that retry logic works correctly.

        This test uses valid API calls and verifies retry_count is 0 on success.
        """
        service = OpenRouterService()

        result = await service.generate_completion(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello.",
            max_tokens=10,
            temperature=0.7,
            max_retries=3,
        )

        # On success, retry_count should be 0
        assert result["retry_count"] == 0

        print(f"\n✅ No retries needed (retry_count = {result['retry_count']})")


class TestResponseGenerationPerformance:
    """Test performance characteristics of response generation."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_response_latency(self, sample_state):
        """Test that response generation completes within reasonable time."""
        import time

        start_time = time.time()
        result = await response_generation_node(sample_state)
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000

        # Verify completion within 30 seconds (generous for API call + retries)
        assert total_time_ms < 30000, f"Response took {total_time_ms}ms (>30s)"

        # Verify latency metadata matches
        assert result["metadata"]["llm_latency_ms"] < total_time_ms

        print(f"\n✅ Response latency: {result['metadata']['llm_latency_ms']}ms")
        print(f"✅ Total time: {total_time_ms:.0f}ms")

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_token_usage_reasonable(self, sample_state):
        """Test that token usage is reasonable for given context."""
        result = await response_generation_node(sample_state)

        # Context is ~50 words, response should be reasonable
        assert result["metadata"]["llm_tokens_used"] < 2000, (
            f"Token usage too high: {result['metadata']['llm_tokens_used']}"
        )

        print(f"\n✅ Token usage: {result['metadata']['llm_tokens_used']} tokens")
        print(f"   - Prompt: {result['metadata']['llm_prompt_tokens']}")
        print(f"   - Completion: {result['metadata']['llm_completion_tokens']}")
