# Technical Constraints and Integration Requirements

## Existing Technology Stack

**Languages:**
- Python 3.11+ (backend, graph algorithms, LangGraph)
- JavaScript/TypeScript (frontend React)

**Frameworks:**
- FastAPI (backend REST API)
- React 18+ with TypeScript (frontend)
- LangGraph (RAG orchestration)

**Databases:**
- Neo4j 5.x (cloud instance, free tier: 50K nodes, 175K relationships)
- PostgreSQL 15+ with Prisma ORM (user accounts, sessions)

**Infrastructure:**
- Local development (React dev server + FastAPI uvicorn)
- Cloud databases (Neo4j Aura free tier, Supabase/PostgreSQL free tier)
- No containerization required for MVP

**External Dependencies:**
- OpenRouter API (`meta-llama/llama-3.3-8b-instruct:free` model)
- HuggingFace Transformers (embedding generation)
- Neo4j Graph Data Science (GDS) library for centrality algorithms

**Constraints:**
- Free tier Neo4j GDS (limited algorithms: eigenvector centrality, shortest path available)
- No GPU (CPU-only inference for embeddings)
- No caching layer (direct database queries)
- Synchronous processing (no async job queue for MVP)

## Integration Approach

### Database Integration Strategy

**Neo4j Graph Schema Migration:**
1. **Phase 1**: Add new node properties (eigenvector_centrality, creation_index) via Cypher `SET` commands
2. **Phase 2**: Create new relationship types (PREREQUISITE_OF, COMPLEMENTS) incrementally
3. **Phase 3**: Compute initial centrality values using Neo4j GDS `gds.eigenvector.write()`
4. **Rollback Plan**: Maintain v1.1 snapshot, use Cypher `REMOVE` to delete new properties if issues

**PostgreSQL Integration:**
- No schema changes required (users table unchanged)
- Optional: Add `user_skills` table for Phase 2 (personalized profiles)

**Data Migration Script:**
```cypher
// Add centrality property to existing skills
MATCH (s:Skill)
SET s.eigenvector_centrality = 0.0,
    s.market_demand = 0,
    s.avg_salary_impact = 0.0

// Compute initial centrality
CALL gds.graph.project('skill-graph', 'Skill', 'SIMILAR_TO')
CALL gds.eigenvector.write('skill-graph', {writeProperty: 'eigenvector_centrality'})
```

### API Integration Strategy

**FastAPI Enhancements:**
- New router: `/api/metrics/*` for centrality, closeness endpoints
- Modify existing `/query` endpoint to accept `include_metrics=true` parameter
- Add background task for centrality recalculation (triggered post-ingestion)

**LangGraph Pipeline Modifications:**
- **Query Understanding Node**: Add skill transfer, learning path intent detection
- **Graph Traversal Node**: Inject Dijkstra shortest path calls, centrality lookups
- **Context Construction Node**: Include metric values in retrieval context
- No structural changes to pipeline (5 nodes remain, enhancements within nodes)

**Backward Compatibility:**
- v1.1 API contracts preserved (existing clients unaffected)
- New features opt-in via query parameters or separate endpoints

### Frontend Integration Strategy

**React Component Enhancements:**
- Create `MetricBadge` component (reusable for centrality, closeness display)
- Create `SkillPathVisualization` component (D3.js or Recharts for graph rendering)
- Modify `ChatMessage` component to parse and render metric citations

**State Management:**
- Existing conversation state unchanged
- Add optional `metricsData` field to message objects
- Use React Context or local state (no Redux/Zustand needed for MVP)

**API Client Updates:**
- Modify query API call to request `include_metrics=true`
- Add new API calls for `/api/metrics/*` endpoints (optional, for dashboard features)

### Testing Integration Strategy

**Unit Tests (New):**
- Centrality calculation accuracy (compare Neo4j GDS output to reference values)
- Shortest path correctness (validate Dijkstra results on known graphs)
- TransitionIndex formula (test edge cases: closeness=0, overlap=1)

**Integration Tests (Enhanced):**
- End-to-end query flow with metrics (submit query → verify metric values in response)
- Graph migration idempotence (run migration script 2x, verify no duplicates/errors)

**Regression Tests (Critical):**
- All v1.1 acceptance criteria must still pass after v2.0 deployment
- Specific focus: CSV ingestion (FR3-FR5), hybrid search (FR15), chat interface (FR26-FR27)

## Code Organization and Standards

### File Structure Approach

**Backend (FastAPI):**
```
backend/
├── app/
│   ├── routers/
│   │   ├── auth.py (unchanged from v1.1)
│   │   ├── ingest.py (unchanged)
│   │   ├── query.py (enhanced: add metrics logic)
│   │   └── metrics.py (NEW: centrality, closeness endpoints)
│   ├── services/
│   │   ├── graph/
│   │   │   ├── centrality.py (NEW: Neo4j GDS wrapper)
│   │   │   ├── shortest_path.py (NEW: Dijkstra implementation)
│   │   │   └── schema_migration.py (NEW: v1.1 → v2.0 migration)
│   │   └── langgraph/
│   │       ├── nodes.py (enhanced: add metric calculation)
│   │       └── workflow.py (unchanged structure)
│   └── models/
│       └── metrics.py (NEW: TransitionIndex, Closeness Pydantic models)
```

**Frontend (React):**
```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/ (existing, enhanced)
│   │   │   ├── ChatMessage.tsx (modify: render metrics)
│   │   │   └── MetricBadge.tsx (NEW)
│   │   └── metrics/ (NEW)
│   │       ├── SkillPathVisualization.tsx
│   │       └── TransitionIndexBreakdown.tsx
│   └── api/
│       └── metricsClient.ts (NEW)
```

### Naming Conventions

**Follow Existing v1.1 Patterns:**
- Python: snake_case for functions/variables, PascalCase for classes
- TypeScript: camelCase for functions/variables, PascalCase for components
- Neo4j: UPPERCASE for relationship types, PascalCase for node labels

**New Conventions for v2.0:**
- Metric properties: `eigenvector_centrality` (snake_case, descriptive)
- Graph algorithm functions: `calculate_skill_centrality()`, `find_shortest_path()`
- API endpoints: `/api/metrics/centrality` (kebab-case, RESTful)

### Coding Standards

**Python (Backend):**
- Type hints for all function signatures (enhanced from v1.1)
- Docstrings with mathematical formulas for metric functions
- Example:
  ```python
  def calculate_closeness(skill_a: str, skill_b: str) -> float:
      """
      Calculate closeness between two skills using shortest path distance.

      Formula: Closeness(A, B) = 1 / (1 + Distance(A, B))

      Args:
          skill_a: Source skill name
          skill_b: Target skill name

      Returns:
          Closeness score in range [0, 1]
      """
  ```

**TypeScript (Frontend):**
- Strict mode enabled (no `any` types)
- Interface definitions for all metric data structures
- Component prop validation with TypeScript interfaces

**Documentation Standards:**
- Inline comments for complex graph algorithms (explain Cypher queries)
- README updates for new environment variables (NFR16)
- API documentation using FastAPI auto-generated OpenAPI schema

## Deployment and Operations

### Build Process Integration

**Backend:**
- No changes to existing FastAPI build process
- Add migration script to deployment checklist: `python scripts/migrate_graph_v2.py`
- Environment variable validation on startup (check `NEO4J_GDS_ENABLED`)

**Frontend:**
- Standard React build (`npm run build`)
- No additional dependencies for MVP (D3.js only if implementing optional dashboards)

### Deployment Strategy

**Phased Rollout:**
1. **Phase 1 (Week 1)**: Deploy schema migration to staging Neo4j instance, validate data integrity
2. **Phase 2 (Week 2)**: Deploy backend enhancements, test new `/api/metrics/*` endpoints
3. **Phase 3 (Week 3)**: Deploy frontend enhancements, enable metric display in chat
4. **Phase 4 (Week 4)**: Production deployment with feature flag (`ENABLE_NETWORK_METRICS=true`)

**Rollback Plan:**
- Maintain v1.1 Docker image/codebase snapshot
- Neo4j Cypher script to remove new properties: `MATCH (s:Skill) REMOVE s.eigenvector_centrality`
- Toggle feature flag to disable metric display without full rollback

### Monitoring and Logging

**Enhanced Logging (Extends v1.1):**
- Log graph algorithm execution time (centrality, shortest path)
- Log metric calculation failures with skill IDs
- Log Neo4j GDS errors separately from query errors

**Performance Monitoring:**
- Track p95 response time for queries with metrics vs without (target: <5s both)
- Monitor Neo4j GDS memory usage (free tier limit warnings)
- Alert if centrality calculation >30s (NFR11 violation)

### Configuration Management

**New Environment Variables (NFR16):**
```env
# Existing v1.1 variables (unchanged)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxxxx
DATABASE_URL=postgresql://xxxxx
OPENROUTER_API_KEY=xxxxx
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free
EMBEDDING_MODEL=all-MiniLM-L6-v2
JWT_SECRET=xxxxx

# New v2.0 variables
NEO4J_GDS_ENABLED=true
EMBEDDING_MODEL_VERSION=all-mpnet-base-v2
CENTRALITY_UPDATE_FREQUENCY=on_ingestion
ENABLE_NETWORK_METRICS=true
```

**Configuration Validation:**
- Startup script checks `NEO4J_GDS_ENABLED` and verifies GDS library availability
- Fail fast if `EMBEDDING_MODEL_VERSION` not supported

## Risk Assessment and Mitigation

### Technical Risks

**Risk 1: Neo4j GDS Performance on Free Tier**
- **Risk**: Centrality calculation exceeds 30s on 8K skill nodes (NFR11 violation)
- **Impact**: Query response time >5s, poor user experience
- **Mitigation**:
  - Benchmark centrality on 1K, 5K, 8K node datasets during Phase 1
  - If >30s, reduce graph size (top 5K skills only) or pre-compute centrality offline
  - Fallback: Use approximate centrality (PageRank instead of eigenvector)
- **Severity**: HIGH

**Risk 2: Embedding Model Insufficient for Career Domain**
- **Risk**: all-mpnet-base-v2 may not capture domain terminology (Kubernetes, GraphQL) well
- **Impact**: Poor semantic similarity, incorrect skill relationships
- **Mitigation**:
  - Validate on 1000 skill pairs with expert ratings (target: correlation >0.7)
  - Fallback: Use BAAI/bge-large-en-v1.5 (1024-dim) or fine-tune on job descriptions
  - A/B test: Compare all-MiniLM-L6-v2 vs all-mpnet-base-v2 on 50 sample queries
- **Severity**: MEDIUM-HIGH

**Risk 3: Graph Schema Migration Data Loss**
- **Risk**: Migration script corrupts existing v1.1 graph data
- **Impact**: Catastrophic (system unusable, requires full restore)
- **Mitigation**:
  - **CRITICAL**: Export full Neo4j snapshot before migration (`neo4j-admin dump`)
  - Test migration on staging database with v1.1 production data copy
  - Use idempotent Cypher queries (`MERGE` instead of `CREATE`)
  - Validation script: Count nodes/relationships before vs after migration (must match)
- **Severity**: CRITICAL

**Risk 4: Free Tier Neo4j Limits Exceeded**
- **Risk**: 50K nodes or 175K relationships exceeded with new relationship types
- **Impact**: Cannot ingest new data, feature degradation
- **Mitigation**:
  - Pre-calculate relationship counts (estimate: Skills 8K, Jobs 40K, new relationships ~80K = 128K total < 175K)
  - Implement data pruning: Archive jobs older than 1 year, keep top 5K skills only
  - Graceful degradation: Disable TRANSITIONS_TO relationships if approaching limit
- **Severity**: MEDIUM

### Integration Risks

**Risk 5: LangGraph Pipeline Performance Degradation**
- **Risk**: Adding centrality/shortest path calculations increases query time >5s (NFR1 violation)
- **Impact**: User complaints about slow responses, poor adoption
- **Mitigation**:
  - Benchmark each graph algorithm separately (centrality lookup <100ms, shortest path <500ms)
  - Cache centrality values (recompute only on CSV ingestion, not per query)
  - Implement query timeout (abort if >4s, return partial results)
- **Severity**: MEDIUM-HIGH

**Risk 6: Backward Compatibility Breakage**
- **Risk**: v2.0 changes inadvertently break v1.1 API contracts
- **Impact**: Existing clients (if any) fail, regression in core features
- **Mitigation**:
  - **MANDATORY**: Run full v1.1 test suite after v2.0 deployment
  - API versioning: Create `/api/v2/query` if significant changes needed (keep `/query` for v1.1)
  - Automated regression tests in CI/CD pipeline
- **Severity**: HIGH

### Deployment Risks

**Risk 7: Production Deployment During Active Users**
- **Risk**: Deploying schema migration while users querying system causes inconsistent results
- **Impact**: User sees errors, partial data, incorrect metric values
- **Mitigation**:
  - Schedule deployment during low-traffic window (announce downtime)
  - Use feature flag to disable new features during migration (`ENABLE_NETWORK_METRICS=false`)
  - Blue-green deployment: Migrate on staging, switch traffic after validation
- **Severity**: MEDIUM

---
