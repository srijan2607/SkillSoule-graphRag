# Story 2.5: TransitionIndex Heuristic Implementation

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.5
**Estimated Effort:** 2-3 days

## User Story
**As a** career transition planner,
**I want** quantified transition difficulty scores,
**so that** I can prioritize feasible career paths.

## Acceptance Criteria
1. Function `calculate_transition_index(user_skills, target_role)` implemented
2. Formula: `0.50*AvgCloseness + 0.30*CoreOverlap + 0.20*MarketDemand`
3. Returns: score (0-1), components breakdown, interpretation, disclaimer flag
4. Interpretation: >0.7 High, 0.4-0.7 Moderate, <0.4 Major pivot
5. Performance: <200ms (NFR13)

## Integration Verification
**IV1:** UI Dev→UX Designer scores 0.5-0.7, UI Dev→Data Scientist scores 0.2-0.4
**IV2:** Weight sensitivity test passes
**IV3:** Disclaimer "heuristic, not validated" displayed

## Dependencies
**Depends on:** Story 2.3, 2.4
**Blocks:** Story 3.2, 3.4

---

## Technical Implementation

### Components

**Primary Service:** `TransitionIndexService` (NEW v2.0)
- **Location:** `backend/app/services/graph/transition_index.py`
- **Method:** `calculate_transition_index(user_skills, target_role)`

**Repository:** `Neo4jRepository`
- **Location:** `backend/app/repositories/neo4j_repository.py`
- **Method:** `get_role_requirements(role_name)` to fetch target role skills

### Database Schema Changes

**Formula Implementation:**

```python
def calculate_transition_index(user_skills: List[str], target_role: str) -> Dict:
    """
    Calculate transition difficulty score from user skills to target role.

    Formula: 0.50*AvgCloseness + 0.30*CoreOverlap + 0.20*MarketDemand

    Returns:
        {
            "score": float (0-1),
            "components": {
                "avg_closeness": float,
                "core_overlap": float,
                "market_demand": float
            },
            "interpretation": str ("High Feasibility" | "Moderate Pivot" | "Major Pivot"),
            "disclaimer": "Heuristic score, not research-validated",
            "is_validated": false
        }
    """
    target_skills = neo4j_repo.get_role_requirements(target_role)
    core_skills = [s for s in target_skills if s.get('importance') == 'core']

    # Component 1: Average Closeness (50% weight)
    closeness_scores = [
        max(calculate_closeness(user_skill, target_skill['name'])
            for user_skill in user_skills)
        for target_skill in target_skills
    ]
    avg_closeness = sum(closeness_scores) / len(closeness_scores)

    # Component 2: Core Overlap (30% weight)
    core_overlaps = [
        max(calculate_closeness(user_skill, core_skill['name'])
            for user_skill in user_skills)
        for core_skill in core_skills
    ]
    core_overlap = sum(1 for overlap in core_overlaps if overlap > 0.7) / len(core_skills)

    # Component 3: Market Demand (20% weight)
    # Normalized 0-1 (higher = more in-demand role)
    market_demand = neo4j_repo.get_role_market_demand(target_role) / 10000  # Normalize

    # Combined TransitionIndex
    transition_index = (
        0.50 * avg_closeness +
        0.30 * core_overlap +
        0.20 * market_demand
    )

    # Interpretation
    if transition_index > 0.7:
        interpretation = "High Feasibility - Strong skill overlap"
    elif transition_index > 0.4:
        interpretation = "Moderate Pivot - Some skill gaps to address"
    else:
        interpretation = "Major Pivot - Significant reskilling required"

    return {
        'score': transition_index,
        'components': {
            'avg_closeness': avg_closeness,
            'core_overlap': core_overlap,
            'market_demand': market_demand
        },
        'interpretation': interpretation,
        'disclaimer': 'Heuristic score, not research-validated',
        'is_validated': False
    }
```

### Testing

**Unit Test:** `tests/unit/test_transition_index.py`
- Test formula with known inputs
- Validate weight sensitivity (change weights, observe score changes)
- Test interpretation thresholds (>0.7, 0.4-0.7, <0.4)

**Integration Test:** `tests/integration/test_transition_index.py`
- Test UI Dev → UX Designer scores 0.5-0.7 (moderate)
- Test UI Dev → Data Scientist scores 0.2-0.4 (major pivot)
- Verify response time <200ms (NFR13)

### Performance Targets

- **Query Time:** <200ms per transition index calculation (NFR13)
- **Batch Mode:** 20 user-role pairs in <5 seconds
- **Accuracy:** Interpretation aligns with expected career transitions

### Security Considerations

From `security.md`:
- **Disclaimer Enforcement:** UI must display "heuristic, not validated" warning
- **Input Validation:** Validate user_skills list and target_role exist
- **Rate Limiting:** Max 50 transition index requests per user per hour
