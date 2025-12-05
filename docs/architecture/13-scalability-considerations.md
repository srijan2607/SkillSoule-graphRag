# 13. Scalability Considerations

**Purpose**: This section addresses how the system will handle growth in users, data volume, and query load beyond MVP scale.

## 13.1 Scale Assumptions

**MVP Scale**:
- Users: 10-100 concurrent
- Skills: ~10,000 nodes
- Jobs: ~50,000 nodes
- Queries: ~100-500/day

**Production Scale Targets** (6-12 months):
- Users: 1,000-10,000 concurrent
- Skills: 50,000+ nodes
- Jobs: 500,000+ nodes (10x growth)
- Queries: 10,000-50,000/day (100x growth)

## 13.2 Database Scalability

**Neo4j Scaling Strategy**:
1. **Immediate**: Query optimization (indexes, traversal limits)
2. **Short-term**: Vertical scaling (upgrade Aura tier)
3. **Long-term**: Read replicas, query result caching

**PostgreSQL Scaling Strategy**:
1. **Immediate**: Connection pooling (PgBouncer)
2. **Short-term**: Indexes, partition old data
3. **Long-term**: Read replicas for analytics

## 13.3 API Scalability

**Solutions**:
1. Horizontal scaling (2-5 FastAPI instances)
2. Background job processing (Celery + Redis)
3. Rate limiting (100 req/min per user)
4. Query result caching (Redis, 1-hour TTL)

**Impact**: Handle 1000+ concurrent users

## 13.4 LLM & Embedding Costs

**Cost Optimization**:
1. Query caching → 60-80% cache hit rate → 80% cost reduction
2. Upgrade to paid tier when free tier exhausted ($100-500/month)
3. GPU instance for embeddings → 10-50x faster generation

## 13.5 Performance Targets

| Metric | MVP | Growth | Scale |
|--------|-----|--------|-------|
| Query Response (p95) | <5s | <3s | <2s |
| CSV Upload (10K rows) | <2min | <1min | <30s |
| API Uptime | 95% | 99% | 99.9% |

**See**: `docs/technical-debt.md` for detailed scalability roadmap

---

This concludes the **Backend Architecture Document** for the Graph RAG System.

**Document Version**: 1.0
**Last Updated**: 2025-10-22
**Status**: Complete (MVP Architecture)
**Total Lines**: 5,600+

For questions or clarifications, refer to:
- [Project PRD](/Users/srijan26/Desktop/Dev/docs/prd.md)
- [Frontend Specification](/Users/srijan26/Desktop/Dev/docs/front-end-spec.md)
- [Project Brief](/Users/srijan26/Desktop/Dev/docs/brief.md)
