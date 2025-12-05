# Epic 2: Network Metrics Implementation

**Epic Goal:** Implement and validate research-driven network metrics (eigenvector centrality, shortest path closeness, TransitionIndex) with performance optimization for <5s query response time

**Integration Requirements:**
- Neo4j GDS library enabled and functional
- Centrality calculation completes in <30s (NFR11)
- Shortest path queries return in <500ms (NFR12)
- All metrics logged for research validation framework

## Story 2.1: Eigenvector Centrality Calculation with Neo4j GDS

**As a** data scientist,
**I want** to compute eigenvector centrality for all skills using Neo4j Graph Data Science,
**so that** we can identify high-leverage skills based on network structure (not just frequency).

### Acceptance Criteria

1. Neo4j GDS in-memory graph projection created:
   - Nodes: Skill (all 5K-8K skills)
   - Relationships: SIMILAR_TO, COMPLEMENTS (weighted by co_occurrence_rate)
   - Projection name: `skill-network`
2. Eigenvector centrality algorithm executed:
   - Algorithm: `gds.eigenvector.stream('skill-network')` or `gds.eigenvector.write()`
   - Write results to `Skill.eigenvector_centrality` property
   - Normalization: Centrality values in [0, 1] range
3. Top 10 skills by centrality logged and validated:
   - Manual review: Do high-centrality skills make sense? (e.g., Python, JavaScript, SQL expected)
4. Performance: Centrality calculation completes in <30s for 8K skills
5. Update frequency: Centrality recalculated after each CSV ingestion batch (configurable via `CENTRALITY_UPDATE_FREQUENCY` env var)

### Integration Verification

**IV1:** Existing skill queries unchanged - Centrality property doesn't affect v1.1 semantic search

**IV2:** Centrality value sanity check - Top 10 skills have centrality >0.5, bottom 10% have centrality <0.1 (reasonable distribution)

**IV3:** Neo4j GDS memory usage - GDS projection fits within free tier limits, no out-of-memory errors

---

## Story 2.2: Shortest Path Distance Calculation (Dijkstra's Algorithm)

**As a** career advisor user,
**I want** to calculate the shortest path distance between any two skills,
**so that** I can quantify skill-to-skill transfer difficulty for career planning.

### Acceptance Criteria

1. Python function `calculate_shortest_path(skill_a: str, skill_b: str)` implemented:
   - Uses Neo4j `shortestPath()` Cypher function or GDS Dijkstra algorithm
   - Relationships used: CO_OCCURS_WITH (primary), PREREQUISITE_OF (optional)
   - Edge weight: `w(s1, s2) = co_occurrence_count` from COMPLEMENTS relationship
   - Edge distance: `d(s1, s2) = 1 / w(s1, s2)` (inverse frequency)
2. Returns:
   - Distance value (float): Sum of edge distances along shortest path
   - Path (list of skill names): [skill_a, intermediate_1, ..., skill_b]
   - Path length (integer): Number of hops
3. Handles edge cases:
   - No path exists: Return distance = infinity, path = null
   - Direct connection: Return distance = 1 / w(a, b), path = [a, b]
4. Performance: Query completes in <500ms for typical skill pairs

### Integration Verification

**IV1:** Path correctness validation - Test on 10 known skill pairs (e.g., HTML → React should path through CSS/JavaScript)

**IV2:** Performance benchmark - 100 random skill pair queries complete in <500ms average

**IV3:** No impact on existing graph traversal - v1.1 Cypher queries still execute at same speed

---

## Story 2.3: Closeness Metric Calculation

**As a** system,
**I want** to convert shortest path distance into normalized closeness scores,
**so that** metric values are intuitive (0-1 range, higher = more related).

### Acceptance Criteria

1. Python function `calculate_closeness(skill_a: str, skill_b: str)` implemented:
   - Formula: `Closeness(A, B) = 1 / (1 + Distance(A, B))`
   - Range: [0, 1] where 1 = direct connection, 0 = very distant/no path
   - Uses `calculate_shortest_path()` function from Story 2.2
2. Returns:
   - Closeness score (float, 0-1)
   - Distance value (float, for transparency)
   - Shortest path (list of skills, for user explanation)
3. Edge cases:
   - No path (distance = infinity): Return closeness = 0.0
   - Same skill (distance = 0): Return closeness = 1.0
4. Batch mode: `calculate_closeness_batch(user_skills: list, target_skills: list)` for efficiency

### Integration Verification

**IV1:** Formula correctness - Test cases: Direct connection (closeness ≈ 0.9-1.0), 2-hop path (closeness ≈ 0.5-0.7), no path (closeness = 0.0)

**IV2:** Batch performance - Calculate closeness for 10 user skills × 20 target skills (200 pairs) in <5s total

**IV3:** Result consistency - Running closeness calculation twice for same pair returns identical results (deterministic)

---

## Story 2.4: User-to-Job Closeness Scoring

**As a** job seeker,
**I want** the system to calculate how close my skill set is to a job's requirements,
**so that** I receive quantified match scores instead of just "qualified" or "not qualified".

### Acceptance Criteria

1. Python function `calculate_job_closeness(user_skills: list, job_id: str)` implemented:
   - Fetch job required skills from Neo4j: `MATCH (j:Job {Job_ID: job_id})-[:REQUIRES]->(s:Skill) RETURN s.NAME`
   - For each required skill: Find minimum distance to any user skill
   - Formula: `JobCloseness = (1/m) * Σ closeness_j` where m = number of required skills
2. Optional enhancement: Core skill weighting
   - Identify core skills (top 3 by centrality or explicitly tagged)
   - Weight core skill closeness 2.0x in average
3. Returns:
   - Overall job closeness score (float, 0-1)
   - Per-skill breakdown (dict: {required_skill: closeness_to_nearest_user_skill})
   - Transferable skills (list: user skills with closeness >0.7 to any required skill)
4. Performance: Calculate closeness for user with 10 skills vs job with 15 required skills in <1s

### Integration Verification

**IV1:** Score sanity check - User with exact skill match scores closeness ≈ 1.0, user with no matching skills scores <0.3

**IV2:** Core skill weighting test - Job requiring Python (core) vs obscure skill: Python mismatch penalizes score more

**IV3:** No regression in job search - Existing v1.1 job listing queries still work, closeness score additive

---

## Story 2.5: TransitionIndex Heuristic Implementation

**As a** career transition planner,
**I want** a quantified transition difficulty score between skill sets,
**so that** I can prioritize feasible career paths and set realistic timelines.

### Acceptance Criteria

1. Python function `calculate_transition_index(user_skills: list, target_role: str)` implemented:
   - Fetch target role required skills from job title matching or skill category
   - Component 1 (50% weight): Average closeness from user skills to target skills
   - Component 2 (30% weight): Core skill overlap ratio
   - Component 3 (20% weight): Market demand (normalized log(job_count) for target skills)
   - Formula: `TransitionIndex = 0.50 * AvgCloseness + 0.30 * CoreOverlap + 0.20 * MarketDemand`
2. Returns:
   - TransitionIndex score (float, 0-1)
   - Component breakdown (dict: {closeness: 0.6, core_overlap: 0.4, market_demand: 0.8})
   - Interpretation (string): "High feasibility" (>0.7), "Moderate" (0.4-0.7), "Major pivot" (<0.4)
   - **Disclaimer flag**: `is_validated = false` (heuristic, not research-validated probability)
3. Edge cases:
   - User skills empty: Return TransitionIndex = 0.0 with warning
   - Target role unknown: Return error with suggested role names
4. Performance: Calculate TransitionIndex in <200ms (NFR13)

### Integration Verification

**IV1:** Heuristic validation - Test on 10 known transitions (UI Dev → UX Designer should score 0.5-0.7, UI Dev → Data Scientist should score 0.2-0.4)

**IV2:** Component weight sensitivity - Manually adjust weights (0.6, 0.2, 0.2) and verify score changes make intuitive sense

**IV3:** Disclaimer enforcement - All API responses including TransitionIndex display "Heuristic score, not validated" warning

---

## Story 2.6: Recombinant Innovation Indices (Optional Beta)

**As a** researcher,
**I want** to classify jobs by skill combination novelty,
**so that** we can test the hypothesis that high-creation jobs correlate with salary premium.

### Acceptance Criteria

1. Python function `calculate_creation_index(job_id: str)` implemented:
   - Fetch job required skills: `MATCH (j:Job {Job_ID: job_id})-[:REQUIRES]->(s:Skill) RETURN s`
   - Compute skill pair novelty:
     - Novel pair: Skill combination appears in <5% of all jobs
     - Established pair: Skill combination appears in >20% of jobs
   - Formula: `CreationIndex = (Novel pairs) / (Total pairs in job)`
2. Python function `calculate_reuse_index(job_id: str)` implemented:
   - Formula: `ReuseIndex = (Established pairs) / (Total pairs in job)`
3. Job classification based on CreationIndex:
   - CUTTING_EDGE: creation_index >0.5
   - EMERGING: creation_index 0.3-0.5
   - ESTABLISHED: creation_index <0.3
4. Store indices as Job node properties: `creation_index`, `reuse_index`, `innovation_class`
5. **Implementation note**: Backend-only for MVP, UI exposure deferred until validation

### Integration Verification

**IV1:** Index calculation correctness - Jobs with all common skills (Python, SQL, Git) have low creation_index (<0.2)

**IV2:** Novel skill detection - Jobs requiring rare combos (Rust + WASM + WebGPU) have high creation_index (>0.7)

**IV3:** Performance - Calculate indices for 40K jobs in <10 minutes (batch processing)

---

## Story 2.7: Metrics API Endpoints

**As a** system administrator,
**I want** API endpoints to access centrality and closeness metrics programmatically,
**so that** we can validate research hypotheses and enable expert evaluation.

### Acceptance Criteria

1. FastAPI endpoint `/api/metrics/centrality` (GET):
   - Query params: `skill_id` (optional), `top_n` (default 10)
   - Response: JSON array with [{skill_name, centrality_score, rank, market_demand}]
   - Example: `/api/metrics/centrality?top_n=20` returns top 20 skills by centrality
2. FastAPI endpoint `/api/metrics/closeness` (GET):
   - Query params: `skill_a` (required), `skill_b` (required)
   - Response: JSON with {distance, closeness_score, shortest_path: [skills], path_length}
   - Example: `/api/metrics/closeness?skill_a=Python&skill_b=Django`
3. FastAPI endpoint `/api/metrics/transition` (POST):
   - Request body: {user_skills: [list], target_role: string}
   - Response: JSON with {transition_index, components: {closeness, core_overlap, market_demand}, interpretation, disclaimer}
4. Authentication: Require JWT token (same as v1.1 endpoints)
5. Rate limiting: Max 100 requests/hour per user (prevent abuse)

### Integration Verification

**IV1:** API contract validation - OpenAPI schema auto-generated by FastAPI, test with Swagger UI

**IV2:** Authentication enforcement - Unauthenticated requests return 401 Unauthorized

**IV3:** Response time - All metrics endpoints respond in <1s for typical queries

---
