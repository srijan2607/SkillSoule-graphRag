# Tech Stack

## Cloud Infrastructure

- **Provider:** None (local development + cloud databases)
- **Key Services:**
  - Neo4j Aura (free tier: 50K nodes, 175K relationships)
  - Supabase PostgreSQL (free tier)
- **Deployment Regions:** N/A (MVP uses cloud database free tiers without custom deployment)

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|-----------|---------|---------|-----------|
| **Language** | Python | 3.11+ | Backend development | Existing v1.1 choice; strong ecosystem for data science, graph algorithms, LangGraph |
| **Language** | TypeScript | 5.x | Frontend development | Existing v1.1 choice; type safety for React components |
| **Runtime** | Node.js | 20.x LTS | Frontend tooling | Standard React development runtime |
| **Framework** | FastAPI | 0.104+ | Backend REST API | Existing v1.1; auto-generated OpenAPI docs, async support, high performance |
| **Framework** | React | 18+ | Frontend UI | Existing v1.1; component-based architecture for chat interface |
| **Orchestration** | LangGraph | 0.0.60+ | RAG pipeline | Existing v1.1; stateful graph-based workflow for multi-step queries |
| **Graph Database** | Neo4j | 5.x | Knowledge graph storage | Existing v1.1; ACID transactions, Cypher query language, native graph algorithms via GDS |
| **Graph Library** | Neo4j GDS | 2.5+ | Network metrics | **NEW v2.0:** Eigenvector centrality, shortest path (Dijkstra) - optimized C++ implementation |
| **Relational DB** | PostgreSQL | 15+ | User accounts, sessions | Existing v1.1; ACID compliance, mature ecosystem |
| **ORM** | Prisma | 5.x | PostgreSQL access | Existing v1.1; type-safe database client, migration management |
| **LLM API** | OpenRouter | N/A | LLM inference | Existing v1.1; aggregates multiple models, free tier available |
| **LLM Model** | Llama 3.3 8B Instruct | meta-llama/llama-3.3-8b-instruct:free | Response generation | Existing v1.1; free tier, good quality for career domain |
| **Embeddings** | all-mpnet-base-v2 | 768-dim | Skill/job embeddings | **UPGRADED v2.0:** Better semantic capture than v1.1's 384-dim model (FR47) |
| **Embeddings (Fallback)** | all-MiniLM-L6-v2 | 384-dim | Skill/job embeddings | v1.1 model; fallback if performance issues with 768-dim |
| **Validation Library** | Pydantic | 2.x | Data validation | Existing v1.1; LangGraph state management, API request/response validation |
| **Testing** | pytest | 7.x+ | Unit/integration tests | Existing v1.1; extended for network metric tests in v2.0 |
| **HTTP Client** | httpx | 0.25+ | Async HTTP requests | Existing v1.1; OpenRouter API calls |
| **Logging** | Python logging | stdlib | Structured logging | Existing v1.1; extended for graph algorithm metrics in v2.0 |
| **Dev Tools** | uvicorn | 0.24+ | ASGI server | Existing v1.1; development server for FastAPI |
| **Dev Tools** | Vite | 5.x | Frontend build | Existing v1.1; React dev server and build tooling |

## Technology Justification Notes

**Embedding Model Upgrade (v1.1 → v2.0):**
- **Decision:** Upgrade from `all-MiniLM-L6-v2` (384-dim) to `all-mpnet-base-v2` (768-dim)
- **Rationale:** Career domain has specialized terminology (Kubernetes, GraphQL, Django) requiring better semantic capture
- **Validation Plan:** Benchmark on 1000 skill pairs with expert ratings; target correlation >0.7 before production (FR47)
- **Fallback:** Revert to 384-dim or try `BAAI/bge-large-en-v1.5` (1024-dim) if performance issues

**Neo4j GDS (NEW for v2.0):**
- **Decision:** Use Neo4j Graph Data Science library (free tier supported)
- **Rationale:** Provides optimized implementations of eigenvector centrality, Dijkstra shortest path - critical for FR31-FR34
- **Risk Mitigation:** Benchmark centrality on 1K/5K/8K node datasets; fallback to approximate PageRank if >30s (Risk 1)

**No Async Job Queue for MVP:**
- **Decision:** Use FastAPI background tasks for centrality recalculation (not Celery/Redis)
- **Rationale:** Simplifies deployment, reduces infrastructure cost for MVP
- **Trade-off:** Background tasks block API thread; migrate to Celery in Phase 2 if needed
- **Constraint:** Acceptable for MVP with low user volume; recalculation triggered only on CSV ingestion (not per-query)

---
