# Phase 7: Visible Impact Integration - Epic Structure

**Created**: 2024-12-06
**Status**: Ready for Story Development
**PRD Source**: `claude_plan/PRD/` (sharded from `08-VISIBLE-IMPACT-INTEGRATION.md`)

---

## Overview

| Metric | Value |
|--------|-------|
| Total Epics | 2 |
| Total Stories | 6 |
| Blocking Dependencies | Epic 1 → Epic 2 |
| Estimated Effort | 17-23 hours |

---

# Epic 1: Data Foundation & Backend Services

**Epic ID**: PHASE7-EPIC-1
**Type**: Brownfield Enhancement (Backend Focus)
**Priority**: P0 (BLOCKING)

## Epic Goal

Establish clean, normalized data foundation and build backend services for skill co-occurrence and job similarity, enabling visible improvements in Neo4j Browser immediately.

## Epic Description

**Existing System Context:**
- **Current functionality**: Career Intelligence GraphRAG system with Neo4j knowledge graph (Skills, Jobs, Companies), LangGraph query pipeline, FastAPI backend
- **Technology stack**: Python 3.11+, FastAPI, Neo4j (with optional GDS), LangGraph, PostgreSQL
- **Integration points**: Neo4j repository layer, batch ingestion pipeline, embedding service

**Enhancement Details:**
- Skill name normalization with canonical names
- Schema migration (dedupe + constraint)
- Co-occurrence relationship builder
- Job similarity builder (GDS-based)
- Stored metrics (demand_count, centrality)

**Success Criteria:**
- No duplicate canonical_names in graph
- SIMILAR_JOB relationships visible in Neo4j Browser
- Skills have demand_count > 0

---

## Stories

### Story 1.1: Schema Migration & Skill Normalization [BLOCKING]

**Priority**: P0 (Must complete first)

**User Story**:
> As a system administrator, I want skill names normalized to canonical forms so that duplicate skills are merged and data quality improves.

**Scope**:

| Type | Files |
|------|-------|
| New | `backend/app/services/skill_normalizer.py` |
| New | `backend/scripts/migrate_neo4j_schema.py` |
| New | `backend/tests/unit/test_skill_normalizer.py` |

**Neo4j Changes**:
- Add `canonical_name` property to Skill nodes
- Add indexes on `canonical_name`, `centrality`, `demand_count`
- Add UNIQUE constraint on `canonical_name` (AFTER dedupe)

**Acceptance Criteria**:
- [ ] SkillNormalizer handles all alias mappings (JS→javascript, C#→csharp, etc.)
- [ ] Migration script runs in correct order: normalize → dedupe → constraint
- [ ] Verification query returns empty: `MATCH (s:Skill) WITH s.canonical_name as cn, count(*) as c WHERE c > 1 RETURN cn, c`
- [ ] Unit tests pass for normalizer

**Technical Notes**:
- CRITICAL: Include `import re` in normalizer
- CRITICAL: Migration order is NON-NEGOTIABLE (normalize → dedupe → constraint)
- Follow existing pattern in `backend/app/services/`

**Checkpoint Query**:
```cypher
MATCH (s:Skill) WITH s.canonical_name as cn, count(*) as c WHERE c > 1 RETURN cn, c
-- Expected: Empty result (no duplicates)
```

**Definition of Done**:
- [ ] SkillNormalizer implemented with all aliases
- [ ] Migration script runs without errors
- [ ] No duplicate canonical_names in graph
- [ ] All tests pass

---

### Story 1.2: Co-Occurrence Builder

**Priority**: P1

**User Story**:
> As a data engineer, I want CO_OCCURS_WITH relationships built between skills that appear together in jobs so that skill bridges can be computed.

**Scope**:

| Type | Files |
|------|-------|
| New | `backend/app/services/co_occurrence_builder.py` |
| New | `backend/tests/unit/test_co_occurrence_builder.py` |

**Acceptance Criteria**:
- [ ] CO_OCCURS_WITH edges created with both `weight` AND `cost` properties
- [ ] Stoplist excludes generic skills (communication, teamwork, etc.)
- [ ] Minimum co-occurrence threshold of 2 enforced
- [ ] `build_all()` method works for initial population
- [ ] `update_for_job()` method works for incremental updates

**Technical Notes**:
- `weight` = raw co-occurrence count (for ranking)
- `cost` = 1/weight (for Dijkstra shortest path)
- Use `id(s1) < id(s2)` to avoid duplicate edges

**Checkpoint Query**:
```cypher
MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r)
-- Expected: > 0
```

**Definition of Done**:
- [ ] Co-occurrence builder implemented
- [ ] Weight AND cost properties set correctly
- [ ] Stoplist filtering works
- [ ] All tests pass

---

### Story 1.3: Job Similarity Builder + Stored Metrics

**Priority**: P1

**User Story**:
> As a user, I want to see similar jobs in Neo4j Browser so that job relationships are visible and queryable.

**Scope**:

| Type | Files |
|------|-------|
| New | `backend/app/services/job_similarity_builder.py` |
| New | `backend/tests/unit/test_job_similarity_builder.py` |
| Modified | `backend/app/services/batch_processor.py` (add content_hash dedup) |

**Acceptance Criteria**:
- [ ] SIMILAR_JOB relationships created using GDS nodeSimilarity (if available)
- [ ] Fallback `update_for_job()` method works without GDS
- [ ] `jaccard_score` and `shared_count` properties set
- [ ] Job content_hash deduplication working
- [ ] `demand_count` updated on Skill nodes

**Technical Notes**:
- GDS nodeSimilarity is the ONLY recommended way for full rebuild
- `update_for_job()` is safe for incremental updates
- Never attempt naive O(n²) comparison

**Checkpoint Query**:
```cypher
MATCH ()-[r:SIMILAR_JOB]->() RETURN count(r)
-- Expected: > 0
```

**Definition of Done**:
- [ ] Job similarity builder implemented
- [ ] GDS integration working (or graceful fallback)
- [ ] Deduplication via content_hash working
- [ ] demand_count populated on skills
- [ ] All tests pass

---

## Epic 1 Compatibility Requirements

- [x] Existing APIs remain unchanged (additive only)
- [x] Database schema changes are backward compatible (new properties only)
- [x] No changes to frontend in this epic
- [x] Existing query pipeline unaffected

## Epic 1 Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration fails on duplicates | Medium | High | Run normalize → dedupe → constraint in exact order |
| GDS not installed | Medium | Medium | Provide fallback methods, skip full similarity rebuild |
| Large graph performance | Medium | Medium | Use LIMIT, batch processing, 600s timeout |

## Epic 1 Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Existing functionality verified (no regressions)
- [ ] Neo4j Browser shows new relationships
- [ ] All verification queries pass
- [ ] Ready for Epic 2 handoff

---

# Epic 2: Query Pipeline & Frontend Integration

**Epic ID**: PHASE7-EPIC-2
**Type**: Brownfield Enhancement (Full-Stack)
**Priority**: P1
**Dependency**: PHASE7-EPIC-1 must be complete

## Epic Goal

Integrate network metrics into the query pipeline and display insights in the frontend, making improvements visible to end users in chat responses.

## Epic Description

**Existing System Context:**
- **Current functionality**: LangGraph RAG pipeline with 5 nodes (query_understanding → vector_search → graph_traversal → context_construction → response_generation)
- **Technology stack**: Python/LangGraph (backend), React/TypeScript (frontend), FastAPI REST API
- **Integration points**: LangGraph workflow, context construction, API response models, React ChatMessage component

**Enhancement Details:**
- New network_enrichment node in LangGraph pipeline
- New intent patterns (career_transition, skill_bridge, job_similarity, skill_importance)
- Enhanced context with network facts
- NetworkInsights in API response
- Frontend NetworkInsightsPanel component

**Success Criteria:**
- Query "most important skills" returns centrality data
- API response includes `network_insights` field
- UI shows collapsible network panels

---

## Stories

### Story 2.1: Network Enrichment Node + New Intents

**Priority**: P0

**User Story**:
> As a user, I want my queries to be enriched with network metrics so that I get more insightful career guidance.

**Scope**:

| Type | Files |
|------|-------|
| New | `backend/app/agents/nodes/network_enrichment.py` |
| New | `backend/tests/integration/test_network_enrichment.py` |
| Modified | `backend/app/agents/graph.py` (add node to workflow) |
| Modified | `backend/app/agents/nodes/query_understanding.py` (new intent patterns) |

**Acceptance Criteria**:
- [ ] New intents detected: `career_transition`, `skill_bridge`, `skill_importance`, `job_similarity`
- [ ] Network enrichment node runs after graph_traversal
- [ ] Skill paths computed (GDS Dijkstra or BFS fallback)
- [ ] Top skills by centrality retrieved from stored metrics
- [ ] Job closeness calculated for queries with user skills

**Technical Notes**:
- Node must gracefully handle missing neo4j_repo
- Use STORED centrality (computed in Epic 1), not live GDS computation
- MVP: Extract user skills from query text patterns

**Checkpoint**:
```
Query: "What are the most important skills?"
Expected: Response includes centrality data
```

**Definition of Done**:
- [ ] Network enrichment node implemented
- [ ] New intent patterns added
- [ ] Workflow wiring complete
- [ ] All tests pass

---

### Story 2.2: Query Response Enhancement

**Priority**: P1

**User Story**:
> As a frontend developer, I want network insights in the API response so that I can display them in the UI.

**Scope**:

| Type | Files |
|------|-------|
| Modified | `backend/app/agents/nodes/context_construction.py` (add network section) |
| Modified | `backend/app/agents/nodes/graph_traversal.py` (add hybrid scoring) |
| Modified | `backend/app/models/query.py` (add NetworkInsights model) |
| Modified | `backend/app/api/query.py` (include network_insights in response) |

**Acceptance Criteria**:
- [ ] Context includes "Network Insights" section for LLM
- [ ] Hybrid scoring applied: 50% vector + 30% centrality + 20% demand
- [ ] NetworkInsights Pydantic model defined with all fields
- [ ] API response includes `network_insights` field (nullable)
- [ ] LLM response mentions graph statistics

**Technical Notes**:
- Follow existing pattern in `backend/app/models/`
- NetworkInsights is Optional (null if no enrichment applied)
- Preserve backward compatibility (existing clients unaffected)

**Checkpoint**:
```
API Response includes: "network_insights": { ... }
```

**Definition of Done**:
- [ ] Context includes network section
- [ ] Hybrid scoring implemented
- [ ] API response enhanced
- [ ] All tests pass

---

### Story 2.3: Frontend NetworkInsightsPanel

**Priority**: P1

**User Story**:
> As a user, I want to see network insights (skill paths, similar jobs, top skills) in a collapsible panel so that I can explore detailed career data.

**Scope**:

| Type | Files |
|------|-------|
| New | `frontend/src/components/NetworkInsightsPanel.tsx` |
| Modified | `frontend/src/components/ChatMessage.tsx` (render panel) |

**Acceptance Criteria**:
- [ ] Skill Bridge Paths section shows visual path (skill → skill → skill)
- [ ] Similar Jobs section shows top 5 with match percentages
- [ ] Top Skills section shows centrality-ranked skills
- [ ] Job Fit Analysis shows skills you have vs skills to learn
- [ ] All sections are collapsible (Job Fit default open)
- [ ] Panel only renders when `network_insights` present

**Technical Notes**:
- Use existing Tailwind/shadcn patterns
- Lazy load component to minimize bundle impact
- Use lucide-react icons (already in project)

**Checkpoint**:
```
UI Test: Network panels visible and collapsible
```

**Definition of Done**:
- [ ] NetworkInsightsPanel component implemented
- [ ] Integrated into ChatMessage
- [ ] All sections render correctly
- [ ] Collapsible behavior works
- [ ] No bundle size regression

---

## Epic 2 Compatibility Requirements

- [x] Existing APIs remain backward compatible (new field is nullable)
- [x] Existing query intents still work
- [x] UI gracefully handles missing network_insights
- [x] No breaking changes to existing components

## Epic 2 Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing queries | Low | High | Keep old intents working, enrichment is additive |
| Large context tokens | Medium | Medium | Cap network section, use token counting |
| Frontend bundle size | Low | Low | Lazy load NetworkInsightsPanel |

## Epic 2 Definition of Done

- [ ] All 3 stories completed with acceptance criteria met
- [ ] Existing functionality verified (no regressions)
- [ ] Demo queries show visible improvement
- [ ] UI panels render correctly
- [ ] All acceptance criteria from PRD met

---

# Implementation Order Summary

```
EPIC 1: Data Foundation (BLOCKING)
├── Story 1.1: Schema Migration & Skill Normalization [BLOCKING]
├── Story 1.2: Co-Occurrence Builder
└── Story 1.3: Job Similarity Builder + Stored Metrics
    │
    ▼ HANDOFF
EPIC 2: Query Pipeline & Frontend
├── Story 2.1: Network Enrichment Node + New Intents
├── Story 2.2: Query Response Enhancement
└── Story 2.3: Frontend NetworkInsightsPanel
```

---

# Verification Checkpoints

| Step | Query/Test | Expected Result |
|------|------------|-----------------|
| 1.1 | `MATCH (s:Skill) WITH s.canonical_name as cn, count(*) as c WHERE c > 1 RETURN cn, c` | Empty (no duplicates) |
| 1.2 | `MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r)` | > 0 |
| 1.3 | `MATCH ()-[r:SIMILAR_JOB]->() RETURN count(r)` | > 0 |
| 2.1 | Query: "most important skills" | Centrality data in response |
| 2.2 | API response inspection | `network_insights` field present |
| 2.3 | UI test | Panels visible and collapsible |

---

# Story Manager Handoff

"Please develop detailed user stories for these two brownfield epics. Key considerations:

- This is an enhancement to an existing GraphRAG system running **Python 3.11+, FastAPI, Neo4j (GDS optional), LangGraph, React/TypeScript**
- **Epic 1 is BLOCKING** - must complete before Epic 2
- Integration points: Neo4j repository, LangGraph workflow, API response models, React components
- Existing patterns to follow:
  - Backend services in `backend/app/services/`
  - LangGraph nodes in `backend/app/agents/nodes/`
  - Models in `backend/app/models/`
  - React components in `frontend/src/components/`
- Critical compatibility requirements: All changes are additive, no breaking changes
- Each story must include verification checkpoints from the PRD

The epics should maintain system integrity while delivering visible impact in Neo4j Browser, query responses, and frontend UI."

---

# File Reference

## New Files (10)

| File | Story | Purpose |
|------|-------|---------|
| `backend/app/services/skill_normalizer.py` | 1.1 | Skill name canonicalization |
| `backend/scripts/migrate_neo4j_schema.py` | 1.1 | Schema migration script |
| `backend/tests/unit/test_skill_normalizer.py` | 1.1 | Normalizer tests |
| `backend/app/services/co_occurrence_builder.py` | 1.2 | CO_OCCURS_WITH builder |
| `backend/tests/unit/test_co_occurrence_builder.py` | 1.2 | Builder tests |
| `backend/app/services/job_similarity_builder.py` | 1.3 | SIMILAR_JOB builder |
| `backend/tests/unit/test_job_similarity_builder.py` | 1.3 | Builder tests |
| `backend/app/agents/nodes/network_enrichment.py` | 2.1 | Network enrichment node |
| `backend/tests/integration/test_network_enrichment.py` | 2.1 | Integration tests |
| `frontend/src/components/NetworkInsightsPanel.tsx` | 2.3 | Network insights UI |

## Modified Files (10)

| File | Story | Changes |
|------|-------|---------|
| `backend/app/services/batch_processor.py` | 1.3 | Add deduplication |
| `backend/app/agents/graph.py` | 2.1 | Add network_enrichment node |
| `backend/app/agents/nodes/query_understanding.py` | 2.1 | Add intent patterns |
| `backend/app/agents/nodes/graph_traversal.py` | 2.2 | Add hybrid scoring |
| `backend/app/agents/nodes/context_construction.py` | 2.2 | Add network section |
| `backend/app/models/query.py` | 2.2 | Add NetworkInsights model |
| `backend/app/api/query.py` | 2.2 | Include network_insights |
| `frontend/src/components/ChatMessage.tsx` | 2.3 | Render panel |

---

**Document Version**: 1.0
**Last Updated**: 2024-12-06
