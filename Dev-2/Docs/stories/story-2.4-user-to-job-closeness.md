# Story 2.4: User-to-Job Closeness Scoring

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.4
**Estimated Effort:** 2-3 days

## User Story
**As a** job seeker,
**I want** the system to calculate how close my skill set is to job requirements,
**so that** I receive quantified match scores.

## Acceptance Criteria
1. Function `calculate_job_closeness(user_skills, job_id)` implemented
2. Formula: `JobCloseness = (1/m) * Σ closeness_j` (m = required skills)
3. Returns: overall score (0-1), per-skill breakdown, transferable skills list
4. Optional: core skill weighting (2.0x)
5. Performance: <1s for 10 user skills vs 15 job requirements

## Integration Verification
**IV1:** Exact match scores ≈1.0, no match <0.3
**IV2:** Core skill weighting penalizes mismatches correctly
**IV3:** Existing v1.1 job queries still work

## Dependencies
**Depends on:** Story 2.3
**Blocks:** Story 3.2

---

## Technical Implementation

### Components

**Primary Service:** `TransitionIndexService` (NEW v2.0)
- **Location:** `backend/app/services/graph/transition_index.py`
- **Method:** `calculate_job_closeness(user_skills, job_id)`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `get_job_requirements(job_id)` to fetch required skills

### Database Schema Changes

**Formula Implementation:**

```python
def calculate_job_closeness(user_skills: List[str], job_id: str) -> Dict:
    """
    Calculate how close user's skills are to job requirements.

    Args:
        user_skills: List of skill names user possesses
        job_id: Job ID to evaluate

    Returns:
        {
            "overall_score": float (0-1),
            "per_skill_breakdown": [{skill, closeness, is_core}],
            "transferable_skills": [skill_names],
            "missing_core_skills": [skill_names]
        }
    """
    required_skills = neo4j_repo.get_job_requirements(job_id)
    m = len(required_skills)  # Number of required skills

    closeness_scores = []
    for req_skill in required_skills:
        # Find closest user skill to this requirement
        best_closeness = max(
            calculate_closeness(user_skill, req_skill)
            for user_skill in user_skills
        )

        # Apply core skill weighting (2.0x penalty if missing)
        is_core = req_skill.get('importance') == 'core'
        weight = 2.0 if is_core else 1.0

        closeness_scores.append({
            'skill': req_skill['name'],
            'closeness': best_closeness,
            'is_core': is_core,
            'weight': weight
        })

    # Compute overall score (weighted average)
    total_weighted_closeness = sum(
        item['closeness'] * item['weight']
        for item in closeness_scores
    )
    total_weight = sum(item['weight'] for item in closeness_scores)

    overall_score = total_weighted_closeness / total_weight

    return {
        'overall_score': overall_score,
        'per_skill_breakdown': closeness_scores,
        'transferable_skills': [
            item['skill'] for item in closeness_scores
            if item['closeness'] > 0.7
        ],
        'missing_core_skills': [
            item['skill'] for item in closeness_scores
            if item['is_core'] and item['closeness'] < 0.5
        ]
    }
```

### Testing

**Unit Test:** `tests/unit/test_job_closeness.py`
- Test exact match scores ≈1.0
- Test no match scores <0.3
- Validate core skill weighting (2.0x penalty)

**Integration Test:** `tests/integration/test_job_closeness.py`
- Test 10 user skills vs 15 job requirements
- Verify response time <1 second
- Test transferable skills identification

### Performance Targets

- **Query Time:** <1 second for 10 user skills vs 15 job requirements
- **Batch Mode:** 50 user-job pairs in <30 seconds
- **Accuracy:** Exact matches score ≥0.95, no overlap <0.3

### Security Considerations

From `security.md`:
- **Input Validation:** Validate user_skills list length (max 50 skills)
- **Job ID Validation:** Verify job exists before computation
- **Rate Limiting:** Max 100 job closeness requests per user per hour
