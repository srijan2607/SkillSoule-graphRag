# Error Handling Strategy

## General Approach

- **Error Model:** Structured exception hierarchy with domain-specific exceptions
  - `GraphServiceError` → `CentralityCalculationError`, `ShortestPathError`
  - `LangGraphExecutionError` → `NodeExecutionError`, `StateValidationError`
  - `APIError` → `AuthenticationError`, `RateLimitError`, `ValidationError`
- **Exception Hierarchy:** Python standard `Exception` base class, custom exceptions inherit
- **Error Propagation:**
  - Services raise domain-specific exceptions
  - Routers catch exceptions, translate to HTTP status codes
  - LangGraph nodes catch exceptions, store in `state.metadata` for diagnostic responses

## Logging Standards

- **Library:** Python `logging` module (stdlib)
- **Format:** JSON structured logging for machine parsing
  ```json
  {
    "timestamp": "2025-11-17T10:30:45.123Z",
    "level": "INFO",
    "logger": "GraphMetricsService",
    "message": "Centrality calculation completed",
    "context": {
      "duration_ms": 28543,
      "skill_count": 5234,
      "avg_centrality": 0.42
    }
  }
  ```
- **Levels:**
  - `DEBUG`: Algorithm intermediate values (centrality iterations, path exploration)
  - `INFO`: Stage completion (centrality calculated, shortest path found)
  - `WARNING`: Performance degradation (centrality >20s, path query >400ms)
  - `ERROR`: Failures (Neo4j GDS unavailable, LLM API timeout)
  - `CRITICAL`: System-level failures (database connection lost)
- **Required Context:**
  - **Correlation ID:** `request_id` (UUID) for tracing query through pipeline
  - **Service Context:** `service_name` (e.g., "GraphMetricsService", "LangGraphService")
  - **User Context:** `user_id` (if authenticated, omit password_hash/email for security)

## Error Handling Patterns

### External API Errors

**OpenRouter LLM API:**
- **Retry Policy:** 3 retries with exponential backoff (1s, 2s, 4s)
- **Circuit Breaker:** Open circuit after 5 consecutive failures, half-open after 60s
- **Timeout Configuration:** 30s per request
- **Error Translation:**
  - 429 (rate limit) → Return cached response or generic fallback
  - 500 (server error) → Retry, fallback to shorter prompt
  - Timeout → Return partial response with disclaimer

**Neo4j GDS:**
- **Retry Policy:** 1 retry for transient errors (connection timeout), no retry for algorithm errors
- **Circuit Breaker:** N/A (database dependency, system unusable if down)
- **Timeout Configuration:** Centrality: 35s (NFR11 + 5s buffer), Shortest path: 1s
- **Error Translation:**
  - GDS unavailable → Fallback to approximate PageRank (centrality) or return "metric unavailable"
  - Timeout → Log warning, return query response without metric values

### Business Logic Errors

**Invalid Query Input:**
- **Custom Exceptions:** `InvalidQueryError` (empty query, unsupported intent)
- **User-Facing Errors:**
  ```json
  {
    "error": "Query cannot be empty",
    "error_code": "INVALID_QUERY_001",
    "suggestion": "Please provide a career-related question"
  }
  ```
- **Error Codes:** `INVALID_QUERY_*`, `SKILL_NOT_FOUND_*`, `JOB_NOT_FOUND_*`

**Metric Calculation Failures:**
- **Custom Exceptions:** `CentralityCalculationError`, `ShortestPathError`
- **User-Facing Errors:** Return query response with disclaimer
  ```
  "Note: Network metrics temporarily unavailable due to system maintenance. Basic career guidance provided."
  ```
- **Error Codes:** `METRIC_CALC_001` (centrality timeout), `METRIC_CALC_002` (no path found)

### Data Consistency

**Graph Schema Migration:**
- **Transaction Strategy:** Cypher transactions with `COMMIT` on success, `ROLLBACK` on failure
- **Compensation Logic:** Rollback script (`rollback_graph_v2.cypher`) to remove new properties/relationships
- **Idempotency:** Use `MERGE` instead of `CREATE` for upsert behavior, `COALESCE` for property defaults

**CSV Ingestion:**
- **Transaction Strategy:** Batch processing (1000 rows per transaction), commit per batch
- **Compensation Logic:** Log failed rows to `ingestion_errors.csv`, manual review and re-ingestion
- **Idempotency:** `MERGE` on skill_id/job_id prevents duplicates, update embeddings on re-ingestion

---
