# Technical Assumptions

## Repository Structure

**Structure**: Monorepo

The project shall use a monolithic repository structure with clear separation of concerns:

```
/
├── frontend/          # React application
├── backend/           # FastAPI application
│   ├── api/          # API endpoints
│   ├── agents/       # LangGraph agents
│   ├── services/     # Business logic (ingestion, query)
│   └── models/       # Data models
├── data/             # Sample CSV files
├── docker-compose.yml
├── .env.example
└── README.md
```

**Rationale**: Monorepo simplifies development for single developer, enables shared configuration, and ensures version consistency between frontend and backend.

## Service Architecture

**Architecture**: Monolithic API (FastAPI) - No microservices for MVP

The system shall use a single FastAPI application handling all backend logic:
- CSV ingestion endpoints
- Authentication endpoints
- Query processing endpoints
- Direct Neo4j connection from backend (no ORM complexity)
- Stateless API design (JWT for auth, no session storage)

**Rationale**: Microservices add unnecessary complexity for MVP scope. Monolithic architecture is faster to develop, easier to debug, and sufficient for 10+ concurrent users.

## Testing Requirements

**Testing Level**: Unit testing for core business logic + Manual testing for UI/integration

The system shall include:
- Unit tests for CSV validation logic
- Unit tests for embedding generation
- Unit tests for graph construction logic
- Unit tests for LangGraph agent workflows
- Manual testing for frontend UI interactions
- Manual testing for end-to-end query workflows

**Not Required for MVP**:
- E2E automated testing
- Integration test automation
- Load testing
- Security testing

**Rationale**: Manual testing is acceptable for internal MVP with single developer. Automated testing infrastructure adds significant development overhead.

## Additional Technical Assumptions and Requests

**Frontend**:
- **Framework**: React with functional components and hooks
- **Styling**: TailwindCSS or Material-UI (simple, clean chat interface)
- **State Management**: React Context API or Zustand (lightweight, no Redux)
- **HTTP Client**: Axios or Fetch API for backend communication

**Backend**:
- **Framework**: FastAPI (Python)
- **LLM Orchestration**: LangGraph for agent workflows
- **LLM Provider**: OpenRouter API with `meta-llama/llama-3.3-8b-instruct:free` model
- **Embeddings**: Hugging Face `all-MiniLM-L6-v2` model (384-dimensional)
- **Authentication**: JWT tokens with PyJWT library
- **Database ORM**: Prisma for PostgreSQL (user management)
- **Neo4j Driver**: Official Neo4j Python driver

**Databases**:
- **Graph Database**: Neo4j (cloud-hosted via connection URI from .env)
- **Relational Database**: PostgreSQL (cloud-hosted for user accounts via Prisma)
- **Vector Storage**: Neo4j vector indexes (native support for embeddings, no separate vector DB)

**Infrastructure**:
- **Deployment**: Local development environment (React dev server + FastAPI uvicorn)
- **Neo4j**: Cloud-hosted (Aura or other cloud provider) via connection URI
- **PostgreSQL**: Cloud-hosted via connection URI
- **No Docker required**: All services accessed via cloud URIs
- **Environment Management**: `.env` files for configuration

**Integration Requirements**:
- OpenRouter API for LLM responses (unified gateway to multiple models)
- Hugging Face Transformers for embedding generation (can run locally or via API)
- Neo4j cloud connection via official driver
- PostgreSQL cloud connection via Prisma

**Security/Compliance**:
- Basic JWT authentication (not production-grade)
- Password hashing with bcrypt
- No encryption at rest (cloud provider responsibility)
- No HTTPS required for local development
- Environment variables for secrets (`.env` file, not committed to git)
- **Internal project only - minimal security hardening acceptable**

**Performance Optimization**:
- Batch embedding generation (32-64 texts per API call)
- Batch Neo4j transactions (commit every 500-1000 records)
- Neo4j vector indexes for fast similarity search
- Connection pooling for Neo4j and PostgreSQL
- No caching layer required for MVP

**Development Workflow**:
- Git for version control
- Feature branches for development
- `.env.example` file for configuration template
- Comprehensive README with setup instructions
- Inline code documentation for complex logic
- No CI/CD pipeline required for MVP

---
