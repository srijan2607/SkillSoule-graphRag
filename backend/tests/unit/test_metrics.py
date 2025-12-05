"""Unit tests for QueryMetrics utility."""

import pytest
import time
import json
from app.utils.metrics import QueryMetrics


class TestQueryMetrics:
    """Test suite for QueryMetrics class."""

    def test_metrics_initialization(self):
        """Test QueryMetrics can be initialized with required fields."""
        metrics = QueryMetrics(
            query_id="test-query-123",
            user_id="user-456",
            query_text="What skills are needed for Python developer?"
        )

        assert metrics.query_id == "test-query-123"
        assert metrics.user_id == "user-456"
        assert metrics.query_text == "What skills are needed for Python developer?"
        assert metrics.timers == {}

    def test_start_timer(self):
        """Test starting a timer for a node."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        metrics.start_timer("vector_search")
        
        # Check that the start time was recorded
        assert "vector_search_start" in metrics.timers
        assert isinstance(metrics.timers["vector_search_start"], float)
        assert metrics.timers["vector_search_start"] > 0

    def test_end_timer(self):
        """Test ending a timer and calculating duration."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        metrics.start_timer("vector_search")
        time.sleep(0.01)  # Sleep 10ms
        duration = metrics.end_timer("vector_search")
        
        # Check duration is reasonable (>10ms, <100ms)
        assert duration >= 10
        assert duration < 100
        
        # Check that duration was stored
        assert "vector_search_duration_ms" in metrics.timers
        assert metrics.timers["vector_search_duration_ms"] == duration
        
        # Check that start time was removed
        assert "vector_search_start" not in metrics.timers

    def test_end_timer_without_start(self):
        """Test ending a timer that was never started."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        duration = metrics.end_timer("nonexistent_node")
        
        # Should return 0 if timer was never started
        assert duration == 0.0

    def test_get_summary(self):
        """Test getting summary of all durations."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        metrics.start_timer("query_understanding")
        time.sleep(0.01)
        metrics.end_timer("query_understanding")
        
        metrics.start_timer("vector_search")
        time.sleep(0.01)
        metrics.end_timer("vector_search")
        
        summary = metrics.get_summary()
        
        # Check summary contains both durations
        assert "query_understanding_duration_ms" in summary
        assert "vector_search_duration_ms" in summary
        
        # Check durations are reasonable
        assert summary["query_understanding_duration_ms"] >= 10
        assert summary["vector_search_duration_ms"] >= 10
        
        # Check start times are not included
        assert "query_understanding_start" not in summary
        assert "vector_search_start" not in summary

    def test_get_total_time(self):
        """Test calculating total time from all node durations."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        metrics.start_timer("node1")
        time.sleep(0.01)
        metrics.end_timer("node1")
        
        metrics.start_timer("node2")
        time.sleep(0.01)
        metrics.end_timer("node2")
        
        total = metrics.get_total_time()
        
        # Total should be sum of both node durations (~20ms)
        assert total >= 20
        assert total < 100

    def test_check_performance_targets_all_pass(self):
        """Test performance target checks when all targets are met."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Simulate fast execution
        metrics.timers["vector_search_duration_ms"] = 500  # < 1000ms target
        metrics.timers["graph_traversal_duration_ms"] = 1500  # < 2000ms target
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["context_construction_duration_ms"] = 300
        metrics.timers["response_generation_duration_ms"] = 800
        # Total: 3300ms < 5000ms target
        
        targets = metrics.check_performance_targets()
        
        assert targets["vector_search_ok"] is True
        assert targets["graph_traversal_ok"] is True
        assert targets["total_ok"] is True

    def test_check_performance_targets_vector_search_fail(self):
        """Test performance target checks when vector search is slow."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Simulate slow vector search
        metrics.timers["vector_search_duration_ms"] = 1500  # > 1000ms target (FAIL)
        metrics.timers["graph_traversal_duration_ms"] = 1000
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["context_construction_duration_ms"] = 300
        metrics.timers["response_generation_duration_ms"] = 500
        
        targets = metrics.check_performance_targets()
        
        assert targets["vector_search_ok"] is False  # Should fail
        assert targets["graph_traversal_ok"] is True
        assert targets["total_ok"] is True  # Total still under 5s

    def test_check_performance_targets_graph_traversal_fail(self):
        """Test performance target checks when graph traversal is slow."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Simulate slow graph traversal
        metrics.timers["vector_search_duration_ms"] = 800
        metrics.timers["graph_traversal_duration_ms"] = 2500  # > 2000ms target (FAIL)
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["context_construction_duration_ms"] = 300
        metrics.timers["response_generation_duration_ms"] = 500
        
        targets = metrics.check_performance_targets()
        
        assert targets["vector_search_ok"] is True
        assert targets["graph_traversal_ok"] is False  # Should fail
        assert targets["total_ok"] is True  # Total still under 5s

    def test_check_performance_targets_total_fail(self):
        """Test performance target checks when total time exceeds 5 seconds."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Simulate very slow execution (total > 5s)
        metrics.timers["vector_search_duration_ms"] = 1500
        metrics.timers["graph_traversal_duration_ms"] = 2500
        metrics.timers["query_understanding_duration_ms"] = 500
        metrics.timers["context_construction_duration_ms"] = 500
        metrics.timers["response_generation_duration_ms"] = 1500
        # Total: 6500ms > 5000ms target (FAIL)
        
        targets = metrics.check_performance_targets()
        
        assert targets["vector_search_ok"] is False
        assert targets["graph_traversal_ok"] is False
        assert targets["total_ok"] is False  # Should fail

    def test_to_dict(self):
        """Test converting metrics to dictionary format."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Simulate some timing data
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["vector_search_duration_ms"] = 800
        metrics.timers["graph_traversal_duration_ms"] = 1500
        metrics.timers["context_construction_duration_ms"] = 300
        metrics.timers["response_generation_duration_ms"] = 900
        
        result = metrics.to_dict()
        
        # Check all required fields are present
        assert result["query_id"] == "test-1"
        assert result["user_id"] == "user-1"
        assert result["query_understanding_time"] == 200
        assert result["vector_search_time"] == 800
        assert result["graph_traversal_time"] == 1500
        assert result["context_construction_time"] == 300
        assert result["llm_generation_time"] == 900
        assert result["total_time"] == 3700

    def test_to_dict_with_missing_nodes(self):
        """Test to_dict when some nodes haven't completed."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Only some nodes completed
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["vector_search_duration_ms"] = 800
        
        result = metrics.to_dict()
        
        # Check completed nodes have values
        assert result["query_understanding_time"] == 200
        assert result["vector_search_time"] == 800
        
        # Check missing nodes default to 0
        assert result["graph_traversal_time"] == 0
        assert result["context_construction_time"] == 0
        assert result["llm_generation_time"] == 0
        
        # Total should be sum of completed nodes
        assert result["total_time"] == 1000

    def test_log_metrics_fast_query(self, caplog):
        """Test logging metrics for a fast query (no alert)."""
        metrics = QueryMetrics(
            query_id="test-1",
            user_id="user-1",
            query_text="What skills for Python?"
        )
        
        # Simulate fast execution (<5s)
        metrics.timers["query_understanding_duration_ms"] = 200
        metrics.timers["vector_search_duration_ms"] = 800
        metrics.timers["graph_traversal_duration_ms"] = 1500
        metrics.timers["context_construction_duration_ms"] = 300
        metrics.timers["response_generation_duration_ms"] = 700
        # Total: 3500ms
        
        with caplog.at_level("INFO"):
            metrics.log_metrics()
        
        # Check INFO log was created
        info_logs = [record for record in caplog.records if record.levelname == "INFO"]
        assert len(info_logs) > 0
        
        # Check log contains metrics
        log_message = info_logs[0].message
        log_data = json.loads(log_message)
        
        assert log_data["event"] == "query_completed"
        assert log_data["query_id"] == "test-1"
        assert log_data["user_id"] == "user-1"
        assert log_data["total_time_ms"] == 3500
        
        # Should NOT have a warning log for slow query
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) == 0

    def test_log_metrics_slow_query_alert(self, caplog):
        """Test logging metrics triggers alert for slow query (>5s)."""
        metrics = QueryMetrics(
            query_id="test-slow",
            user_id="user-1",
            query_text="Complex query that takes long"
        )
        
        # Simulate slow execution (>5s)
        metrics.timers["query_understanding_duration_ms"] = 500
        metrics.timers["vector_search_duration_ms"] = 1500
        metrics.timers["graph_traversal_duration_ms"] = 2500
        metrics.timers["context_construction_duration_ms"] = 500
        metrics.timers["response_generation_duration_ms"] = 1500
        # Total: 6500ms > 5000ms threshold
        
        with caplog.at_level("WARNING"):
            metrics.log_metrics()
        
        # Check WARNING log was created
        warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
        assert len(warning_logs) > 0
        
        # Check alert contains metrics and query text
        alert_message = warning_logs[0].message
        alert_data = json.loads(alert_message)
        
        assert alert_data["event"] == "slow_query_alert"
        assert alert_data["query_id"] == "test-slow"
        assert alert_data["total_time_ms"] == 6500
        assert alert_data["query_text"] == "Complex query that takes long"
        assert "breakdown" in alert_data
        assert alert_data["breakdown"]["vector_search_duration_ms"] == 1500

    def test_multiple_timers_concurrent(self):
        """Test that multiple timers can be active simultaneously."""
        metrics = QueryMetrics(query_id="test-1", user_id="user-1")
        
        # Start multiple timers
        metrics.start_timer("node1")
        time.sleep(0.01)
        metrics.start_timer("node2")
        time.sleep(0.01)
        
        # End them in reverse order
        duration2 = metrics.end_timer("node2")
        duration1 = metrics.end_timer("node1")
        
        # node1 should have longer duration (started first)
        assert duration1 > duration2
        assert duration1 >= 20  # At least 20ms
        assert duration2 >= 10  # At least 10ms
        
        # Both should be recorded
        summary = metrics.get_summary()
        assert len(summary) == 2
