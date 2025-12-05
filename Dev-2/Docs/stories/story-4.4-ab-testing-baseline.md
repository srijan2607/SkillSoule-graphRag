# Story 4.4: Baseline A/B Testing - Job-Centric vs Skill-Centric

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.4
**Estimated Effort:** 3-4 days

## User Story
**As a** product manager,
**I want** to compare user satisfaction with v1.1 vs v2.0,
**so that** we validate graph restructuring improves relevance.

## Acceptance Criteria
1. A/B test: Group A (v1.1 job-centric), Group B (v2.0 skill-centric)
2. Metrics: relevance rating (1-5), time to answer, click-through rate
3. Sample: 50 users, 3+ queries each (150 total)
4. Target: Group B outperforms by >15%
5. Two-sample t-test, p<0.05

## Integration Verification
**IV1:** Random user assignment (no bias)
**IV2:** All data in PostgreSQL `ab_test_results`
**IV3:** Summary report with statistical results

## Dependencies
**Depends on:** Epic 3 complete (v2.0 query pipeline ready)
**Blocks:** Story 4.5

---

## Technical Implementation

### Components

**Primary Service:** `ABTestService` (NEW v2.0)
- **Location:** `backend/app/services/ab_test_service.py`
- **Method:** `assign_user_to_group()`, `log_ab_test_result()`

**Database:**
**PostgreSQL Tables:**

```sql
-- User group assignments
CREATE TABLE ab_test_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    group_name VARCHAR(10) CHECK (group_name IN ('A', 'B')),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id)  -- Each user assigned to one group only
);

-- A/B test results
CREATE TABLE ab_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    group_name VARCHAR(10) NOT NULL,
    query_id UUID NOT NULL REFERENCES query_history(id),

    -- Metrics
    relevance_rating INTEGER CHECK (relevance_rating BETWEEN 1 AND 5),
    time_to_answer_seconds INTEGER,
    click_through BOOLEAN,  -- Did user click on any source links?

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ab_test_results_group ON ab_test_results(group_name);
CREATE INDEX idx_ab_test_results_user ON ab_test_results(user_id);
```

### A/B Test Implementation

```python
class ABTestService:
    """A/B testing service for comparing v1.1 (Group A) vs v2.0 (Group B)."""

    async def assign_user_to_group(self, user_id: str) -> str:
        """
        Randomly assign user to Group A or B (50/50 split).
        """
        # Check if already assigned
        assignment = await db.query(
            "SELECT group_name FROM ab_test_assignments WHERE user_id = $1",
            user_id
        )

        if assignment:
            return assignment['group_name']

        # Random assignment
        group = random.choice(['A', 'B'])
        await db.execute(
            "INSERT INTO ab_test_assignments (user_id, group_name) VALUES ($1, $2)",
            user_id, group
        )

        return group

    async def log_ab_test_result(
        self,
        user_id: str,
        group: str,
        query_id: str,
        relevance_rating: int,
        time_to_answer: int,
        click_through: bool
    ):
        """Log A/B test metrics."""
        await db.execute("""
            INSERT INTO ab_test_results
            (user_id, group_name, query_id, relevance_rating, time_to_answer_seconds, click_through)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, user_id, group, query_id, relevance_rating, time_to_answer, click_through)
```

### Statistical Analysis Script

```python
def compute_ab_test_results():
    """
    Compute A/B test statistical results.
    """
    # Fetch metrics for both groups
    group_a = await db.query("""
        SELECT AVG(relevance_rating) as avg_relevance,
               AVG(time_to_answer_seconds) as avg_time,
               SUM(CASE WHEN click_through THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as ctr
        FROM ab_test_results WHERE group_name = 'A'
    """)

    group_b = await db.query("""
        SELECT AVG(relevance_rating) as avg_relevance,
               AVG(time_to_answer_seconds) as avg_time,
               SUM(CASE WHEN click_through THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as ctr
        FROM ab_test_results WHERE group_name = 'B'
    """)

    # Two-sample t-test
    from scipy.stats import ttest_ind

    group_a_relevance = get_all_ratings('A')
    group_b_relevance = get_all_ratings('B')

    t_stat, p_value = ttest_ind(group_a_relevance, group_b_relevance)

    # Calculate improvement percentage
    improvement = ((group_b['avg_relevance'] - group_a['avg_relevance']) / group_a['avg_relevance']) * 100

    return {
        'group_a': group_a,
        'group_b': group_b,
        'improvement_percentage': improvement,
        't_statistic': t_stat,
        'p_value': p_value,
        'significant': p_value < 0.05,
        'target_met': improvement > 15 and p_value < 0.05
    }
```

### Testing

**Unit Test:** `tests/unit/test_ab_test.py`
- Test random user assignment (50/50 split)
- Validate metrics logging
- Test t-test calculation

**Integration Test:** `tests/integration/test_ab_test.py`
- Assign 50 users to groups
- Simulate 150 queries (3 per user)
- Compute statistical results
- Verify Group B outperforms by >15% (target)

### Performance Targets

- **User Assignment:** <50ms
- **Metrics Logging:** <100ms per result
- **Target Improvement:** Group B (v2.0) outperforms Group A (v1.1) by >15%
- **Statistical Significance:** p-value <0.05

### Security Considerations

From `security.md`:
- **Random Assignment:** Cryptographically secure random for user assignment
- **Data Privacy:** Anonymize user data in published results
- **No Bias:** Verify random assignment distribution (50% ± 5%)
