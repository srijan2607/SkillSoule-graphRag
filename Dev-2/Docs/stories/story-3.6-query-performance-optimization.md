# Story 3.6: Query Performance Optimization

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.6
**Estimated Effort:** 1-2 days

## User Story
**As a** system,
**I want** to maintain <5s query response time with metrics,
**so that** user experience remains fast (NFR1).

## Acceptance Criteria
1. Performance profiling identifies bottlenecks
2. Optimizations: cache centrality, batch closeness, query timeout (>4s abort)
3. 90% queries <5s, median 2-3s
4. Monitoring: log query time per intent

## Integration Verification
**IV1:** 100 random queries p95 <5s
**IV2:** Centrality cache hit rate >95%
**IV3:** Timeout returns partial results + warning (not error)

## Dependencies
**Depends on:** Stories 3.1-3.5
**Blocks:** None (Epic 3 complete)

---

## Technical Implementation

### Components

**Primary Service:** `LangGraphService` (OPTIMIZED v2.0)
- **Location:** `backend/app/services/langgraph_service.py`
- **Method:** Enhanced with caching, batching, timeout handling

**Caching Layer:** `CentralityCacheService` (NEW v2.0)
- **Location:** `backend/app/services/cache/centrality_cache.py`
- **Method:** `get_cached_centrality()`, `cache_centrality_scores()`

**Monitoring:** `PerformanceMonitor` (ENHANCED v2.0)
- **Location:** `backend/app/utils/metrics.py`
- **Method:** Log query time per intent

### Performance Optimizations

From `components.md`:

**1. Cache Centrality (Redis)**
```python
class CentralityCacheService:
    """Cache centrality scores to avoid recomputation."""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour

    async def get_cached_centrality(self, skill_name: str) -> Optional[float]:
        """Get cached centrality score for skill."""
        key = f"centrality:{skill_name}"
        value = await self.redis.get(key)
        return float(value) if value else None

    async def cache_centrality_scores(self, scores: Dict[str, float]):
        """Batch cache centrality scores."""
        pipeline = self.redis.pipeline()
        for skill_name, score in scores.items():
            pipeline.setex(f"centrality:{skill_name}", self.ttl, score)
        await pipeline.execute()
```

**2. Batch Closeness Queries**
```python
async def batch_closeness(skill_pairs: List[Tuple[str, str]]) -> List[float]:
    """
    Batch closeness calculations for efficiency.
    Process 10 skill pairs in single Neo4j transaction.
    """
    closeness_scores = []
    batch_size = 10

    for i in range(0, len(skill_pairs), batch_size):
        batch = skill_pairs[i:i + batch_size]
        scores = await neo4j_repo.batch_shortest_path(batch)
        closeness_scores.extend([
            1.0 / (1.0 + distance) for distance in scores
        ])

    return closeness_scores
```

**3. Query Timeout (4 seconds)**
```python
async def execute_query_with_timeout(query: str, timeout: float = 4.0):
    """
    Execute query with timeout. Return partial results + warning if timeout.
    """
    try:
        result = await asyncio.wait_for(
            langgraph_workflow.ainvoke(query),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        # Return partial results from completed nodes
        partial_result = get_partial_results()
        partial_result['warning'] = 'Query timeout - returning partial results'
        return partial_result
```

### Testing

**Unit Test:** `tests/unit/test_performance.py`
- Test centrality cache hit/miss
- Validate batch closeness efficiency
- Test timeout handling (partial results)

**Integration Test:** `tests/integration/test_performance.py`
- Run 100 random queries
- Verify p95 <5 seconds, median 2-3 seconds
- Measure cache hit rate (>95%)
- Test timeout returns partial results (not error)

### Performance Targets

- **p95 Query Time:** <5 seconds (NFR1)
- **Median Query Time:** 2-3 seconds
- **Cache Hit Rate:** >95% for centrality queries
- **Timeout Behavior:** Return partial results + warning (not error)

### Security Considerations

From `security.md`:
- **Redis Security:** Use authentication, TLS for cache connections
- **Cache Poisoning:** Validate cached values before use
- **Timeout Safety:** Ensure partial results don't leak sensitive data
