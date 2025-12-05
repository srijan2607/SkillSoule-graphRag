# Story 2.2: Shortest Path Distance Calculation (Dijkstra's Algorithm)

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.2
**Estimated Effort:** 2-3 days

## User Story
**As a** career advisor user,
**I want** to calculate shortest path distance between skills,
**so that** I can quantify skill-to-skill transfer difficulty.

## Acceptance Criteria
1. Function `calculate_shortest_path(skill_a, skill_b)` implemented using Neo4j Dijkstra
2. Returns: distance (float), path (list), path_length (int)
3. Edge distance: `d(s1,s2) = 1 / co_occurrence_count`
4. Handles: no path (distance=infinity), direct connection, edge cases
5. Performance: <500ms per query (NFR12)

## Integration Verification
**IV1:** Path correctness (HTML→React through CSS/JavaScript)
**IV2:** 100 random pairs average <500ms
**IV3:** v1.1 Cypher queries unchanged speed

## Dependencies
**Depends on:** Story 1.3 (uses COMPLEMENTS weights)
**Blocks:** Story 2.3 (closeness uses shortest path)

---

## Technical Implementation

### Components

**Primary Service:** `ShortestPathService` (NEW v2.0)
- **Location:** `backend/app/services/graph/shortest_path.py`
- **Method:** `calculate_shortest_path(skill_a, skill_b)`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_read()` for Dijkstra queries

### Database Schema Changes

From `database-schema.md`:

```cypher
// Dijkstra shortest path query
MATCH (start:Skill {name: $skill_a}), (end:Skill {name: $skill_b})
CALL gds.shortestPath.dijkstra.stream(
  'skill-centrality-graph',
  {
    sourceNode: start,
    targetNode: end,
    relationshipWeightProperty: 'co_occurrence_rate'
  }
)
YIELD path, totalCost
RETURN nodes(path) AS skill_path, totalCost AS distance, length(path) AS path_length
```

**Edge Distance Formula:**
- `distance(s1, s2) = 1 / co_occurrence_count`
- Lower co-occurrence → higher distance (harder to transition)

### Testing

**Unit Test:** `tests/unit/test_shortest_path.py`
- Test shortest path calculation
- Validate edge cases: no path (distance=infinity), same skill (distance=0)
- Test path correctness: HTML→React should traverse CSS/JavaScript

**Integration Test:** `tests/integration/test_shortest_path.py`
- Query 100 random skill pairs
- Verify average response time <500ms (NFR12)
- Test edge cases: disconnected skills, direct connections

### Performance Targets

- **Query Time:** <500ms per shortest path query (NFR12)
- **Batch Processing:** 100 skill pairs in <50 seconds
- **Path Length:** Most paths <5 hops (verify with test data)

### Security Considerations

From `security.md`:
- **Input Validation:** Validate skill names exist before querying
- **Query Timeout:** Set 10-second timeout for Dijkstra queries
- **Resource Limits:** Use GDS stream mode (no write) to conserve memory
