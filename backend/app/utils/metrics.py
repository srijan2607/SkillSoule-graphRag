"""
Query performance metrics collection and tracking.
"""
import time
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, field

from app.utils.logger import logger


@dataclass
class QueryMetrics:
    """Collect and track query performance metrics."""

    query_id: str
    user_id: str
    query_text: Optional[str] = None
    timers: Dict[str, float] = field(default_factory=dict)

    def start_timer(self, node_name: str) -> None:
        """Start timer for a node.
        
        Args:
            node_name: Name of the node being timed
        """
        self.timers[f"{node_name}_start"] = time.time()

    def end_timer(self, node_name: str) -> float:
        """End timer for a node and calculate duration.
        
        Args:
            node_name: Name of the node to stop timing
            
        Returns:
            Duration in milliseconds
        """
        start_key = f"{node_name}_start"
        if start_key in self.timers:
            duration_ms = (time.time() - self.timers[start_key]) * 1000
            self.timers[f"{node_name}_duration_ms"] = duration_ms
            del self.timers[start_key]
            return duration_ms
        return 0.0

    def get_summary(self) -> Dict[str, float]:
        """Get metrics summary with all durations.
        
        Returns:
            Dictionary of node durations in milliseconds
        """
        return {k: v for k, v in self.timers.items() if k.endswith("_duration_ms")}

    def get_total_time(self) -> float:
        """Calculate total time from all node durations.
        
        Returns:
            Total time in milliseconds
        """
        summary = self.get_summary()
        return sum(summary.values())

    def check_performance_targets(self) -> Dict[str, bool]:
        """Check if performance targets are met.
        
        Performance targets:
        - Vector search: < 1000ms
        - Graph traversal: < 2000ms
        - Total query: < 5000ms
        
        Returns:
            Dictionary with target check results
        """
        summary = self.get_summary()
        total_time = self.get_total_time()
        
        return {
            "vector_search_ok": summary.get("vector_search_duration_ms", 0) < 1000,
            "graph_traversal_ok": summary.get("graph_traversal_duration_ms", 0) < 2000,
            "total_ok": total_time < 5000
        }

    def log_metrics(self) -> None:
        """Log metrics in structured JSON format."""
        summary = self.get_summary()
        total_time = self.get_total_time()
        performance_targets = self.check_performance_targets()
        
        # Log successful query metrics
        logger.info(
            json.dumps({
                "event": "query_completed",
                "query_id": self.query_id,
                "user_id": self.user_id,
                "total_time_ms": total_time,
                "metrics": summary,
                "performance_targets": performance_targets
            })
        )
        
        # Alert for slow queries (>5 seconds)
        if total_time > 5000:
            logger.warning(
                json.dumps({
                    "event": "slow_query_alert",
                    "query_id": self.query_id,
                    "user_id": self.user_id,
                    "query_text": self.query_text,
                    "total_time_ms": total_time,
                    "breakdown": summary,
                    "performance_targets": performance_targets
                })
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for API response or storage.
        
        Returns:
            Dictionary with all metrics data
        """
        summary = self.get_summary()
        return {
            "query_id": self.query_id,
            "user_id": self.user_id,
            "query_understanding_time": summary.get("query_understanding_duration_ms", 0),
            "vector_search_time": summary.get("vector_search_duration_ms", 0),
            "graph_traversal_time": summary.get("graph_traversal_duration_ms", 0),
            "context_construction_time": summary.get("context_construction_duration_ms", 0),
            "llm_generation_time": summary.get("response_generation_duration_ms", 0),
            "total_time": self.get_total_time()
        }
