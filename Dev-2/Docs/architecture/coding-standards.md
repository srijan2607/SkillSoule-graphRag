# Coding Standards

## Core Standards

- **Languages & Runtimes:**
  - Python 3.11+ (backend)
  - TypeScript 5.x (frontend)
  - Node.js 20.x LTS (frontend tooling)
- **Style & Linting:**
  - Python: `black` formatter (line length 100), `ruff` linter
  - TypeScript: `prettier` formatter, `eslint` linter (Airbnb style guide)
  - Cypher: Use `UPPER_CASE` for keywords, `camelCase` for parameters, indentation 2 spaces
- **Test Organization:**
  - Unit tests: `tests/unit/test_<module>.py` (mirror `app/` structure)
  - Integration tests: `tests/integration/test_<feature>.py`
  - Fixtures: `tests/fixtures/` (sample skills, jobs, expected metrics)

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Python functions | snake_case | `calculate_eigenvector_centrality()` |
| Python classes | PascalCase | `GraphMetricsService` |
| Python constants | UPPER_SNAKE_CASE | `MAX_CENTRALITY_ITERATIONS` |
| TypeScript functions | camelCase | `calculateTransitionIndex()` |
| TypeScript components | PascalCase | `MetricBadge` |
| Neo4j node labels | PascalCase | `Skill`, `Job` |
| Neo4j relationships | UPPER_SNAKE_CASE | `PREREQUISITE_OF`, `COMPLEMENTS` |
| Neo4j properties | snake_case | `eigenvector_centrality`, `co_occurrence_rate` |
| API endpoints | kebab-case | `/api/metrics/centrality` |
| Environment variables | UPPER_SNAKE_CASE | `NEO4J_GDS_ENABLED` |

## Critical Rules

**1. Metric Calculation Transparency**
- **Rule:** All metric calculation functions MUST include mathematical formula in docstring
- **Rationale:** Research validation requires reproducible methodology (FR45, FR46)
- **Example:**
  ```python
  def calculate_closeness(skill_a: str, skill_b: str) -> float:
      """
      Calculate closeness between two skills using shortest path distance.

      Formula: Closeness(A, B) = 1 / (1 + Distance(A, B))
      where Distance = shortest path via Dijkstra (edge weight = 1/co_occurrence_count)

      Research citation: Adapted from "Ties that Bind: ICT Network" (Page 15-16)

      Args:
          skill_a: Source skill name
          skill_b: Target skill name

      Returns:
          Closeness score in range [0, 1]

      Raises:
          ShortestPathError: If no path exists between skills
      """
  ```

**2. Backward Compatibility Enforcement**
- **Rule:** Never modify v1.1 API contracts (request/response schemas) - only extend
- **Rationale:** Avoid breaking existing clients (CR1, NFR17)
- **Validation:** Run v1.1 regression tests in CI/CD pipeline

**3. Graph Algorithm Timeout Handling**
- **Rule:** All Neo4j GDS calls MUST have explicit timeout with fallback behavior
- **Rationale:** Prevent query timeout cascades (NFR11, NFR12, Risk 1)
- **Example:**
  ```python
  try:
      centrality = neo4j_gds.eigenvector(timeout=30)
  except TimeoutError:
      logger.warning("Centrality calculation timeout, using approximate PageRank")
      centrality = neo4j_gds.pagerank(timeout=10)
  ```

**4. LangGraph State Validation**
- **Rule:** All LangGraph nodes MUST validate `state.metadata` for pipeline errors before processing
- **Rationale:** Prevent error propagation through pipeline (error handling pattern)
- **Example:**
  ```python
  def response_generation(state: GraphRAGState) -> dict:
      if state.metadata.get("vector_search_error"):
          return {"final_response": "⚠️ PIPELINE ERROR: Vector search failed..."}
      # Normal processing
  ```

**5. Metric Disclaimer for Heuristics**
- **Rule:** TransitionIndex and unvalidated metrics MUST include disclaimer in UI/API responses
- **Rationale:** Ethical requirement - users must know heuristic vs validated metrics (FR46, NFR18)
- **Example:** Response includes: "TransitionIndex is a heuristic score, not a research-validated probability"

---
