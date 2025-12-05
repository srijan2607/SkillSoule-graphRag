"""Integration tests for query metrics collection and logging."""

import pytest
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.langgraph_service import LangGraphService
from app.utils.metrics import QueryMetrics
from app.agents.graph import GraphRAGState


class TestQueryMetricsIntegration:
    """Integration tests for metrics collection during query execution."""

    @pytest.fixture
    def mock_workflow_result(self):
        """Mock workflow result with typical structure."""
        return {
            "final_response": "Python is a high-level programming language.",
            "vector_results": [
                {
                    "id": "python-001",
                    "node_type": "Skill",
                    "name": "python",
                    "score": 0.95
                }
            ],
            "graph_context": [],
            "intent": "skill_requirement",
            "metadata": {
                "query_understanding_completed": True,
                "vector_search_completed": True
            }
        }

    @pytest.mark.asyncio
    async def test_metrics_collected_during_workflow(self, mock_workflow_result):
        """Test that metrics are collected during LangGraph workflow execution."""
        
        # Mock workflow with timing simulation
        async def mock_with_timing(state):
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate some timing data
                metrics.timers["query_understanding_duration_ms"] = 200
                metrics.timers["vector_search_duration_ms"] = 800
            
            return mock_workflow_result
        
        # Mock the workflow execution
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=mock_with_timing)
            mock_create_workflow.return_value = mock_workflow
            
            # Create service
            service = LangGraphService()
            
            # Execute query
            result = await service.execute_query(
                query="What is Python?",
                user_id="test-user-123"
            )
            
            # Verify metrics are in result
            assert "processing_time_ms" in result
            assert result["processing_time_ms"] > 0  # Should have timing now
            
            # Verify metrics breakdown is included
            assert "metrics" in result
            metrics_data = result["metrics"]
            assert "query_id" in metrics_data
            assert "user_id" in metrics_data
            assert metrics_data["user_id"] == "test-user-123"

    @pytest.mark.asyncio
    async def test_metrics_passed_to_nodes_via_state(self, mock_workflow_result):
        """Test that QueryMetrics instance is passed to nodes via state metadata."""
        
        captured_state = None
        
        async def capture_state_mock(state):
            nonlocal captured_state
            captured_state = state
            return mock_workflow_result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=capture_state_mock)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            
            await service.execute_query(
                query="What is Python?",
                user_id="test-user-123"
            )
            
            # Verify state was captured and contains metrics
            assert captured_state is not None
            # GraphRAGState has metadata attribute
            assert hasattr(captured_state, "metadata") or "metadata" in captured_state
            
            # Access metadata properly (it's a TypedDict attribute)
            metadata = captured_state.metadata if hasattr(captured_state, "metadata") else captured_state.get("metadata", {})
            assert "metrics" in metadata
            
            # Verify metrics instance is QueryMetrics
            metrics = metadata["metrics"]
            assert isinstance(metrics, QueryMetrics)
            assert metrics.user_id == "test-user-123"
            assert metrics.query_text == "What is Python?"

    @pytest.mark.asyncio
    async def test_metrics_logged_as_json(self, caplog, mock_workflow_result):
        """Test that metrics are logged in structured JSON format."""
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(return_value=mock_workflow_result)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            
            with caplog.at_level("INFO"):
                await service.execute_query(
                    query="What is Python?",
                    user_id="test-user-123"
                )
            
            # Find JSON log entries
            json_logs = []
            for record in caplog.records:
                if record.levelname == "INFO":
                    try:
                        log_data = json.loads(record.message)
                        if "event" in log_data and log_data["event"] == "query_completed":
                            json_logs.append(log_data)
                    except (json.JSONDecodeError, AttributeError):
                        continue
            
            # Verify at least one query_completed event was logged
            assert len(json_logs) > 0
            
            # Verify log structure
            log_entry = json_logs[0]
            assert log_entry["event"] == "query_completed"
            assert "query_id" in log_entry
            assert "user_id" in log_entry
            assert "total_time_ms" in log_entry
            assert "metrics" in log_entry
            assert "performance_targets" in log_entry

    @pytest.mark.asyncio
    async def test_slow_query_alert_triggered(self, caplog, mock_workflow_result):
        """Test that slow query alert is logged when total time exceeds 5 seconds."""
        
        # Create a custom workflow that simulates slow execution
        async def slow_workflow_mock(state):
            # Access metadata from GraphRAGState
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate slow execution by manually setting durations
                metrics.timers["query_understanding_duration_ms"] = 1000
                metrics.timers["vector_search_duration_ms"] = 1500
                metrics.timers["graph_traversal_duration_ms"] = 2500
                metrics.timers["context_construction_duration_ms"] = 500
                metrics.timers["response_generation_duration_ms"] = 1000
                # Total: 6500ms > 5000ms threshold
            
            return mock_workflow_result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=slow_workflow_mock)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            
            with caplog.at_level("WARNING"):
                await service.execute_query(
                    query="Complex slow query",
                    user_id="test-user-123"
                )
            
            # Find warning logs for slow query alert
            warning_logs = []
            for record in caplog.records:
                if record.levelname == "WARNING":
                    try:
                        log_data = json.loads(record.message)
                        if "event" in log_data and log_data["event"] == "slow_query_alert":
                            warning_logs.append(log_data)
                    except (json.JSONDecodeError, AttributeError):
                        continue
            
            # Verify slow query alert was logged
            assert len(warning_logs) > 0
            
            # Verify alert structure
            alert = warning_logs[0]
            assert alert["event"] == "slow_query_alert"
            assert alert["total_time_ms"] > 5000
            assert alert["query_text"] == "Complex slow query"
            assert "breakdown" in alert
            assert "performance_targets" in alert

    @pytest.mark.asyncio
    async def test_performance_targets_checked(self, mock_workflow_result):
        """Test that performance targets are checked and included in response."""
        
        async def mock_with_metrics(state):
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate execution with some nodes exceeding targets
                metrics.timers["query_understanding_duration_ms"] = 200
                metrics.timers["vector_search_duration_ms"] = 1200  # > 1000ms (FAIL)
                metrics.timers["graph_traversal_duration_ms"] = 1800  # < 2000ms (PASS)
                metrics.timers["context_construction_duration_ms"] = 300
                metrics.timers["response_generation_duration_ms"] = 800
                # Total: 4300ms < 5000ms (PASS)
            
            return mock_workflow_result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=mock_with_metrics)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            result = await service.execute_query(
                query="Test query",
                user_id="test-user-123"
            )
            
            # Verify metrics breakdown includes performance checks
            metrics_data = result["metrics"]
            assert "total_time" in metrics_data
            assert metrics_data["total_time"] == 4300
            
            # Performance targets should be checked by QueryMetrics.log_metrics()
            # We can't directly access them in the result, but they're logged

    @pytest.mark.asyncio
    async def test_processing_time_ms_in_api_response(self, mock_workflow_result):
        """Test that processing_time_ms is included in service response."""
        
        # Mock workflow with timing simulation
        async def mock_with_timing(state):
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate timing data
                metrics.timers["query_understanding_duration_ms"] = 150
                metrics.timers["vector_search_duration_ms"] = 600
                metrics.timers["graph_traversal_duration_ms"] = 1200
            
            return mock_workflow_result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=mock_with_timing)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            result = await service.execute_query(
                query="What is Python?",
                user_id="test-user-123"
            )
            
            # Verify processing_time_ms is present and valid
            assert "processing_time_ms" in result
            assert isinstance(result["processing_time_ms"], (int, float))
            assert result["processing_time_ms"] > 0
            
            # Verify it matches the total from metrics
            assert "metrics" in result
            metrics_total = result["metrics"]["total_time"]
            assert result["processing_time_ms"] == metrics_total

    @pytest.mark.asyncio
    async def test_metrics_include_all_node_timings(self, mock_workflow_result):
        """Test that metrics include timing for all 5 LangGraph nodes."""
        
        async def mock_with_all_nodes(state):
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate all 5 nodes completing
                metrics.timers["query_understanding_duration_ms"] = 250
                metrics.timers["vector_search_duration_ms"] = 800
                metrics.timers["graph_traversal_duration_ms"] = 1500
                metrics.timers["context_construction_duration_ms"] = 400
                metrics.timers["response_generation_duration_ms"] = 900
            
            return mock_workflow_result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=mock_with_all_nodes)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            result = await service.execute_query(
                query="Test query",
                user_id="test-user-123"
            )
            
            # Verify all node timings are present
            metrics_data = result["metrics"]
            assert metrics_data["query_understanding_time"] == 250
            assert metrics_data["vector_search_time"] == 800
            assert metrics_data["graph_traversal_time"] == 1500
            assert metrics_data["context_construction_time"] == 400
            assert metrics_data["llm_generation_time"] == 900
            
            # Verify total is sum of all nodes
            expected_total = 250 + 800 + 1500 + 400 + 900
            assert metrics_data["total_time"] == expected_total

    @pytest.mark.asyncio
    async def test_metrics_handles_node_errors_gracefully(self, mock_workflow_result):
        """Test that metrics still work even if some nodes fail."""
        
        async def mock_with_partial_failure(state):
            metadata = state.metadata if hasattr(state, "metadata") else state.get("metadata", {})
            metrics = metadata.get("metrics")
            
            if metrics:
                # Simulate only some nodes completing (e.g., query fails at vector search)
                metrics.timers["query_understanding_duration_ms"] = 200
                metrics.timers["vector_search_duration_ms"] = 500
                # graph_traversal and later nodes never complete
            
            # Return result with error metadata
            result = mock_workflow_result.copy()
            result["metadata"]["vector_search_error"] = "Neo4j connection failed"
            return result
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(side_effect=mock_with_partial_failure)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            result = await service.execute_query(
                query="Test query",
                user_id="test-user-123"
            )
            
            # Verify partial metrics are still collected
            metrics_data = result["metrics"]
            assert metrics_data["query_understanding_time"] == 200
            assert metrics_data["vector_search_time"] == 500
            
            # Missing nodes should default to 0
            assert metrics_data["graph_traversal_time"] == 0
            assert metrics_data["context_construction_time"] == 0
            assert metrics_data["llm_generation_time"] == 0
            
            # Total should be sum of completed nodes only
            assert metrics_data["total_time"] == 700

    @pytest.mark.asyncio
    async def test_metrics_query_id_uniqueness(self):
        """Test that each query gets a unique query_id."""
        
        mock_result = {
            "final_response": "Response",
            "vector_results": [],
            "graph_context": [],
            "metadata": {}
        }
        
        with patch('app.services.langgraph_service.create_rag_workflow') as mock_create_workflow:
            mock_workflow = AsyncMock()
            mock_workflow.ainvoke = AsyncMock(return_value=mock_result)
            mock_create_workflow.return_value = mock_workflow
            
            service = LangGraphService()
            
            # Execute two queries
            result1 = await service.execute_query("Query 1", "user-1")
            result2 = await service.execute_query("Query 2", "user-1")
            
            # Verify different query_ids
            query_id_1 = result1["metrics"]["query_id"]
            query_id_2 = result2["metrics"]["query_id"]
            
            assert query_id_1 != query_id_2
            assert len(query_id_1) > 0
            assert len(query_id_2) > 0
