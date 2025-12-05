# Story 1.4: Relationship Type Addition - SUBSTITUTES

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.4
**Estimated Effort:** 1-2 days

---

## User Story

**As a** career transition planner,
**I want** to understand which skills are substitutable (e.g., Django vs Flask),
**so that** I can make strategic learning decisions based on job market flexibility.

---

## Acceptance Criteria

1. Cypher relationship type `SUBSTITUTES` created with properties:
   - `substitution_score` (float, 0-1 range)
   - `context` (string, e.g., "web frameworks", "databases")
2. Initial SUBSTITUTES relationships loaded from manual curation:
   - Example: Django -[SUBSTITUTES {substitution_score: 0.8, context: "Python web frameworks"}]-> Flask
   - Minimum 30 curated substitution pairs for common tool categories
3. Bidirectional relationships: If Django substitutes Flask, create Flask substitutes Django
4. Query to find substitutes: `MATCH (s1 {NAME: 'Django'})-[r:SUBSTITUTES]-(s2) RETURN s2, r.context`

---

## Integration Verification

**IV1:** Existing skill similarity queries (SIMILAR_TO) unchanged and distinct from SUBSTITUTES

**IV2:** Relationship validation - SUBSTITUTES count ~60-80 (30 pairs * 2 directions)

**IV3:** Context field populated - No null/empty context values, all have meaningful categories

---

## Definition of Done

- [ ] SUBSTITUTES relationship type created
- [ ] Minimum 30 curated substitution pairs loaded
- [ ] Bidirectional relationships created correctly
- [ ] Query for substitutes returns both directions
- [ ] Context field populated for all relationships
- [ ] v1.1 test suite passes

---

## Dependencies

**Depends on:** Story 1.1

**Blocks:** None (informational relationships for user guidance)

---

## Technical Implementation

### Components

**Primary Service:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `create_relationship()` for SUBSTITUTES relationships

**Data Loading:**
- **CSV File:** `data/substitutes_relationships.csv`
- **Script:** `backend/scripts/load_substitutes.py`

### Database Schema Changes

From `database-schema.md`:

```cypher
// (Skill)-[:SUBSTITUTES]->(Skill)
//   Properties: substitution_score (0-1), context (string)
//   Example: Django -[:SUBSTITUTES {substitution_score: 0.82, context: "web frameworks"}]-> Flask

// Create SUBSTITUTES relationship (bidirectional)
MATCH (s1:Skill {name: 'Django'}), (s2:Skill {name: 'Flask'})
CREATE (s1)-[:SUBSTITUTES {
  substitution_score: 0.8,
  context: 'Python web frameworks'
}]->(s2)
CREATE (s2)-[:SUBSTITUTES {
  substitution_score: 0.8,
  context: 'Python web frameworks'
}]->(s1)
```

**Relationship Properties:**
- `substitution_score`: Float (0-1) - Similarity in job market context
- `context`: String - Category context (e.g., "web frameworks", "databases", "cloud platforms")

### Testing

**Unit Test:** `tests/unit/test_substitutes.py`
- Verify relationship creation
- Test bidirectional relationships (Django ↔ Flask both exist)
- Validate context field populated

**Integration Test:** `tests/integration/test_substitutes.py`
- Load 30 curated substitution pairs
- Query substitutes for Django, PostgreSQL, AWS
- Verify bidirectional queries return correct results

### Performance Targets

- **CSV Loading:** <1 minute for 60 relationships (30 pairs × 2 directions)
- **Query Time:** <50ms to find all substitutes for a skill
- **Relationship Count:** 60-80 curated relationships for MVP

### Security Considerations

From `security.md`:
- **Input Validation:** Validate skill names exist before creating relationships
- **CSV Sanitization:** Check for malicious input in substitutes CSV
- **Transaction Safety:** Use `MERGE` to avoid duplicate relationships

### Sample Substitutes Data

```csv
skill_a,skill_b,substitution_score,context
Django,Flask,0.80,Python web frameworks
PostgreSQL,MySQL,0.75,Relational databases
AWS,Azure,0.70,Cloud platforms
React,Vue,0.72,Frontend frameworks
Docker,Podman,0.68,Container runtimes
Kubernetes,Docker Swarm,0.65,Container orchestration
```
