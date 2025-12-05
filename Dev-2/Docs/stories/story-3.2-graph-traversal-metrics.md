# Story 3.2: Graph Traversal Node Enhancement - Metric Integration

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.2
**Estimated Effort:** 2-3 days

## User Story
**As a** LangGraph query pipeline,
**I want** to inject centrality/closeness calculations into graph traversal,
**so that** responses include quantified metrics.

## Acceptance Criteria
1. Graph Traversal node enhanced with metric functions for each new intent
2. Cypher templates: learning_path (PREREQUISITE_OF), high_leverage (centrality >0.5)
3. Context includes centrality scores, closeness values, shortest paths
4. Performance: <2s graph traversal with metrics

## Integration Verification
**IV1:** v1.1 queries use same Cypher patterns
**IV2:** skill_transfer query includes closeness scores in context
**IV3:** <1s performance increase vs v1.1

## Dependencies
**Depends on:** Stories 2.1-2.5, 3.1
**Blocks:** Story 3.3

---

## Technical Implementation

### Components

**Primary Service:** `GraphTraversalNode` (ENHANCED v2.0)
- **Location:** `backend/app/agents/nodes/graph_traversal.py`
- **Method:** Enhanced with metric calculations per intent

**Metric Services:**
- `CentralityService` - For high_leverage_skills intent
- `ShortestPathService` - For skill_transfer, learning_path intents
- `TransitionIndexService` - For transition_difficulty intent

### Enhanced Cypher Templates

From `components.md`:

**learning_path Intent:**
```cypher
// Traverse PREREQUISITE_OF relationships to find learning path
MATCH path = (start:Skill {name: $skill_start})-[:PREREQUISITE_OF*1..5]->(end:Skill {name: $skill_end})
WITH path, nodes(path) AS skill_path, relationships(path) AS prereq_rels
RETURN
    skill_path,
    [skill IN skill_path | skill.name] AS skill_names,
    [skill IN skill_path | skill.eigenvector_centrality] AS centrality_scores,
    length(path) AS path_length
ORDER BY path_length ASC
LIMIT 3
```

**high_leverage_skills Intent:**
```cypher
// Find skills with high centrality (>0.5)
MATCH (s:Skill)
WHERE s.eigenvector_centrality > 0.5
WITH s
ORDER BY s.eigenvector_centrality DESC
LIMIT 20
RETURN s.name AS skill_name, s.eigenvector_centrality AS centrality
```

**skill_transfer Intent:**
```cypher
// Find shortest path and calculate closeness
MATCH (start:Skill {name: $skill_start}), (end:Skill {name: $skill_end})
CALL gds.shortestPath.dijkstra.stream('skill-centrality-graph', {
    sourceNode: start,
    targetNode: end,
    relationshipWeightProperty: 'co_occurrence_rate'
})
YIELD path, totalCost
WITH nodes(path) AS skill_path, totalCost AS distance
RETURN
    [skill IN skill_path | skill.name] AS skill_path,
    distance,
    1.0 / (1.0 + distance) AS closeness
```

### Testing

**Unit Test:** `tests/unit/test_graph_traversal.py`
- Test new Cypher templates for each intent
- Validate metric injection (centrality, closeness)
- Test error handling (no path found)

**Integration Test:** `tests/integration/test_graph_traversal.py`
- Run skill_transfer query, verify closeness in context
- Run learning_path query, verify PREREQUISITE_OF traversal
- Verify <2s graph traversal with metrics (NFR)

### Performance Targets

- **Graph Traversal Time:** <2 seconds with metric calculations
- **Performance Delta:** <1 second slower than v1.1 (without metrics)
- **Cypher Query Optimization:** Use indexes on skill names

### Security Considerations

From `security.md`:
- **Query Timeout:** Set 10-second timeout for graph traversal
- **Resource Limits:** Limit path depth to 5 hops (prevent infinite loops)
- **Input Validation:** Validate skill names exist before traversal
