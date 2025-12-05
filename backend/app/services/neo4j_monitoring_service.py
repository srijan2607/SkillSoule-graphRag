"""
Neo4j Query Monitoring Service.

Provides query logging, performance tracking, and real-time monitoring
for all Neo4j Cypher queries executed in the application.
"""

import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from collections import deque
from dataclasses import dataclass, asdict
from prisma import Prisma

logger = logging.getLogger(__name__)


@dataclass
class QueryLogEntry:
    """
    Represents a logged Neo4j query with execution details.
    """
    query_text: str
    parameters: Optional[Dict[str, Any]]
    operation_type: str
    execution_time_ms: float
    result_count: Optional[int]
    status: str
    error_message: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]
    source: Optional[str]
    metadata: Optional[Dict[str, Any]]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_text": self.query_text,
            "parameters": self.parameters,
            "operation_type": self.operation_type,
            "execution_time_ms": self.execution_time_ms,
            "result_count": self.result_count,
            "status": self.status,
            "error_message": self.error_message,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


class Neo4jMonitoringService:
    """
    Service for monitoring and logging Neo4j query operations.

    Features:
    - Query execution logging to PostgreSQL
    - In-memory cache for recent queries (fast access)
    - Real-time WebSocket broadcasting
    - Performance metrics aggregation
    - Query classification (READ/WRITE/VECTOR_SEARCH/GRAPH_TRAVERSAL)
    """

    def __init__(
        self,
        prisma_client: Prisma,
        max_cache_size: int = 1000,
        enable_persistence: bool = True
    ):
        """
        Initialize monitoring service.

        Args:
            prisma_client: Prisma client for PostgreSQL persistence
            max_cache_size: Maximum number of queries to keep in memory
            enable_persistence: Whether to persist logs to PostgreSQL
        """
        self.prisma = prisma_client
        self.max_cache_size = max_cache_size
        self.enable_persistence = enable_persistence

        # In-memory cache for recent queries (FIFO deque)
        self._query_cache: deque = deque(maxlen=max_cache_size)

        # WebSocket connections for real-time streaming
        self._websocket_connections: List[Any] = []

        # Performance metrics aggregation
        self._metrics = {
            "total_queries": 0,
            "total_execution_time_ms": 0.0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_execution_time_ms": 0.0,
            "operation_counts": {
                "READ": 0,
                "WRITE": 0,
                "VECTOR_SEARCH": 0,
                "GRAPH_TRAVERSAL": 0,
                "OTHER": 0
            }
        }

    async def log_query(
        self,
        query_text: str,
        parameters: Optional[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0,
        result_count: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a Neo4j query execution.

        Args:
            query_text: The Cypher query string
            parameters: Query parameters (dict)
            execution_time_ms: Query execution time in milliseconds
            result_count: Number of records returned
            status: Query status ("success" or "error")
            error_message: Error details if failed
            user_id: Optional user identifier
            session_id: Session identifier for grouping
            source: Source of query (e.g., "ingestion", "query_pipeline")
            metadata: Additional metadata

        Returns:
            str: Log entry ID (UUID)
        """
        # Classify operation type
        operation_type = self._classify_query(query_text)

        # Create log entry
        log_entry = QueryLogEntry(
            query_text=query_text,
            parameters=parameters,
            operation_type=operation_type,
            execution_time_ms=execution_time_ms,
            result_count=result_count,
            status=status,
            error_message=error_message,
            user_id=user_id,
            session_id=session_id,
            source=source,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )

        # Add to in-memory cache
        self._query_cache.append(log_entry)

        # Update metrics
        self._update_metrics(log_entry)

        # Broadcast to WebSocket connections
        await self._broadcast_to_websockets(log_entry)

        # Persist to PostgreSQL (async, non-blocking)
        log_id = None
        if self.enable_persistence:
            try:
                log_id = await self._persist_to_database(log_entry)
            except Exception as e:
                logger.error(f"Failed to persist query log to database: {str(e)}")
                # Don't raise - monitoring shouldn't break the app

        return log_id or "memory-only"

    async def execute_and_log(
        self,
        query_func: Callable,
        query_text: str,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute a Neo4j query and automatically log it.

        This is a wrapper function that executes the query, times it,
        and logs the execution details.

        Args:
            query_func: Async function that executes the query
            query_text: Cypher query string
            parameters: Query parameters
            user_id: Optional user identifier
            session_id: Session identifier
            source: Source of query
            metadata: Additional metadata

        Returns:
            Query results from query_func

        Example:
            >>> results = await monitoring_service.execute_and_log(
            ...     lambda: neo4j_repo.execute_query(query, params),
            ...     query_text=query,
            ...     parameters=params,
            ...     source="vector_search"
            ... )
        """
        start_time = time.time()
        status = "success"
        error_message = None
        result = None
        result_count = None

        try:
            result = await query_func()

            # Count results if it's a list
            if isinstance(result, list):
                result_count = len(result)
            elif isinstance(result, dict) and "data" in result:
                result_count = len(result["data"]) if isinstance(result["data"], list) else 1

        except Exception as e:
            status = "error"
            error_message = str(e)
            logger.error(f"Neo4j query failed: {str(e)}")
            raise  # Re-raise to preserve original error handling

        finally:
            execution_time_ms = (time.time() - start_time) * 1000

            # Log query execution
            await self.log_query(
                query_text=query_text,
                parameters=parameters,
                execution_time_ms=execution_time_ms,
                result_count=result_count,
                status=status,
                error_message=error_message,
                user_id=user_id,
                session_id=session_id,
                source=source,
                metadata=metadata
            )

        return result

    def get_recent_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent queries from in-memory cache.

        Args:
            limit: Maximum number of queries to return

        Returns:
            List of query log entries as dictionaries
        """
        queries = list(self._query_cache)[-limit:]
        return [q.to_dict() for q in reversed(queries)]

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated query performance metrics.

        Returns:
            Dictionary with performance statistics
        """
        return {
            **self._metrics,
            "cache_size": len(self._query_cache),
            "websocket_connections": len(self._websocket_connections)
        }

    async def search_queries(
        self,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        source: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search query logs with filters.

        Args:
            operation_type: Filter by operation type
            status: Filter by status ("success" or "error")
            source: Filter by source
            user_id: Filter by user ID
            session_id: Filter by session ID
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of matching query logs
        """
        if not self.enable_persistence:
            # Search in-memory cache only
            queries = list(self._query_cache)

            # Apply filters
            if operation_type:
                queries = [q for q in queries if q.operation_type == operation_type]
            if status:
                queries = [q for q in queries if q.status == status]
            if source:
                queries = [q for q in queries if q.source == source]
            if user_id:
                queries = [q for q in queries if q.user_id == user_id]
            if session_id:
                queries = [q for q in queries if q.session_id == session_id]

            # Pagination
            queries = queries[offset:offset + limit]
            return [q.to_dict() for q in queries]

        # Search in PostgreSQL
        where_filters = {}
        if operation_type:
            where_filters["operation_type"] = operation_type
        if status:
            where_filters["status"] = status
        if source:
            where_filters["source"] = source
        if user_id:
            where_filters["user_id"] = user_id
        if session_id:
            where_filters["session_id"] = session_id

        logs = await self.prisma.neo4jquerylog.find_many(
            where=where_filters,
            order={"created_at": "desc"},
            take=limit,
            skip=offset
        )

        return [log.dict() for log in logs]

    def register_websocket(self, websocket: Any):
        """Register a WebSocket connection for real-time query streaming."""
        self._websocket_connections.append(websocket)
        logger.info(f"WebSocket registered. Total connections: {len(self._websocket_connections)}")

    def unregister_websocket(self, websocket: Any):
        """Unregister a WebSocket connection."""
        if websocket in self._websocket_connections:
            self._websocket_connections.remove(websocket)
            logger.info(f"WebSocket unregistered. Total connections: {len(self._websocket_connections)}")

    async def _broadcast_to_websockets(self, log_entry: QueryLogEntry):
        """Broadcast query log to all connected WebSockets."""
        if not self._websocket_connections:
            return

        message = json.dumps(log_entry.to_dict())

        # Remove disconnected connections
        disconnected = []
        for ws in self._websocket_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"WebSocket send failed: {str(e)}")
                disconnected.append(ws)

        # Clean up disconnected connections
        for ws in disconnected:
            self.unregister_websocket(ws)

    async def _persist_to_database(self, log_entry: QueryLogEntry) -> str:
        """Persist query log to PostgreSQL."""
        # Prepare data with proper JSON field handling
        data = {
            "query_text": log_entry.query_text,
            "operation_type": log_entry.operation_type,
            "execution_time_ms": log_entry.execution_time_ms,
            "result_count": log_entry.result_count,
            "status": log_entry.status,
            "error_message": log_entry.error_message,
            "user_id": log_entry.user_id,
            "session_id": log_entry.session_id,
            "source": log_entry.source,
        }

        # Handle JSON fields - Prisma Python has issues with empty dicts
        # Skip parameters and metadata if they're empty or None
        if log_entry.parameters and len(log_entry.parameters) > 0:
            try:
                # Serialize to JSON string to handle datetime objects
                params_json = json.dumps(log_entry.parameters, default=str)
                data["parameters"] = json.loads(params_json)
            except Exception as e:
                logger.debug(f"Skipping parameters due to serialization error: {e}")

        if log_entry.metadata and len(log_entry.metadata) > 0:
            try:
                # Serialize to JSON string to handle datetime objects
                metadata_json = json.dumps(log_entry.metadata, default=str)
                data["metadata"] = json.loads(metadata_json)
            except Exception as e:
                logger.debug(f"Skipping metadata due to serialization error: {e}")

        log = await self.prisma.neo4jquerylog.create(data=data)
        return log.id

    def _classify_query(self, query_text: str) -> str:
        """
        Classify query operation type based on Cypher keywords.

        Args:
            query_text: Cypher query string

        Returns:
            Operation type: READ, WRITE, VECTOR_SEARCH, GRAPH_TRAVERSAL, or OTHER
        """
        query_upper = query_text.upper().strip()

        # Vector search
        if "db.index.vector.queryNodes" in query_text or "VECTOR" in query_upper:
            return "VECTOR_SEARCH"

        # Graph traversal (multi-hop patterns)
        if "-[" in query_text and ("OPTIONAL MATCH" in query_upper or query_text.count("-[") > 1):
            return "GRAPH_TRAVERSAL"

        # Write operations
        write_keywords = ["CREATE", "MERGE", "SET", "DELETE", "REMOVE", "DROP"]
        if any(keyword in query_upper for keyword in write_keywords):
            return "WRITE"

        # Read operations
        read_keywords = ["MATCH", "RETURN", "WHERE", "WITH"]
        if any(keyword in query_upper for keyword in read_keywords):
            return "READ"

        return "OTHER"

    def _update_metrics(self, log_entry: QueryLogEntry):
        """Update aggregated performance metrics."""
        self._metrics["total_queries"] += 1
        self._metrics["total_execution_time_ms"] += log_entry.execution_time_ms

        if log_entry.status == "success":
            self._metrics["successful_queries"] += 1
        else:
            self._metrics["failed_queries"] += 1

        # Update operation counts
        op_type = log_entry.operation_type
        if op_type in self._metrics["operation_counts"]:
            self._metrics["operation_counts"][op_type] += 1
        else:
            self._metrics["operation_counts"]["OTHER"] += 1

        # Update average execution time
        if self._metrics["total_queries"] > 0:
            self._metrics["avg_execution_time_ms"] = (
                self._metrics["total_execution_time_ms"] / self._metrics["total_queries"]
            )


# Global monitoring service instance
_monitoring_service: Optional[Neo4jMonitoringService] = None


def get_monitoring_service(prisma_client: Prisma) -> Neo4jMonitoringService:
    """
    Get or create the global monitoring service instance.

    Args:
        prisma_client: Prisma client for database persistence

    Returns:
        Neo4jMonitoringService instance
    """
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = Neo4jMonitoringService(prisma_client)
    return _monitoring_service
