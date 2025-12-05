# Story 2.1: Eigenvector Centrality Calculation with Neo4j GDS

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.1
**Estimated Effort:** 2-3 days

## User Story
**As a** data scientist,
**I want** to compute eigenvector centrality for all skills using Neo4j Graph Data Science,
**so that** we can identify high-leverage skills based on network structure (not just frequency).

## Acceptance Criteria
1. Neo4j GDS in-memory graph projection created (Nodes: Skill, Relationships: SIMILAR_TO, COMPLEMENTS)
2. Eigenvector centrality algorithm executed: `gds.eigenvector.write()` to Skill.eigenvector_centrality
3. Top 10 skills by centrality logged (Python, JavaScript, SQL expected)
4. Performance: <30s for 8K skills (NFR11)
5. Update frequency: After CSV ingestion (configurable)

## Integration Verification
**IV1:** Centrality property doesn't affect v1.1 semantic search
**IV2:** Top 10 centrality >0.5, bottom 10% <0.1
**IV3:** GDS projection fits free tier limits

## Dependencies
**Depends on:** Story 1.3 (needs COMPLEMENTS relationships)
**Blocks:** Story 2.3, 3.2 (centrality used in queries)

---

## Technical Implementation

### Components

**Primary Service:** `CentralityService` (NEW v2.0)
- **Location:** `backend/app/services/graph/centrality.py`
- **Method:** `compute_eigenvector_centrality()`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_write()` for GDS operations

**Computation Script:**
- **Location:** `backend/scripts/compute_centrality.py`
- **Trigger:** After CSV ingestion or manual invocation

### Database Schema Changes

From `database-schema.md`:

```cypher
// Project skill graph for centrality calculation
CALL gds.graph.project(
  'skill-centrality-graph',
  'Skill',
  {
    SIMILAR_TO: {orientation: 'UNDIRECTED'},
    COMPLEMENTS: {orientation: 'UNDIRECTED', properties: 'co_occurrence_rate'},
    PREREQUISITE_OF: {orientation: 'DIRECTED'}
  }
);

// Compute eigenvector centrality and write to skill.eigenvector_centrality property
CALL gds.eigenvector.write(
  'skill-centrality-graph',
  {
    writeProperty: 'eigenvector_centrality',
    maxIterations: 100,
    tolerance: 0.0001
  }
);
```

**Updated Skill Properties:**
- `eigenvector_centrality`: Float (0-1) - Network importance score

### Testing

**Unit Test:** `tests/unit/test_centrality.py`
- Test centrality calculation accuracy
- Validate top-10 skills (Python, JavaScript, SQL expected)
- Test distribution (top 10 >0.5, bottom 10% <0.1)

**Integration Test:** `tests/integration/test_centrality.py`
- Create test graph with 8K skills
- Run GDS projection and centrality computation
- Query results, verify property written to all nodes
- Verify computation completes <30s (NFR11)

### Performance Targets

- **Computation Time:** <30 seconds for 8K skills (NFR11)
- **GDS Projection:** In-memory graph fits Neo4j free tier limits
- **Update Frequency:** After CSV ingestion (configurable via cron job)
- **Iterations:** Max 100 iterations, convergence tolerance 0.0001

### Security Considerations

From `security.md`:
- **Resource Limits:** Monitor Neo4j memory usage during GDS operations
- **Free Tier Compliance:** Verify graph projection size <200MB
- **Transaction Safety:** Use GDS write mode to atomically update properties
