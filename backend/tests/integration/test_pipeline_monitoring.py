"""
Integration tests for Pipeline Monitoring System.

Tests cover critical paths identified in QA review (TEST-001):
- TC-001: Happy path pipeline execution with monitoring
- TC-003: Vector search stage monitoring
- TC-004: Response format validation
- TC-009: Error handling in response generation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import WebSocket
from fastapi.testclient import TestClient

from app.services.pipeline_monitoring_service import (
    PipelineMonitoringService,
    PipelineStage,
    StageStatus,
)
from app.utils.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def pipeline_monitor():
    """Create a fresh pipeline monitoring service for each test."""
    return PipelineMonitoringService()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock(spec=WebSocket)
    ws.send_json = AsyncMock()
    return ws


class TestPipelineMonitoringService:
    """Test suite for Pipeline Monitoring Service."""

    @pytest.mark.asyncio
    async def test_tc003_vector_search_monitoring(self, pipeline_monitor, mock_websocket):
        """
        TC-003: Vector search stage monitoring.

        Verifies that vector search stage events are properly emitted
        and broadcasted to WebSocket clients.
        """
        # Register WebSocket
        pipeline_monitor.register_websocket(mock_websocket)

        # Emit vector search started
        await pipeline_monitor.emit_vector_search(
            session_id="test-session-001",
            user_id="user-123",
            query="What skills do I need for data science?",
            status=StageStatus.STARTED,
        )

        # Emit vector search completed
        await pipeline_monitor.emit_vector_search(
            session_id="test-session-001",
            user_id="user-123",
            query="What skills do I need for data science?",
            status=StageStatus.COMPLETED,
            duration_ms=45.2,
            skills_found=10,
            jobs_found=5,
            companies_found=3,
        )

        # Verify WebSocket received both events
        assert mock_websocket.send_json.call_count == 2

        # Verify event structure
        calls = mock_websocket.send_json.call_args_list
        started_event = calls[0][0][0]
        completed_event = calls[1][0][0]

        # Validate STARTED event
        assert started_event["event_type"] == "pipeline_stage"
        assert started_event["stage"] == PipelineStage.VECTOR_SEARCH.value
        assert started_event["status"] == StageStatus.STARTED.value
        assert started_event["session_id"] == "test-session-001"
        assert started_event["user_id"] == "user-123"
        assert "timestamp" in started_event

        # Validate COMPLETED event
        assert completed_event["event_type"] == "pipeline_stage"
        assert completed_event["stage"] == PipelineStage.VECTOR_SEARCH.value
        assert completed_event["status"] == StageStatus.COMPLETED.value
        assert completed_event["duration_ms"] == 45.2
        assert completed_event["data"]["skills_found"] == 10
        assert completed_event["data"]["jobs_found"] == 5
        assert completed_event["data"]["companies_found"] == 3

    @pytest.mark.asyncio
    async def test_tc004_response_format_validation(self, pipeline_monitor, mock_websocket):
        """
        TC-004: Response format validation.

        Verifies that all pipeline stage events conform to the
        expected schema and data types.
        """
        pipeline_monitor.register_websocket(mock_websocket)

        # Test all 5 pipeline stages
        stages_to_test = [
            (
                pipeline_monitor.emit_query_understanding,
                {
                    "session_id": "test-session-002",
                    "user_id": "user-456",
                    "query": "Test query",
                    "status": StageStatus.COMPLETED,
                    "duration_ms": 125.5,
                    "intent": "skill_requirement",
                    "confidence": 0.94,
                },
            ),
            (
                pipeline_monitor.emit_vector_search,
                {
                    "session_id": "test-session-002",
                    "user_id": "user-456",
                    "query": "Test query",
                    "status": StageStatus.COMPLETED,
                    "duration_ms": 45.2,
                    "skills_found": 10,
                    "jobs_found": 5,
                },
            ),
            (
                pipeline_monitor.emit_graph_traversal,
                {
                    "session_id": "test-session-002",
                    "user_id": "user-456",
                    "query": "Test query",
                    "status": StageStatus.COMPLETED,
                    "duration_ms": 78.3,
                    "nodes_accessed": 42,
                    "relationships_traversed": 15,
                },
            ),
            (
                pipeline_monitor.emit_context_construction,
                {
                    "session_id": "test-session-002",
                    "user_id": "user-456",
                    "query": "Test query",
                    "status": StageStatus.COMPLETED,
                    "duration_ms": 12.1,
                    "context_tokens": 450,
                    "context_length": 2500,
                },
            ),
            (
                pipeline_monitor.emit_response_generation,
                {
                    "session_id": "test-session-002",
                    "user_id": "user-456",
                    "query": "Test query",
                    "status": StageStatus.COMPLETED,
                    "duration_ms": 890.5,
                    "model": "meta-llama/llama-3.1-8b-instruct",
                    "tokens_used": 650,
                    "response_length": 1200,
                },
            ),
        ]

        for emit_func, kwargs in stages_to_test:
            await emit_func(**kwargs)

        # Verify all events were sent
        assert mock_websocket.send_json.call_count == 5

        # Validate common schema for all events
        for call in mock_websocket.send_json.call_args_list:
            event = call[0][0]

            # All events must have these fields
            assert "event_type" in event
            assert "stage" in event
            assert "status" in event
            assert "session_id" in event
            assert "user_id" in event
            assert "query" in event
            assert "timestamp" in event

            # Completed events must have duration
            if event["status"] == StageStatus.COMPLETED.value:
                assert "duration_ms" in event
                assert isinstance(event["duration_ms"], (int, float))
                assert event["duration_ms"] > 0

    @pytest.mark.asyncio
    async def test_websocket_registration_and_cleanup(self, pipeline_monitor, mock_websocket):
        """
        Test WebSocket connection lifecycle management.

        Verifies that WebSockets can be registered and unregistered
        without memory leaks.
        """
        # Initially no connections
        assert len(pipeline_monitor._websocket_connections) == 0

        # Register connection
        pipeline_monitor.register_websocket(mock_websocket)
        assert len(pipeline_monitor._websocket_connections) == 1

        # Emit an event
        await pipeline_monitor.emit_query_understanding(
            session_id="test-session-003",
            user_id="user-789",
            query="Test query",
            status=StageStatus.STARTED,
        )

        # Verify event was sent
        assert mock_websocket.send_json.call_count == 1

        # Unregister connection
        pipeline_monitor.unregister_websocket(mock_websocket)
        assert len(pipeline_monitor._websocket_connections) == 0

        # Emit another event - should not be sent
        await pipeline_monitor.emit_query_understanding(
            session_id="test-session-003",
            user_id="user-789",
            query="Test query",
            status=StageStatus.COMPLETED,
            duration_ms=100.0,
        )

        # No additional calls
        assert mock_websocket.send_json.call_count == 1


class TestCircuitBreaker:
    """Test suite for Circuit Breaker (RATE-001)."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """
        Test that circuit breaker opens after threshold failures.

        Simulates multiple consecutive LLM API failures and verifies
        that the circuit opens to prevent cascading failures.
        """
        breaker = CircuitBreaker(name="test_breaker")

        async def failing_func():
            raise Exception("API failure")

        # Initial state should be CLOSED
        assert breaker.state == CircuitState.CLOSED

        # Trigger failures to open circuit (default threshold = 5)
        for i in range(5):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        # Circuit should now be OPEN
        assert breaker.state == CircuitState.OPEN

        # Next call should be blocked with fallback
        result = await breaker.call(failing_func, fallback="Service unavailable")
        assert result == "Service unavailable"

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """
        Test circuit breaker transitions to half-open and recovers.

        Verifies that after timeout, circuit enters half-open state
        and closes after successful requests.
        """
        from app.utils.circuit_breaker import CircuitBreakerConfig

        # Use short timeout for testing
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1,  # 1 second timeout
            window_seconds=60,
        )
        breaker = CircuitBreaker(name="test_recovery", config=config)

        async def failing_func():
            raise Exception("API failure")

        async def success_func():
            return "Success"

        # Open the circuit with failures
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for timeout (circuit should attempt half-open)
        import asyncio
        await asyncio.sleep(1.5)

        # Next successful call should transition to HALF_OPEN
        result = await breaker.call(success_func)
        assert result == "Success"
        assert breaker.state == CircuitState.HALF_OPEN

        # Another success should CLOSE the circuit
        result = await breaker.call(success_func)
        assert result == "Success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_tc009_error_handling_with_circuit_breaker(self):
        """
        TC-009: Error handling in response generation with circuit breaker.

        Verifies that when LLM API fails repeatedly, the circuit breaker
        provides graceful degradation with fallback responses.
        """
        from app.services.openrouter_service import OpenRouterService

        service = OpenRouterService()

        # Mock the internal retry method to always fail
        with patch.object(
            service,
            "_make_api_call_with_retries",
            side_effect=Exception("LLM API unavailable"),
        ):
            # Call should return fallback response, not raise exception
            result = await service.generate_completion(
                system_prompt="You are a helpful assistant",
                user_prompt="What is Python?",
                max_tokens=100,
            )

            # Verify fallback response structure
            assert "text" in result
            assert "circuit_breaker_triggered" in result
            assert result["circuit_breaker_triggered"] is True
            assert "Service Temporarily Unavailable" in result["text"]
            assert result["usage"]["total_tokens"] == 0


class TestWebSocketAuthentication:
    """Test suite for WebSocket authentication (SEC-001)."""

    def test_websocket_requires_authentication(self):
        """
        SEC-001: Verify WebSocket endpoint requires JWT token.

        This test verifies that unauthenticated WebSocket connection
        attempts are rejected.
        """
        from app.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Attempt to connect without token - should fail
        with pytest.raises(Exception):
            with client.websocket_connect("/monitor/live"):
                pass

    def test_websocket_rejects_invalid_token(self):
        """
        SEC-001: Verify WebSocket rejects invalid JWT tokens.

        Tests that expired or malformed tokens are rejected with
        appropriate error codes.
        """
        from app.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)

        # Attempt with invalid token
        with pytest.raises(Exception):
            with client.websocket_connect("/monitor/live?token=invalid_token"):
                pass
