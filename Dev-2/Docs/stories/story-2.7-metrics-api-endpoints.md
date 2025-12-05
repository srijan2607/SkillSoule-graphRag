# Story 2.7: Metrics API Endpoints

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.7
**Estimated Effort:** 1-2 days

## User Story
**As a** system administrator,
**I want** API endpoints to access metrics programmatically,
**so that** we can validate hypotheses and enable expert evaluation.

## Acceptance Criteria
1. GET `/api/metrics/centrality?top_n=20` - Returns top skills by centrality
2. GET `/api/metrics/closeness?skill_a=Python&skill_b=Django` - Returns closeness data
3. POST `/api/metrics/transition` - Body: {user_skills, target_role}, Returns: TransitionIndex
4. JWT authentication required (same as v1.1)
5. Rate limiting: 100 req/hour per user

## Integration Verification
**IV1:** OpenAPI schema auto-generated, Swagger UI tested
**IV2:** Unauth requests return 401
**IV3:** All endpoints respond <1s

## Dependencies
**Depends on:** Stories 2.1-2.5
**Blocks:** Story 4.1-4.3 (validation needs these APIs)

---

## Technical Implementation

### Components

**Primary Router:** `MetricsRouter` (NEW v2.0)
- **Location:** `backend/app/routers/metrics.py`
- **Endpoints:** `/api/metrics/centrality`, `/api/metrics/closeness`, `/api/metrics/transition`

**Services:**
- `CentralityService` - For centrality queries
- `ShortestPathService` - For closeness queries
- `TransitionIndexService` - For transition index queries

**Middleware:**
- **Auth:** JWT authentication (same as v1.1)
- **Rate Limiting:** 100 requests/hour per user

### API Endpoints

From `rest-api-spec.md`:

**1. GET `/api/metrics/centrality`**
```python
@router.get("/api/metrics/centrality")
async def get_top_centrality(
    top_n: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Returns top skills by eigenvector centrality.

    Query Parameters:
        - top_n: Number of top skills to return (1-100, default: 20)

    Response:
        {
            "skills": [
                {
                    "skill_id": "uuid",
                    "name": "Python",
                    "centrality": 0.95,
                    "rank": 1
                }
            ],
            "total_skills": 8000
        }
    """
```

**2. GET `/api/metrics/closeness`**
```python
@router.get("/api/metrics/closeness")
async def get_closeness(
    skill_a: str = Query(..., description="Source skill name"),
    skill_b: str = Query(..., description="Target skill name"),
    current_user: User = Depends(get_current_user)
):
    """
    Returns closeness score between two skills.

    Response:
        {
            "skill_a": "Python",
            "skill_b": "Django",
            "closeness": 0.85,
            "distance": 0.18,
            "path": ["Python", "Web Development", "Django"],
            "path_length": 2
        }
    """
```

**3. POST `/api/metrics/transition`**
```python
@router.post("/api/metrics/transition")
async def calculate_transition(
    request: TransitionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate transition index from user skills to target role.

    Request Body:
        {
            "user_skills": ["Python", "JavaScript", "React"],
            "target_role": "Data Scientist"
        }

    Response:
        {
            "score": 0.62,
            "components": {
                "avg_closeness": 0.58,
                "core_overlap": 0.67,
                "market_demand": 0.72
            },
            "interpretation": "Moderate Pivot",
            "disclaimer": "Heuristic score, not validated",
            "is_validated": false
        }
    """
```

### Testing

**Unit Test:** `tests/unit/test_metrics_api.py`
- Test endpoint validation (auth, rate limits)
- Test query parameter validation
- Mock service responses

**Integration Test:** `tests/integration/test_metrics_api.py`
- Test all endpoints with real data
- Verify JWT authentication (401 for unauth)
- Test rate limiting (429 after 100 requests)
- Verify OpenAPI schema generation

### Performance Targets

- **Response Time:** All endpoints <1 second
- **Rate Limiting:** 100 requests/hour per user
- **Concurrent Users:** Support 50 concurrent users

### Security Considerations

From `security.md`:
- **JWT Authentication:** Required for all endpoints (same as v1.1)
- **Input Validation:** Pydantic models validate request bodies
- **Rate Limiting:** SlowAPI middleware (100 req/hour per user)
- **CORS:** Configure allowed origins for production deployment
