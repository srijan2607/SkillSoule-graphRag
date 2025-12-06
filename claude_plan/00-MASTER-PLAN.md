# Network Math Implementation - Master Plan

## Executive Summary

This plan implements ICT-paper-inspired network mathematics into the Career Intelligence GraphRAG system. The implementation adds co-occurrence-based skill relationships, Dijkstra shortest path for skill distance calculation, closeness metrics, and eigenvector centrality for skill importance ranking.

**Current State**: 88k nodes, ~400k relationships with semantic SIMILAR_TO relationships
**Target State**: Add CO_OCCURS_WITH analytic layer with network math capabilities

---

## Phase Status Overview

| Phase | Name | Status | Document |
|-------|------|--------|----------|
| 1 | Data Layer | ✅ QA Approved | `01-DATA-LAYER.md` |
| 2 | Services Layer | ✅ QA Approved | `02-SERVICES-LAYER.md` |
| 3 | API Layer | ✅ QA Approved | `03-API-LAYER.md` |
| 4 | LangGraph Integration | ✅ QA Approved | `04-LANGGRAPH-INTEGRATION.md` |
| 5 | Testing Strategy | ✅ QA Approved | `05-TESTING-STRATEGY.md` |
| 6 | Network API Enhancements | 📝 DRAFTED | `07-NETWORK-API-ENHANCEMENTS.md` |

---

## Mathematical Foundation

### From ICT Paper to Career Skills Graph

| ICT Paper Concept | Career System Mapping |
|-------------------|----------------------|
| Industry | Skill |
| Patent | Job Posting |
| Patent cites Industry | Job REQUIRES Skill |
| Citation count | Co-occurrence count |
| Citation network | Skill co-occurrence network |

### Core Formulas

```
Edge Weight:     w(s1, s2) = count of jobs requiring BOTH skills
Edge Cost:       cost(s1, s2) = 1 / w(s1, s2)
Path Distance:   D(A, B) = sum of costs along shortest path (Dijkstra)
Closeness:       closeness(A, B) = 1 / (1 + D(A, B))
JobCloseness:    avg(closeness(skill_i, skill_j)) for all skill pairs in job
TransitionIndex: 0.50*AvgCloseness + 0.30*CoreSkillOverlap + 0.20*MarketDemand
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer                                 │
│  /api/skills/*           /api/network/* (Phase 6)               │
│  └─ metrics, transition   └─ path, centrality, job-closeness    │
│     path                     transition-index, capabilities     │
│                              build-cooccurrence (admin)         │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     LangGraph Pipeline                           │
│  QueryUnderstanding → VectorSearch → GraphTraversal → Response   │
│         │                                   │                    │
│   TRANSITION_PATH                    Dijkstra Path               │
│   intent detection                   Closeness calc              │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Services Layer                               │
│  NetworkMetricsService    CoOccurrenceBuilder    SkillGraphService│
│  - closeness()           - build_from_jobs()    - existing SIMILAR_TO│
│  - eigenvector()         - batch_update()                        │
│  - shortest_path()       - get_statistics()                      │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  (:Skill)-[:CO_OCCURS_WITH {weight, cost}]-(:Skill)             │
│  (:Job)-[:REQUIRES]->(:Skill)  [SOURCE OF TRUTH]                │
│  GDS Graph Projections for centrality algorithms                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Data Layer (Days 1-2)
**Files**: `01-DATA-LAYER.md`

1. Define CO_OCCURS_WITH relationship schema
2. Create indexes for performance
3. Build batch co-occurrence computation
4. Verify data integrity

**Deliverables**:
- Neo4j schema updates
- CoOccurrenceBuilder service
- Batch computation scripts

### Phase 2: Network Metrics Service (Days 3-4)
**Files**: `02-SERVICES-LAYER.md`

1. Implement NetworkMetricsService
2. Add GDS integration for eigenvector centrality
3. Implement Dijkstra shortest path
4. Add closeness calculation
5. Implement TransitionIndex formula

**Deliverables**:
- NetworkMetricsService class
- GDS graph projection management
- Caching layer for expensive computations

### Phase 3: API Layer (Day 5)
**Files**: `03-API-LAYER.md`

1. Create /api/skills/metrics endpoints
2. Create /api/skills/transition endpoints
3. Create /api/skills/path endpoints
4. Add request validation and error handling

**Deliverables**:
- FastAPI router with new endpoints
- Pydantic models for requests/responses
- API documentation

### Phase 4: LangGraph Integration (Days 6-7)
**Files**: `04-LANGGRAPH-INTEGRATION.md`

1. Add TRANSITION_PATH intent to intent analyzer
2. Update graph traversal for path-based queries
3. Enhance context construction with network metrics
4. Update response generation prompts

**Deliverables**:
- Updated intent patterns
- New Cypher queries for path traversal
- Enhanced context formatting

### Phase 5: Testing & Validation (Day 8)
**Files**: `05-TESTING-STRATEGY.md`

1. Unit tests for NetworkMetricsService
2. Integration tests for API endpoints
3. E2E tests for LangGraph pipeline
4. Performance benchmarks

**Deliverables**:
- Test suite with >80% coverage
- Performance benchmarks
- Validation reports

### Phase 6: Network API Enhancements (Day 9-10)
**Files**: `07-NETWORK-API-ENHANCEMENTS.md`
**Status**: 📝 DRAFTED - Pending Approval

1. Generic Skills Stoplist - Filter hyper-common skills from co-occurrence
2. New `/api/network/*` API namespace with dedicated endpoints
3. Enhanced Job Closeness - Per-skill breakdown with paths
4. Admin Build Endpoint - Trigger co-occurrence rebuilds
5. GDS Graceful Fallback - Proper handling when GDS unavailable
6. Toy Graph Tests - Mathematical correctness validation

**Deliverables**:
- `NETWORK_GENERIC_SKILLS_STOPLIST` configuration
- `/api/network/*` router with 6 new endpoints
- Enhanced `calculate_job_closeness()` with per-skill details
- GDS availability checking and graceful fallback
- Toy graph integration tests

**New Endpoints**:
- `POST /api/network/build-cooccurrence` (admin)
- `GET /api/network/path?from=X&to=Y`
- `GET /api/network/centrality?topK=N`
- `POST /api/network/job-closeness`
- `POST /api/network/transition-index`
- `GET /api/network/capabilities`

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── network_metrics_service.py      # Phase 2: Core network math
│   │   ├── co_occurrence_builder.py        # Phase 1: Build CO_OCCURS_WITH
│   │   ├── skill_similarity_service.py     # EXISTING: Semantic SIMILAR_TO
│   │   └── ...
│   ├── api/
│   │   ├── skills.py                       # Phase 3: Skill metrics endpoints
│   │   ├── network.py                      # Phase 6: Network API namespace
│   │   └── ...
│   ├── agents/nodes/
│   │   ├── query_understanding.py          # Phase 4: Add TRANSITION_PATH
│   │   ├── graph_traversal.py              # Phase 4: Add path queries
│   │   └── context_construction.py         # Phase 4: Format network metrics
│   ├── models/
│   │   ├── network_metrics.py              # Phase 3: Pydantic models
│   │   ├── network_models.py               # Phase 6: Enhanced Pydantic models
│   │   └── intent.py                       # Phase 4: Add new intent
│   └── ...
├── scripts/
│   ├── build_co_occurrence.py              # Phase 1: Batch builder script
│   └── ...
└── tests/
    ├── unit/
    │   ├── test_network_metrics_service.py # Phase 5
    │   ├── test_co_occurrence_builder.py   # Phase 5
    │   ├── test_network_math_correctness.py # Phase 6: Toy graph math tests
    │   └── ...
    ├── integration/
    │   ├── test_network_metrics_neo4j.py   # Phase 5
    │   ├── test_toy_graph_network.py       # Phase 6: Toy graph integration
    │   └── ...
    └── ...
```

---

## Configuration Additions

```python
# config.py additions

# Network Metrics Configuration (Phase 1-2)
NETWORK_MIN_CO_OCCURRENCE: int = 2       # Minimum jobs for edge
NETWORK_DIJKSTRA_TIMEOUT: float = 5.0    # Seconds
NETWORK_CACHE_TTL: int = 3600            # 1 hour cache
NETWORK_BATCH_SIZE: int = 1000           # Co-occurrence batch size

# GDS Configuration (Phase 2)
GDS_PROJECTION_NAME: str = "skillNetwork"
GDS_EIGENVECTOR_ITERATIONS: int = 100
GDS_EIGENVECTOR_TOLERANCE: float = 1e-7

# Phase 6: Network API Enhancements
NETWORK_GENERIC_SKILLS_STOPLIST: List[str] = [
    "Communication", "Problem Solving", "Teamwork",
    "MS Excel", "Microsoft Office", "Leadership", ...
]
ALLOW_NETWORK_ADMIN: bool = False        # Admin endpoints protection
ENVIRONMENT: str = "production"          # development|staging|production
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GDS not installed | Medium | High | Fallback to native Cypher |
| Large graph performance | Medium | Medium | Use projections, caching |
| Co-occurrence sparsity | Low | Medium | Lower threshold, handle nulls |
| Memory for eigenvector | Low | High | Stream results, batch processing |

---

## Success Criteria

1. **Functional**: All endpoints return correct network metrics
2. **Performance**: Path queries < 500ms, centrality < 2s
3. **Integration**: TRANSITION_PATH queries work in RAG pipeline
4. **Quality**: Test coverage > 80%, no regressions

---

## Dependencies

### External
- Neo4j GDS Library (for eigenvector, Dijkstra)
- numpy (for matrix operations)

### Internal
- Neo4jRepository (existing)
- EmbeddingService (existing)
- SkillSimilarityService (existing)

---

## Rollback Strategy

1. CO_OCCURS_WITH relationships are additive - can delete without affecting REQUIRES
2. New services are independent - can disable without breaking existing flow
3. New intent is additive - system falls back to existing intents
4. API endpoints are new - no breaking changes to existing API

---

## Next Steps

### Completed
- [x] Phase 1: Data Layer - QA Approved
- [x] Phase 2: Services Layer - QA Approved
- [x] Phase 3: API Layer - QA Approved
- [x] Phase 4: LangGraph Integration - QA Approved
- [x] Phase 5: Testing Strategy - QA Approved

### Current
- [ ] **Phase 6: Network API Enhancements** - DRAFTED, awaiting approval
  - Review `07-NETWORK-API-ENHANCEMENTS.md`
  - Approve or request changes
  - Begin development once approved

### Workflow After Approval
1. Development implementation
2. Code Review
3. QA validation
4. Mark as Done

---

*Generated: 2025-12-06*
*Updated: 2025-12-06 (Phase 6 added)*
*Version: 1.1*
