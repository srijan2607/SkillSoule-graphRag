# Story 2.6: Recombinant Innovation Indices (Optional Beta)

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.6
**Estimated Effort:** 2-3 days

## User Story
**As a** researcher,
**I want** to classify jobs by skill combination novelty,
**so that** we can test high-creation jobs vs salary premium hypothesis.

## Acceptance Criteria
1. Functions `calculate_creation_index(job_id)` and `calculate_reuse_index(job_id)`
2. CreationIndex = (Novel pairs) / (Total pairs), Novel = <5% jobs
3. Classification: CUTTING_EDGE (>0.5), EMERGING (0.3-0.5), ESTABLISHED (<0.3)
4. Store as Job properties: creation_index, reuse_index, innovation_class
5. Backend-only for MVP (UI deferred)

## Integration Verification
**IV1:** Common skills (Python, SQL, Git) have low creation_index (<0.2)
**IV2:** Rare combos (Rust+WASM+WebGPU) have high creation_index (>0.7)
**IV3:** 40K jobs processed in <10 minutes

## Dependencies
**Depends on:** Story 1.3
**Blocks:** Story 4.5 (validation testing)

---

## Technical Implementation

### Components

**Primary Service:** `GraphMetricsService` (NEW v2.0)
- **Location:** `backend/app/services/graph/transition_index.py`
- **Method:** `calculate_creation_index(job_id)`, `calculate_reuse_index(job_id)`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `update_job_properties(job_id, properties)` to store indices

**Computation Script:**
- **Location:** `backend/scripts/compute_innovation_indices.py`
- **Trigger:** After CSV ingestion (batch process all jobs)

### Database Schema Changes

From `database-schema.md`:

```cypher
// Add innovation properties to Job nodes
MATCH (j:Job)
SET j.creation_index = COALESCE(j.creation_index, 0.0),
    j.reuse_index = COALESCE(j.reuse_index, 0.0),
    j.classification = COALESCE(j.classification, 'ESTABLISHED');
```

**New Job Properties:**
- `creation_index`: Float (0-1) - Proportion of novel skill pairs
- `reuse_index`: Float (0-1) - Proportion of common skill pairs
- `classification`: String - "CUTTING_EDGE" (>0.5), "EMERGING" (0.3-0.5), "ESTABLISHED" (<0.3)

**Formula Implementation:**

```python
def calculate_creation_index(job_id: str) -> float:
    """
    Calculate proportion of novel skill combinations in job.

    CreationIndex = (Novel pairs) / (Total pairs)
    Novel pair = appears in <5% of jobs
    """
    required_skills = neo4j_repo.get_job_requirements(job_id)
    total_pairs = len(list(combinations(required_skills, 2)))

    novel_pairs = 0
    for skill_a, skill_b in combinations(required_skills, 2):
        co_occurrence_count = neo4j_repo.get_co_occurrence_count(skill_a, skill_b)
        total_jobs = neo4j_repo.count_jobs()

        # Novel = appears in <5% of jobs
        if co_occurrence_count / total_jobs < 0.05:
            novel_pairs += 1

    creation_index = novel_pairs / total_pairs if total_pairs > 0 else 0.0

    return creation_index

def calculate_reuse_index(job_id: str) -> float:
    """
    Calculate proportion of common skill combinations.
    ReuseIndex = 1.0 - CreationIndex
    """
    return 1.0 - calculate_creation_index(job_id)

def classify_innovation(creation_index: float) -> str:
    """Classify job by innovation level."""
    if creation_index > 0.5:
        return 'CUTTING_EDGE'
    elif creation_index > 0.3:
        return 'EMERGING'
    else:
        return 'ESTABLISHED'
```

### Testing

**Unit Test:** `tests/unit/test_innovation_indices.py`
- Test common skills (Python, SQL, Git) → low creation_index (<0.2)
- Test rare combos (Rust+WASM+WebGPU) → high creation_index (>0.7)
- Validate classification thresholds

**Integration Test:** `tests/integration/test_innovation_indices.py`
- Process 40K jobs in <10 minutes
- Verify distribution: ~70% ESTABLISHED, ~25% EMERGING, ~5% CUTTING_EDGE
- Validate creation_index + reuse_index = 1.0

### Performance Targets

- **Computation Time:** <10 minutes for 40K jobs
- **Batch Size:** Process 500 jobs per transaction
- **Storage:** Properties stored on all Job nodes

### Security Considerations

From `security.md`:
- **Backend-only:** UI deferred to prevent misuse (experimental metric)
- **Batch Processing:** Process during off-peak hours to avoid resource contention
- **Disclaimer:** Mark as experimental in documentation
