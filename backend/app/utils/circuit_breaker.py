"""
Circuit Breaker Pattern for External API Calls.

Prevents cascading failures when external services are down or degraded.
Implements the three-state circuit breaker pattern: CLOSED, OPEN, HALF_OPEN.

RATE-001 FIX: Protects OpenRouter LLM API from overload and provides
graceful degradation during outages.
"""

import time
import asyncio
import logging
from enum import Enum
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Failure threshold exceeded, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes to close from half-open
    timeout_seconds: int = 60  # Time to wait before trying half-open
    window_seconds: int = 60  # Rolling window for failure counting


class CircuitBreaker:
    """
    Circuit breaker for protecting external API calls.

    Tracks failures and automatically opens the circuit to prevent
    cascading failures. Provides fallback responses during outages.

    Example:
        >>> breaker = CircuitBreaker(name="openrouter_api")
        >>> async def api_call():
        ...     # Make risky API call
        ...     return result
        >>> result = await breaker.call(api_call, fallback="Service unavailable")
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit breaker
            config: Configuration for thresholds and timeouts
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_changed_at = time.time()

        # Failure tracking (rolling window)
        self._failure_times: list[float] = []

        logger.info(
            f"[CircuitBreaker:{name}] Initialized with "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        return self._state == CircuitState.OPEN

    def _clean_old_failures(self) -> None:
        """Remove failures outside the rolling window."""
        current_time = time.time()
        cutoff_time = current_time - self.config.window_seconds

        self._failure_times = [t for t in self._failure_times if t > cutoff_time]

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open state."""
        if self._state != CircuitState.OPEN:
            return False

        if not self._last_failure_time:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.timeout_seconds

    def _record_success(self) -> None:
        """Record successful API call and update state."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.info(
                f"[CircuitBreaker:{self.name}] Success in HALF_OPEN state "
                f"({self._success_count}/{self.config.success_threshold})"
            )

            if self._success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self._state == CircuitState.OPEN:
            # First success after opening, transition to half-open
            self._transition_to_half_open()
            self._success_count = 1

    def _record_failure(self) -> None:
        """Record failed API call and update state."""
        current_time = time.time()
        self._failure_times.append(current_time)
        self._last_failure_time = current_time

        # Clean old failures outside window
        self._clean_old_failures()

        failure_count = len(self._failure_times)

        logger.warning(
            f"[CircuitBreaker:{self.name}] Failure recorded "
            f"({failure_count}/{self.config.failure_threshold} in {self.config.window_seconds}s window)"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open means service still unhealthy
            self._transition_to_open()

        elif self._state == CircuitState.CLOSED:
            if failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state (blocking requests)."""
        if self._state != CircuitState.OPEN:
            logger.error(
                f"[CircuitBreaker:{self.name}] OPENING circuit "
                f"(failures={len(self._failure_times)}, "
                f"threshold={self.config.failure_threshold})"
            )
            self._state = CircuitState.OPEN
            self._state_changed_at = time.time()
            self._success_count = 0

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state (testing recovery)."""
        if self._state != CircuitState.HALF_OPEN:
            logger.info(
                f"[CircuitBreaker:{self.name}] Entering HALF_OPEN state "
                f"(testing service recovery)"
            )
            self._state = CircuitState.HALF_OPEN
            self._state_changed_at = time.time()
            self._success_count = 0

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (normal operation)."""
        if self._state != CircuitState.CLOSED:
            logger.info(f"[CircuitBreaker:{self.name}] CLOSING circuit " f"(service recovered)")
            self._state = CircuitState.CLOSED
            self._state_changed_at = time.time()
            self._failure_times.clear()
            self._success_count = 0

    async def call(
        self, func: Callable[..., Any], fallback: Optional[Any] = None, *args, **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            fallback: Fallback value if circuit is open
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func, or fallback if circuit is open

        Raises:
            Exception: If circuit is open and no fallback provided
        """
        # Check if we should attempt reset to half-open
        if self._should_attempt_reset():
            self._transition_to_half_open()

        # Block requests if circuit is open
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._state_changed_at
            logger.warning(
                f"[CircuitBreaker:{self.name}] Circuit OPEN, request blocked "
                f"(open for {elapsed:.1f}s, timeout={self.config.timeout_seconds}s)"
            )

            if fallback is not None:
                return fallback

            raise Exception(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Service unavailable. Try again in "
                f"{self.config.timeout_seconds - int(elapsed)}s"
            )

        # Allow request through circuit
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            raise

    def get_stats(self) -> dict:
        """
        Get current circuit breaker statistics.

        Returns:
            Dict with state, failure count, uptime, etc.
        """
        self._clean_old_failures()

        return {
            "name": self.name,
            "state": self._state.value,
            "failures_in_window": len(self._failure_times),
            "failure_threshold": self.config.failure_threshold,
            "window_seconds": self.config.window_seconds,
            "time_in_current_state": time.time() - self._state_changed_at,
            "last_failure_time": self._last_failure_time,
        }
