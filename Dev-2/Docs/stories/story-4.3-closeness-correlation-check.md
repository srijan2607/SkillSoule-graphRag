# Story 4.3: Closeness Correlation Check with Expert Judgment

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.3
**Estimated Effort:** 2-3 days

## User Story
**As a** researcher,
**I want** to measure correlation between closeness scores and expert ratings,
**so that** we validate our network metric.

## Acceptance Criteria
1. 100 skill pairs dataset (50 highly related, 30 moderate, 20 unrelated)
2. 5 experts rate each pair 1-10 scale
3. Compute system closeness for all pairs
4. Pearson correlation: Target >0.7
5. Scatter plot visualization

## Integration Verification
**IV1:** 100 pairs cover diverse skill categories
**IV2:** Inter-rater reliability (Cronbach's alpha) >0.7
**IV3:** Correlation p-value <0.05 (significant)

## Dependencies
**Depends on:** Story 2.3, 2.7
**Blocks:** Story 4.5

---

## Technical Implementation

### Components

**Primary Script:** `CorrelationAnalysis`
- **Location:** `backend/scripts/correlation_analysis.py`
- **Method:** `compute_pearson_correlation()`, `generate_scatter_plot()`

**Database:**
**PostgreSQL Table:** `closeness_expert_ratings`

```sql
CREATE TABLE closeness_expert_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_pair_id VARCHAR(100) NOT NULL,
    skill_a VARCHAR(255) NOT NULL,
    skill_b VARCHAR(255) NOT NULL,
    expert_id UUID NOT NULL REFERENCES users(id),
    expert_name VARCHAR(255) NOT NULL,
    expert_rating INTEGER CHECK (expert_rating BETWEEN 1 AND 10),
    system_closeness FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_closeness_ratings_pair ON closeness_expert_ratings(skill_pair_id);
```

### Skill Pair Dataset

```python
SKILL_PAIRS_DATASET = {
    # Highly related (50 pairs)
    "highly_related": [
        ("HTML", "CSS"),
        ("React", "React Native"),
        ("Python", "Django"),
        # ... 47 more pairs
    ],
    # Moderately related (30 pairs)
    "moderately_related": [
        ("Python", "Rust"),
        ("Frontend", "Backend"),
        # ... 28 more pairs
    ],
    # Unrelated (20 pairs)
    "unrelated": [
        ("Accounting", "Machine Learning"),
        ("Graphic Design", "Embedded Systems"),
        # ... 18 more pairs
    ]
}
```

### Correlation Analysis Script

```python
def compute_pearson_correlation():
    """
    Compute Pearson correlation between system closeness and expert ratings.
    """
    # Fetch all expert ratings and system closeness scores
    ratings = await db.query("""
        SELECT skill_pair_id, AVG(expert_rating) as avg_expert_rating, AVG(system_closeness) as avg_closeness
        FROM closeness_expert_ratings
        GROUP BY skill_pair_id
    """)

    expert_ratings = [r['avg_expert_rating'] for r in ratings]
    system_closeness = [r['avg_closeness'] for r in ratings]

    # Compute Pearson correlation
    correlation, p_value = pearsonr(expert_ratings, system_closeness)

    # Compute inter-rater reliability (Cronbach's alpha)
    alpha = compute_cronbachs_alpha(ratings)

    return {
        'correlation': correlation,
        'p_value': p_value,
        'cronbachs_alpha': alpha,
        'target_correlation': 0.7,
        'target_alpha': 0.7,
        'correlation_met': correlation > 0.7,
        'alpha_met': alpha > 0.7,
        'significant': p_value < 0.05
    }

def generate_scatter_plot():
    """Generate scatter plot of expert ratings vs system closeness."""
    plt.figure(figsize=(10, 6))
    plt.scatter(expert_ratings, system_closeness, alpha=0.6)
    plt.xlabel('Average Expert Rating (1-10)')
    plt.ylabel('System Closeness Score (0-1)')
    plt.title(f'Correlation: {correlation:.2f}, p-value: {p_value:.3f}')
    plt.savefig('/Users/srijan26/Desktop/Dev/Dev-2/Docs/research/closeness_correlation.png')
```

### Testing

**Unit Test:** `tests/unit/test_correlation_analysis.py`
- Test Pearson correlation calculation
- Validate Cronbach's alpha computation
- Test scatter plot generation

**Integration Test:** `tests/integration/test_correlation_analysis.py`
- Submit 500 ratings (100 pairs × 5 experts)
- Verify inter-rater reliability >0.7
- Verify correlation >0.7, p-value <0.05

### Performance Targets

- **Correlation Coefficient:** >0.7 (Pearson)
- **Inter-Rater Reliability:** >0.7 (Cronbach's alpha)
- **Statistical Significance:** p-value <0.05

### Security Considerations

From `security.md`:
- **Admin-Only Script:** Only admins can run correlation analysis
- **Data Privacy:** Anonymize expert names in published results
- **Data Validation:** Validate all ratings between 1-10
