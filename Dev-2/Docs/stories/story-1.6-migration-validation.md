# Story 1.6: Graph Migration Validation & Rollback Testing

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.6
**Estimated Effort:** 1-2 days

---

## User Story

**As a** system administrator,
**I want** comprehensive validation of the graph migration,
**so that** I can confidently deploy v2.0 without data loss or corruption.

---

## Acceptance Criteria

1. Automated validation script checks:
   - Node count unchanged from v1.1 (Job, Skill, Company, Location, Category, Subcategory counts match pre-migration snapshot)
   - All existing relationships preserved (REQUIRES, POSTED_BY, LOCATED_IN counts match)
   - New properties added to all Skill nodes (100% coverage)
   - New relationship types created (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO exist)
2. Rollback script tested on staging database:
   - Removes new properties: `MATCH (s:Skill) REMOVE s.eigenvector_centrality, s.market_demand, s.avg_salary_impact`
   - Removes new relationships: `MATCH ()-[r:PREREQUISITE_OF|COMPLEMENTS|SUBSTITUTES|TRANSITIONS_TO]->() DELETE r`
   - Validation: Post-rollback graph identical to v1.1 snapshot
3. Performance regression test:
   - Run v1.1 query benchmark suite (10 sample queries)
   - Query response time within ±10% of v1.1 baseline
4. Export full graph snapshot (neo4j-admin dump) for disaster recovery

---

## Integration Verification

**IV1:** Zero data loss - Node/relationship counts before vs after migration match exactly (existing data)

**IV2:** v1.1 feature parity - All v1.1 acceptance criteria still pass (authentication, CSV ingestion, chat queries)

**IV3:** Rollback success - Rollback script executes without errors, graph restored to v1.1 state

---

## Technical Notes

### Validation Script
```python
def validate_migration():
    # Count checks
    assert count_nodes('Job') == pre_migration_job_count
    assert count_nodes('Skill') == pre_migration_skill_count
    assert count_relationships('REQUIRES') == pre_migration_requires_count

    # Property checks
    skills_without_centrality = count_skills_missing_property('eigenvector_centrality')
    assert skills_without_centrality == 0

    # New relationship checks
    assert count_relationships('PREREQUISITE_OF') >= 50
    assert count_relationships('COMPLEMENTS') >= 5000

    # Performance checks
    for query in v1_1_benchmark_queries:
        response_time = execute_query(query)
        assert response_time < (v1_1_baseline_time * 1.1)  # Within 10%
```

---

## Definition of Done

- [ ] Validation script passes all checks
- [ ] Rollback script tested and verified on staging
- [ ] Performance regression test passes
- [ ] Neo4j snapshot exported for disaster recovery
- [ ] Migration documentation complete
- [ ] Stakeholder sign-off on migration readiness

---

## Dependencies

**Depends on:** Stories 1.1-1.5 (all migration stories must be complete)

**Blocks:** Epic 2 (cannot proceed with metrics until migration validated)

---

---

## Technical Implementation

### Components

**Primary Service:** `GraphMetricsService` (NEW v2.0)
- **Location:** `backend/app/services/graph/schema_migration.py`
- **Method:** `validate_migration()`, `rollback_migration()`

**Validation Script:**
- **Location:** `backend/scripts/validate_migration.py`
- **Snapshot Export:** `backend/scripts/export_graph_snapshot.sh`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `get_node_count()`, `get_relationship_count()`

### Database Schema Changes

**Validation Queries:**

```cypher
// Count nodes (should match pre-migration)
MATCH (n:Job) RETURN count(n) as job_count;
MATCH (n:Skill) RETURN count(n) as skill_count;
MATCH (n:Company) RETURN count(n) as company_count;

// Count existing relationships (should be unchanged)
MATCH ()-[r:REQUIRES]->() RETURN count(r) as requires_count;
MATCH ()-[r:POSTED_BY]->() RETURN count(r) as posted_by_count;

// Check new properties (should be 100% coverage)
MATCH (s:Skill) WHERE s.eigenvector_centrality IS NULL RETURN count(s) as missing_centrality;

// Count new relationships (should meet minimums)
MATCH ()-[r:PREREQUISITE_OF]->() RETURN count(r) as prerequisite_count;
MATCH ()-[r:COMPLEMENTS]->() RETURN count(r) as complements_count;
```

**Rollback Script:**

```cypher
// Remove new properties from Skill nodes
MATCH (s:Skill)
REMOVE s.eigenvector_centrality, s.market_demand, s.avg_salary_impact;

// Remove new properties from Job nodes
MATCH (j:Job)
REMOVE j.creation_index, j.reuse_index, j.classification;

// Remove new relationship types
MATCH ()-[r:PREREQUISITE_OF|COMPLEMENTS|SUBSTITUTES|TRANSITIONS_TO]->()
DELETE r;
```

### Testing

**Unit Test:** `tests/unit/test_migration_validation.py`
- Test validation function accuracy
- Test rollback function completeness
- Verify snapshot export/import

**Integration Test:** `tests/integration/test_migration_validation.py`
- Run full migration on test database
- Execute validation script (all checks pass)
- Run rollback script
- Verify graph restored to v1.1 state
- Re-run v1.1 test suite (100% pass rate)

### Performance Targets

- **Validation Time:** <2 minutes for all checks
- **Rollback Time:** <3 minutes to remove properties and relationships
- **Snapshot Export:** <5 minutes for full graph dump (neo4j-admin dump)
- **v1.1 Query Benchmark:** All queries within ±10% of baseline

### Security Considerations

From `security.md`:
- **Disaster Recovery:** Export full graph snapshot before migration
- **Idempotent Rollback:** Rollback script can run multiple times safely
- **Audit Logging:** Log all validation results with timestamps
- **Stakeholder Approval:** Require sign-off before production migration

### Validation Checklist

```python
def validate_migration():
    # 1. Node count checks
    assert count_nodes('Job') == 40000  # Example baseline
    assert count_nodes('Skill') == 8000

    # 2. Existing relationship counts
    assert count_relationships('REQUIRES') == 120000
    assert count_relationships('POSTED_BY') == 40000

    # 3. New property coverage
    assert count_skills_missing('eigenvector_centrality') == 0
    assert count_skills_missing('market_demand') == 0

    # 4. New relationship minimums
    assert count_relationships('PREREQUISITE_OF') >= 50
    assert count_relationships('COMPLEMENTS') >= 5000
    assert count_relationships('SUBSTITUTES') >= 60
    assert count_relationships('TRANSITIONS_TO') >= 2000

    # 5. Performance regression
    for query in v1_1_benchmark_queries:
        duration = execute_query(query)
        assert duration <= baseline_duration * 1.1

    # 6. Total relationship limit
    total_relationships = sum(count_relationships(rel_type) for rel_type in all_relationship_types)
    assert total_relationships < 175000  # Free tier limit
```

---

## CRITICAL

This story is the **quality gate** for Epic 1. Do not proceed to Epic 2 until all validation checks pass.
