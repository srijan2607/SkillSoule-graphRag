# Network Math Implementation - Master Plan

## Executive Summary

This plan implements ICT-paper-inspired network mathematics into the Career Intelligence GraphRAG system. The implementation adds co-occurrence-based skill relationships, Dijkstra shortest path for skill distance calculation, closeness metrics, and eigenvector centrality for skill importance ranking.

**Current State**: 88k nodes, ~400k relationships with semantic SIMILAR_TO relationships
**Target State**: Add CO_OCCURS_WITH analytic layer with network math capabilities

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
│  /api/skills/metrics  /api/skills/transition  /api/skills/path  │
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

---

## File Structure

```
backend/
├── app/
│   ├── services/
│   │   ├── network_metrics_service.py      # NEW: Core network math
│   │   ├── co_occurrence_builder.py        # NEW: Build CO_OCCURS_WITH
│   │   ├── skill_similarity_service.py     # EXISTING: Semantic SIMILAR_TO
│   │   └── ...
│   ├── api/
│   │   ├── skills.py                       # NEW: Skill metrics endpoints
│   │   └── ...
│   ├── agents/nodes/
│   │   ├── query_understanding.py          # UPDATE: Add TRANSITION_PATH
│   │   ├── graph_traversal.py              # UPDATE: Add path queries
│   │   └── context_construction.py         # UPDATE: Format network metrics
│   ├── models/
│   │   ├── network_metrics.py              # NEW: Pydantic models
│   │   └── intent.py                       # UPDATE: Add new intent
│   └── ...
├── scripts/
│   ├── build_co_occurrence.py              # NEW: Batch builder script
│   └── ...
└── tests/
    ├── test_network_metrics_service.py     # NEW
    ├── test_co_occurrence_builder.py       # NEW
    └── ...
```

---

## Configuration Additions

```python
# config.py additions

# Network Metrics Configuration
NETWORK_MIN_CO_OCCURRENCE: int = 2       # Minimum jobs for edge
NETWORK_DIJKSTRA_TIMEOUT: float = 5.0    # Seconds
NETWORK_CACHE_TTL: int = 3600            # 1 hour cache
NETWORK_BATCH_SIZE: int = 1000           # Co-occurrence batch size

# GDS Configuration
GDS_PROJECTION_NAME: str = "skillNetwork"
GDS_EIGENVECTOR_ITERATIONS: int = 100
GDS_EIGENVECTOR_TOLERANCE: float = 1e-7
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

1. Review and approve this master plan
2. Proceed to Phase 1: Data Layer implementation
3. Daily checkpoints to validate progress

---

*Generated: 2025-12-06*
*Version: 1.0*
