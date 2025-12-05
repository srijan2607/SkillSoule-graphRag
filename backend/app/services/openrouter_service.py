"""
OpenRouter Service - LLM API client using OpenRouter.

Uses OpenAI SDK for compatibility with OpenRouter API.
Includes circuit breaker protection (RATE-001) to prevent cascading failures.
"""

import asyncio
import time
from typing import Dict, Any, Optional
import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.utils.logger import logger
from app.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# Module-level circuit breaker singleton (RATE-001 FIX)
# Protects OpenRouter API from overload and provides graceful degradation
_openrouter_circuit_breaker = CircuitBreaker(
    name="openrouter_api",
    config=CircuitBreakerConfig(
        failure_threshold=5,  # Open after 5 failures
        success_threshold=2,  # Close after 2 successes in half-open
        timeout_seconds=60,  # Wait 60s before trying again
        window_seconds=60,  # Count failures in 60s window
    ),
)


class OpenRouterService:
    """
    Service for interacting with OpenRouter LLM API.

    Uses OpenAI SDK with OpenRouter base URL for compatibility.
    Includes retry logic with exponential backoff for reliability.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        Initialize OpenRouter service.

        Args:
            api_key: OpenRouter API key (defaults to settings)
            base_url: OpenRouter base URL (defaults to settings)
            model: Model to use (defaults to settings)
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.model = model or settings.OPENROUTER_MODEL

        # Initialize OpenAI client with OpenRouter configuration
        # Timeout set to 180 seconds for reasoning models (DeepSeek-R1, o1, etc.)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=180.0,  # 3 minutes for reasoning models
        )

        logger.info(
            f"[OpenRouterService] Initialized with model: {self.model}, "
            f"base_url: {self.base_url}"
        )

    async def _make_api_call_with_retries(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        max_retries: int,
    ) -> Dict[str, Any]:
        """
        Internal method: Make LLM API call with retry logic.

        This method contains the actual retry loop and is wrapped by
        the circuit breaker in generate_completion().

        Args:
            system_prompt: System instructions
            user_prompt: User query and context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum retry attempts

        Returns:
            Dict with text, usage, model, latency_ms, retry_count

        Raises:
            Exception: If all retries fail
        """
        delays = [1, 2, 4]  # Exponential backoff delays in seconds

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                logger.info(
                    f"[OpenRouterService] Calling LLM (attempt {attempt + 1}/{max_retries}): "
                    f"system_prompt_len={len(system_prompt)}, "
                    f"user_prompt_len={len(user_prompt)}, "
                    f"max_tokens={max_tokens}, "
                    f"temperature={temperature}"
                )

                # Call OpenRouter API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

                latency_ms = int((time.time() - start_time) * 1000)

                # Extract response text
                response_text = response.choices[0].message.content or ""

                # Extract usage statistics
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }

                logger.info(
                    f"[OpenRouterService] LLM call succeeded: "
                    f"response_len={len(response_text)}, "
                    f"tokens_used={usage['total_tokens']}, "
                    f"latency_ms={latency_ms}, "
                    f"retry_count={attempt}"
                )

                return {
                    "text": response_text,
                    "usage": usage,
                    "model": self.model,
                    "latency_ms": latency_ms,
                    "retry_count": attempt,
                }

            except httpx.TimeoutException as e:
                logger.warning(
                    f"[OpenRouterService] Timeout on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                else:
                    logger.error("[OpenRouterService] All retry attempts exhausted (timeout)")
                    raise Exception("LLM API timeout after all retries")

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"[OpenRouterService] HTTP error on attempt {attempt + 1}/{max_retries}: "
                    f"status={e.response.status_code}, error={e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                else:
                    logger.error(
                        f"[OpenRouterService] All retry attempts exhausted "
                        f"(HTTP {e.response.status_code})"
                    )
                    raise Exception(
                        f"LLM API HTTP error {e.response.status_code} after all retries"
                    )

            except Exception as e:
                logger.warning(
                    f"[OpenRouterService] Unexpected error on attempt {attempt + 1}/{max_retries}: "
                    f"{type(e).__name__}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delays[attempt])
                else:
                    logger.error(
                        f"[OpenRouterService] All retry attempts exhausted: {type(e).__name__}"
                    )
                    raise Exception(f"LLM API error after all retries: {type(e).__name__}")

        # Should never reach here, but for type safety
        raise Exception("LLM API call failed unexpectedly")

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Generate LLM completion with circuit breaker protection and retry logic.

        RATE-001 FIX: Wraps LLM API calls with circuit breaker to prevent
        cascading failures during outages. Returns fallback response when
        circuit is open.

        Args:
            system_prompt: System instructions for the LLM
            user_prompt: User query and context
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            max_retries: Maximum retry attempts on failure

        Returns:
            Dict with:
                - text: Generated response text (or fallback if circuit open)
                - usage: Token usage statistics
                - model: Model name used
                - latency_ms: API call latency in milliseconds
                - retry_count: Number of retries (0 if first attempt succeeded)
                - circuit_breaker_triggered: True if fallback was used

        Note:
            If circuit breaker is OPEN, returns graceful fallback response
            instead of raising exception. Check circuit_breaker_triggered
            field to detect degraded mode.
        """
        # RATE-001: Fallback response when LLM API is unavailable
        fallback_response = {
            "text": (
                "⚠️ **Service Temporarily Unavailable**\n\n"
                "I apologize, but I'm currently unable to process your query due to "
                "temporary service issues with the AI response generation system.\n\n"
                "**What you can do:**\n"
                "- Try your query again in a minute\n"
                "- Simplify your question if it's complex\n"
                "- Contact support if the issue persists\n\n"
                "The knowledge graph search completed successfully, but I cannot "
                "generate a natural language response at this time. "
                "Your data is safe and will be available when service resumes.\n\n"
                "<details>\n"
                "<summary>🔧 Technical Details</summary>\n\n"
                "- Status: Circuit breaker OPEN (service protection activated)\n"
                "- Reason: Multiple consecutive API failures detected\n"
                "- Recovery: Automatic retry in 60 seconds\n"
                "</details>"
            ),
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "model": f"{self.model} (fallback)",
            "latency_ms": 0,
            "retry_count": 0,
            "circuit_breaker_triggered": True,
        }

        # RATE-001: Wrap API call with circuit breaker
        try:
            result = await _openrouter_circuit_breaker.call(
                self._make_api_call_with_retries,
                fallback=fallback_response,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=max_retries,
            )

            # Add circuit breaker status to result
            if "circuit_breaker_triggered" not in result:
                result["circuit_breaker_triggered"] = False

            return result

        except Exception as e:
            # If circuit breaker raised exception (no fallback scenario)
            # or some other unexpected error, return fallback gracefully
            logger.error(
                f"[OpenRouterService] Error in generate_completion: {str(e)}, "
                f"returning fallback response"
            )
            return fallback_response
