# Story 2.3: Closeness Metric Calculation

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.3
**Estimated Effort:** 1-2 days

## User Story
**As a** system,
**I want** to convert shortest path distance into normalized closeness scores,
**so that** metric values are intuitive (0-1 range, higher = more related).

## Acceptance Criteria
1. Function `calculate_closeness(skill_a, skill_b)` implemented
2. Formula: `Closeness(A,B) = 1 / (1 + Distance(A,B))`
3. Returns: closeness (0-1), distance, path
4. Edge cases: no path (0.0), same skill (1.0)
5. Batch mode for efficiency

## Integration Verification
**IV1:** Formula correctness (direct≈0.9-1.0, 2-hop≈0.5-0.7, no path=0.0)
**IV2:** Batch 200 pairs in <5s
**IV3:** Deterministic (same input = same output)

## Dependencies
**Depends on:** Story 2.2
**Blocks:** Story 2.4, 2.5

---

## Technical Implementation

### Components

**Primary Service:** `ShortestPathService` (NEW v2.0)
- **Location:** `backend/app/services/graph/shortest_path.py`
- **Method:** `calculate_closeness(skill_a, skill_b)`, `calculate_closeness_batch(skill_pairs)`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_read()` for batch queries

### Database Schema Changes

**Formula Implementation:**

```python
def calculate_closeness(skill_a: str, skill_b: str) -> float:
    """
    Convert shortest path distance to normalized closeness score.

    Returns:
        float: Closeness score (0-1)
            - 1.0: Same skill (distance=0)
            - ~0.9-1.0: Direct connection (distance≈0.1-0.2)
            - ~0.5-0.7: 2-hop path (distance≈0.5-1.0)
            - 0.0: No path (distance=infinity)
    """
    distance = shortest_path_distance(skill_a, skill_b)

    if distance == float('inf'):
        return 0.0

    if distance == 0:
        return 1.0

    return 1.0 / (1.0 + distance)
```

### Testing

**Unit Test:** `tests/unit/test_closeness.py`
- Test formula correctness: `closeness(A, A) = 1.0`
- Validate ranges: direct≈0.9-1.0, 2-hop≈0.5-0.7, no path=0.0
- Test determinism: same input → same output

**Integration Test:** `tests/integration/test_closeness.py`
- Batch process 200 skill pairs
- Verify batch completion <5 seconds
- Validate closeness scores within expected ranges

### Performance Targets

- **Single Query:** <500ms (delegates to shortest path)
- **Batch Mode:** 200 pairs in <5 seconds
- **Deterministic:** Same inputs always produce identical outputs

### Security Considerations

From `security.md`:
- **Input Validation:** Validate skill names before computation
- **Batch Limits:** Max 500 pairs per batch request
- **Caching:** Cache closeness scores for frequently queried pairs (TTL: 1 hour)
