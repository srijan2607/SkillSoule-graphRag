# Story 1.3: Relationship Type Addition - COMPLEMENTS

**Epic:** Epic 1 - Skill-Centric Graph Restructuring
**Story ID:** 1.3
**Estimated Effort:** 2-3 days

---

## User Story

**As a** job seeker,
**I want** to discover complementary skills that often appear together,
**so that** I can learn skill combinations valued by employers.

---

## Acceptance Criteria

1. Cypher relationship type `COMPLEMENTS` created with properties:
   - `co_occurrence_rate` (float, 0-1 range)
   - `job_count` (integer, number of jobs requiring both skills)
2. Algorithm computes COMPLEMENTS relationships:
   - For each skill pair in same job: Increment co-occurrence counter
   - Compute co_occurrence_rate = (jobs_with_both) / (jobs_with_either)
   - Create relationship if co_occurrence_rate >0.6 threshold
3. Query to find complementary skills: `MATCH (s1 {NAME: 'Python'})-[r:COMPLEMENTS]->(s2) RETURN s2, r.co_occurrence_rate ORDER BY r.co_occurrence_rate DESC LIMIT 10`
4. Estimated ~5K-10K COMPLEMENTS relationships created (within Neo4j free tier limit)

---

## Integration Verification

**IV1:** Job requirement queries unchanged - REQUIRES relationships unaffected by COMPLEMENTS additions

**IV2:** Performance test - COMPLEMENTS computation completes in <5 minutes for 40K jobs, 8K skills

**IV3:** Relationship limit check - Total relationships <175K (free tier limit), graceful degradation if exceeded (keep top co-occurrence pairs only)

---

## Technical Notes

### Implementation Approach
- Query all jobs and their required skills from Neo4j
- Build co-occurrence matrix (skill pairs appearing in same jobs)
- Calculate co_occurrence_rate for each pair
- Create COMPLEMENTS relationships for pairs above threshold (0.6)

### Algorithm Pseudocode
```python
# Build co-occurrence matrix
for job in all_jobs:
    required_skills = job.get_required_skills()
    for skill_a, skill_b in combinations(required_skills, 2):
        co_occurrence_count[(skill_a, skill_b)] += 1

# Calculate rates and create relationships
for (skill_a, skill_b), count in co_occurrence_count.items():
    jobs_with_a = count_jobs_with_skill(skill_a)
    jobs_with_b = count_jobs_with_skill(skill_b)
    co_occurrence_rate = count / (jobs_with_a + jobs_with_b - count)  # Jaccard similarity

    if co_occurrence_rate > 0.6:
        create_complements_relationship(skill_a, skill_b, co_occurrence_rate, count)
```

### Example COMPLEMENTS
```
Python COMPLEMENTS PostgreSQL (co_occurrence_rate: 0.78, job_count: 1200)
React COMPLEMENTS TypeScript (co_occurrence_rate: 0.82, job_count: 950)
Docker COMPLEMENTS Kubernetes (co_occurrence_rate: 0.85, job_count: 800)
```

---

## Definition of Done

- [ ] COMPLEMENTS relationship type created with properties
- [ ] Algorithm computes co-occurrence rates correctly
- [ ] 5K-10K COMPLEMENTS relationships created
- [ ] Query for complementary skills returns correct results
- [ ] Performance target met (<5 minutes computation)
- [ ] Free tier limit check passes (<175K total relationships)
- [ ] v1.1 test suite passes (no regression)

---

## Dependencies

**Depends on:** Story 1.1 (Graph Schema Enhancement)

**Blocks:** Story 2.1 (Eigenvector Centrality - uses COMPLEMENTS as weighted edges)

---

## Technical Implementation

### Components

**Primary Service:** `GraphMetricsService` (NEW v2.0)
- **Location:** `backend/app/services/graph/schema_migration.py`
- **Method:** `compute_complements_relationships()`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `execute_write()` for Cypher queries

**Computation Script:**
- **Location:** `backend/scripts/compute_complements.py`
- **Validation Script:** `backend/scripts/validate_complements.py`

### Database Schema Changes

From `database-schema.md`:

```cypher
// Phase 3: Create COMPLEMENTS relationships from job skill co-occurrence
MATCH (j:Job)-[:REQUIRES]->(s1:Skill)
MATCH (j)-[:REQUIRES]->(s2:Skill)
WHERE id(s1) < id(s2) // Avoid duplicates
WITH s1, s2, count(j) AS co_occurrence_count, count(j) * 1.0 / (SELECT count(*) FROM Job) AS co_occurrence_rate
WHERE co_occurrence_count >= 5 // Minimum 5 jobs
MERGE (s1)-[c:COMPLEMENTS]->(s2)
SET c.co_occurrence_rate = co_occurrence_rate,
    c.job_count = co_occurrence_count;
```

**Relationship Properties:**
- `co_occurrence_rate`: Float (0-1) - Jaccard similarity score
- `job_count`: Integer - Number of jobs requiring both skills

### Testing

**Unit Test:** `tests/unit/test_complements.py`
- Test co-occurrence matrix calculation
- Validate Jaccard similarity formula
- Test threshold filtering (>0.6)

**Integration Test:** `tests/integration/test_complements.py`
- Load 40K jobs with skill requirements
- Compute COMPLEMENTS relationships
- Query complementary skills for Python, React, Docker
- Verify bidirectional relationships exist

### Performance Targets

- **Computation Time:** <5 minutes for 40K jobs, 8K skills
- **Batch Size:** Process 1000 job-skill pairs per transaction
- **Relationship Count:** 5K-10K COMPLEMENTS relationships (threshold: co_occurrence_rate >0.6)
- **Free Tier Limit:** Total relationships <175K (graceful degradation if exceeded)

### Security Considerations

From `security.md`:
- **Transaction Safety:** Use `MERGE` to prevent duplicate relationships
- **Resource Limits:** Monitor Neo4j memory usage during computation
- **Batch Processing:** Process in batches to avoid timeout (10-minute Neo4j transaction limit)

---

## Risks & Mitigation

**Risk:** Co-occurrence computation may be slow on 40K jobs
**Mitigation:** Batch processing, optimize Cypher queries, consider caching intermediate results

**Risk:** Too many COMPLEMENTS relationships exceed free tier limit
**Mitigation:** Use threshold to control relationship count, keep only high co-occurrence pairs (>0.6)
