# Career Intelligence AI System - User Stories

**PRD Version:** 2.0
**Total Stories:** 25 stories across 4 epics
**Project:** Career Intelligence AI System - Research-Driven Skill-Centric Transformation

---

## Epic Overview

| Epic | Stories | Focus Area | Status |
|------|---------|------------|--------|
| [Epic 1](#epic-1-skill-centric-graph-restructuring) | 6 | Graph schema restructuring | Ready |
| [Epic 2](#epic-2-network-metrics-implementation) | 7 | Network metrics & algorithms | Ready |
| [Epic 3](#epic-3-advanced-query-intelligence) | 6 | Query enhancement & UI | Ready |
| [Epic 4](#epic-4-research-validation-framework) | 6 | Validation & testing | Ready |

---

## Epic 1: Skill-Centric Graph Restructuring

Transform Neo4j graph from job-centric to skill-centric model while preserving existing data.

| Story | Title | Effort | Status |
|-------|-------|--------|--------|
| [1.1](./story-1.1-graph-schema-enhancement.md) | Graph Schema Enhancement - Add Node Properties | 1-2 days | Ready |
| [1.2](./story-1.2-prerequisite-of-relationships.md) | Relationship Type Addition - PREREQUISITE_OF | 1-2 days | Ready |
| [1.3](./story-1.3-complements-relationships.md) | Relationship Type Addition - COMPLEMENTS | 2-3 days | Ready |
| [1.4](./story-1.4-substitutes-relationships.md) | Relationship Type Addition - SUBSTITUTES | 1-2 days | Ready |
| [1.5](./story-1.5-transitions-to-relationships.md) | Relationship Type Addition - TRANSITIONS_TO (Experimental) | 2-3 days | Ready |
| [1.6](./story-1.6-migration-validation.md) | Graph Migration Validation & Rollback Testing | 1-2 days | Ready |

**Total Estimated Effort:** 8-14 days

---

## Epic 2: Network Metrics Implementation

Implement research-driven network metrics with performance optimization.

| Story | Title | Effort | Status |
|-------|-------|--------|--------|
| [2.1](./story-2.1-eigenvector-centrality.md) | Eigenvector Centrality Calculation with Neo4j GDS | 2-3 days | Ready |
| [2.2](./story-2.2-shortest-path-distance.md) | Shortest Path Distance Calculation (Dijkstra's Algorithm) | 2-3 days | Ready |
| [2.3](./story-2.3-closeness-metric.md) | Closeness Metric Calculation | 1-2 days | Ready |
| [2.4](./story-2.4-user-to-job-closeness.md) | User-to-Job Closeness Scoring | 2-3 days | Ready |
| [2.5](./story-2.5-transition-index.md) | TransitionIndex Heuristic Implementation | 2-3 days | Ready |
| [2.6](./story-2.6-recombinant-innovation.md) | Recombinant Innovation Indices (Optional Beta) | 2-3 days | Ready |
| [2.7](./story-2.7-metrics-api-endpoints.md) | Metrics API Endpoints | 1-2 days | Ready |

**Total Estimated Effort:** 12-19 days

---

## Epic 3: Advanced Query Intelligence

Enhance LangGraph query pipeline with network metric integration.

| Story | Title | Effort | Status |
|-------|-------|--------|--------|
| [3.1](./story-3.1-query-understanding-enhancement.md) | Query Understanding Node Enhancement - New Intent Types | 1-2 days | Ready |
| [3.2](./story-3.2-graph-traversal-metrics.md) | Graph Traversal Node Enhancement - Metric Integration | 2-3 days | Ready |
| [3.3](./story-3.3-context-construction-citations.md) | Context Construction Node Enhancement - Research Citations | 1-2 days | Ready |
| [3.4](./story-3.4-response-generation-explanation.md) | Response Generation Node Enhancement - Metric Explanation | 1-2 days | Ready |
| [3.5](./story-3.5-frontend-metric-display.md) | Frontend Metric Display - Inline Citations | 2-3 days | Ready |
| [3.6](./story-3.6-query-performance-optimization.md) | Query Performance Optimization | 1-2 days | Ready |

**Total Estimated Effort:** 8-14 days

---

## Epic 4: Research Validation Framework

Implement expert evaluation and A/B testing for research validation.

| Story | Title | Effort | Status |
|-------|-------|--------|--------|
| [4.1](./story-4.1-expert-validation-skill-transfer.md) | Expert Validation Interface - Skill Transfer Identification | 2-3 days | Ready |
| [4.2](./story-4.2-expert-validation-learning-path.md) | Expert Validation Interface - Learning Path Quality | 2-3 days | Ready |
| [4.3](./story-4.3-closeness-correlation-check.md) | Closeness Correlation Check with Expert Judgment | 2-3 days | Ready |
| [4.4](./story-4.4-ab-testing-baseline.md) | Baseline A/B Testing - Job-Centric vs Skill-Centric | 3-4 days | Ready |
| [4.5](./story-4.5-research-methodology-documentation.md) | Research Methodology Documentation | 2-3 days | Ready |
| [4.6](./story-4.6-monitoring-dashboard.md) | Monitoring Dashboard for Research Metrics (Optional Stretch Goal) | 3-4 days | Optional |

**Total Estimated Effort:** 14-20 days

---

## Development Timeline

**Total Project Estimated Effort:** 42-67 days (6-10 weeks)

### Recommended Sprint Structure

**Sprint 1 (Week 1-2):** Epic 1 - Graph Restructuring
- Stories 1.1 through 1.6
- Milestone: Skill-centric graph schema deployed

**Sprint 2 (Week 3-4):** Epic 2 - Network Metrics
- Stories 2.1 through 2.7
- Milestone: Centrality, closeness, TransitionIndex operational

**Sprint 3 (Week 5-6):** Epic 3 - Query Intelligence
- Stories 3.1 through 3.6
- Milestone: Enhanced query pipeline with metrics

**Sprint 4 (Week 7-8):** Epic 4 - Research Validation
- Stories 4.1 through 4.5 (skip 4.6 for MVP)
- Milestone: Validation framework ready for expert evaluation

---

## Story Status Legend

- **Ready:** Story defined and ready for development
- **In Progress:** Currently being implemented
- **Blocked:** Waiting on dependencies or external factors
- **Complete:** All acceptance criteria met and integrated

---

## Usage Notes

1. **Story Files:** Each story has a detailed markdown file with acceptance criteria, integration verification, and technical notes
2. **Epic Dependencies:** Stories within an epic build on each other - follow sequential order
3. **Cross-Epic Dependencies:** Epic 2 depends on Epic 1, Epic 3 depends on Epic 2, Epic 4 can partially overlap with Epic 3
4. **Integration Verification:** Every story includes specific tests to ensure existing v1.1 functionality remains intact

---

## Related Documentation

- [PRD Index](../prd/index.md) - Full Product Requirements Document
- [Epic 1 Details](../prd/epic-1-skill-centric-graph-restructuring.md)
- [Epic 2 Details](../prd/epic-2-network-metrics-implementation.md)
- [Epic 3 Details](../prd/epic-3-advanced-query-intelligence.md)
- [Epic 4 Details](../prd/epic-4-research-validation-framework.md)
- [Requirements](../prd/requirements.md) - Functional and non-functional requirements
- [Technical Constraints](../prd/technical-constraints-and-integration-requirements.md)

---

**Last Updated:** November 17, 2025
**Maintained By:** Product Management Team
