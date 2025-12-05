# Story 1.1: Graph Schema Enhancement - Add Node Properties

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.1
**Estimated Effort:** 1-2 days

---

## User Story

**As a** system administrator,
**I want** to add new metric properties to Skill nodes,
**so that** we can store centrality, market demand, and salary impact data without breaking existing queries.

---

## Acceptance Criteria

1. Cypher script adds properties to all Skill nodes:
   - `eigenvector_centrality` (float, default 0.0)
   - `market_demand` (integer, default 0)
   - `avg_salary_impact` (float, default 0.0)
2. Script is idempotent (safe to run multiple times)
3. Existing Skill node properties unchanged (ID, NAME, LEVEL, CATEGORY, DESCRIPTION, embeddings)
4. Validation: Query 100 random skills, verify new properties exist with default values
5. Rollback script tested: `REMOVE` properties and verify clean removal

---

## Integration Verification

**IV1:** Run v1.1 query test suite - All skill-based queries return identical results (property additions don't affect query logic)

**IV2:** CSV ingestion test - Upload 100 skill records, verify new properties initialized correctly and existing properties unchanged

**IV3:** Vector search test - Run 10 sample semantic queries, verify similarity search performance unchanged (<500ms)

---

## Technical Notes

### Implementation Approach
- Use Cypher `SET` command to add properties to all Skill nodes
- Batch processing for large node sets (process 1000 nodes per batch)
- Log property additions for audit trail

### Cypher Script Example
```cypher
// Add new properties to all Skill nodes
MATCH (s:Skill)
SET s.eigenvector_centrality = COALESCE(s.eigenvector_centrality, 0.0),
    s.market_demand = COALESCE(s.market_demand, 0),
    s.avg_salary_impact = COALESCE(s.avg_salary_impact, 0.0)
RETURN count(s) as updated_nodes
```

### Rollback Script
```cypher
// Remove new properties from Skill nodes
MATCH (s:Skill)
REMOVE s.eigenvector_centrality,
       s.market_demand,
       s.avg_salary_impact
RETURN count(s) as reverted_nodes
```

---

## Definition of Done

- [ ] Cypher script executed successfully on all Skill nodes
- [ ] New properties exist on 100% of Skill nodes
- [ ] Existing Skill properties unchanged (verified by sample query)
- [ ] v1.1 test suite passes (no regression)
- [ ] Rollback script tested and verified on staging
- [ ] Performance benchmarks match v1.1 baseline (±10%)
- [ ] Documentation updated (schema diagram, migration notes)

---

## Dependencies

**Depends on:** None (first story in Epic 1)

**Blocks:** Story 2.1 (Eigenvector Centrality Calculation) - needs these properties to store centrality values

---

## Technical Implementation

### Components

**Primary Service:** `GraphMetricsService` (NEW v2.0)
- **Location:** `backend/app/services/graph/schema_migration.py`
- **Method:** `add_skill_properties()`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_write()` for Cypher migration script

**Migration Script:**
- **Location:** `backend/scripts/migrate_graph_v2.py`
- **Validation Script:** `backend/scripts/validate_migration.py`

### Database Schema Changes

From `database-schema.md`:

```cypher
// Phase 1: Add new properties to existing Skill nodes
MATCH (s:Skill)
SET s.eigenvector_centrality = COALESCE(s.eigenvector_centrality, 0.0),
    s.market_demand = COALESCE(s.market_demand, 0),
    s.avg_salary_impact = COALESCE(s.avg_salary_impact, 0.0);
```

**New Skill Properties:**
- `eigenvector_centrality`: Float (0-1) - Network importance score
- `market_demand`: Integer - Number of jobs requiring this skill
- `avg_salary_impact`: Float - Average salary premium

### Testing

**Unit Test:** `tests/unit/test_migration.py`
- Test idempotence (run script 2x, verify no duplicates)
- Validate property defaults (all 0.0 or 0)

**Integration Test:** `tests/integration/test_migration.py`
- Run migration on test database
- Query 100 random skills, verify properties exist
- Run v1.1 query suite, verify identical results

### Performance Targets

- **Migration Time:** <5 minutes for 5K-8K skills
- **Batch Size:** 1000 nodes per transaction
- **Zero Downtime:** Use `COALESCE` to avoid overwriting existing values

### Security Considerations

From `security.md`:
- **Transaction Safety:** Cypher transactions with `COMMIT` on success
- **Rollback Plan:** Maintain v1.1 snapshot, use `REMOVE` to delete properties
- **Audit Logging:** Log property additions with skill IDs and timestamps

---

## Risks & Mitigation

**Risk:** Property addition fails on large node sets (>10K skills)
**Mitigation:** Batch processing (1000 nodes/batch), transaction safety, dry-run testing on staging

**Risk:** Existing queries break due to property additions
**Mitigation:** Properties additive only (don't modify existing structure), comprehensive regression testing with v1.1 test suite

**Risk:** Migration script not idempotent
**Mitigation:** Use `COALESCE` to preserve existing values, test running script multiple times
