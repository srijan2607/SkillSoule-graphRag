"""
Monitoring API endpoints for Neo4j query logging and real-time streaming.

Provides REST endpoints to view query logs, performance metrics,
and WebSocket endpoint for real-time query monitoring.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from prisma import Prisma

from app.dependencies import get_prisma_client, get_current_user_optional
from app.services.neo4j_monitoring_service import get_monitoring_service
from app.services.pipeline_monitoring_service import get_pipeline_monitoring_service
from app.models.user import User
from app.utils.jwt import verify_jwt_token
from app.exceptions import AuthenticationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitoring"])


@router.get("/queries")
async def get_recent_queries(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of queries to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    status: Optional[str] = Query(None, description="Filter by status (success/error)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    prisma: Prisma = Depends(get_prisma_client),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Get recent Neo4j query logs with optional filtering.

    **Query Parameters:**
    - `limit`: Maximum number of queries to return (1-500)
    - `offset`: Pagination offset for results
    - `operation_type`: Filter by operation type (READ, WRITE, VECTOR_SEARCH, GRAPH_TRAVERSAL)
    - `status`: Filter by execution status (success, error)
    - `source`: Filter by query source (e.g., "ingestion", "query_pipeline")
    - `session_id`: Filter by session identifier

    **Response:**
    ```json
    {
        "queries": [
            {
                "query_text": "MATCH (s:Skill) RETURN s LIMIT 10",
                "operation_type": "READ",
                "execution_time_ms": 45.2,
                "status": "success",
                "timestamp": "2025-10-25T12:34:56.789Z"
            }
        ],
        "count": 50,
        "limit": 50,
        "offset": 0
    }
    ```

    **Authorization:** Optional - provides user_id filtering if authenticated
    """
    try:
        monitoring_service = get_monitoring_service(prisma)

        # Add user_id filter if authenticated
        user_id = current_user.id if current_user else None

        queries = await monitoring_service.search_queries(
            operation_type=operation_type,
            status=status,
            source=source,
            user_id=user_id,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

        return {"queries": queries, "count": len(queries), "limit": limit, "offset": offset}

    except Exception as e:
        logger.error(f"Failed to fetch query logs: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch query logs", "message": str(e)}
        )


@router.get("/stats")
async def get_monitoring_stats(prisma: Prisma = Depends(get_prisma_client)):
    """
    Get aggregated query performance statistics.

    Returns real-time metrics about Neo4j query execution including:
    - Total queries executed
    - Success/failure counts
    - Average execution time
    - Operation type breakdown
    - Cache statistics

    **Response:**
    ```json
    {
        "total_queries": 15234,
        "successful_queries": 15100,
        "failed_queries": 134,
        "avg_execution_time_ms": 127.5,
        "total_execution_time_ms": 1942350.0,
        "operation_counts": {
            "READ": 8500,
            "WRITE": 4200,
            "VECTOR_SEARCH": 2000,
            "GRAPH_TRAVERSAL": 500,
            "OTHER": 34
        },
        "cache_size": 1000,
        "websocket_connections": 2
    }
    ```

    **Authorization:** None required (read-only metrics)
    """
    try:
        monitoring_service = get_monitoring_service(prisma)
        metrics = monitoring_service.get_metrics()

        return metrics

    except Exception as e:
        logger.error(f"Failed to fetch monitoring stats: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch statistics", "message": str(e)}
        )


@router.get("/queries/slow")
async def get_slow_queries(
    threshold_ms: float = Query(1000.0, ge=0, description="Minimum execution time in milliseconds"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of queries to return"),
    prisma: Prisma = Depends(get_prisma_client),
):
    """
    Get slow queries exceeding the specified execution time threshold.

    Useful for identifying performance bottlenecks and optimization opportunities.

    **Query Parameters:**
    - `threshold_ms`: Minimum execution time in milliseconds (default: 1000ms = 1 second)
    - `limit`: Maximum number of queries to return (1-100)

    **Response:**
    ```json
    {
        "slow_queries": [
            {
                "query_text": "MATCH (s:Skill)-[:SIMILAR_TO*3]->(related) RETURN ...",
                "execution_time_ms": 2345.6,
                "operation_type": "GRAPH_TRAVERSAL",
                "timestamp": "2025-10-25T12:34:56.789Z"
            }
        ],
        "count": 5,
        "threshold_ms": 1000.0
    }
    ```

    **Authorization:** None required
    """
    try:
        slow_queries = await prisma.neo4jquerylog.find_many(
            where={"execution_time_ms": {"gte": threshold_ms}},
            order={"execution_time_ms": "desc"},
            take=limit,
        )

        return {
            "slow_queries": [q.dict() for q in slow_queries],
            "count": len(slow_queries),
            "threshold_ms": threshold_ms,
        }

    except Exception as e:
        logger.error(f"Failed to fetch slow queries: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch slow queries", "message": str(e)}
        )


@router.get("/queries/{query_id}")
async def get_query_by_id(query_id: str, prisma: Prisma = Depends(get_prisma_client)):
    """
    Get detailed information about a specific query by ID.

    **Path Parameters:**
    - `query_id`: UUID of the query log entry

    **Response:**
    ```json
    {
        "id": "uuid",
        "query_text": "MATCH (s:Skill {id: $id}) RETURN s",
        "parameters": {"id": "python-001"},
        "operation_type": "READ",
        "execution_time_ms": 23.5,
        "result_count": 1,
        "status": "success",
        "metadata": {...},
        "timestamp": "2025-10-25T12:34:56.789Z"
    }
    ```

    **Status Codes:**
    - 200: Query log found and returned
    - 404: Query log not found
    - 500: Server error
    """
    try:
        query_log = await prisma.neo4jquerylog.find_unique(where={"id": query_id})

        if not query_log:
            return JSONResponse(
                status_code=404, content={"error": "Query log not found", "query_id": query_id}
            )

        return query_log.dict()

    except Exception as e:
        logger.error(f"Failed to fetch query log {query_id}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Failed to fetch query log", "message": str(e)}
        )


@router.websocket("/live")
async def websocket_live_queries(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    prisma: Prisma = Depends(get_prisma_client),
):
    """
    WebSocket endpoint for real-time query and pipeline monitoring.

    **SECURITY:** Requires JWT authentication via query parameter.

    Streams both Neo4j query logs AND Graph RAG pipeline stage events.

    **Connection:**
    ```javascript
    const token = localStorage.getItem('access_token');
    const ws = new WebSocket(`ws://localhost:8000/monitor/live?token=${token}`);

    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.event_type === 'pipeline_stage') {
            console.log('Pipeline stage:', message.stage, message.status);
        } else if (message.event_type === 'neo4j_query') {
            console.log('Query executed:', message.query_text);
        }
    };
    ```

    **Message Formats:**

    1. Pipeline Stage Event:
    ```json
    {
        "event_type": "pipeline_stage",
        "stage": "vector_search",
        "status": "completed",
        "session_id": "uuid",
        "user_id": "uuid",
        "duration_ms": 45.2,
        "data": {
            "skills_found": 10,
            "jobs_found": 5
        },
        "timestamp": "2025-10-25T12:34:56.789Z"
    }
    ```

    2. Neo4j Query Event:
    ```json
    {
        "event_type": "neo4j_query",
        "query_text": "MATCH (s:Skill) WHERE s.name = $name RETURN s",
        "execution_time_ms": 23.5,
        "status": "success",
        "timestamp": "2025-10-25T12:34:56.789Z"
    }
    ```

    **Connection Lifecycle:**
    - Client connects with valid JWT token
    - Server validates authentication
    - Server registers with both monitoring services
    - Server broadcasts pipeline stages + Neo4j queries in real-time
    - Client disconnects → server automatically unregisters

    **Authorization:**
    - Only authenticated users can connect
    - Token must be valid and not expired
    - Connection rejected with 1008 (Policy Violation) if unauthorized
    """
    # SECURITY FIX (SEC-001): Validate JWT token before accepting connection
    try:
        payload = verify_jwt_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            logger.warning("WebSocket connection rejected: No user_id in token")
            await websocket.close(code=1008, reason="Invalid token: No user_id")
            return

        logger.info(f"WebSocket authentication successful for user_id={user_id}")

    except Exception as e:
        logger.warning(f"WebSocket connection rejected: {str(e)}")
        await websocket.close(code=1008, reason=f"Authentication failed: {str(e)}")
        return

    # Accept connection after successful authentication
    await websocket.accept()
    monitoring_service = get_monitoring_service(prisma)
    pipeline_monitor = get_pipeline_monitoring_service()

    try:
        # Register WebSocket with BOTH monitoring services
        monitoring_service.register_websocket(websocket)
        pipeline_monitor.register_websocket(websocket)
        logger.info("WebSocket client connected to /monitor/live (Neo4j + Pipeline)")

        # Send welcome message
        await websocket.send_json(
            {
                "event_type": "connection_established",
                "message": "Connected to monitoring stream (Neo4j queries + RAG pipeline)",
                "timestamp": str(
                    logger.root.handlers[0].formatter.formatTime(
                        logging.LogRecord("", 0, "", 0, "", (), None)
                    )
                ),
            }
        )

        # Keep connection alive and wait for disconnect
        while True:
            # Wait for client messages (ping/pong for keep-alive)
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /monitor/live")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
    finally:
        # Unregister WebSocket from BOTH monitoring services
        monitoring_service.unregister_websocket(websocket)
        pipeline_monitor.unregister_websocket(websocket)
        logger.info("WebSocket client unregistered from Neo4j + Pipeline monitors")
