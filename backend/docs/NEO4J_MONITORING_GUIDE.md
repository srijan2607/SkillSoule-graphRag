# Neo4j Query Monitoring System - User Guide

## Overview

The Neo4j Query Monitoring System provides comprehensive visibility into all Cypher queries executed in the Graph RAG application. It enables:

- **Query Logging**: All Cypher queries logged to PostgreSQL with execution details
- **Performance Tracking**: Execution time, result counts, and success/failure metrics
- **Real-Time Streaming**: WebSocket endpoint for live query monitoring
- **Query Classification**: Automatic categorization (READ/WRITE/VECTOR_SEARCH/GRAPH_TRAVERSAL)
- **Filtering & Search**: Query logs by operation type, status, source, user, session

---

## Architecture

### Components

1. **`Neo4jMonitoringService`** - Core monitoring service with in-memory cache and PostgreSQL persistence
2. **`MonitoredNeo4jRepository`** - Wrapper for Neo4jRepository with automatic logging
3. **Monitoring API Router** (`/monitor/*`) - REST + WebSocket endpoints
4. **Prisma Schema** - `Neo4jQueryLog` table for persistent storage

### Data Flow

```
Neo4j Query Execution
  ↓
MonitoredNeo4jRepository.execute_and_log()
  ↓
Neo4jMonitoringService
  ├→ In-Memory Cache (deque, max 1000 queries)
  ├→ PostgreSQL (Neo4jQueryLog table)
  └→ WebSocket Broadcast (real-time clients)
```

---

## API Endpoints

### 1. Get Recent Queries

**Endpoint:** `GET /monitor/queries`

**Query Parameters:**
- `limit` (1-500, default: 50) - Maximum number of queries to return
- `offset` (default: 0) - Pagination offset
- `operation_type` - Filter by operation type (READ/WRITE/VECTOR_SEARCH/GRAPH_TRAVERSAL)
- `status` - Filter by status (success/error)
- `source` - Filter by query source (e.g., "ingestion", "query_pipeline")
- `session_id` - Filter by session identifier

**Example Request:**
```bash
curl "http://localhost:8000/monitor/queries?limit=20&operation_type=VECTOR_SEARCH&status=success"
```

**Example Response:**
```json
{
  "queries": [
    {
      "query_text": "CALL db.index.vector.queryNodes('skill_embedding_idx', 15, $query_embedding) YIELD node, score...",
      "operation_type": "VECTOR_SEARCH",
      "execution_time_ms": 45.2,
      "result_count": 10,
      "status": "success",
      "source": "vector_search_skills",
      "timestamp": "2025-10-25T12:34:56.789Z"
    }
  ],
  "count": 20,
  "limit": 20,
  "offset": 0
}
```

---

### 2. Get Query by ID

**Endpoint:** `GET /monitor/queries/{query_id}`

**Example Request:**
```bash
curl "http://localhost:8000/monitor/queries/uuid-here"
```

**Example Response:**
```json
{
  "id": "uuid-here",
  "query_text": "MATCH (s:Skill {id: $id}) RETURN s",
  "parameters": {"id": "python-001"},
  "operation_type": "READ",
  "execution_time_ms": 23.5,
  "result_count": 1,
  "status": "success",
  "metadata": {"node_type": "Skill"},
  "timestamp": "2025-10-25T12:34:56.789Z"
}
```

---

### 3. Get Performance Statistics

**Endpoint:** `GET /monitor/stats`

**Example Request:**
```bash
curl "http://localhost:8000/monitor/stats"
```

**Example Response:**
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

---

### 4. Get Slow Queries

**Endpoint:** `GET /monitor/queries/slow`

**Query Parameters:**
- `threshold_ms` (default: 1000) - Minimum execution time in milliseconds
- `limit` (1-100, default: 20) - Maximum number of queries

**Example Request:**
```bash
curl "http://localhost:8000/monitor/queries/slow?threshold_ms=500&limit=10"
```

**Example Response:**
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
  "threshold_ms": 500.0
}
```

---

### 5. Real-Time WebSocket Stream

**Endpoint:** `WS /monitor/live`

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/monitor/live');

ws.onopen = () => {
  console.log('Connected to query monitoring stream');
};

ws.onmessage = (event) => {
  const queryLog = JSON.parse(event.data);

  console.log(`Query: ${queryLog.query_text}`);
  console.log(`Operation: ${queryLog.operation_type}`);
  console.log(`Execution Time: ${queryLog.execution_time_ms}ms`);
  console.log(`Status: ${queryLog.status}`);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from query monitoring stream');
};

// Keep-alive ping/pong
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send('ping');
  }
}, 30000);
```

**Python Example:**
```python
import asyncio
import websockets
import json

async def monitor_queries():
    uri = "ws://localhost:8000/monitor/live"

    async with websockets.connect(uri) as websocket:
        print("Connected to query monitoring stream")

        while True:
            message = await websocket.recv()
            data = json.loads(message)

            print(f"Query: {data.get('query_text')}")
            print(f"Execution Time: {data.get('execution_time_ms')}ms")
            print(f"Status: {data.get('status')}")
            print("---")

asyncio.run(monitor_queries())
```

---

## Integration Guide

### Option 1: Use MonitoredNeo4jRepository (Recommended)

Replace `Neo4jRepository` with `MonitoredNeo4jRepository` for automatic monitoring:

```python
from app.repositories.monitored_neo4j_repository import MonitoredNeo4jRepository
from app.dependencies import get_prisma

# Create monitored repository
neo4j_repo = MonitoredNeo4jRepository(
    uri=settings.NEO4J_URI,
    user=settings.NEO4J_USER,
    password=settings.NEO4J_PASSWORD,
    prisma_client=get_prisma(),
    session_id="ingestion-session-123",  # Optional
    enable_monitoring=True
)

await neo4j_repo.connect()

# All queries are automatically monitored
results = await neo4j_repo.vector_search_skills(
    query_embedding=embedding,
    k=10,
    user_id="user-123"  # Optional
)
```

### Option 2: Manual Integration

Use `Neo4jMonitoringService.execute_and_log()` to wrap individual queries:

```python
from app.services.neo4j_monitoring_service import get_monitoring_service
from app.dependencies import get_prisma

monitoring_service = get_monitoring_service(get_prisma())

# Wrap query execution
async def execute_fn():
    return await neo4j_repo.execute_query(query, params)

results = await monitoring_service.execute_and_log(
    query_func=execute_fn,
    query_text=query,
    parameters=params,
    source="custom_source",
    user_id="user-123",
    session_id="session-456",
    metadata={"custom_key": "custom_value"}
)
```

### Option 3: Manual Logging Only

Log queries without automatic execution wrapping:

```python
import time
from app.services.neo4j_monitoring_service import get_monitoring_service

monitoring_service = get_monitoring_service(get_prisma())

# Execute query manually
start_time = time.time()
try:
    results = await neo4j_repo.execute_query(query, params)
    execution_time_ms = (time.time() - start_time) * 1000

    # Log after execution
    await monitoring_service.log_query(
        query_text=query,
        parameters=params,
        execution_time_ms=execution_time_ms,
        result_count=len(results),
        status="success",
        source="manual_logging"
    )
except Exception as e:
    execution_time_ms = (time.time() - start_time) * 1000

    # Log error
    await monitoring_service.log_query(
        query_text=query,
        parameters=params,
        execution_time_ms=execution_time_ms,
        status="error",
        error_message=str(e),
        source="manual_logging"
    )
    raise
```

---

## Configuration

### Environment Variables

No additional environment variables required. Uses existing:
- `DATABASE_URL` - PostgreSQL connection (Prisma)
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - Neo4j connection

### Monitoring Settings

Configure in `Neo4jMonitoringService` initialization:

```python
monitoring_service = Neo4jMonitoringService(
    prisma_client=prisma,
    max_cache_size=1000,  # In-memory cache size
    enable_persistence=True  # PostgreSQL logging
)
```

---

## Database Schema

### Neo4jQueryLog Table

```sql
CREATE TABLE neo4j_query_logs (
  id UUID PRIMARY KEY,
  query_text TEXT NOT NULL,
  parameters JSONB,
  operation_type VARCHAR NOT NULL,  -- READ, WRITE, VECTOR_SEARCH, GRAPH_TRAVERSAL
  execution_time_ms FLOAT NOT NULL,
  result_count INTEGER,
  status VARCHAR NOT NULL,  -- success, error
  error_message TEXT,
  user_id VARCHAR,
  session_id VARCHAR,
  source VARCHAR,  -- ingestion, query_pipeline, vector_search, etc.
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW(),

  INDEX idx_operation_type (operation_type),
  INDEX idx_status (status),
  INDEX idx_created_at (created_at),
  INDEX idx_execution_time_ms (execution_time_ms),
  INDEX idx_user_id (user_id),
  INDEX idx_session_id (session_id),
  INDEX idx_source (source)
);
```

---

## Query Classification

Queries are automatically classified into operation types:

| Operation Type | Detection Rules |
|----------------|-----------------|
| `VECTOR_SEARCH` | Contains `db.index.vector.queryNodes` or `VECTOR` keyword |
| `GRAPH_TRAVERSAL` | Multiple relationship patterns (`-[`), `OPTIONAL MATCH` |
| `WRITE` | Contains `CREATE`, `MERGE`, `SET`, `DELETE`, `REMOVE`, `DROP` |
| `READ` | Contains `MATCH`, `RETURN`, `WHERE`, `WITH` |
| `OTHER` | Doesn't match above patterns |

---

## Use Cases

### 1. Debugging Slow Queries

```bash
# Find queries taking > 1 second
curl "http://localhost:8000/monitor/queries/slow?threshold_ms=1000"
```

### 2. Monitoring Ingestion Pipeline

```bash
# Get all ingestion queries
curl "http://localhost:8000/monitor/queries?source=ingestion&limit=100"
```

### 3. Analyzing Query Performance by Type

```bash
# Get statistics breakdown
curl "http://localhost:8000/monitor/stats"

# Get all vector search queries
curl "http://localhost:8000/monitor/queries?operation_type=VECTOR_SEARCH"
```

### 4. Tracking User Activity

```bash
# Get queries for specific user (requires authentication)
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/monitor/queries?user_id=user-123"
```

### 5. Real-Time Development Debugging

Connect WebSocket client during development to see all queries in real-time as they execute.

---

## Performance Considerations

1. **In-Memory Cache**: Limited to 1000 most recent queries (configurable)
2. **PostgreSQL Persistence**: All queries stored permanently (consider retention policies)
3. **WebSocket Broadcasting**: Minimal overhead, async non-blocking
4. **Query Logging Overhead**: ~1-2ms per query for logging operation

**Recommendation**: Enable monitoring in development/staging. For production, consider:
- Sampling queries (log 10% of queries)
- Disabling monitoring for specific endpoints
- Setting up database retention policies (delete logs older than 30 days)

---

## Troubleshooting

### Queries Not Appearing in Logs

**Check:**
1. Monitoring enabled: `enable_monitoring=True` in MonitoredNeo4jRepository
2. Prisma client connected: `await prisma.connect()`
3. Database migrations applied: `prisma migrate deploy`

### WebSocket Connection Fails

**Check:**
1. CORS settings in `main.py` allow WebSocket connections
2. WebSocket endpoint accessible: `ws://localhost:8000/monitor/live`
3. Client sends ping/pong for keep-alive

### High Memory Usage

**Solution:**
Reduce in-memory cache size:

```python
monitoring_service = Neo4jMonitoringService(
    prisma_client=prisma,
    max_cache_size=500  # Reduce from default 1000
)
```

---

## Future Enhancements

- [ ] Query performance alerting (Slack/email notifications for slow queries)
- [ ] Query sampling (log 10% of queries in production)
- [ ] Retention policies (auto-delete old logs)
- [ ] Dashboard UI for query visualization
- [ ] Query explain plans integration
- [ ] Distributed tracing integration (OpenTelemetry)

---

## Support

For issues or questions:
1. Check logs: `docker logs backend-container`
2. Verify database connection: `GET /health`
3. Review monitoring stats: `GET /monitor/stats`
