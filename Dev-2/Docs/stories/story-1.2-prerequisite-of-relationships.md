# Story 1.2: Relationship Type Addition - PREREQUISITE_OF

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.2
**Estimated Effort:** 1-2 days

---

## User Story

**As a** career advisor user,
**I want** the system to understand prerequisite relationships between skills,
**so that** learning paths can be ordered correctly (e.g., HTML before React).

---

## Acceptance Criteria

1. Cypher relationship type `PREREQUISITE_OF` created with properties:
   - `confidence_score` (float, 0-1 range)
   - `source` (string: "manual_curated" | "inferred")
2. Initial curated prerequisite relationships loaded from CSV:
   - Example: HTML -[PREREQUISITE_OF {confidence_score: 1.0, source: "manual_curated"}]-> React
   - Minimum 50 curated relationships for common skill chains
3. Query to find all prerequisites for a skill: `MATCH (s1)-[:PREREQUISITE_OF]->(s2 {NAME: 'React'}) RETURN s1`
4. No impact on existing REQUIRES, SIMILAR_TO relationships

---

## Integration Verification

**IV1:** Existing job-skill queries unchanged - REQUIRES relationships still return correct results

**IV2:** Graph visualization test - Open Neo4j Browser, verify PREREQUISITE_OF relationships visible alongside existing relationships

**IV3:** Relationship count validation - Total relationship count increases by ~50-100 (prerequisite additions only)

---

## Technical Notes

### Implementation Approach
- Create CSV file with curated prerequisite relationships
- Load relationships using Cypher `LOAD CSV` or batch processing
- Bidirectional prerequisite chains (if A prerequisite of B, query can traverse both directions)

### Sample Prerequisites
```
HTML → CSS → JavaScript → React
Python → Django/Flask
SQL → PostgreSQL/MySQL
Git → GitHub/GitLab
```

### Cypher Script Example
```cypher
// Create PREREQUISITE_OF relationship
MATCH (s1:Skill {NAME: 'HTML'}), (s2:Skill {NAME: 'React'})
CREATE (s1)-[:PREREQUISITE_OF {
  confidence_score: 1.0,
  source: 'manual_curated'
}]->(s2)
```

---

## Definition of Done

- [ ] PREREQUISITE_OF relationship type created
- [ ] Minimum 50 curated prerequisite relationships loaded
- [ ] Query to find prerequisites works correctly
- [ ] v1.1 test suite passes (no regression)
- [ ] Neo4j Browser visualization shows new relationships
- [ ] Documentation updated (relationship schema)

---

## Dependencies

**Depends on:** Story 1.1 (Graph Schema Enhancement)

**Blocks:** Story 3.2 (Graph Traversal - Learning Path queries need this)

---

## Technical Implementation

### Components

**Primary Service:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `create_relationship()` for PREREQUISITE_OF relationships

**Data Loading:**
- **CSV File:** `data/prerequisite_relationships.csv`
- **Script:** `backend/scripts/load_prerequisites.py`

### Database Schema Changes

From `database-schema.md`:

```cypher
// (Skill)-[:PREREQUISITE_OF]->(Skill)
//   Properties: confidence_score (0-1), source (manual_curated | inferred)
//   Example: HTML -[:PREREQUISITE_OF {confidence_score: 0.95}]-> React

// Create PREREQUISITE_OF relationship
MATCH (s1:Skill {name: 'HTML'}), (s2:Skill {name: 'React'})
CREATE (s1)-[:PREREQUISITE_OF {
  confidence_score: 1.0,
  source: 'manual_curated'
}]->(s2)
```

**Relationship Properties:**
- `confidence_score`: Float (0-1) - Certainty of prerequisite relationship
- `source`: String - "manual_curated" or "inferred"

### Testing

**Unit Test:** `tests/unit/test_prerequisites.py`
- Verify relationship creation
- Test bidirectional traversal (find prerequisites, find dependents)

**Integration Test:** `tests/integration/test_prerequisites.py`
- Load 50+ prerequisite relationships
- Query prerequisites for specific skills (e.g., React → HTML, CSS, JavaScript)
- Verify REQUIRES relationships unaffected

### Performance Targets

- **CSV Loading:** <2 minutes for 100 prerequisite relationships
- **Query Time:** <100ms to find all prerequisites for a skill
- **Relationship Count:** 50-100 curated relationships for MVP

### Security Considerations

From `security.md`:
- **Input Validation:** Validate skill names exist before creating relationships
- **CSV Sanitization:** Check for malicious input in prerequisite CSV
- **Transaction Safety:** Use `MERGE` to avoid duplicate relationships

---

## Risks & Mitigation

**Risk:** Prerequisite relationships may be subjective (HTML before CSS vs CSS before HTML)
**Mitigation:** Use confidence_score to indicate certainty (1.0 for definite, 0.7 for probable), allow manual curation and expert review

**Risk:** Skill names in CSV don't match Neo4j node names
**Mitigation:** Pre-validation script to check skill existence, fuzzy matching for close matches
