# Test Strategy and Standards

## Testing Philosophy

- **Approach:** Test-after development for MVP (TDD for critical algorithms post-MVP)
- **Coverage Goals:**
  - Backend: >80% line coverage (pytest-cov)
  - Frontend: >70% component coverage (Jest + React Testing Library)
- **Test Pyramid:**
  - 70% Unit tests (fast, isolated, algorithm correctness)
  - 20% Integration tests (API endpoints, database queries)
  - 10% End-to-end tests (full query flow with UI)

## Test Types and Organization

### Unit Tests

- **Framework:** pytest 7.x (backend), Jest 29.x (frontend)
- **File Convention:** `test_<module>.py` (backend), `<Component>.test.tsx` (frontend)
- **Location:** `backend/tests/unit/`, `frontend/src/__tests__/`
- **Mocking Library:** `unittest.mock` (Python), `jest.mock()` (TypeScript)
- **Coverage Requirement:** >80% (backend), >70% (frontend)

**AI Agent Requirements (Backend):**
- Generate tests for all public methods in services (GraphMetricsService, EmbeddingService)
- Cover edge cases: empty input, invalid skill_id, no path found
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies (Neo4j, HuggingFace API, OpenRouter)

**Critical Test Cases (v2.0):**
1. **Centrality Calculation Accuracy** (`test_centrality.py`)
   - Compare Neo4j GDS output to reference values (hand-calculated or from research paper)
   - Validate range [0, 1], sum of centrality ≈ number of nodes
   - Test convergence (max iterations reached without oscillation)

2. **Shortest Path Correctness** (`test_shortest_path.py`)
   - Validate Dijkstra results on known graphs (triangle inequality)
   - Test edge cases: no path (disconnected skills), self-loop (same skill)
   - Performance: <500ms for typical skill-to-skill queries (NFR12)

3. **TransitionIndex Formula** (`test_transition_index.py`)
   - Test edge cases: closeness=0 (no path), overlap=1 (all skills match), demand=0 (unknown skills)
   - Validate range [0, 1], component weights sum to 1.0
   - Regression: Ensure formula unchanged (0.5 closeness + 0.3 overlap + 0.2 demand)

### Integration Tests

- **Scope:** API endpoints + database interactions (Neo4j, PostgreSQL)
- **Location:** `backend/tests/integration/`
- **Test Infrastructure:**
  - **Neo4j:** Testcontainers for isolated Neo4j instance (or in-memory H2 graph if available)
  - **PostgreSQL:** Testcontainers PostgreSQL
  - **OpenRouter LLM:** WireMock for stubbing API responses (avoid real API calls in tests)

**Critical Integration Tests (v2.0):**
1. **Query Flow with Metrics** (`test_query_flow.py`)
   - Submit query → Verify metric values in response (centrality, closeness, TransitionIndex)
   - Validate sources include skill paths, centrality rankings
   - Performance: <5s total query time (NFR1)

2. **Graph Migration Idempotence** (`test_migration.py`)
   - Run migration script 2x on same database
   - Verify no duplicate properties, relationships
   - Validate data integrity (node count unchanged, new properties present)

3. **CSV Ingestion + Centrality Recalculation** (`test_ingestion.py`)
   - Ingest 100 skills → Trigger centrality recalculation
   - Verify centrality values updated, `market_demand` incremented
   - Performance: Centrality <30s for 5K skills (NFR11)

### End-to-End Tests

- **Framework:** Playwright (browser automation)
- **Scope:** Full user journey (login → query → view response with metrics)
- **Environment:** Local development (backend + frontend running)
- **Test Data:** Seeded database with known skills, jobs (fixtures)

**Critical E2E Tests:**
1. User submits "Which skills transfer to UX Designer?" → Response includes closeness scores, TransitionIndex
2. User clicks "View skill path" → SkillPathVisualization renders correctly
3. Regression: v1.1 query "What skills for Backend Developer?" returns same results (no degradation)

## Test Data Management

- **Strategy:** Fixtures with known expected values (deterministic)
- **Fixtures:** `tests/fixtures/skills.json`, `tests/fixtures/jobs.json`
- **Factories:** `SkillFactory.create()` for dynamic test data generation
- **Cleanup:** Tear down Testcontainers after each test suite, clear in-memory state

**Example Fixture (Centrality Validation):**
```json
{
  "skills": [
    {"skill_id": "1", "name": "Python", "expected_centrality": 0.92},
    {"skill_id": "2", "name": "Django", "expected_centrality": 0.78},
    {"skill_id": "3", "name": "Flask", "expected_centrality": 0.75}
  ],
  "relationships": [
    {"type": "SIMILAR_TO", "from": "1", "to": "2", "weight": 0.85},
    {"type": "COMPLEMENTS", "from": "1", "to": "3", "weight": 0.72}
  ]
}
```

## Continuous Testing

- **CI Integration:** GitHub Actions workflow (`.github/workflows/ci.yml`)
  - On push: Linting (black, ruff, eslint)
  - On pull request: Unit tests, integration tests
  - Nightly: E2E tests (heavier, not blocking)
- **Performance Tests:** Benchmark centrality, shortest path on 1K/5K/8K skill datasets
- **Security Tests:** `bandit` (Python static analysis), `npm audit` (dependency vulnerabilities)

---
