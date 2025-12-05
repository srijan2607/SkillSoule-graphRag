# Infrastructure and Deployment

## Infrastructure as Code

- **Tool:** N/A (No IaC for MVP - using cloud database free tiers)
- **Location:** N/A
- **Approach:** Manual provisioning of Neo4j Aura, Supabase PostgreSQL via web consoles

**Future Enhancement (Post-MVP):**
- **Tool:** Terraform or Pulumi for cloud database provisioning
- **Location:** `infrastructure/` directory
- **Rationale:** Enable reproducible staging/production environments, automated backups

## Deployment Strategy

- **Strategy:** Manual deployment (local development + cloud databases)
- **CI/CD Platform:** GitHub Actions (for automated testing only, not deployment in MVP)
- **Pipeline Configuration:** `.github/workflows/ci.yml` (linting, unit tests, integration tests)

**Phased Rollout (v2.0):**

1. **Phase 1 (Week 1):** Deploy schema migration to staging Neo4j instance
   - Run `python scripts/migrate_graph_v2.py` on staging database copy
   - Validate data integrity with `python scripts/validate_migration.py`
   - Benchmark centrality calculation time (target: <30s for 5K-8K skills)

2. **Phase 2 (Week 2):** Deploy backend enhancements to local development
   - Test new `/api/metrics/*` endpoints
   - Validate LangGraph pipeline with metric integration
   - Run regression tests (all v1.1 acceptance criteria must pass)

3. **Phase 3 (Week 3):** Deploy frontend enhancements to local development
   - Test metric display in chat interface
   - Validate TransitionIndex visualization
   - End-to-end testing with real user queries

4. **Phase 4 (Week 4):** Production deployment with feature flag
   - Set `ENABLE_NETWORK_METRICS=true` in production environment
   - Monitor query response times (target: <5s, NFR1)
   - Monitor Neo4j GDS performance (centrality <30s, NFR11)

## Environments

- **Development:** Local (localhost:8000 backend, localhost:5173 frontend) - Full feature access, debug logging enabled
- **Staging:** Cloud databases only (Neo4j Aura + Supabase) - v2.0 migration testing, performance benchmarking
- **Production:** Same as staging for MVP (future: separate production database instances) - Feature flag controlled rollout, monitoring enabled

## Environment Promotion Flow

```
Development (local) → Staging (cloud databases) → Production (cloud databases + feature flag)
```

**Promotion Criteria:**
- Development → Staging: All unit tests pass, migration script validated locally
- Staging → Production: Integration tests pass, performance benchmarks met (NFR11-13), regression tests pass (v1.1 acceptance criteria)

## Rollback Strategy

- **Primary Method:** Feature flag toggle (`ENABLE_NETWORK_METRICS=false`)
- **Trigger Conditions:**
  - Query response time >5s (NFR1 violation)
  - Centrality calculation >30s (NFR11 violation)
  - >5% error rate in graph metric queries
  - User-reported errors in v1.1 functionality (backward compatibility breakage)
- **Recovery Time Objective:** <15 minutes (toggle feature flag, restart backend service)

**Full Rollback (if feature flag insufficient):**
1. Revert backend code to v1.1 (git tag: `v1.1-stable`)
2. Run Neo4j rollback script: `scripts/rollback_graph_v2.cypher`
3. Verify v1.1 functionality with regression tests
4. RTO: <30 minutes

---
