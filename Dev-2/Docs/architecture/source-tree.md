# Source Tree

```
career-intelligence-system/
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py                   # FastAPI app initialization
│   │   ├── config.py                 # Environment configuration (NFR16 variables)
│   │   ├── dependencies.py           # Dependency injection (repositories, services)
│   │   │
│   │   ├── routers/                  # API endpoints
│   │   │   ├── auth.py               # [v1.1] /auth/* - JWT authentication
│   │   │   ├── ingest.py             # [v1.1] /ingest/* - CSV ingestion
│   │   │   ├── query.py              # [v1.1 + v2.0] /query - RAG execution
│   │   │   └── metrics.py            # [NEW v2.0] /api/metrics/* - Centrality, closeness
│   │   │
│   │   ├── services/
│   │   │   ├── embedding_service.py  # [v1.1 + v2.0] HuggingFace embeddings (768-dim)
│   │   │   ├── openrouter_service.py # [v1.1] LLM API client
│   │   │   ├── langgraph_service.py  # [v1.1 + v2.0] LangGraph pipeline orchestration
│   │   │   │
│   │   │   └── graph/                # [NEW v2.0] Graph algorithm services
│   │   │       ├── centrality.py     # Eigenvector centrality calculation (Neo4j GDS)
│   │   │       ├── shortest_path.py  # Dijkstra shortest path queries
│   │   │       ├── transition_index.py # TransitionIndex calculation
│   │   │       └── schema_migration.py # v1.1 → v2.0 migration utilities
│   │   │
│   │   ├── agents/                   # LangGraph nodes
│   │   │   ├── graph.py              # [v1.1] Workflow definition (5 nodes)
│   │   │   └── nodes/
│   │   │       ├── query_understanding.py # [v1.1 + v2.0] Intent + entity extraction
│   │   │       ├── vector_search.py       # [v1.1] Semantic similarity
│   │   │       ├── graph_traversal.py     # [v1.1 + v2.0] Cypher queries + metrics
│   │   │       ├── context_construction.py# [v1.1 + v2.0] Context formatting + citations
│   │   │       └── response_generation.py # [v1.1 + v2.0] LLM response
│   │   │
│   │   ├── repositories/
│   │   │   ├── neo4j_repository.py   # [v1.1 + v2.0] Neo4j CRUD operations
│   │   │   └── query_history_repository.py # [v1.1] PostgreSQL query logging
│   │   │
│   │   ├── models/                   # Pydantic models
│   │   │   ├── graph.py              # [v1.1] GraphRAGState (LangGraph state)
│   │   │   ├── query.py              # [v1.1] QueryRequest, QueryResponse
│   │   │   └── metrics.py            # [NEW v2.0] TransitionIndex, Closeness, CentralityResponse
│   │   │
│   │   ├── middleware/
│   │   │   ├── auth.py               # [v1.1] JWT validation
│   │   │   └── rate_limit.py         # [v1.1] 10 requests/min per user
│   │   │
│   │   └── utils/
│   │       ├── logger.py             # [v1.1 + v2.0] Structured logging
│   │       └── metrics.py            # [v1.1 + v2.0] Performance tracking
│   │
│   ├── scripts/                      # Migration and admin scripts
│   │   ├── migrate_graph_v2.py       # [NEW v2.0] Execute Neo4j schema migration
│   │   ├── compute_centrality.py     # [NEW v2.0] Manual centrality recalculation
│   │   └── validate_migration.py     # [NEW v2.0] Validate v1.1 → v2.0 data integrity
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_centrality.py    # [NEW v2.0] Centrality calculation accuracy
│   │   │   ├── test_shortest_path.py # [NEW v2.0] Dijkstra correctness
│   │   │   └── test_transition_index.py # [NEW v2.0] TransitionIndex formula
│   │   ├── integration/
│   │   │   ├── test_query_flow.py    # [v1.1 + v2.0] End-to-end query with metrics
│   │   │   └── test_migration.py     # [NEW v2.0] Migration idempotence
│   │   └── fixtures/                 # Test data (skills, jobs, expected metrics)
│   │
│   ├── prisma/
│   │   └── schema.prisma             # [v1.1] PostgreSQL schema definition
│   │
│   ├── requirements.txt              # [v1.1 + v2.0] Python dependencies
│   ├── .env.example                  # [v1.1 + v2.0] Environment variable template
│   └── README.md                     # Backend setup instructions
│
├── frontend/                         # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/                 # [v1.1] Chat interface components
│   │   │   │   ├── ChatContainer.tsx
│   │   │   │   ├── ChatMessage.tsx   # [v1.1 + v2.0] Enhanced to render metrics
│   │   │   │   └── ChatInput.tsx
│   │   │   │
│   │   │   └── metrics/              # [NEW v2.0] Metric visualization
│   │   │       ├── MetricBadge.tsx   # Display centrality, closeness inline
│   │   │       ├── TransitionIndexBreakdown.tsx # TransitionIndex component breakdown
│   │   │       └── SkillPathVisualization.tsx # Optional: D3.js skill path diagram
│   │   │
│   │   ├── api/
│   │   │   ├── queryClient.ts        # [v1.1 + v2.0] /query API calls
│   │   │   └── metricsClient.ts      # [NEW v2.0] /api/metrics/* API calls
│   │   │
│   │   ├── types/
│   │   │   ├── query.ts              # [v1.1 + v2.0] Query request/response types
│   │   │   └── metrics.ts            # [NEW v2.0] Metric data types
│   │   │
│   │   ├── App.tsx                   # [v1.1] Main app component
│   │   └── main.tsx                  # [v1.1] React entry point
│   │
│   ├── package.json                  # [v1.1] Frontend dependencies
│   ├── vite.config.ts                # [v1.1] Vite configuration
│   └── README.md                     # Frontend setup instructions
│
├── docs/                             # Documentation
│   ├── prd/                          # [v2.0] Product requirements
│   │   ├── index.md
│   │   ├── epic-1-skill-centric-graph-restructuring.md
│   │   ├── epic-2-network-metrics-implementation.md
│   │   ├── epic-3-advanced-query-intelligence.md
│   │   └── epic-4-research-validation-framework.md
│   │
│   ├── architecture/                 # [v2.0] Architecture documents
│   │   ├── backend-architecture-v2.md  # THIS DOCUMENT
│   │   └── frontend-architecture.md    # (To be created)
│   │
│   └── research/                     # [v2.0] Research methodology
│       ├── network-metrics-methodology.md
│       └── validation-framework.md
│
├── .github/
│   └── workflows/
│       └── ci.yml                    # [v1.1 + v2.0] CI/CD pipeline (test + lint)
│
├── .gitignore
├── README.md                         # Project overview
└── LICENSE
```

---
