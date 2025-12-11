# Acceptance Criteria

- [ ] **Neo4j Schema**
  - [ ] Skill nodes have canonical_name, centrality, demand_count properties
  - [ ] Job nodes have content_hash, skill_count properties
  - [ ] SIMILAR_JOB relationships exist with jaccard_score
  - [ ] All required indexes created

- [ ] **Ingestion Pipeline**
  - [ ] Skills are normalized (JS → javascript)
  - [ ] Duplicate jobs are detected and skipped
  - [ ] CO_OCCURS_WITH edges created after ingestion
  - [ ] SIMILAR_JOB edges created after ingestion
  - [ ] Status endpoint shows enrichment progress

- [ ] **Query Pipeline**
  - [ ] New intents detected (CAREER_TRANSITION, SKILL_BRIDGE, etc.)
  - [ ] Network enrichment node runs and populates state
  - [ ] Hybrid scoring applied (vector + centrality + demand)
  - [ ] Context includes network facts section
  - [ ] Response includes network_insights field

- [ ] **Frontend**
  - [ ] NetworkInsightsPanel renders for relevant queries
  - [ ] Skill paths shown with visual bridge
  - [ ] Similar jobs shown with match percentages
  - [ ] Job closeness breakdown displayed

- [ ] **Demo Queries**
  - [ ] All 4 Neo4j visualization queries work
  - [ ] All 4 sample chat queries show improvement

---
