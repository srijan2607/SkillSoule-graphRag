# Story 4.1: Expert Validation Interface - Skill Transfer Identification

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.1
**Estimated Effort:** 2-3 days

## User Story
**As a** career counselor (expert evaluator),
**I want** to validate whether system correctly identifies transferable skills,
**so that** we measure ground truth accuracy.

## Acceptance Criteria
1. Admin API `/api/validation/skill-transfer` (POST, admin-only)
2. 10 career transition scenarios predefined
3. Expert evaluation: binary judgment (Yes/No), rating (1-5), notes
4. Store in PostgreSQL `expert_validations` table
5. Target: >80% agreement with system prediction

## Integration Verification
**IV1:** 10 scenarios × 5 experts = 50 evaluations stored
**IV2:** Automated agreement calculation script
**IV3:** Validation endpoints isolated from production

## Dependencies
**Depends on:** Story 2.7 (metrics APIs)
**Blocks:** Story 4.5

---

## Technical Implementation

### Components

**Primary Router:** `ValidationRouter` (NEW v2.0)
- **Location:** `backend/app/routers/validation.py`
- **Endpoint:** `POST /api/validation/skill-transfer` (admin-only)

**Database:**
**PostgreSQL Table:** `expert_validations`
```sql
CREATE TABLE expert_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_type VARCHAR(50) NOT NULL, -- 'skill_transfer', 'learning_path', etc.
    scenario_id VARCHAR(100) NOT NULL,
    scenario_description TEXT NOT NULL,
    expert_id UUID NOT NULL REFERENCES users(id),
    expert_name VARCHAR(255) NOT NULL,

    -- Skill Transfer specific fields
    binary_judgment BOOLEAN,  -- Yes/No: Are skills transferable?
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    notes TEXT,

    -- System prediction for comparison
    system_prediction_score FLOAT,
    system_prediction_method VARCHAR(100),  -- e.g., "closeness", "transition_index"

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expert_validations_type ON expert_validations(validation_type);
CREATE INDEX idx_expert_validations_scenario ON expert_validations(scenario_id);
```

### Predefined Scenarios

```python
SKILL_TRANSFER_SCENARIOS = [
    {
        "scenario_id": "st_001",
        "description": "Python developer transitioning to Rust for systems programming",
        "skill_from": "Python",
        "skill_to": "Rust",
        "system_prediction": 0.42  # Closeness score
    },
    {
        "scenario_id": "st_002",
        "description": "Frontend developer (React) moving to mobile development (React Native)",
        "skill_from": "React",
        "skill_to": "React Native",
        "system_prediction": 0.88
    },
    # ... 8 more scenarios
]
```

### API Endpoint

```python
@router.post("/api/validation/skill-transfer", dependencies=[Depends(admin_only)])
async def submit_skill_transfer_validation(
    validation: SkillTransferValidation,
    current_user: User = Depends(get_current_user)
):
    """
    Expert validation submission for skill transfer scenarios.

    Request Body:
        {
            "scenario_id": "st_001",
            "binary_judgment": true,
            "rating": 4,
            "notes": "Moderate difficulty, requires systems programming fundamentals"
        }
    """
    # Store validation
    await validation_repo.create_expert_validation(
        validation_type="skill_transfer",
        scenario_id=validation.scenario_id,
        expert_id=current_user.id,
        expert_name=current_user.full_name,
        binary_judgment=validation.binary_judgment,
        rating=validation.rating,
        notes=validation.notes
    )

    # Calculate agreement with system prediction
    agreement = calculate_agreement(validation, SKILL_TRANSFER_SCENARIOS)

    return {"success": True, "agreement_percentage": agreement}
```

### Testing

**Unit Test:** `tests/unit/test_validation_api.py`
- Test endpoint validation (admin-only)
- Validate rating constraints (1-5)
- Test agreement calculation

**Integration Test:** `tests/integration/test_validation_api.py`
- Submit 50 validations (10 scenarios × 5 experts)
- Verify all stored in PostgreSQL
- Calculate system agreement (target: >80%)

### Performance Targets

- **Validation Submission:** <200ms per submission
- **Agreement Calculation:** <50ms
- **Target Agreement:** >80% with system predictions

### Security Considerations

From `security.md`:
- **Admin-Only Access:** JWT authentication + admin role check
- **Input Validation:** Pydantic models validate all fields
- **Data Isolation:** Validation endpoints isolated from production
