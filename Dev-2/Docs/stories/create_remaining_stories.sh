#!/bin/bash

# Epic 2 Stories
cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.1-eigenvector-centrality.md" << 'EOF'
# Story 2.1: Eigenvector Centrality Calculation with Neo4j GDS

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.1
**Estimated Effort:** 2-3 days

## User Story
**As a** data scientist,
**I want** to compute eigenvector centrality for all skills using Neo4j Graph Data Science,
**so that** we can identify high-leverage skills based on network structure (not just frequency).

## Acceptance Criteria
1. Neo4j GDS in-memory graph projection created (Nodes: Skill, Relationships: SIMILAR_TO, COMPLEMENTS)
2. Eigenvector centrality algorithm executed: `gds.eigenvector.write()` to Skill.eigenvector_centrality
3. Top 10 skills by centrality logged (Python, JavaScript, SQL expected)
4. Performance: <30s for 8K skills (NFR11)
5. Update frequency: After CSV ingestion (configurable)

## Integration Verification
**IV1:** Centrality property doesn't affect v1.1 semantic search
**IV2:** Top 10 centrality >0.5, bottom 10% <0.1
**IV3:** GDS projection fits free tier limits

## Dependencies
**Depends on:** Story 1.3 (needs COMPLEMENTS relationships)
**Blocks:** Story 2.3, 3.2 (centrality used in queries)
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.2-shortest-path-distance.md" << 'EOF'
# Story 2.2: Shortest Path Distance Calculation (Dijkstra's Algorithm)

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.2
**Estimated Effort:** 2-3 days

## User Story
**As a** career advisor user,
**I want** to calculate shortest path distance between skills,
**so that** I can quantify skill-to-skill transfer difficulty.

## Acceptance Criteria
1. Function `calculate_shortest_path(skill_a, skill_b)` implemented using Neo4j Dijkstra
2. Returns: distance (float), path (list), path_length (int)
3. Edge distance: `d(s1,s2) = 1 / co_occurrence_count`
4. Handles: no path (distance=infinity), direct connection, edge cases
5. Performance: <500ms per query (NFR12)

## Integration Verification
**IV1:** Path correctness (HTML→React through CSS/JavaScript)
**IV2:** 100 random pairs average <500ms
**IV3:** v1.1 Cypher queries unchanged speed

## Dependencies
**Depends on:** Story 1.3 (uses COMPLEMENTS weights)
**Blocks:** Story 2.3 (closeness uses shortest path)
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.3-closeness-metric.md" << 'EOF'
# Story 2.3: Closeness Metric Calculation

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.3
**Estimated Effort:** 1-2 days

## User Story
**As a** system,
**I want** to convert shortest path distance into normalized closeness scores,
**so that** metric values are intuitive (0-1 range, higher = more related).

## Acceptance Criteria
1. Function `calculate_closeness(skill_a, skill_b)` implemented
2. Formula: `Closeness(A,B) = 1 / (1 + Distance(A,B))`
3. Returns: closeness (0-1), distance, path
4. Edge cases: no path (0.0), same skill (1.0)
5. Batch mode for efficiency

## Integration Verification
**IV1:** Formula correctness (direct≈0.9-1.0, 2-hop≈0.5-0.7, no path=0.0)
**IV2:** Batch 200 pairs in <5s
**IV3:** Deterministic (same input = same output)

## Dependencies
**Depends on:** Story 2.2
**Blocks:** Story 2.4, 2.5
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.4-user-to-job-closeness.md" << 'EOF'
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
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.5-transition-index.md" << 'EOF'
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
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.6-recombinant-innovation.md" << 'EOF'
# Story 2.6: Recombinant Innovation Indices (Optional Beta)

**Epic:** Epic 2 - Network Metrics Implementation
**Story ID:** 2.6
**Estimated Effort:** 2-3 days

## User Story
**As a** researcher,
**I want** to classify jobs by skill combination novelty,
**so that** we can test high-creation jobs vs salary premium hypothesis.

## Acceptance Criteria
1. Functions `calculate_creation_index(job_id)` and `calculate_reuse_index(job_id)`
2. CreationIndex = (Novel pairs) / (Total pairs), Novel = <5% jobs
3. Classification: CUTTING_EDGE (>0.5), EMERGING (0.3-0.5), ESTABLISHED (<0.3)
4. Store as Job properties: creation_index, reuse_index, innovation_class
5. Backend-only for MVP (UI deferred)

## Integration Verification
**IV1:** Common skills (Python, SQL, Git) have low creation_index (<0.2)
**IV2:** Rare combos (Rust+WASM+WebGPU) have high creation_index (>0.7)
**IV3:** 40K jobs processed in <10 minutes

## Dependencies
**Depends on:** Story 1.3
**Blocks:** Story 4.5 (validation testing)
EOF

cat > "/Users/srijan26/desktop/Dev/Dev-2/docs/stories/story-2.7-metrics-api-endpoints.md" << 'EOF'
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
EOF

echo "Epic 2 stories created successfully!"
