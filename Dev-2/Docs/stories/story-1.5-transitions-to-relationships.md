# Story 1.5: Relationship Type Addition - TRANSITIONS_TO (Experimental)

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.5
**Estimated Effort:** 2-3 days

---

## User Story

**As a** career intelligence system,
**I want** to approximate career transition paths from job-skill data,
**so that** users receive transition likelihood estimates even without observed user trajectory data.

---

## Acceptance Criteria

1. Cypher relationship type `TRANSITIONS_TO` created with properties:
   - `transition_likelihood` (float, 0-1 range, HEURISTIC SCORE)
   - `estimated_learning_time_hours` (integer)
2. Algorithm computes TRANSITIONS_TO relationships:
   - Factor 1 (50% weight): Skill co-occurrence in jobs
   - Factor 2 (30% weight): Embedding cosine similarity
   - Factor 3 (20% weight, penalty): Skill complexity delta
   - Create relationship if combined score >0.3 threshold
3. Disclaimer property: `is_validated = false` (experimental, not research-validated)
4. Query to find likely transitions: `MATCH (s1 {NAME: 'Python'})-[r:TRANSITIONS_TO]->(s2) WHERE r.transition_likelihood > 0.5 RETURN s2 ORDER BY r.transition_likelihood DESC`
5. Estimated ~2K-5K TRANSITIONS_TO relationships created

---

## Integration Verification

**IV1:** Existing SIMILAR_TO relationships unchanged (different semantic meaning)

**IV2:** Experimental flag validation - All TRANSITIONS_TO relationships have `is_validated = false` property

**IV3:** Relationship limit check - Total relationships still <175K after additions

---

## Technical Notes

### Algorithm Implementation
```python
def calculate_transition_likelihood(skill_a, skill_b):
    # Factor 1: Co-occurrence (50%)
    co_occur_score = count_jobs_with_both(skill_a, skill_b) / count_jobs_with(skill_a)

    # Factor 2: Embedding similarity (30%)
    semantic_sim = cosine_similarity(embedding_a, embedding_b)

    # Factor 3: Complexity penalty (20%)
    complexity_gap = abs(complexity(skill_a) - complexity(skill_b))
    complexity_penalty = 1.0 - (complexity_gap / max_complexity_gap)

    # Combined score
    transition_likelihood = (
        0.5 * co_occur_score +
        0.3 * semantic_sim +
        0.2 * complexity_penalty
    )

    return transition_likelihood
```

### IMPORTANT DISCLAIMER
This is an **approximation** based on static data, not observed user trajectories. Mark all relationships with `is_validated = false` and include disclaimer in UI.

---

## Definition of Done

- [ ] TRANSITIONS_TO relationship type created
- [ ] Algorithm implemented and tested
- [ ] 2K-5K relationships created
- [ ] All relationships have `is_validated = false` flag
- [ ] Query for transitions works correctly
- [ ] Documentation includes experimental disclaimer

---

## Dependencies

**Depends on:** Story 1.3 (needs COMPLEMENTS for co-occurrence data)

**Blocks:** Story 2.5 (TransitionIndex uses this data)

---

## Technical Implementation

### Components

**Primary Service:** `GraphMetricsService` (NEW v2.0)
- **Location:** `backend/app/services/graph/transition_index.py`
- **Method:** `compute_transitions_to_relationships()`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_write()` for relationship creation

**Computation Script:**
- **Location:** `backend/scripts/compute_transitions.py`
- **Validation Script:** `backend/scripts/validate_transitions.py`

### Database Schema Changes

From `database-schema.md`:

```cypher
// (Skill)-[:TRANSITIONS_TO]->(Skill)
//   Properties: transition_likelihood (0-1), estimated_learning_time_hours (integer)
//   Example: Python -[:TRANSITIONS_TO {transition_likelihood: 0.65, estimated_learning_time_hours: 40}]-> Django

// Create TRANSITIONS_TO relationship
MATCH (s1:Skill {name: 'Python'}), (s2:Skill {name: 'Django'})
CREATE (s1)-[:TRANSITIONS_TO {
  transition_likelihood: 0.65,
  estimated_learning_time_hours: 40,
  is_validated: false
}]->(s2)
```

**Relationship Properties:**
- `transition_likelihood`: Float (0-1) - Heuristic score combining co-occurrence, similarity, complexity
- `estimated_learning_time_hours`: Integer - Estimated learning time
- `is_validated`: Boolean - Always `false` (experimental, not research-validated)

### Testing

**Unit Test:** `tests/unit/test_transitions.py`
- Test transition likelihood calculation formula
- Validate weighted factors (50% co-occurrence, 30% similarity, 20% complexity)
- Test threshold filtering (>0.3)

**Integration Test:** `tests/integration/test_transitions.py`
- Compute TRANSITIONS_TO for 2K-5K skill pairs
- Query transitions from Python, JavaScript, SQL
- Verify `is_validated=false` flag on all relationships

### Performance Targets

- **Computation Time:** <10 minutes for 8K skills (2K-5K relationships created)
- **Batch Size:** Process 500 skill pairs per transaction
- **Relationship Count:** 2K-5K TRANSITIONS_TO relationships (threshold: transition_likelihood >0.3)
- **Query Time:** <100ms to find all transitions from a skill

### Security Considerations

From `security.md`:
- **Experimental Flag:** All relationships marked `is_validated=false` to prevent misuse
- **Disclaimer:** UI must display experimental warning for transition recommendations
- **Data Validation:** Validate co-occurrence data exists before computing transitions

### Algorithm Implementation

**Multi-Factor Scoring:**
1. **Factor 1 (50% weight):** Skill co-occurrence in jobs
   - `co_occur_score = count_jobs_with_both(s1, s2) / count_jobs_with(s1)`
2. **Factor 2 (30% weight):** Embedding cosine similarity
   - `semantic_sim = cosine_similarity(embedding_s1, embedding_s2)`
3. **Factor 3 (20% weight):** Complexity penalty
   - `complexity_penalty = 1.0 - (complexity_gap / max_complexity_gap)`

**Combined Score:**
```python
transition_likelihood = (
    0.5 * co_occur_score +
    0.3 * semantic_sim +
    0.2 * complexity_penalty
)
```
