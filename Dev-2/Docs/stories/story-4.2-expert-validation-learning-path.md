# Story 4.2: Expert Validation Interface - Learning Path Quality

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.2
**Estimated Effort:** 2-3 days

## User Story
**As a** hiring manager (expert evaluator),
**I want** to rate recommended learning paths,
**so that** we validate prerequisite ordering.

## Acceptance Criteria
1. Admin API `/api/validation/learning-path` (POST, admin-only)
2. 10 learning path scenarios (e.g., HTML → Full-Stack Developer)
3. Expert evaluation: path_logical (bool), rating (1-5), time estimate
4. Target: Average rating >4.0/5

## Integration Verification
**IV1:** Ratings span 1-5 range (critical evaluation)
**IV2:** Time estimates within ±30% for >70% scenarios
**IV3:** Expert feedback stored for refinement

## Dependencies
**Depends on:** Story 2.7
**Blocks:** Story 4.5

---

## Technical Implementation

### Components

**Primary Router:** `ValidationRouter` (NEW v2.0)
- **Location:** `backend/app/routers/validation.py`
- **Endpoint:** `POST /api/validation/learning-path` (admin-only)

**Database:**
**PostgreSQL Table:** Extend `expert_validations` table with learning path fields

```sql
ALTER TABLE expert_validations ADD COLUMN path_logical BOOLEAN;
ALTER TABLE expert_validations ADD COLUMN time_estimate_hours INTEGER;
ALTER TABLE expert_validations ADD COLUMN suggested_path TEXT[];
```

### Predefined Learning Path Scenarios

```python
LEARNING_PATH_SCENARIOS = [
    {
        "scenario_id": "lp_001",
        "description": "Complete beginner to Full-Stack Developer",
        "start_skill": "None (Beginner)",
        "target_role": "Full-Stack Developer",
        "system_path": ["HTML", "CSS", "JavaScript", "React", "Node.js", "PostgreSQL"],
        "system_time_estimate": 120  # hours
    },
    {
        "scenario_id": "lp_002",
        "description": "Frontend Developer to Data Engineer",
        "start_skill": "React",
        "target_role": "Data Engineer",
        "system_path": ["Python", "SQL", "ETL Tools", "Apache Spark", "Data Warehousing"],
        "system_time_estimate": 200
    },
    # ... 8 more scenarios
]
```

### API Endpoint

```python
@router.post("/api/validation/learning-path", dependencies=[Depends(admin_only)])
async def submit_learning_path_validation(
    validation: LearningPathValidation,
    current_user: User = Depends(get_current_user)
):
    """
    Expert validation for learning path scenarios.

    Request Body:
        {
            "scenario_id": "lp_001",
            "path_logical": true,
            "rating": 4,
            "time_estimate_hours": 110,
            "notes": "Path is logical, time estimate slightly optimistic",
            "suggested_path": ["HTML", "CSS", "JavaScript", "TypeScript", "React", "Node.js", "PostgreSQL"]
        }
    """
    await validation_repo.create_expert_validation(
        validation_type="learning_path",
        scenario_id=validation.scenario_id,
        expert_id=current_user.id,
        expert_name=current_user.full_name,
        path_logical=validation.path_logical,
        rating=validation.rating,
        time_estimate_hours=validation.time_estimate_hours,
        notes=validation.notes,
        suggested_path=validation.suggested_path
    )

    return {"success": True}
```

### Testing

**Unit Test:** `tests/unit/test_learning_path_validation.py`
- Test endpoint validation
- Validate rating range (1-5)
- Test time estimate within ±30%

**Integration Test:** `tests/integration/test_learning_path_validation.py`
- Submit 50 validations (10 scenarios × 5 experts)
- Calculate average rating (target: >4.0)
- Verify time estimates within ±30% for >70% scenarios

### Performance Targets

- **Validation Submission:** <200ms
- **Average Rating:** >4.0/5.0
- **Time Estimate Accuracy:** ±30% for >70% scenarios

### Security Considerations

From `security.md`:
- **Admin-Only Access:** JWT + admin role check
- **Input Validation:** Validate rating, time estimate ranges
- **Data Privacy:** Expert feedback only visible to admins
