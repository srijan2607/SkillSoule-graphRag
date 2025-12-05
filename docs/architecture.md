# Graph RAG System for Skills & Jobs Knowledge Graph Architecture Document

## Introduction

This document outlines the **backend architecture** for the **Graph RAG System for Skills & Jobs Knowledge Graph**, including API design, database schemas, LangGraph orchestration workflows, and system integration patterns. Its primary goal is to serve as the definitive technical blueprint for backend development, ensuring consistency and adherence to the chosen technology stack.

**Project Overview:**

The system enables conversational AI-powered career intelligence through a knowledge graph-based RAG (Retrieval-Augmented Generation) pipeline. Users upload CSV files containing skills and jobs taxonomies, which are processed into a Neo4j knowledge graph with semantic embeddings. Natural language queries are orchestrated through LangGraph agents that perform hybrid search (vector similarity + graph traversal) and generate intelligent responses via OpenRouter LLM.

**Relationship to Frontend Architecture:**

The frontend architecture is documented separately in `docs/front-end-spec.md`. This backend architecture document defines:
- RESTful API contracts that the React frontend consumes
- Data models and validation rules
- Authentication and authorization mechanisms
- Error response formats and status codes

The frontend spec defines UI/UX patterns, while this document defines the backend services that power those experiences.

**Core Technology Stack (Definitive):**
- **Backend Framework**: FastAPI (Python)
- **LLM Orchestration**: LangGraph for RAG workflows
- **Graph Database**: Neo4j (cloud-hosted)
- **Relational Database**: PostgreSQL (cloud-hosted) with Prisma ORM
- **LLM Provider**: OpenRouter API (`meta-llama/llama-3.3-8b-instruct:free`)
- **Embeddings**: Hugging Face Transformers (`all-MiniLM-L6-v2`)

All technology decisions documented in the "Tech Stack" section are the single source of truth for the entire project, including frontend dependencies.

### Starter Template or Existing Project

**Decision**: No starter template or boilerplate will be used.

**Rationale**:
- The project has specific requirements (LangGraph + Neo4j + FastAPI integration) that don't align well with generic templates
- Custom architecture allows optimization for Graph RAG workflows without template constraints
- Manual setup ensures full understanding of all components and dependencies
- Cleaner codebase without unnecessary boilerplate code

**Implication**: All tooling, configuration, and project structure will be set up manually following best practices for FastAPI, LangGraph, and Neo4j integration.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-22 | 1.0 | Initial backend architecture document creation | Winston (Architect) |

---

## High Level Architecture

### Technical Summary

The system employs a **monolithic FastAPI backend architecture** with direct database connections to Neo4j (graph) and PostgreSQL (relational). The core architecture follows a **pipeline-based RAG pattern** orchestrated by LangGraph, where CSV data flows through ingestion → embedding → graph construction, and user queries flow through understanding → hybrid search → LLM generation. FastAPI exposes RESTful endpoints for authentication, CSV upload, and conversational queries, while LangGraph agents coordinate complex multi-step reasoning workflows. This design prioritizes simplicity for MVP development while maintaining clear separation of concerns through service layers, enabling future extensibility without microservices complexity.

### High Level Overview

**Architectural Style**: Monolithic API (Single FastAPI Application)

The system uses a single FastAPI application that handles all backend responsibilities without service decomposition. This aligns with the PRD's technical assumptions favoring simplicity over distributed complexity for MVP scope.

**Repository Structure**: Monorepo (from PRD Technical Assumptions)

```
/
├── frontend/          # React application (separate architecture doc)
├── backend/           # FastAPI application (this document)
│   ├── api/          # API endpoints (FastAPI routers)
│   ├── agents/       # LangGraph agents and workflows
│   ├── services/     # Business logic (ingestion, query, embedding)
│   ├── models/       # Data models (Pydantic, Prisma)
│   └── utils/        # Shared utilities
├── data/             # Sample CSV files
└── docs/             # Architecture documentation
```

**Service Architecture**: Monolith - No Microservices (from PRD Technical Assumptions)

All functionality consolidated into a single deployable unit:
- Authentication and authorization
- CSV file upload and validation
- Embedding generation and graph construction
- LangGraph RAG query pipeline
- Direct database connections (Neo4j driver + Prisma ORM)

**Primary Data Flow**:

1. **Ingestion Pipeline** (CSV → Knowledge Graph):
   - User uploads CSV via `/ingest/skills` or `/ingest/jobs`
   - FastAPI validates format and required columns
   - Batch processor chunks records (1000/batch)
   - Embedding service generates vectors (Hugging Face)
   - Neo4j driver constructs graph nodes and relationships
   - Progress tracked in PostgreSQL, polled by frontend

2. **Query Pipeline** (Natural Language → AI Response):
   - User sends query to `/query` endpoint
   - LangGraph StateGraph orchestrates 5-node workflow:
     - Query Understanding → classify intent, generate embedding
     - Vector Search → Neo4j similarity search
     - Graph Traversal → Cypher queries based on intent
     - Context Construction → combine results into LLM prompt
     - Response Generation → OpenRouter API call
   - Response + source citations returned to frontend

**Key Architectural Decisions**:

- **Stateless API**: JWT tokens for auth, no session storage
- **Direct Database Access**: Neo4j Python driver + Prisma (no ORMs for Neo4j)
- **Synchronous Processing**: CSV ingestion runs synchronously with progress polling (no async workers/queues for MVP)
- **Cloud Databases**: Neo4j Aura + PostgreSQL cloud (URIs in `.env`)
- **Single Deployment Unit**: Uvicorn serves FastAPI app, connects to remote databases

### High Level Project Diagram

```mermaid
graph TB
    subgraph "Frontend (React)"
        UI[React UI<br/>TailwindCSS]
    end

    subgraph "Backend (FastAPI)"
        API[FastAPI<br/>Uvicorn Server]

        subgraph "API Layer"
            AuthAPI[Auth Endpoints<br/>/auth/login, /register]
            IngestAPI[Ingest Endpoints<br/>/ingest/skills, /jobs]
            QueryAPI[Query Endpoint<br/>/query]
            HealthAPI[Health Check<br/>/health]
        end

        subgraph "Service Layer"
            AuthSvc[Auth Service<br/>JWT + bcrypt]
            IngestSvc[Ingestion Service<br/>CSV Validation + Batching]
            EmbedSvc[Embedding Service<br/>HuggingFace all-MiniLM-L6-v2]
            GraphSvc[Graph Service<br/>Neo4j Node/Relationship Creation]
        end

        subgraph "LangGraph Agents"
            QueryAgent[Query Orchestrator]
            UnderstandNode[Query Understanding]
            VectorNode[Vector Search]
            GraphNode[Graph Traversal]
            ContextNode[Context Construction]
            LLMNode[Response Generation]
        end
    end

    subgraph "External Services"
        OpenRouter[OpenRouter API<br/>LLM: llama-3.3-8b-instruct]
        HuggingFace[Hugging Face<br/>Embedding Model API]
    end

    subgraph "Data Layer"
        Neo4j[(Neo4j Cloud<br/>Knowledge Graph<br/>+ Vector Indexes)]
        Postgres[(PostgreSQL Cloud<br/>Users, Jobs, QueryHistory)]
    end

    UI -->|HTTP/JSON<br/>JWT Auth| API

    API --> AuthAPI
    API --> IngestAPI
    API --> QueryAPI
    API --> HealthAPI

    AuthAPI --> AuthSvc
    IngestAPI --> IngestSvc
    QueryAPI --> QueryAgent

    IngestSvc --> EmbedSvc
    IngestSvc --> GraphSvc

    QueryAgent --> UnderstandNode
    UnderstandNode --> VectorNode
    VectorNode --> GraphNode
    GraphNode --> ContextNode
    ContextNode --> LLMNode

    AuthSvc --> Postgres
    IngestSvc --> Postgres
    EmbedSvc --> HuggingFace
    GraphSvc --> Neo4j

    VectorNode --> Neo4j
    GraphNode --> Neo4j
    LLMNode --> OpenRouter

    style UI fill:#e3f2fd
    style API fill:#fff3e0
    style Neo4j fill:#c8e6c9
    style Postgres fill:#c8e6c9
    style OpenRouter fill:#f8bbd0
    style HuggingFace fill:#f8bbd0
    style QueryAgent fill:#ffecb3
```

### Architectural and Design Patterns

#### 1. API Architecture Pattern

**Chosen Pattern: REST with JSON**

**Rationale**:
- Frontend spec already defines RESTful interaction patterns
- Simpler for MVP development (no GraphQL schema complexity)
- FastAPI has excellent REST support with automatic OpenAPI docs
- Aligns with PRD's simplicity-first approach

**Alternatives Considered**:
- GraphQL: Too complex for MVP, overkill for simple CRUD + query operations
- gRPC: Unnecessary performance overhead for cloud-hosted databases

---

#### 2. Code Organization Pattern

**Chosen Pattern: Layered Architecture (API → Service → Data)**

**Rationale**:
- Clear separation: API layer (routers), Service layer (business logic), Data layer (database access)
- Easy to navigate: `/api/` for endpoints, `/services/` for logic, `/models/` for schemas
- Balances simplicity with maintainability for single developer
- Natural fit for FastAPI dependency injection

**Structure**:
```
api/ → routes and request/response handling
services/ → business logic, no HTTP concerns
models/ → Pydantic schemas, Prisma models
agents/ → LangGraph workflows (special service layer)
```

---

#### 3. LangGraph Orchestration Pattern

**Chosen Pattern: StateGraph with Conditional Routing**

**Rationale**:
- Query intent determines graph traversal strategy (5 intent types from PRD)
- Allows branching based on query classification
- Maintains conversation state across workflow nodes
- Enables future extensions (multi-turn conversations, replanning)

**Implementation**: `QueryUnderstanding` classifies intent → routes to appropriate Cypher patterns in `GraphTraversal` node

---

#### 4. Database Access Pattern

**Chosen Pattern: Repository Pattern for PostgreSQL, Direct Driver for Neo4j**

**Rationale**:
- **PostgreSQL**: Prisma ORM with repository services abstracts data access
- **Neo4j**: Direct Python driver usage (no mature ORM for graph DBs)
- Clean separation: services call repositories, repositories manage queries
- Testable: can mock repositories for unit tests

**Implementation**:
- `repositories/user_repository.py` → Prisma queries for users
- `services/graph_service.py` → Direct Neo4j driver calls with Cypher

---

#### 5. Error Handling Pattern

**Chosen Pattern: Exception-Based with Custom Exceptions**

**Rationale**:
- FastAPI natively supports HTTPException with status codes
- Python's try/except is idiomatic
- Custom exceptions for domain errors (CSVValidationError, EmbeddingError, GraphConstructionError)
- Middleware catches all exceptions and formats consistent error responses

**Pattern Example**:
```python
# Custom exceptions
class CSVValidationError(Exception): pass

# Service layer raises
if not valid_csv:
    raise CSVValidationError("Missing required columns: ID, NAME")

# API layer catches and converts
@app.exception_handler(CSVValidationError)
def validation_exception_handler(request, exc):
    return JSONResponse(status_code=400, content={"error": str(exc)})
```

---

#### 6. Asynchronous Processing Pattern

**Chosen Pattern: Synchronous Processing with Progress Polling**

**Rationale**:
- Simpler for MVP: no worker infrastructure needed
- CSV ingestion runs in request context, updates PostgreSQL progress table
- Frontend polls `/ingest/status/{job_id}` every 2 seconds
- Sufficient for internal MVP with single user upload at a time

**Future Enhancement**: Move to background task queue (Celery) for concurrent uploads

---

#### 7. Authentication & Authorization Pattern

**Chosen Pattern: JWT Stateless with FastAPI Security**

**Rationale**:
- Stateless: no session storage required
- FastAPI has built-in OAuth2PasswordBearer for JWT
- Simple for MVP: email/password → JWT token (24h expiry)
- Token stored in frontend localStorage

**Pattern Example**:
```python
# Login endpoint generates JWT
token = jwt.encode({"user_id": user.id, "exp": exp}, JWT_SECRET)

# Protected endpoints verify JWT
@router.get("/protected", dependencies=[Depends(get_current_user)])
async def protected_route(user: User = Depends(get_current_user)):
    ...
```

---

## Tech Stack

This section defines the complete technology stack with specific versions, installation requirements, and justifications aligned with the PRD's technical preferences.

### Core Backend Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Python** | 3.11+ | Backend language | - Excellent AI/ML ecosystem (LangGraph, Transformers)<br/>- FastAPI native support<br/>- Strong typing with type hints<br/>- Neo4j official driver support |
| **FastAPI** | 0.109+ | Web framework | - High performance (async support)<br/>- Automatic OpenAPI documentation<br/>- Native Pydantic integration<br/>- Built-in dependency injection<br/>- Excellent developer experience |
| **Uvicorn** | 0.27+ | ASGI server | - Production-ready async server<br/>- FastAPI recommended server<br/>- Hot reload for development |
| **Pydantic** | 2.5+ | Data validation | - Type-safe request/response models<br/>- Automatic validation<br/>- JSON schema generation<br/>- FastAPI integration |

### LangGraph & LLM Stack

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **LangGraph** | 0.0.60+ | Agent orchestration | - StateGraph for RAG workflows<br/>- Conditional routing for intent-based queries<br/>- Built-in state management<br/>- Debugging/visualization tools |
| **LangChain** | 0.1.0+ | LLM utilities | - Dependency for LangGraph<br/>- Prompt templates<br/>- Output parsers<br/>- Document loaders |
| **OpenAI SDK** | 1.10+ | LLM API client | - OpenRouter compatibility<br/>- Streaming support<br/>- Async operations<br/>- Error handling |

### Database Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Neo4j** | 5.x (Cloud) | Graph database | - Native graph data model<br/>- Vector similarity search (5.x)<br/>- Cypher query language<br/>- Cloud-hosted (Aura)<br/>- Excellent visualization tools |
| **neo4j-driver** | 5.15+ | Python Neo4j client | - Official Neo4j driver<br/>- Connection pooling<br/>- Transaction support<br/>- Async operations |
| **PostgreSQL** | 15.x (Cloud) | Relational database | - Robust ACID transactions<br/>- User authentication storage<br/>- Ingestion job tracking<br/>- Query history logging<br/>- Cloud-hosted (Supabase/Render) |
| **Prisma** | 5.8+ | PostgreSQL ORM | - Type-safe database queries<br/>- Automatic migrations<br/>- Python client generation<br/>- Database schema management |

### AI/ML Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Transformers (HuggingFace)** | 4.36+ | Embedding generation | - `all-MiniLM-L6-v2` model support<br/>- Sentence embeddings (384-dim)<br/>- Local inference (no API cost)<br/>- Fast CPU inference |
| **sentence-transformers** | 2.2+ | Sentence embeddings | - Optimized embedding models<br/>- Batch processing<br/>- GPU acceleration support<br/>- Model caching |
| **torch** | 2.1+ | ML framework | - Dependency for Transformers<br/>- CPU inference for embeddings<br/>- No GPU required for MVP |
| **NumPy** | 1.24+ | Numerical computing | - Array operations<br/>- Embedding vector manipulation<br/>- Fast numerical computations |

### Authentication & Security

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **PyJWT** | 2.8+ | JWT tokens | - Token generation/verification<br/>- Expiration handling<br/>- HS256 signing<br/>- FastAPI integration |
| **passlib** | 1.7+ | Password hashing | - bcrypt hashing<br/>- Secure password storage<br/>- Salt generation<br/>- Verification utilities |
| **python-multipart** | 0.0.6+ | File upload | - FastAPI file upload support<br/>- Multipart form data parsing<br/>- Large file handling |

### Development & Utilities

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **python-dotenv** | 1.0+ | Environment config | - `.env` file loading<br/>- Environment variable management<br/>- Development/production separation |
| **pydantic-settings** | 2.1+ | Settings management | - Type-safe configuration<br/>- Environment validation<br/>- Settings inheritance |
| **httpx** | 0.26+ | HTTP client | - Async HTTP requests<br/>- OpenRouter API calls<br/>- Connection pooling<br/>- Timeout handling |
| **pandas** | 2.1+ | CSV processing | - CSV parsing and validation<br/>- Data transformation<br/>- Batch processing<br/>- Column validation |

### Testing & Quality

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **pytest** | 7.4+ | Testing framework | - Unit and integration tests<br/>- Fixture support<br/>- Async test support<br/>- Coverage reporting |
| **pytest-asyncio** | 0.23+ | Async testing | - FastAPI async endpoint testing<br/>- Async fixture support |
| **black** | 23.12+ | Code formatting | - Consistent code style<br/>- PEP 8 compliance<br/>- Automatic formatting |
| **ruff** | 0.1+ | Linting | - Fast Python linter<br/>- Replaces flake8/pylint<br/>- Auto-fix support |
| **mypy** | 1.8+ | Type checking | - Static type validation<br/>- Catches type errors early<br/>- Better IDE support |

---

### External Services & APIs

| Service | Purpose | Configuration | Cost |
|---------|---------|---------------|------|
| **OpenRouter API** | LLM responses | - API key in `.env`<br/>- Model: `meta-llama/llama-3.3-8b-instruct:free`<br/>- Endpoint: `https://openrouter.ai/api/v1` | Free tier (MVP) |
| **Hugging Face Hub** | Embedding models | - Model: `sentence-transformers/all-MiniLM-L6-v2`<br/>- Local inference (no API key needed)<br/>- Model auto-download on first use | Free (local inference) |
| **Neo4j Aura** | Graph database hosting | - Connection URI in `.env`<br/>- Username/password auth<br/>- Free tier: 50K nodes, 175K relationships | Free tier (sufficient for MVP) |
| **PostgreSQL Cloud** | Relational database hosting | - Connection URI in `.env`<br/>- Supabase/Render/Railway<br/>- SSL connection required | Free tier |

---

### Technology Decision Rationale

**Why FastAPI over Django/Flask?**
- Async support crucial for LLM streaming (future)
- Automatic OpenAPI docs reduce documentation overhead
- Type hints and Pydantic validation prevent runtime errors
- Faster performance than Django for API-only workloads

**Why LangGraph over LangChain Chains?**
- Complex RAG workflow requires state management
- Conditional routing based on query intent (5 types)
- Better debugging with state inspection
- Future-proof for multi-turn conversations

**Why Neo4j over Traditional SQL?**
- Skills/jobs naturally form a graph (not flat tables)
- Cypher queries express relationships more naturally than SQL joins
- Native vector similarity search in Neo4j 5.x
- Graph traversal performance (2-3 hops) superior to SQL

**Why Prisma over SQLAlchemy?**
- Type-safe queries reduce runtime errors
- Automatic migration generation
- Better Python typing support
- Cleaner API for simple CRUD operations

**Why Local Embeddings over OpenAI API?**
- No per-embedding cost (40-50K job records)
- Faster inference (no network latency)
- `all-MiniLM-L6-v2` sufficient quality for career domain
- Privacy: data never leaves infrastructure

**Why Synchronous Processing over Celery?**
- Simpler MVP architecture (no worker/broker infrastructure)
- Single-user upload sufficient for internal testing
- Progress polling adequate for 5-10 minute ingestion
- Can migrate to Celery post-MVP if needed

---

### Dependencies Installation

**`requirements.txt`** (Production):
```txt
# Core Backend
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# LangGraph & LLM
langgraph==0.0.60
langchain==0.1.0
openai==1.10.0

# Databases
neo4j==5.15.0
prisma==0.11.0

# AI/ML
transformers==4.36.0
sentence-transformers==2.2.2
torch==2.1.0
numpy==1.24.3

# Auth & Security
PyJWT==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Utilities
python-dotenv==1.0.0
httpx==0.26.0
pandas==2.1.4
```

**`requirements-dev.txt`** (Development):
```txt
# Testing
pytest==7.4.3
pytest-asyncio==0.23.2

# Code Quality
black==23.12.1
ruff==0.1.9
mypy==1.8.0
```

**Installation Commands**:
```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Prisma client generation
prisma generate
```

---

### Environment Configuration

**`.env` File Structure**:
```bash
# Application
APP_ENV=development  # development, staging, production
DEBUG=True
LOG_LEVEL=INFO

# API Server
API_HOST=0.0.0.0
API_PORT=8000

# Authentication
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Neo4j
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-neo4j-password

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-your-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# CSV Processing
MAX_FILE_SIZE_MB=100
BATCH_SIZE=1000
```

---

### Version Compatibility Matrix

| Python Version | FastAPI | LangGraph | Neo4j Driver | Prisma | Status |
|----------------|---------|-----------|--------------|--------|--------|
| 3.11 | ✅ 0.109+ | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | **Recommended** |
| 3.10 | ✅ 0.109+ | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | Supported |
| 3.9 | ⚠️ Limited | ⚠️ Limited | ✅ 5.15+ | ⚠️ 0.10 only | Not recommended |
| 3.12 | ⚠️ Beta | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | Experimental |

**Recommendation**: Use **Python 3.11** for best compatibility and performance.

---

## Data Models

This section defines the complete data architecture for both Neo4j (knowledge graph) and PostgreSQL (relational data). All schemas are designed to align with the CSV data structures defined in the PRD (Appendix A).

### Overview

The system uses two databases with distinct responsibilities:

- **Neo4j (Graph Database)**: Stores Skills, Jobs, Companies, Locations, and their relationships + embeddings
- **PostgreSQL (Relational Database)**: Stores Users, Ingestion Jobs, Query History

**Data Flow**:
1. CSV upload → PostgreSQL (IngestionJob tracking)
2. CSV processing → Neo4j (graph nodes + relationships)
3. User query → LangGraph reads Neo4j, logs to PostgreSQL

---

### Neo4j Graph Schema

#### Node Types

**1. Skill Node**

Represents a professional skill from the skills taxonomy CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `id` | String | Yes | `ID` | Unique skill identifier (primary key) |
| `name` | String | Yes | `NAME` | Canonical skill name (normalized, lowercase) |
| `level` | Integer | No | `LEVEL` | Skill complexity level (1-5) |
| `type` | String | No | `TYPE` | Skill type classification |
| `is_software` | Boolean | No | `IS_SOFTWARE` | Software skill flag |
| `is_language` | Boolean | No | `IS_LANGUAGE` | Programming language flag |
| `description` | String | No | `DESCRIPTION` | Skill description |
| `description_source` | String | No | `DESCRIPTION_SOURCE` | Source of the description (e.g., "wikipedia", "manual") |
| `version` | String | No | `VERSION` | Current version of the technology/tool |
| `latest_version` | String | No | `LATEST_VERSION` | Latest available version |
| `wiki_link` | String | No | `WIKI_LINK` | Wikipedia reference URL |
| `wiki_extract` | String | No | `WIKI_EXTRACT` | Wikipedia summary |
| `embedding` | List[Float] | Yes | (Generated) | 384-dimensional vector |
| `embedding_model_version` | String | Yes | (Generated) | Embedding model identifier (e.g., "all-MiniLM-L6-v2:2024-01") |
| `embedding_generated_at` | DateTime | Yes | (Generated) | Timestamp when embedding was generated |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE`
- **Name Index**: `CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)`
- **Vector Index**: `CREATE VECTOR INDEX skill_embedding_idx IF NOT EXISTS FOR (s:Skill) ON (s.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}`

**Cypher Creation Example**:
```cypher
CREATE (s:Skill {
  id: $id,
  name: toLower(trim($name)),
  level: $level,
  type: $type,
  is_software: $is_software,
  is_language: $is_language,
  description: $description,
  description_source: $description_source,
  version: $version,
  latest_version: $latest_version,
  wiki_link: $wiki_link,
  wiki_extract: $wiki_extract,
  embedding: $embedding,
  embedding_model_version: $embedding_model_version,  // e.g., "all-MiniLM-L6-v2:2024-01"
  embedding_generated_at: datetime(),
  created_at: datetime()
})
```

---

**2. Job Node**

Represents a job posting from the jobs taxonomy CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `job_id` | String | Yes | `Job ID` | Unique job identifier (primary key) |
| `job_title` | String | Yes | `Job Title` | Job position name |
| `location` | String | No | `Location` | Job location |
| `district` | String | No | `District` | Geographic district |
| `via` | String | No | `Via` | Job source/platform (e.g., "LinkedIn", "Indeed") |
| `salary` | String | No | `Salary` | Salary range text |
| `min_salary` | Float | No | `Minimum Salary` | Minimum salary value |
| `max_salary` | Float | No | `Maximum Salary` | Maximum salary value |
| `mean_salary` | Float | No | `Mean Salary` | Average salary |
| `salary_unit` | String | No | `Unit of Measure` | Salary unit (annual/monthly) |
| `schedule_type` | String | No | `Schedule Type` | Full-time/Part-time |
| `work_from_home` | Boolean | No | `Work From Home` | Remote work flag (0/1) |
| `posted_at` | DateTime | No | `Posted At` | Job posting date |
| `description` | String | No | `Description` | Full job description |
| `job_description` | String | No | `Job Description` | Detailed job description |
| `apply_options` | String | No | `Apply Options` | Application methods/links (JSON or comma-separated) |
| `exact_matched_company` | Boolean | No | `Exact Matched Company` | Company name matching confidence flag |
| `nco_code` | String | No | `NCO_Code_algo` | National Classification of Occupations |
| `description_token_count` | Integer | No | `Description Token Count` | Token count for LLM cost optimization |
| `company_description_token_count` | Integer | No | `Company Description Token Count` | Token count for company description |
| `job_description_token_count` | Integer | No | `Job Description Token Count` | Token count for job description |
| `embedding` | List[Float] | Yes | (Generated) | 384-dimensional vector |
| `embedding_model_version` | String | Yes | (Generated) | Embedding model identifier (e.g., "all-MiniLM-L6-v2:2024-01") |
| `embedding_generated_at` | DateTime | Yes | (Generated) | Timestamp when embedding was generated |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE`
- **Title Index**: `CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.job_title)`
- **Vector Index**: `CREATE VECTOR INDEX job_embedding_idx IF NOT EXISTS FOR (j:Job) ON (j.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}`

**Cypher Creation Example**:
```cypher
CREATE (j:Job {
  job_id: $job_id,
  job_title: $job_title,
  location: $location,
  district: $district,
  via: $via,
  salary: $salary,
  min_salary: $min_salary,
  max_salary: $max_salary,
  mean_salary: $mean_salary,
  salary_unit: $salary_unit,
  schedule_type: $schedule_type,
  work_from_home: $work_from_home,
  posted_at: datetime($posted_at),
  description: $description,
  job_description: $job_description,
  apply_options: $apply_options,
  exact_matched_company: $exact_matched_company,
  nco_code: $nco_code,
  description_token_count: $description_token_count,
  company_description_token_count: $company_description_token_count,
  job_description_token_count: $job_description_token_count,
  embedding: $embedding,
  embedding_model_version: $embedding_model_version,  // e.g., "all-MiniLM-L6-v2:2024-01"
  embedding_generated_at: datetime(),
  created_at: datetime()
})
```

---

**3. Company Node**

Represents an employer from the jobs CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `company_name` | String | Yes | `Company Name` | Employer name (primary key) |
| `cin` | String | No | `CIN` | Corporate Identification Number |
| `company_description` | String | No | `Company Description` | Company overview |
| `industry_classification` | String | No | `CompanyIndustrialClassification` | Industry classification |
| `nic_code` | String | No | `NIC_Code_algo` | National Industrial Classification |
| `nic_code_2008` | String | No | `nic_code_2_2008` | NIC 2008 classification code |
| `embedding` | List[Float] | No | (Generated) | 384-dimensional vector (if company_description exists) |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT company_name_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_name IS UNIQUE`
- **Name Index**: `CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (toLower(c.company_name))`

**Cypher Creation Example**:
```cypher
MERGE (c:Company {company_name: $company_name})
ON CREATE SET
  c.cin = $cin,
  c.company_description = $company_description,
  c.industry_classification = $industry_classification,
  c.nic_code = $nic_code,
  c.nic_code_2008 = $nic_code_2008,
  c.embedding = $embedding,
  c.created_at = datetime()
```

---

**4. Location Node**

Represents geographic location from jobs CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `location_name` | String | Yes | `Location` | Location name (primary key) |
| `district` | String | No | `District` | Geographic district |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT location_name_unique IF NOT EXISTS FOR (l:Location) REQUIRE l.location_name IS UNIQUE`

**Cypher Creation Example**:
```cypher
MERGE (l:Location {location_name: $location_name})
ON CREATE SET
  l.district = $district,
  l.created_at = datetime()
```

---

**5. Category Node**

Represents skill category from skills taxonomy CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `category_id` | String | Yes | `CATEGORY` | Category ID (primary key) |
| `category_name` | String | Yes | `CATEGORY_NAME` | Category name |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.category_id IS UNIQUE`

**Cypher Creation Example**:
```cypher
MERGE (cat:Category {category_id: $category_id})
ON CREATE SET
  cat.category_name = $category_name,
  cat.created_at = datetime()
```

---

**6. Subcategory Node**

Represents skill subcategory from skills taxonomy CSV.

**Properties**:
| Property | Type | Required | Source CSV Column | Description |
|----------|------|----------|-------------------|-------------|
| `subcategory_id` | String | Yes | `SUBCATEGORY` | Subcategory ID (primary key) |
| `subcategory_name` | String | Yes | `SUBCATEGORY_NAME` | Subcategory name |
| `created_at` | DateTime | Yes | (Generated) | Node creation timestamp |

**Indexes**:
- **Unique Constraint**: `CREATE CONSTRAINT subcategory_id_unique IF NOT EXISTS FOR (sub:Subcategory) REQUIRE sub.subcategory_id IS UNIQUE`

**Cypher Creation Example**:
```cypher
MERGE (sub:Subcategory {subcategory_id: $subcategory_id})
ON CREATE SET
  sub.subcategory_name = $subcategory_name,
  sub.created_at = datetime()
```

---

#### Relationship Types

**1. REQUIRES (Job → Skill)**

Represents job-skill requirement relationship from `standardized_skills` in jobs CSV.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `similarity_score` | Float | No | Pre-computed skill match confidence (0.0-1.0) from CSV |
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (j:Job {job_id: $job_id})
MATCH (s:Skill {name: toLower(trim($skill_name))})
MERGE (j)-[r:REQUIRES]->(s)
ON CREATE SET
  r.similarity_score = $similarity_score,
  r.created_at = datetime()
```

**Matching Logic** (from PRD):
1. Parse `standardized_skills` list from jobs CSV (e.g., `["Python", "FastAPI", "Neo4j"]`)
2. Normalize each skill name: `toLower(trim(skill_name))`
3. Match against Skill nodes: `WHERE toLower(s.name) = normalized_name`
4. Create REQUIRES relationship
5. If `similarity_scores` array exists and aligns with `standardized_skills` (same length/order), store as `similarity_score` property

---

**2. POSTED_BY (Job → Company)**

Represents employer relationship.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (j:Job {job_id: $job_id})
MATCH (c:Company {company_name: $company_name})
MERGE (j)-[r:POSTED_BY]->(c)
ON CREATE SET r.created_at = datetime()
```

---

**3. LOCATED_IN (Job → Location)**

Represents job location relationship.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (j:Job {job_id: $job_id})
MATCH (l:Location {location_name: $location_name})
MERGE (j)-[r:LOCATED_IN]->(l)
ON CREATE SET r.created_at = datetime()
```

---

**4. BELONGS_TO_CATEGORY (Skill → Category)**

Represents skill-category hierarchy.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (s:Skill {id: $skill_id})
MATCH (cat:Category {category_id: $category_id})
MERGE (s)-[r:BELONGS_TO_CATEGORY]->(cat)
ON CREATE SET r.created_at = datetime()
```

---

**5. BELONGS_TO_SUBCATEGORY (Skill → Subcategory)**

Represents skill-subcategory hierarchy.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (s:Skill {id: $skill_id})
MATCH (sub:Subcategory {subcategory_id: $subcategory_id})
MERGE (s)-[r:BELONGS_TO_SUBCATEGORY]->(sub)
ON CREATE SET r.created_at = datetime()
```

---

**6. CONTAINS (Category → Subcategory)**

Represents category-subcategory hierarchy.

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example**:
```cypher
MATCH (cat:Category {category_id: $category_id})
MATCH (sub:Subcategory {subcategory_id: $subcategory_id})
MERGE (cat)-[r:CONTAINS]->(sub)
ON CREATE SET r.created_at = datetime()
```

---

**7. SIMILAR_TO (Skill → Skill)**

Represents semantic similarity between skills (computed from embeddings, optional for MVP).

**Properties**:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `similarity_score` | Float | Yes | Cosine similarity (0.0-1.0) |
| `created_at` | DateTime | Yes | Relationship creation timestamp |

**Cypher Creation Example** (post-ingestion computation):
```cypher
// Find similar skills via vector similarity
CALL db.index.vector.queryNodes('skill_embedding_idx', 5, $embedding)
YIELD node, score
WHERE score > 0.8 AND node.id <> $skill_id
MATCH (s:Skill {id: $skill_id})
MERGE (s)-[r:SIMILAR_TO]->(node)
ON CREATE SET
  r.similarity_score = score,
  r.created_at = datetime()
```

---

#### Embedding Version Management & Reindexing Strategy

**Purpose**: Track embedding model versions to enable safe model upgrades without invalidating existing vectors.

**Problem Statement**:
- Embedding models evolve over time (performance improvements, dimension changes, algorithm updates)
- When the model changes, all existing embeddings become incompatible with new embeddings
- Vector similarity searches between old and new embeddings produce incorrect results
- System must be able to identify outdated embeddings and regenerate them systematically

**Solution**: Version tracking with automated detection and batch reindexing.

---

##### 1. Version Tracking Implementation

All nodes with embeddings (Skill, Job, Company) include version metadata:

```python
# app/services/embedding_service.py
class EmbeddingService:
    """
    Embedding generation service with version tracking.

    Version Format: {model-name}:{release-date}
    Example: "all-MiniLM-L6-v2:2024-01"
    """

    # Current embedding model configuration
    CURRENT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    CURRENT_MODEL_VERSION = "all-MiniLM-L6-v2:2024-01"
    EMBEDDING_DIMENSIONS = 384

    def __init__(self):
        self.model = SentenceTransformer(self.CURRENT_MODEL_NAME)

    async def generate_embedding(self, text: str) -> dict:
        """
        Generate embedding with version metadata.

        Returns:
            dict: {
                "embedding": [0.123, -0.456, ...],  # 384 dimensions
                "model_version": "all-MiniLM-L6-v2:2024-01",
                "generated_at": datetime.utcnow()
            }
        """
        embedding_vector = self.model.encode(text).tolist()

        return {
            "embedding": embedding_vector,
            "model_version": self.CURRENT_MODEL_VERSION,
            "generated_at": datetime.utcnow()
        }
```

---

##### 2. Identify Outdated Embeddings

**Query 1: Count outdated embeddings by node type**
```cypher
// Check how many nodes need reindexing
MATCH (n)
WHERE n.embedding IS NOT NULL
  AND n.embedding_model_version <> $current_model_version
RETURN labels(n)[0] as node_type,
       count(n) as outdated_count,
       n.embedding_model_version as old_version
ORDER BY outdated_count DESC
```

**Example Output**:
```
node_type    | outdated_count | old_version
-------------|----------------|------------------------
Skill        | 15,234         | all-MiniLM-L6-v2:2023-06
Job          | 8,921          | all-MiniLM-L6-v2:2023-06
Company      | 1,456          | all-MiniLM-L6-v2:2023-06
```

**Query 2: Get specific outdated nodes for reindexing batch**
```cypher
// Fetch 1000 outdated Skill nodes for batch processing
MATCH (s:Skill)
WHERE s.embedding_model_version <> $current_model_version
RETURN s.id, s.name, s.description, s.embedding_model_version
LIMIT 1000
```

**Query 3: Verify embedding consistency**
```cypher
// Check if all embeddings use the same model version (health check)
MATCH (n)
WHERE n.embedding IS NOT NULL
RETURN DISTINCT n.embedding_model_version as version, count(n) as count
ORDER BY count DESC
```

---

##### 3. Batch Reindexing Process

**Strategy**: Process in batches to avoid memory exhaustion and allow resumable progress.

**Python Implementation**:
```python
# scripts/reindex_embeddings.py
import asyncio
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository

class EmbeddingReindexer:
    """
    Batch reindexing orchestrator for embedding model migrations.

    Process:
    1. Query outdated nodes in batches (1000 at a time)
    2. Generate new embeddings with updated model
    3. Update nodes with new embeddings + version metadata
    4. Track progress in reindexing_log table
    5. Resume from last batch if interrupted
    """

    BATCH_SIZE = 1000  # Process 1000 nodes per batch
    NODE_TYPES = ["Skill", "Job", "Company"]  # Node types with embeddings

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.neo4j_repo = Neo4jRepository()
        self.current_version = EmbeddingService.CURRENT_MODEL_VERSION

    async def reindex_node_type(self, node_type: str) -> dict:
        """
        Reindex all outdated embeddings for a specific node type.

        Args:
            node_type: "Skill", "Job", or "Company"

        Returns:
            dict: {
                "node_type": "Skill",
                "total_reindexed": 15234,
                "batches_processed": 16,
                "duration_seconds": 3421.5,
                "errors": []
            }
        """
        start_time = datetime.utcnow()
        total_reindexed = 0
        batches_processed = 0
        errors = []

        while True:
            # Fetch batch of outdated nodes
            batch = await self._fetch_outdated_batch(node_type)

            if not batch:
                break  # No more outdated nodes

            # Generate new embeddings
            try:
                await self._reindex_batch(node_type, batch)
                total_reindexed += len(batch)
                batches_processed += 1

                # Log progress every 5 batches
                if batches_processed % 5 == 0:
                    logger.info(
                        f"Reindexing {node_type}: {total_reindexed} nodes completed "
                        f"({batches_processed} batches)"
                    )

            except Exception as e:
                error_msg = f"Batch {batches_processed} failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Continue with next batch (don't fail entire reindex)

        duration = (datetime.utcnow() - start_time).total_seconds()

        return {
            "node_type": node_type,
            "total_reindexed": total_reindexed,
            "batches_processed": batches_processed,
            "duration_seconds": duration,
            "errors": errors
        }

    async def _fetch_outdated_batch(self, node_type: str) -> list[dict]:
        """Fetch batch of nodes with outdated embeddings."""
        query = f"""
        MATCH (n:{node_type})
        WHERE n.embedding_model_version <> $current_version
        RETURN n.id as id,
               n.name as name,
               n.description as description,
               n.embedding_model_version as old_version
        LIMIT $batch_size
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "current_version": self.current_version,
                "batch_size": self.BATCH_SIZE
            }
        )

        return [dict(record) for record in result]

    async def _reindex_batch(self, node_type: str, batch: list[dict]) -> None:
        """
        Generate new embeddings and update nodes in transaction.

        Uses Neo4j transaction to ensure atomicity:
        - If any node in batch fails, rollback entire batch
        - Prevents partial updates that could corrupt vector index
        """
        # Generate embeddings for all nodes in batch
        embedding_tasks = [
            self.embedding_service.generate_embedding(node["description"])
            for node in batch
        ]
        embeddings = await asyncio.gather(*embedding_tasks)

        # Update all nodes in single transaction
        async with self.neo4j_repo.transaction() as tx:
            for node, embedding_data in zip(batch, embeddings):
                update_query = f"""
                MATCH (n:{node_type} {{id: $id}})
                SET n.embedding = $embedding,
                    n.embedding_model_version = $model_version,
                    n.embedding_generated_at = datetime()
                """

                await tx.run(
                    update_query,
                    {
                        "id": node["id"],
                        "embedding": embedding_data["embedding"],
                        "model_version": embedding_data["model_version"]
                    }
                )

# CLI usage
async def main():
    """Run embedding reindexing for all node types."""
    reindexer = EmbeddingReindexer()

    print(f"🔄 Starting embedding reindexing")
    print(f"Current model version: {EmbeddingService.CURRENT_MODEL_VERSION}\n")

    total_start = datetime.utcnow()
    results = []

    for node_type in EmbeddingReindexer.NODE_TYPES:
        print(f"📊 Reindexing {node_type} nodes...")
        result = await reindexer.reindex_node_type(node_type)
        results.append(result)

        print(f"✅ {node_type}: {result['total_reindexed']} nodes reindexed")
        print(f"   Duration: {result['duration_seconds']:.1f}s")
        if result['errors']:
            print(f"   ⚠️  {len(result['errors'])} errors occurred\n")
        else:
            print()

    total_duration = (datetime.utcnow() - total_start).total_seconds()
    total_reindexed = sum(r['total_reindexed'] for r in results)

    print(f"🎉 Reindexing complete!")
    print(f"Total nodes reindexed: {total_reindexed}")
    print(f"Total duration: {total_duration:.1f}s")
    print(f"Average speed: {total_reindexed / total_duration:.1f} nodes/second")

if __name__ == "__main__":
    asyncio.run(main())
```

---

##### 4. Vector Index Rebuild Considerations

**Important**: After reindexing embeddings, the vector index does NOT need to be dropped and recreated in Neo4j 5.x+.

**How Neo4j Vector Indexes Work**:
- Vector indexes are **automatically updated** when node embeddings change
- When you `SET n.embedding = $new_embedding`, the index entry is updated in real-time
- No manual `DROP INDEX` or `CREATE INDEX` required

**However, you should verify index health after large reindexing operations**:

```cypher
// 1. Check index status
SHOW INDEXES
YIELD name, type, state, populationPercent
WHERE type = "VECTOR"
RETURN name, state, populationPercent
```

**Expected Output**:
```
name                      | state    | populationPercent
--------------------------|----------|------------------
skill_embedding_idx       | ONLINE   | 100.0
job_embedding_idx         | ONLINE   | 100.0
company_embedding_idx     | ONLINE   | 100.0
```

**If index state is not ONLINE or populationPercent < 100**:
```cypher
// Force index rebuild (only if corrupted)
DROP INDEX skill_embedding_idx IF EXISTS;

CREATE VECTOR INDEX skill_embedding_idx IF NOT EXISTS
FOR (s:Skill)
ON s.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 384,
    `vector.similarity_function`: 'cosine'
  }
};
```

---

##### 5. Model Migration Checklist

**Before Migration** (Testing Phase):
- [ ] Test new model on sample data (compare similarity scores with old model)
- [ ] Benchmark embedding generation speed (CPU vs GPU)
- [ ] Verify new model dimensions match existing vector index configuration
- [ ] If dimensions changed, plan vector index recreation (requires downtime)
- [ ] Estimate reindexing time: `(total_nodes / 100 nodes per second) / 3600` hours
- [ ] Schedule maintenance window for reindexing (recommend off-peak hours)

**During Migration**:
- [ ] Update `EmbeddingService.CURRENT_MODEL_VERSION` to new version identifier
- [ ] Deploy updated application code (new embeddings will use new model)
- [ ] **Immediately disable vector similarity queries** (inconsistent results during migration)
- [ ] Run reindexing script: `python scripts/reindex_embeddings.py`
- [ ] Monitor progress logs and error rates
- [ ] Verify index health after each node type completes

**After Migration**:
- [ ] Verify all nodes have new model version: `MATCH (n) WHERE n.embedding IS NOT NULL RETURN DISTINCT n.embedding_model_version`
- [ ] Run test queries comparing old vs new model results
- [ ] Re-enable vector similarity queries
- [ ] Update documentation with new model version and migration date
- [ ] Archive old model weights (rollback capability)

---

##### 6. Downtime Mitigation Strategies

**Option 1: Blue-Green Deployment** (Zero Downtime, High Resource Cost)
```
1. Spin up second Neo4j instance (green)
2. Replicate data to green instance
3. Run reindexing on green instance (production unaffected)
4. Cutover traffic to green instance
5. Decommission blue instance
```
- **Pros**: No downtime, safe rollback
- **Cons**: 2x database resources, complex setup

**Option 2: Rolling Reindex** (Minimal Downtime, Recommended)
```
1. Deploy new model version but keep generating embeddings with both models temporarily
2. Store both old and new embeddings in separate properties:
   - n.embedding_old (legacy model)
   - n.embedding_new (current model)
3. Gradually migrate nodes in background
4. Switch queries to use n.embedding_new when threshold reached (e.g., 80%)
5. Drop n.embedding_old after 100% migration
```
- **Pros**: Gradual migration, always queryable, resource-efficient
- **Cons**: More complex code, temporary storage overhead

**Option 3: Scheduled Maintenance** (Simplest, Short Downtime)
```
1. Schedule 2-4 hour maintenance window
2. Disable vector queries during reindexing
3. Run reindexing script
4. Verify completion and re-enable queries
```
- **Pros**: Simple, predictable, clean cutover
- **Cons**: Service disruption during migration

**Recommendation for MVP**: Use Option 3 (Scheduled Maintenance) with clear user communication.

---

##### 7. Monitoring Reindexing Progress

**PostgreSQL Progress Tracking Table** (optional but recommended):
```prisma
// prisma/schema.prisma
model EmbeddingMigration {
  id                String   @id @default(uuid())
  migration_name    String   // e.g., "all-MiniLM-L6-v2:2023-06 -> 2024-01"
  node_type         String   // "Skill", "Job", or "Company"
  old_version       String
  new_version       String
  total_nodes       Int
  reindexed_nodes   Int      @default(0)
  batches_completed Int      @default(0)
  status            String   // "in_progress", "completed", "failed"
  started_at        DateTime @default(now())
  completed_at      DateTime?
  error_message     String?

  @@index([status, node_type])
}
```

**Progress Query During Reindexing**:
```sql
-- Check migration progress
SELECT
  node_type,
  reindexed_nodes,
  total_nodes,
  ROUND((reindexed_nodes::numeric / total_nodes) * 100, 2) as progress_percent,
  EXTRACT(EPOCH FROM (NOW() - started_at)) as elapsed_seconds,
  status
FROM embedding_migrations
WHERE status = 'in_progress'
ORDER BY node_type;
```

---

##### 8. Testing Strategy

**Unit Tests** (`tests/services/test_embedding_service.py`):
```python
def test_embedding_includes_version_metadata():
    """Verify embeddings include version tracking."""
    service = EmbeddingService()
    result = await service.generate_embedding("Python programming")

    assert "embedding" in result
    assert "model_version" in result
    assert "generated_at" in result
    assert len(result["embedding"]) == 384
    assert result["model_version"] == "all-MiniLM-L6-v2:2024-01"

def test_reindex_identifies_outdated_nodes():
    """Verify outdated nodes are correctly identified."""
    # Create test nodes with old version
    create_skill("Python", embedding_version="all-MiniLM-L6-v2:2023-06")
    create_skill("Java", embedding_version="all-MiniLM-L6-v2:2024-01")

    reindexer = EmbeddingReindexer()
    outdated = await reindexer._fetch_outdated_batch("Skill")

    assert len(outdated) == 1
    assert outdated[0]["name"] == "Python"
    assert outdated[0]["old_version"] == "all-MiniLM-L6-v2:2023-06"
```

**Integration Tests** (`tests/integration/test_reindexing.py`):
```python
async def test_full_reindexing_workflow():
    """Test complete reindexing process end-to-end."""
    # Setup: Create 100 skills with old embeddings
    for i in range(100):
        await create_skill(
            name=f"Skill-{i}",
            embedding_version="old-model:2023-01"
        )

    # Execute reindexing
    reindexer = EmbeddingReindexer()
    result = await reindexer.reindex_node_type("Skill")

    # Verify results
    assert result["total_reindexed"] == 100
    assert result["batches_processed"] == 1  # 100 nodes in 1 batch
    assert len(result["errors"]) == 0

    # Verify all nodes now have new version
    query = """
    MATCH (s:Skill)
    WHERE s.embedding_model_version = $new_version
    RETURN count(s) as updated_count
    """
    result = await neo4j_repo.execute_query(
        query,
        {"new_version": EmbeddingService.CURRENT_MODEL_VERSION}
    )

    assert result[0]["updated_count"] == 100
```

---

**Summary**:
- All embeddings tracked with `model_version` + `generated_at` metadata
- Outdated embeddings identifiable via Cypher queries
- Batch reindexing process handles large-scale migrations
- Neo4j vector indexes automatically update (no manual rebuild needed)
- Migration checklist ensures safe model upgrades
- Multiple deployment strategies available (zero-downtime to scheduled maintenance)

---

#### Graph Schema Diagram

```mermaid
graph LR
    Job[Job Node<br/>job_id, job_title, salary<br/>embedding]
    Skill[Skill Node<br/>id, name, level<br/>embedding]
    Company[Company Node<br/>company_name, cin<br/>embedding]
    Location[Location Node<br/>location_name, district]
    Category[Category Node<br/>category_id, category_name]
    Subcategory[Subcategory Node<br/>subcategory_id, subcategory_name]

    Job -->|REQUIRES<br/>similarity_score| Skill
    Job -->|POSTED_BY| Company
    Job -->|LOCATED_IN| Location
    Skill -->|BELONGS_TO_CATEGORY| Category
    Skill -->|BELONGS_TO_SUBCATEGORY| Subcategory
    Category -->|CONTAINS| Subcategory
    Skill -.->|SIMILAR_TO<br/>similarity_score| Skill

    style Job fill:#e3f2fd
    style Skill fill:#c8e6c9
    style Company fill:#fff3e0
    style Location fill:#f8bbd0
    style Category fill:#ffecb3
    style Subcategory fill:#ffe0b2
```

---

### PostgreSQL Schema (Prisma)

#### Prisma Schema File

**`prisma/schema.prisma`**:
```prisma
// Prisma schema for PostgreSQL database
// Database URL from environment variable: DATABASE_URL

generator client {
  provider = "prisma-client-py"
  interface = "asyncio"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// User authentication table
model User {
  id            String   @id @default(uuid())
  email         String   @unique
  password_hash String
  created_at    DateTime @default(now())
  updated_at    DateTime @updatedAt

  // Relations
  query_history QueryHistory[]
  ingestion_jobs IngestionJob[]

  @@map("users")
}

// CSV ingestion job tracking
model IngestionJob {
  id             String   @id @default(uuid())
  user_id        String
  file_type      String   // "skills" or "jobs"
  file_name      String
  file_size_mb   Float
  status         String   // "pending", "processing", "completed", "failed"
  total_records  Int      @default(0)
  processed_records Int   @default(0)
  failed_records Int      @default(0)
  batch_number   Int?     // Current batch being processed
  error_log      String?  // JSON array of error messages
  started_at     DateTime @default(now())
  completed_at   DateTime?
  created_at     DateTime @default(now())
  updated_at     DateTime @updatedAt

  // Relations
  user           User     @relation(fields: [user_id], references: [id], onDelete: Cascade)

  @@index([user_id])
  @@index([status])
  @@index([file_type])
  @@map("ingestion_jobs")
}

// User query history logging
model QueryHistory {
  id              String   @id @default(uuid())
  user_id         String
  query_text      String   @db.Text
  query_intent    String?  // "skill_requirements", "salary_insights", etc.
  response_text   String   @db.Text
  sources_count   Int      @default(0)  // Number of graph nodes used
  response_time_ms Int     // Query processing time
  created_at      DateTime @default(now())

  // Relations
  user            User     @relation(fields: [user_id], references: [id], onDelete: Cascade)

  @@index([user_id])
  @@index([created_at])
  @@index([query_intent])
  @@map("query_history")
}
```

---

#### PostgreSQL Tables

**1. users Table**

Stores user authentication credentials.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | User unique identifier |
| `email` | VARCHAR | UNIQUE, NOT NULL | User email (login) |
| `password_hash` | VARCHAR | NOT NULL | bcrypt hashed password |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Account creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- Primary Key on `id`
- Unique index on `email`

---

**2. ingestion_jobs Table**

Tracks CSV upload and processing status.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Job unique identifier |
| `user_id` | UUID | FOREIGN KEY → users(id), NOT NULL | User who uploaded CSV |
| `file_type` | VARCHAR | NOT NULL | "skills" or "jobs" |
| `file_name` | VARCHAR | NOT NULL | Original CSV filename |
| `file_size_mb` | FLOAT | NOT NULL | File size in megabytes |
| `status` | VARCHAR | NOT NULL | "pending", "processing", "completed", "failed" |
| `total_records` | INTEGER | DEFAULT 0 | Total CSV records |
| `processed_records` | INTEGER | DEFAULT 0 | Successfully processed records |
| `failed_records` | INTEGER | DEFAULT 0 | Failed records |
| `batch_number` | INTEGER | NULL | Current batch being processed |
| `error_log` | TEXT | NULL | JSON array of error messages |
| `started_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Processing start time |
| `completed_at` | TIMESTAMP | NULL | Processing completion time |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Job creation timestamp |
| `updated_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Last update timestamp |

**Indexes**:
- Primary Key on `id`
- Foreign Key on `user_id`
- Index on `user_id`
- Index on `status`
- Index on `file_type`

---

**3. query_history Table**

Logs user queries and responses for analytics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Query unique identifier |
| `user_id` | UUID | FOREIGN KEY → users(id), NOT NULL | User who submitted query |
| `query_text` | TEXT | NOT NULL | Natural language query |
| `query_intent` | VARCHAR | NULL | Classified intent (e.g., "skill_requirements") |
| `response_text` | TEXT | NOT NULL | LLM-generated response |
| `sources_count` | INTEGER | DEFAULT 0 | Number of graph nodes used in response |
| `response_time_ms` | INTEGER | NOT NULL | Query processing time (milliseconds) |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT NOW() | Query timestamp |

**Indexes**:
- Primary Key on `id`
- Foreign Key on `user_id`
- Index on `user_id`
- Index on `created_at` (for time-based queries)
- Index on `query_intent` (for analytics)

---

### Data Validation Rules

#### Neo4j Validation

**Skills CSV Validation**:
- **Required Columns**: `ID`, `NAME` (other columns optional)
- **ID Format**: Non-empty string
- **NAME Format**: Non-empty string, normalized to lowercase
- **LEVEL**: Integer 1-5 or NULL
- **IS_SOFTWARE, IS_LANGUAGE**: Boolean (0/1) or NULL
- **Embedding**: Always generated fresh (ignore CSV embeddings)

**Jobs CSV Validation**:
- **Required Columns**: `Job ID`, `Job Title` (other columns optional)
- **Job ID Format**: Non-empty string, unique
- **standardized_skills**: Must be parseable list/array
- **Salary Fields**: Numeric or NULL
- **Work From Home**: Boolean (0/1) or NULL
- **Embedding**: Always generated fresh

**Skill Matching Logic with Fuzzy Matching & Deduplication** (PRD Appendix A + QA Enhancement):

**Overview**: Match incoming skill names from CSV to existing taxonomy using fuzzy matching to prevent duplicates while flagging ambiguous cases for manual review.

**Dependencies**:
```txt
python-Levenshtein==0.21.1  # Fast Levenshtein distance calculation
```

**Matching Algorithm** (3-tier strategy):

**Tier 1: Exact Match** (Case-Insensitive)
```
Input: "Python"
1. Normalize: name.lower().strip() → "python"
2. Cypher: MATCH (s:Skill) WHERE toLower(s.name) = $normalized_name
3. If found → create REQUIRES relationship
4. Result: ✅ Exact match to existing "python" skill
```

**Tier 2: Fuzzy Match** (Levenshtein Distance ≤ 2)
```
Input: "Pyton" (typo)
1. No exact match found
2. Query all skill names from Neo4j
3. Calculate Levenshtein distance for each:
   - Levenshtein("pyton", "python") = 1 ✅
   - Levenshtein("pyton", "julia") = 5 ❌
4. Filter candidates with distance ≤ 2
5. If single candidate → use that skill (log fuzzy match)
6. If multiple candidates → create orphan with requires_manual_review=true
7. Result: ✅ Fuzzy matched to "python" (confidence: high)
```

**Tier 3: Orphan Creation** (No Match Found)
```
Input: "NewFramework2025"
1. No exact match, no fuzzy match within threshold
2. Create orphan Skill node with:
   - name: "newframework2025" (normalized)
   - requires_manual_review: true
   - created_from_job: true
   - matched_via: "orphan_creation"
3. Log warning for manual taxonomy review
4. Create REQUIRES relationship to orphan node
5. Result: ⚠️  Orphan created, requires admin review
```

**Python Implementation**:
```python
# app/services/skill_matching_service.py
from Levenshtein import distance as levenshtein_distance
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class SkillMatchingService:
    """
    Fuzzy skill matching service with deduplication.

    Prevents skill taxonomy pollution by:
    1. Exact case-insensitive matching (primary)
    2. Fuzzy matching with Levenshtein distance (typo correction)
    3. Orphan flagging for manual review (unknown skills)
    """

    FUZZY_MATCH_THRESHOLD = 2  # Maximum Levenshtein distance
    MIN_SKILL_NAME_LENGTH = 2  # Minimum characters for fuzzy matching

    def __init__(self, neo4j_repo):
        self.neo4j_repo = neo4j_repo
        self._skill_cache: Optional[List[str]] = None  # Cache for fuzzy matching

    async def match_skill(self, skill_name: str, job_id: str) -> dict:
        """
        Match skill name to existing taxonomy or create orphan.

        Args:
            skill_name: Raw skill name from CSV (e.g., "Python", "Pyton", "FastAPI")
            job_id: Job ID for logging and relationship creation

        Returns:
            dict: {
                "skill_id": "uuid-or-orphan-id",
                "matched_name": "python",  # Canonical name from taxonomy
                "match_type": "exact" | "fuzzy" | "orphan",
                "confidence": float,  # 1.0 (exact), 0.5-0.9 (fuzzy), 0.0 (orphan)
                "requires_manual_review": bool,
                "fuzzy_candidates": List[str]  # If multiple fuzzy matches
            }
        """
        # Normalize input
        normalized_name = skill_name.lower().strip()

        if len(normalized_name) < self.MIN_SKILL_NAME_LENGTH:
            logger.warning(f"Skill name too short: '{skill_name}' (job: {job_id})")
            return await self._create_orphan(normalized_name, job_id, "too_short")

        # Tier 1: Exact match (fast path)
        exact_match = await self._find_exact_match(normalized_name)
        if exact_match:
            logger.info(f"✅ Exact match: '{skill_name}' → {exact_match['name']}")
            return {
                "skill_id": exact_match["id"],
                "matched_name": exact_match["name"],
                "match_type": "exact",
                "confidence": 1.0,
                "requires_manual_review": False,
                "fuzzy_candidates": []
            }

        # Tier 2: Fuzzy match (typo correction)
        fuzzy_result = await self._find_fuzzy_match(normalized_name)

        if fuzzy_result["match_type"] == "fuzzy_single":
            # Single candidate within threshold
            logger.info(
                f"🔍 Fuzzy match: '{skill_name}' → {fuzzy_result['matched_name']} "
                f"(distance: {fuzzy_result['distance']})"
            )
            return {
                "skill_id": fuzzy_result["skill_id"],
                "matched_name": fuzzy_result["matched_name"],
                "match_type": "fuzzy",
                "confidence": 1.0 - (fuzzy_result["distance"] / 10),  # 0.8-0.9
                "requires_manual_review": False,
                "fuzzy_candidates": []
            }

        elif fuzzy_result["match_type"] == "fuzzy_multiple":
            # Ambiguous: multiple candidates within threshold
            logger.warning(
                f"⚠️  Ambiguous fuzzy match: '{skill_name}' → "
                f"{fuzzy_result['candidates']} (creating orphan for review)"
            )
            return await self._create_orphan(
                normalized_name,
                job_id,
                "ambiguous_fuzzy_match",
                fuzzy_candidates=fuzzy_result["candidates"]
            )

        # Tier 3: No match - create orphan
        logger.warning(f"⚠️  No match found: '{skill_name}' (creating orphan)")
        return await self._create_orphan(normalized_name, job_id, "no_match")

    async def _find_exact_match(self, normalized_name: str) -> Optional[dict]:
        """Find exact case-insensitive match in skill taxonomy."""
        query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) = $normalized_name
        RETURN s.id as id, s.name as name
        LIMIT 1
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {"normalized_name": normalized_name}
        )

        return dict(result[0]) if result else None

    async def _find_fuzzy_match(self, normalized_name: str) -> dict:
        """
        Find fuzzy matches using Levenshtein distance.

        Returns:
            dict with match_type: "fuzzy_single", "fuzzy_multiple", or "no_fuzzy_match"
        """
        # Refresh skill cache if needed
        if self._skill_cache is None:
            await self._refresh_skill_cache()

        # Calculate Levenshtein distance for all skills
        candidates = []
        for taxonomy_skill in self._skill_cache:
            distance = levenshtein_distance(normalized_name, taxonomy_skill["name_lower"])

            if distance <= self.FUZZY_MATCH_THRESHOLD:
                candidates.append({
                    "skill_id": taxonomy_skill["id"],
                    "name": taxonomy_skill["name"],
                    "distance": distance
                })

        # Sort by distance (closest first)
        candidates.sort(key=lambda x: x["distance"])

        if len(candidates) == 0:
            return {"match_type": "no_fuzzy_match"}

        elif len(candidates) == 1:
            # Unambiguous fuzzy match
            return {
                "match_type": "fuzzy_single",
                "skill_id": candidates[0]["skill_id"],
                "matched_name": candidates[0]["name"],
                "distance": candidates[0]["distance"]
            }

        else:
            # Multiple candidates - ambiguous
            return {
                "match_type": "fuzzy_multiple",
                "candidates": [c["name"] for c in candidates]
            }

    async def _refresh_skill_cache(self) -> None:
        """Load all skill names from Neo4j for fuzzy matching."""
        query = """
        MATCH (s:Skill)
        RETURN s.id as id, s.name as name, toLower(s.name) as name_lower
        """

        result = await self.neo4j_repo.execute_query(query)
        self._skill_cache = [dict(record) for record in result]

        logger.info(f"Skill cache refreshed: {len(self._skill_cache)} skills loaded")

    async def _create_orphan(
        self,
        normalized_name: str,
        job_id: str,
        reason: str,
        fuzzy_candidates: Optional[List[str]] = None
    ) -> dict:
        """
        Create orphan skill node for manual review.

        Orphan Node Properties:
        - name: Normalized skill name
        - requires_manual_review: true (admin must validate)
        - created_from_job: true (auto-generated from job CSV)
        - orphan_reason: Why no match was found
        - fuzzy_candidates: Ambiguous matches (if any)
        - created_at: Timestamp
        """
        query = """
        MERGE (s:Skill {name: $normalized_name})
        ON CREATE SET
          s.id = randomUUID(),
          s.requires_manual_review = true,
          s.created_from_job = true,
          s.orphan_reason = $reason,
          s.fuzzy_candidates = $fuzzy_candidates,
          s.created_at = datetime()
        RETURN s.id as id, s.name as name
        """

        result = await self.neo4j_repo.execute_query(
            query,
            {
                "normalized_name": normalized_name,
                "reason": reason,
                "fuzzy_candidates": fuzzy_candidates or []
            }
        )

        orphan = dict(result[0])

        # Log for manual review dashboard
        await self._log_orphan_creation(orphan["id"], normalized_name, job_id, reason)

        return {
            "skill_id": orphan["id"],
            "matched_name": orphan["name"],
            "match_type": "orphan",
            "confidence": 0.0,
            "requires_manual_review": True,
            "fuzzy_candidates": fuzzy_candidates or []
        }

    async def _log_orphan_creation(
        self,
        skill_id: str,
        skill_name: str,
        job_id: str,
        reason: str
    ) -> None:
        """Log orphan creation for admin review dashboard."""
        # Store in PostgreSQL for admin review interface
        await self.ingestion_repo.create_orphan_log(
            skill_id=skill_id,
            skill_name=skill_name,
            job_id=job_id,
            reason=reason,
            status="pending_review"
        )

        logger.warning(
            f"Orphan skill created: '{skill_name}' (reason: {reason}, job: {job_id})"
        )
```

**Deduplication Strategy**:

**Problem**: Prevent duplicate skills from proliferating (e.g., "python", "Python", "PYTHON")

**Solution**: Case-insensitive MERGE with normalization
```cypher
// ✅ CORRECT: Case-insensitive MERGE prevents duplicates
MERGE (s:Skill {name: toLower(trim($skill_name))})
ON CREATE SET
  s.id = randomUUID(),
  s.created_at = datetime()
ON MATCH SET
  s.last_seen_at = datetime()
RETURN s
```

**Anti-Pattern** (DO NOT USE):
```cypher
// ❌ WRONG: Case-sensitive creates duplicates
CREATE (s:Skill {name: $skill_name})  // Creates "Python", "python", "PYTHON"
```

**Orphan Node Schema Update**:
```cypher
// Enhanced Skill node properties for orphan tracking
CREATE (s:Skill {
  id: randomUUID(),
  name: "newframework2025",
  requires_manual_review: true,      // NEW: Flag for admin review
  created_from_job: true,             // NEW: Auto-generated vs taxonomy
  orphan_reason: "no_match",          // NEW: Why orphan was created
  fuzzy_candidates: ["framework", "newfoundland"],  // NEW: Ambiguous matches
  created_at: datetime()
})
```

**Admin Review Dashboard Query**:
```cypher
// Find all orphan skills requiring manual review
MATCH (s:Skill)
WHERE s.requires_manual_review = true
OPTIONAL MATCH (j:Job)-[r:REQUIRES]->(s)
RETURN s.name as skill_name,
       s.orphan_reason as reason,
       s.fuzzy_candidates as suggested_matches,
       count(j) as jobs_requiring_skill,
       s.created_at as created_at
ORDER BY jobs_requiring_skill DESC, created_at DESC
LIMIT 50
```

**Example Output**:
```
skill_name         | reason                | suggested_matches      | jobs_requiring | created_at
-------------------|---------------------- |------------------------|----------------|-------------------
newframework2025   | no_match              | []                     | 23             | 2025-10-22T14:30:00
pyton              | ambiguous_fuzzy_match | ["python", "cython"]   | 5              | 2025-10-22T13:15:00
reaktjs            | ambiguous_fuzzy_match | ["react", "reactjs"]   | 12             | 2025-10-22T12:00:00
```

**Testing Strategy**:
```python
# tests/services/test_skill_matching.py
import pytest

@pytest.mark.asyncio
async def test_exact_match_case_insensitive():
    """Verify exact matching works regardless of case."""
    matcher = SkillMatchingService(neo4j_repo)

    # Create taxonomy skill
    await create_skill(name="Python")

    # Test various casings
    for variant in ["Python", "python", "PYTHON", "PyThOn"]:
        result = await matcher.match_skill(variant, job_id="test-job")

        assert result["match_type"] == "exact"
        assert result["matched_name"] == "Python"  # Canonical name
        assert result["confidence"] == 1.0
        assert result["requires_manual_review"] is False

@pytest.mark.asyncio
async def test_fuzzy_match_typo_correction():
    """Verify fuzzy matching corrects typos."""
    matcher = SkillMatchingService(neo4j_repo)

    await create_skill(name="Python")

    # Typo: "Pyton" (missing 'h')
    result = await matcher.match_skill("Pyton", job_id="test-job")

    assert result["match_type"] == "fuzzy"
    assert result["matched_name"] == "Python"
    assert 0.8 <= result["confidence"] <= 0.9  # Distance 1
    assert result["requires_manual_review"] is False

@pytest.mark.asyncio
async def test_ambiguous_fuzzy_match_creates_orphan():
    """Verify ambiguous matches create orphan for review."""
    matcher = SkillMatchingService(neo4j_repo)

    # Create two similar skills
    await create_skill(name="React")
    await create_skill(name="ReactJS")

    # Input: "Reactjs" could match either (distance 2 for both)
    result = await matcher.match_skill("Reactjs", job_id="test-job")

    assert result["match_type"] == "orphan"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True
    assert set(result["fuzzy_candidates"]) == {"React", "ReactJS"}

@pytest.mark.asyncio
async def test_orphan_creation_no_match():
    """Verify orphan creation when no match found."""
    matcher = SkillMatchingService(neo4j_repo)

    await create_skill(name="Python")

    # Completely unrelated skill
    result = await matcher.match_skill("BlockchainFramework2025", job_id="test-job")

    assert result["match_type"] == "orphan"
    assert result["confidence"] == 0.0
    assert result["requires_manual_review"] is True
    assert result["fuzzy_candidates"] == []

    # Verify orphan node exists in Neo4j
    query = "MATCH (s:Skill {name: 'blockchainframework2025'}) RETURN s"
    orphan = await neo4j_repo.execute_query(query)
    assert orphan[0]["s"]["requires_manual_review"] is True

@pytest.mark.asyncio
async def test_deduplication_prevents_duplicates():
    """Verify MERGE prevents case-variant duplicates."""
    matcher = SkillMatchingService(neo4j_repo)

    # Process same skill with different casings
    for variant in ["Python", "python", "PYTHON"]:
        await matcher.match_skill(variant, job_id=f"job-{variant}")

    # Verify only ONE Skill node exists
    query = """
    MATCH (s:Skill)
    WHERE toLower(s.name) = 'python'
    RETURN count(s) as count
    """
    result = await neo4j_repo.execute_query(query)
    assert result[0]["count"] == 1  # No duplicates created
```

**Performance Considerations**:
- **Exact match**: O(1) with Neo4j index lookup (fast)
- **Fuzzy match**: O(n) where n = taxonomy size (use skill cache to avoid repeated DB queries)
- **Skill cache refresh**: Every 1 hour or after taxonomy updates
- **Batch ingestion**: Refresh cache once before processing CSV, not per skill

**Summary**:
- ✅ Exact matching (case-insensitive) as primary strategy
- ✅ Fuzzy matching (Levenshtein ≤ 2) for typo correction
- ✅ Orphan creation with `requires_manual_review` flag
- ✅ Deduplication via case-insensitive MERGE
- ✅ Admin dashboard query for orphan review
- ✅ Comprehensive test coverage

---

#### PostgreSQL Validation

**User Registration**:
- **Email**: Valid email format (regex validation)
- **Password**: Minimum 8 characters (PRD doesn't specify, use industry standard)
- **Password Hash**: bcrypt with cost factor 12

**Ingestion Job**:
- **file_type**: Must be "skills" or "jobs"
- **status**: Must be one of ["pending", "processing", "completed", "failed"]
- **total_records**: Must be >= 0
- **processed_records**: Must be >= 0 and <= total_records
- **failed_records**: Must be >= 0

**Query History**:
- **query_text**: Non-empty string
- **response_text**: Non-empty string
- **response_time_ms**: Must be > 0

---

### Data Model Pydantic Schemas

#### Request/Response Models

**`models/skill.py`**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SkillBase(BaseModel):
    id: str
    name: str
    level: Optional[int] = Field(None, ge=1, le=5)
    type: Optional[str] = None
    is_software: bool = False
    is_language: bool = False
    description: Optional[str] = None
    wiki_link: Optional[str] = None
    wiki_extract: Optional[str] = None

class SkillCreate(SkillBase):
    embedding: List[float] = Field(..., min_length=384, max_length=384)

class SkillResponse(SkillBase):
    created_at: datetime

    class Config:
        from_attributes = True
```

**`models/job.py`**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    job_id: str
    job_title: str
    location: Optional[str] = None
    salary: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    mean_salary: Optional[float] = None
    description: Optional[str] = None
    nco_code: Optional[str] = None

class JobCreate(JobBase):
    embedding: List[float] = Field(..., min_length=384, max_length=384)
    standardized_skills: List[str]

class JobResponse(JobBase):
    created_at: datetime
    required_skills: Optional[List[str]] = []

    class Config:
        from_attributes = True
```

**`models/user.py`**:
```python
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
import re

class UserCreate(BaseModel):
    """User registration model with secure password requirements."""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters with uppercase, lowercase, digit, and special character"
    )

    @validator('password')
    def validate_password_complexity(cls, v):
        """
        Enforce password complexity requirements.

        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter (A-Z)
        - At least one lowercase letter (a-z)
        - At least one digit (0-9)
        - At least one special character (@$!%*?&#)
        """
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError("Password must contain at least one special character (@$!%*?&#)")

        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

---

## Components

This section describes all major components in the backend architecture, organized by layer.

---

### 5.1 API Layer (FastAPI Endpoints)

The API layer exposes REST endpoints organized by domain. All endpoints follow RESTful conventions and return JSON responses.

#### **Authentication Endpoints**

**Router**: `/api/auth`
**Module**: `app/api/auth.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/auth/register` | User registration | `UserCreate` | `UserResponse` |
| POST | `/auth/login` | User login | `UserLogin` | `TokenResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, auth_service: AuthService = Depends()):
    """Register a new user account."""
    return await auth_service.register_user(user_data)

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, auth_service: AuthService = Depends()):
    """Authenticate user and return JWT token."""
    return await auth_service.login_user(credentials)
```

---

#### **Ingestion Endpoints**

**Router**: `/api/ingest`
**Module**: `app/api/ingest.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/ingest/skills` | Upload skills CSV | `UploadFile` | `IngestionJobResponse` |
| POST | `/ingest/jobs` | Upload jobs CSV | `UploadFile` | `IngestionJobResponse` |
| GET | `/ingest/status/{job_id}` | Check ingestion status | - | `IngestionStatusResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, UploadFile, File, Depends
from app.models.ingestion import IngestionJobResponse, IngestionStatusResponse
from app.services.ingestion_service import IngestionService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

@router.post("/skills", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_skills_csv(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Upload and process skills taxonomy CSV."""
    return await ingestion_service.start_skills_ingestion(file, current_user)

@router.post("/jobs", response_model=IngestionJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_jobs_csv(
    file: UploadFile = File(...),
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Upload and process jobs taxonomy CSV."""
    return await ingestion_service.start_jobs_ingestion(file, current_user)

@router.get("/status/{job_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    job_id: str,
    current_user: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """Poll ingestion job status and progress."""
    return await ingestion_service.get_job_status(job_id, current_user)
```

---

#### **Query Endpoint**

**Router**: `/api/query`
**Module**: `app/api/query.py`

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/query/ask` | Conversational AI query | `QueryRequest` | `QueryResponse` |

**Example Implementation**:
```python
from fastapi import APIRouter, Depends
from app.models.query import QueryRequest, QueryResponse
from app.services.langgraph_service import LangGraphService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/query", tags=["query"])

@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    query_data: QueryRequest,
    current_user: str = Depends(get_current_user),
    langgraph_service: LangGraphService = Depends()
):
    """Process natural language query through LangGraph RAG workflow."""
    return await langgraph_service.execute_query(query_data, current_user)
```

---

### 5.2 LangGraph Agent Layer

The LangGraph layer orchestrates the RAG workflow using a StateGraph with 5 specialized nodes.

#### **StateGraph Definition**

**Module**: `app/agents/graph.py`

```python
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from app.agents.nodes import (
    query_understanding_node,
    vector_search_node,
    graph_traversal_node,
    context_construction_node,
    response_generation_node
)

class GraphRAGState(BaseModel):
    """
    Type-safe shared state for the RAG workflow.

    Uses Pydantic for runtime validation to prevent silent failures:
    - Typos in field names raise validation errors immediately
    - Type mismatches are caught at runtime
    - Required vs optional fields are enforced
    - Extra fields are forbidden (catches typos like 'user_qeury')
    """

    # Input fields (required)
    user_query: str = Field(..., min_length=1, description="Original user query text")
    user_id: str = Field(..., description="UUID of authenticated user")

    # Intermediate state (set by nodes, optional initially)
    intent: Optional[str] = Field(default=None, description="Detected query intent")
    entities: List[str] = Field(default_factory=list, description="Extracted named entities")
    vector_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Vector similarity search results from Neo4j"
    )
    graph_context: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Graph traversal context from Neo4j"
    )
    constructed_context: Optional[str] = Field(
        default=None,
        description="Constructed context string for LLM prompt"
    )

    # Output field (set by final node)
    final_response: Optional[str] = Field(
        default=None,
        description="Generated response from LLM"
    )

    # Metadata (optional)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (timestamps, costs, etc.)"
    )

    class Config:
        """Pydantic configuration for strict validation."""
        extra = "forbid"  # Raise error on unknown fields (catches typos)
        validate_assignment = True  # Validate on field assignment, not just initialization
        arbitrary_types_allowed = True  # Allow Any types for flexibility

    @validator('intent')
    def validate_intent(cls, v):
        """Ensure intent is one of the expected types."""
        if v is not None:
            valid_intents = ["skill_lookup", "job_search", "comparison", "explanation", "general"]
            if v not in valid_intents:
                raise ValueError(
                    f"Invalid intent: '{v}'. Must be one of {valid_intents}"
                )
        return v

    @validator('user_query')
    def validate_query_not_empty(cls, v):
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError("user_query cannot be empty or whitespace")
        return v.strip()

def create_rag_workflow() -> StateGraph:
    """Create and compile the RAG StateGraph with type-safe state."""
    workflow = StateGraph(GraphRAGState)

    # Add nodes
    workflow.add_node("understand_query", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)
    workflow.add_node("construct_context", context_construction_node)
    workflow.add_node("generate_response", response_generation_node)

    # Define edges (linear flow for MVP)
    workflow.set_entry_point("understand_query")
    workflow.add_edge("understand_query", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")
    workflow.add_edge("graph_traversal", "construct_context")
    workflow.add_edge("construct_context", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()
```

**Benefits of Pydantic over TypedDict**:

**Problem with TypedDict** (Previous Implementation):
```python
# ❌ TypedDict allows silent failures
class GraphRAGState(TypedDict):
    user_query: str
    intent: str

state = GraphRAGState(user_query="test", intnet="skill")  # Typo: 'intnet'
# Result: No error! Typo goes unnoticed, causes bugs later
print(state["intent"])  # KeyError at runtime (hard to debug)
```

**Solution with Pydantic** (Current Implementation):
```python
# ✅ Pydantic catches typos immediately
class GraphRAGState(BaseModel):
    user_query: str
    intent: Optional[str] = None

    class Config:
        extra = "forbid"  # Catch typos

try:
    state = GraphRAGState(user_query="test", intnet="skill")  # Typo: 'intnet'
except ValidationError as e:
    # Result: Immediate error with clear message!
    # pydantic.ValidationError: 1 validation error for GraphRAGState
    # intnet
    #   extra fields not permitted (type=value_error.extra)
    print(e)
```

**Runtime Type Safety Examples**:

**Example 1: Prevent Type Mismatches**
```python
# ❌ TypedDict: Wrong type accepted silently
state_dict = {"user_query": "test", "entities": "should be list"}  # Wrong type!
# No error until you try to iterate

# ✅ Pydantic: Immediate validation error
try:
    state = GraphRAGState(user_query="test", entities="should be list")
except ValidationError as e:
    # pydantic.ValidationError: entities
    #   value is not a valid list (type=type_error.list)
    print(e)
```

**Example 2: Intent Validation**
```python
# ❌ TypedDict: Invalid intent accepted
state_dict = {"user_query": "test", "intent": "invalid_intent"}
# Fails later in business logic with cryptic errors

# ✅ Pydantic: Custom validator catches invalid values
try:
    state = GraphRAGState(user_query="test", intent="invalid_intent")
except ValidationError as e:
    # pydantic.ValidationError: intent
    #   Invalid intent: 'invalid_intent'. Must be one of [...] (type=value_error)
    print(e)
```

**Example 3: Assignment Validation**
```python
# With validate_assignment=True, even field updates are validated
state = GraphRAGState(user_query="test query", user_id="user-123")

# ❌ TypedDict: Any assignment allowed
# state["entities"] = "not a list"  # No error until iteration

# ✅ Pydantic: Assignment validation
try:
    state.entities = "not a list"  # Wrong type!
except ValidationError as e:
    # pydantic.ValidationError: entities
    #   value is not a valid list (type=type_error.list)
    print(e)
```

**Node Return Value Pattern**:

**Pattern 1: Partial Updates** (Recommended for LangGraph)
```python
async def query_understanding_node(state: GraphRAGState) -> dict:
    """Return only the fields that changed."""
    # LangGraph merges the dict into the existing state
    return {
        "intent": "skill_lookup",
        "entities": ["Python", "FastAPI"],
        "metadata": {**state.metadata, "node": "query_understanding"}
    }
    # Pydantic validates these updates before merging
```

**Pattern 2: Full State Return** (Alternative)
```python
async def query_understanding_node(state: GraphRAGState) -> GraphRAGState:
    """Return updated full state object."""
    state.intent = "skill_lookup"
    state.entities = ["Python", "FastAPI"]
    state.metadata["node"] = "query_understanding"
    return state
    # Pydantic validates on each field assignment
```

**Error Handling in Nodes**:
```python
async def safe_node_wrapper(state: GraphRAGState) -> dict:
    """Wrapper to catch validation errors in node logic."""
    try:
        # Node logic that might have typos or type errors
        updates = {
            "intent": "skill_lookup",
            "entites": ["Python"]  # Typo: 'entites'
        }

        # Validate updates before returning
        temp_state = state.copy(update=updates)  # Pydantic validates here

        return updates

    except ValidationError as e:
        logger.error(f"State validation failed: {e}")
        return {
            "final_response": "Internal error: Invalid state update",
            "metadata": {"error": str(e), "node": "query_understanding"}
        }
```

**Testing Strategy**:

**Test 1: Typo Detection**
```python
# tests/agents/test_state_validation.py
import pytest
from pydantic import ValidationError
from app.agents.graph import GraphRAGState

def test_extra_fields_rejected():
    """Verify typos in field names are caught."""
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            intnet="skill"  # Typo: should be 'intent'
        )

    assert "extra fields not permitted" in str(exc_info.value)
    assert "intnet" in str(exc_info.value)

def test_typo_in_assignment():
    """Verify typos in field assignment are caught."""
    state = GraphRAGState(user_query="test", user_id="user-123")

    with pytest.raises(AttributeError):
        state.intnet = "skill"  # Typo: no such attribute
```

**Test 2: Type Validation**
```python
def test_type_mismatches_rejected():
    """Verify wrong types are caught immediately."""
    # Test 1: entities must be list
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            entities="should be list"  # Wrong type!
        )

    assert "value is not a valid list" in str(exc_info.value)

    # Test 2: vector_results must be list of dicts
    with pytest.raises(ValidationError):
        GraphRAGState(
            user_query="test",
            user_id="user-123",
            vector_results=["wrong", "type"]  # Should be list of dicts
        )
```

**Test 3: Intent Validation**
```python
def test_intent_validation():
    """Verify custom intent validator works."""
    valid_intents = ["skill_lookup", "job_search", "comparison", "explanation", "general"]

    # Valid intents should work
    for intent in valid_intents:
        state = GraphRAGState(user_query="test", user_id="user-123", intent=intent)
        assert state.intent == intent

    # Invalid intent should fail
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_query="test", user_id="user-123", intent="invalid")

    assert "Invalid intent" in str(exc_info.value)
    assert valid_intents[0] in str(exc_info.value)  # Shows valid options
```

**Test 4: Required Fields**
```python
def test_required_fields_enforced():
    """Verify required fields cannot be omitted."""
    # Missing user_query
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_id="user-123")

    assert "user_query" in str(exc_info.value)
    assert "field required" in str(exc_info.value).lower()

    # Missing user_id
    with pytest.raises(ValidationError):
        GraphRAGState(user_query="test")
```

**Test 5: Empty Query Validation**
```python
def test_empty_query_rejected():
    """Verify user_query cannot be empty or whitespace."""
    # Empty string
    with pytest.raises(ValidationError) as exc_info:
        GraphRAGState(user_query="", user_id="user-123")

    assert "at least 1 characters" in str(exc_info.value).lower()

    # Whitespace only
    with pytest.raises(ValidationError):
        GraphRAGState(user_query="   ", user_id="user-123")

    # Should be stripped and validated
```

**Test 6: Node Return Value Validation**
```python
@pytest.mark.asyncio
async def test_node_updates_validated():
    """Verify node return values are validated before merging."""
    state = GraphRAGState(user_query="test query", user_id="user-123")

    # Simulate node returning invalid update
    invalid_updates = {
        "intent": "invalid_intent",  # Will fail validator
        "entities": ["Python"]
    }

    with pytest.raises(ValidationError):
        # This would happen in LangGraph when merging updates
        updated_state = state.copy(update=invalid_updates)
```

**Migration Path from TypedDict**:

If you have existing code using TypedDict:

1. **Update imports**:
   ```python
   # Before
   from typing import TypedDict

   # After
   from pydantic import BaseModel, Field, validator
   ```

2. **Update class definition**:
   ```python
   # Before
   class GraphRAGState(TypedDict):
       user_query: str

   # After
   class GraphRAGState(BaseModel):
       user_query: str = Field(..., min_length=1)
       class Config:
           extra = "forbid"
   ```

3. **Update field access** (dict-style to attribute-style):
   ```python
   # Before (works with both)
   query = state["user_query"]

   # After (preferred with Pydantic)
   query = state.user_query
   ```

4. **Add validators** for business logic constraints:
   ```python
   @validator('intent')
   def validate_intent(cls, v):
       if v not in valid_intents:
           raise ValueError(f"Invalid intent: {v}")
       return v
   ```

**Summary**:
- ✅ Runtime type validation prevents silent failures
- ✅ Typo detection with `extra="forbid"` catches field name errors
- ✅ Custom validators enforce business logic constraints
- ✅ Clear error messages aid debugging
- ✅ Assignment validation with `validate_assignment=True`
- ✅ Comprehensive test coverage for validation logic

---

#### **Node 1: Query Understanding**

**Purpose**: Parse user query to extract intent, entities, and query type.
**Module**: `app/agents/nodes/query_understanding.py`

**Logic**:
1. Use lightweight NLP to detect intent (skill_lookup, job_search, comparison, explanation)
2. Extract named entities (skill names, job titles, locations, companies)
3. Classify query complexity (simple, moderate, complex)
4. Set query parameters (k for vector search, depth for graph traversal)

**Example**:
```python
from pydantic import ValidationError
import re
from app.agents.graph import GraphRAGState

async def query_understanding_node(state: GraphRAGState) -> dict:
    """
    Analyze user query to extract intent and entities.

    Args:
        state: Type-safe GraphRAGState Pydantic model

    Returns:
        dict: Updates to apply to state (Pydantic will validate)

    Raises:
        ValidationError: If state updates violate schema constraints
    """
    user_query = state.user_query.lower()  # Type-safe field access

    # Intent detection (simple keyword-based for MVP)
    intent = "general"
    if any(kw in user_query for kw in ["what is", "explain", "tell me about"]):
        intent = "explanation"
    elif any(kw in user_query for kw in ["jobs", "openings", "positions"]):
        intent = "job_search"
    elif any(kw in user_query for kw in ["skills", "technologies", "tools"]):
        intent = "skill_lookup"
    elif any(kw in user_query for kw in ["compare", "difference", "vs"]):
        intent = "comparison"

    # Entity extraction (basic regex for MVP)
    entities = extract_entities(user_query)

    # Update state
    state["intent"] = intent
    state["entities"] = entities
    state["metadata"] = {
        "query_length": len(user_query),
        "intent_confidence": 0.8,  # Placeholder for future ML model
        "k_results": 10,  # Top-k for vector search
        "graph_depth": 2  # Traversal depth
    }

    return state

def extract_entities(query: str) -> List[str]:
    """Extract potential skill/job entities from query."""
    # Placeholder: Simple tokenization (replace with NER model in future)
    tokens = re.findall(r'\b[a-z]{3,}\b', query)
    return [t for t in tokens if t not in {"what", "the", "for", "with"}]
```

---

#### **Node 2: Vector Search**

**Purpose**: Retrieve top-k most similar nodes from Neo4j using vector embeddings.
**Module**: `app/agents/nodes/vector_search.py`

**Logic**:
1. Generate embedding for user query using HuggingFace model
2. Perform vector similarity search in Neo4j (cosine similarity)
3. Retrieve top-k Skill and Job nodes
4. Return results with similarity scores

**Example**:
```python
from typing import Dict, Any, List
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.embedding_service import EmbeddingService

async def vector_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Perform vector similarity search in Neo4j."""
    user_query = state["user_query"]
    k = state["metadata"]["k_results"]

    # Generate query embedding
    embedding_service = EmbeddingService()
    query_embedding = await embedding_service.generate_embedding(user_query)

    # Search Neo4j
    neo4j_repo = Neo4jRepository()
    skill_results = await neo4j_repo.vector_search_skills(query_embedding, k=k)
    job_results = await neo4j_repo.vector_search_jobs(query_embedding, k=k//2)

    # Combine results
    state["vector_results"] = {
        "skills": skill_results,
        "jobs": job_results
    }

    return state
```

**Neo4j Cypher Query Example**:
```cypher
// Vector search for skills
CALL db.index.vector.queryNodes('skill_embedding_idx', $k, $query_embedding)
YIELD node, score
MATCH (node:Skill)
OPTIONAL MATCH (node)-[:BELONGS_TO_CATEGORY]->(cat:Category)
OPTIONAL MATCH (node)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
RETURN node.id AS skill_id, node.name AS skill_name,
       node.description AS description, score,
       cat.category_name AS category, sub.subcategory_name AS subcategory
ORDER BY score DESC
LIMIT $k
```

---

#### **Node 3: Graph Traversal**

**Purpose**: Expand context by traversing relationships around retrieved nodes.
**Module**: `app/agents/nodes/graph_traversal.py`

**Logic**:
1. For each top-k result from vector search, traverse outgoing relationships
2. Retrieve connected nodes (Skills → Categories, Jobs → Skills, Jobs → Companies)
3. Apply depth limit (1-2 hops for MVP)
4. Return enriched context with relationship metadata

**Example**:
```python
from typing import Dict, Any, List

async def graph_traversal_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse graph relationships to enrich context."""
    vector_results = state["vector_results"]
    depth = state["metadata"]["graph_depth"]

    neo4j_repo = Neo4jRepository()
    graph_context = []

    # Traverse from top skills
    for skill in vector_results["skills"][:5]:
        skill_context = await neo4j_repo.traverse_skill_context(
            skill_id=skill["skill_id"],
            depth=depth
        )
        graph_context.append(skill_context)

    # Traverse from top jobs
    for job in vector_results["jobs"][:3]:
        job_context = await neo4j_repo.traverse_job_context(
            job_id=job["job_id"],
            depth=depth
        )
        graph_context.append(job_context)

    state["graph_context"] = graph_context
    return state
```

**Neo4j Cypher Query Example**:
```cypher
// Traverse skill context
MATCH (s:Skill {id: $skill_id})
OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
OPTIONAL MATCH (s)-[:SIMILAR_TO]-(similar:Skill)
OPTIONAL MATCH (j:Job)-[req:REQUIRES]->(s)
RETURN s, cat, sub, collect(distinct similar)[0..5] as related_skills,
       collect(distinct {job: j, similarity: req.similarity_score})[0..3] as requiring_jobs
```

---

#### **Node 4: Context Construction**

**Purpose**: Merge vector search results + graph context into LLM-optimized text.
**Module**: `app/agents/nodes/context_construction.py`

**Logic**:
1. Format vector search results as structured text
2. Merge graph traversal relationships
3. Apply token limits (max 3000 tokens for context)
4. Structure context with clear sections

**Example**:
```python
from typing import Dict, Any

async def context_construction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Construct LLM context from vector + graph results."""
    vector_results = state["vector_results"]
    graph_context = state["graph_context"]

    context_parts = []

    # Section 1: Top matching skills
    context_parts.append("## Relevant Skills\n")
    for skill in vector_results["skills"][:5]:
        context_parts.append(
            f"- **{skill['skill_name']}** (Match: {skill['score']:.2f})\n"
            f"  Category: {skill['category']}, Subcategory: {skill['subcategory']}\n"
            f"  Description: {skill['description'][:200]}...\n"
        )

    # Section 2: Related jobs
    context_parts.append("\n## Related Job Postings\n")
    for job in vector_results["jobs"][:3]:
        context_parts.append(
            f"- **{job['job_title']}** at {job['company_name']}\n"
            f"  Location: {job['location']}, Salary: {job['salary']}\n"
            f"  Description: {job['description'][:200]}...\n"
        )

    # Section 3: Graph relationships
    context_parts.append("\n## Connections & Relationships\n")
    for ctx in graph_context[:3]:
        context_parts.append(format_graph_context(ctx))

    constructed_context = "\n".join(context_parts)

    # Apply token limit (rough estimate: 4 chars = 1 token)
    if len(constructed_context) > 12000:  # ~3000 tokens
        constructed_context = constructed_context[:12000] + "\n... (context truncated)"

    state["constructed_context"] = constructed_context
    return state

def format_graph_context(ctx: Dict[str, Any]) -> str:
    """Format graph traversal results into readable text."""
    # Implementation depends on graph structure returned
    return f"Context: {ctx}\n"
```

---

#### **Node 5: Response Generation**

**Purpose**: Generate final conversational response using OpenRouter LLM.
**Module**: `app/agents/nodes/response_generation.py`

**Logic**:
1. Build prompt with system instructions + constructed context + user query
2. Call OpenRouter API (meta-llama/llama-3.3-8b-instruct:free)
3. Parse LLM response
4. Return structured response with citations

**Example**:
```python
from typing import Dict, Any
from app.services.openrouter_service import OpenRouterService

async def response_generation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate final response using OpenRouter LLM."""
    user_query = state["user_query"]
    context = state["constructed_context"]

    # Build prompt
    system_prompt = (
        "You are a helpful AI assistant specialized in skills and job market analysis. "
        "Use the provided context to answer the user's question accurately and concisely. "
        "If the context doesn't contain enough information, say so clearly."
    )

    user_prompt = f"""Context:
{context}

User Question: {user_query}

Please provide a helpful, accurate answer based on the context above."""

    # Call OpenRouter
    openrouter_service = OpenRouterService()
    llm_response = await openrouter_service.generate_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=500,
        temperature=0.7
    )

    state["final_response"] = llm_response["text"]
    state["metadata"]["tokens_used"] = llm_response["usage"]["total_tokens"]
    state["metadata"]["model"] = "meta-llama/llama-3.3-8b-instruct:free"

    return state
```

---

### 5.3 Service Layer

The service layer contains business logic and orchestrates repository operations.

#### **AuthService**

**Module**: `app/services/auth_service.py`

**Responsibilities**:
- User registration with password hashing (bcrypt)
- User login with JWT token generation
- Token validation and decoding

**Key Methods**:
```python
class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """Register new user with hashed password."""
        # Check if user exists
        # Hash password with bcrypt
        # Create user in PostgreSQL
        # Return UserResponse
        pass

    async def login_user(self, credentials: UserLogin) -> TokenResponse:
        """Authenticate user and return JWT token."""
        # Verify credentials
        # Generate JWT with 24h expiry
        # Return TokenResponse
        pass

    async def verify_token(self, token: str) -> str:
        """Decode JWT and return user_id."""
        # Decode JWT
        # Validate expiry
        # Return user_id
        pass
```

---

#### **IngestionService**

**Module**: `app/services/ingestion_service.py`

**Responsibilities**:
- CSV file validation and parsing
- Batch processing with progress tracking
- Neo4j graph creation
- PostgreSQL job tracking

**Key Methods**:
```python
class IngestionService:
    def __init__(
        self,
        neo4j_repo: Neo4jRepository,
        ingestion_repo: IngestionJobRepository,
        embedding_service: EmbeddingService
    ):
        self.neo4j_repo = neo4j_repo
        self.ingestion_repo = ingestion_repo
        self.embedding_service = embedding_service

    async def start_skills_ingestion(
        self, file: UploadFile, user_id: str
    ) -> IngestionJobResponse:
        """Start skills CSV ingestion job."""
        # Validate CSV format
        # Create IngestionJob in PostgreSQL
        # Process in batches (1000 rows)
        # Generate embeddings
        # Create Skill nodes + relationships in Neo4j
        # Update job progress
        pass

    async def start_jobs_ingestion(
        self, file: UploadFile, user_id: str
    ) -> IngestionJobResponse:
        """Start jobs CSV ingestion job."""
        # Similar to skills ingestion
        # Parse skill associations
        # Create Job, Company, Location nodes
        # Create REQUIRES relationships with similarity scores
        pass

    async def get_job_status(
        self, job_id: str, user_id: str
    ) -> IngestionStatusResponse:
        """Get ingestion job status and progress."""
        # Query IngestionJob from PostgreSQL
        # Return status, progress, batch info
        pass
```

---

#### **LangGraphService**

**Module**: `app/services/langgraph_service.py`

**Responsibilities**:
- Execute RAG workflow via LangGraph StateGraph
- Log query history to PostgreSQL
- Return structured response

**Key Methods**:
```python
class LangGraphService:
    def __init__(
        self,
        query_repo: QueryHistoryRepository,
        rag_workflow: StateGraph
    ):
        self.query_repo = query_repo
        self.rag_workflow = rag_workflow

    async def execute_query(
        self, query_data: QueryRequest, user_id: str
    ) -> QueryResponse:
        """Execute RAG workflow and return response."""
        # Initialize state
        initial_state = {
            "user_query": query_data.query,
            "user_id": user_id,
            "metadata": {}
        }

        # Execute workflow
        final_state = await self.rag_workflow.ainvoke(initial_state)

        # Log to PostgreSQL
        await self.query_repo.create_query_history(
            user_id=user_id,
            query_text=query_data.query,
            response_text=final_state["final_response"],
            metadata=final_state["metadata"]
        )

        # Return response
        return QueryResponse(
            response=final_state["final_response"],
            metadata=final_state["metadata"]
        )
```

---

#### **EmbeddingService**

**Module**: `app/services/embedding_service.py`

**Responsibilities**:
- Generate embeddings using HuggingFace Transformers
- Cache embeddings for performance (future enhancement)

**Key Methods**:
```python
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate 384-dimensional embedding for text."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        embeddings = self.model.encode(texts, convert_to_tensor=False, batch_size=32)
        return embeddings.tolist()
```

---

#### **OpenRouterService**

**Module**: `app/services/openrouter_service.py`

**Responsibilities**:
- Call OpenRouter API for LLM completions
- Handle retries and rate limiting

**Key Methods**:
```python
import httpx
from typing import Dict, Any

class OpenRouterService:
    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.3-8b-instruct:free"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate LLM completion via OpenRouter."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
            )
            response.raise_for_status()
            result = response.json()

            return {
                "text": result["choices"][0]["message"]["content"],
                "usage": result["usage"]
            }
```

---

### 5.4 Repository Layer

The repository layer handles direct database operations (PostgreSQL via Prisma, Neo4j via driver).

#### **UserRepository**

**Module**: `app/repositories/user_repository.py`

**Responsibilities**: CRUD operations for User table in PostgreSQL

**Key Methods**:
```python
from prisma import Prisma
from prisma.models import User

class UserRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_user(self, email: str, password_hash: str) -> User:
        """Create new user in PostgreSQL."""
        return await self.prisma.user.create(
            data={"email": email, "password_hash": password_hash}
        )

    async def get_user_by_email(self, email: str) -> User | None:
        """Find user by email."""
        return await self.prisma.user.find_unique(where={"email": email})

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Find user by ID."""
        return await self.prisma.user.find_unique(where={"id": user_id})
```

---

#### **IngestionJobRepository**

**Module**: `app/repositories/ingestion_job_repository.py`

**Responsibilities**: Track CSV ingestion jobs in PostgreSQL

**Key Methods**:
```python
from prisma.models import IngestionJob

class IngestionJobRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_job(
        self, user_id: str, file_type: str, total_records: int
    ) -> IngestionJob:
        """Create new ingestion job."""
        return await self.prisma.ingestionjob.create(
            data={
                "user_id": user_id,
                "file_type": file_type,
                "status": "pending",
                "total_records": total_records
            }
        )

    async def update_progress(
        self, job_id: str, processed_records: int, status: str
    ) -> IngestionJob:
        """Update job progress."""
        return await self.prisma.ingestionjob.update(
            where={"id": job_id},
            data={"processed_records": processed_records, "status": status}
        )

    async def get_job(self, job_id: str) -> IngestionJob | None:
        """Get job by ID."""
        return await self.prisma.ingestionjob.find_unique(where={"id": job_id})
```

---

#### **QueryHistoryRepository**

**Module**: `app/repositories/query_history_repository.py`

**Responsibilities**: Log query history in PostgreSQL

**Key Methods**:
```python
from prisma.models import QueryHistory
import json

class QueryHistoryRepository:
    def __init__(self, prisma: Prisma):
        self.prisma = prisma

    async def create_query_history(
        self, user_id: str, query_text: str, response_text: str, metadata: dict
    ) -> QueryHistory:
        """Log query to history."""
        return await self.prisma.queryhistory.create(
            data={
                "user_id": user_id,
                "query_text": query_text,
                "response_text": response_text,
                "metadata": json.dumps(metadata)
            }
        )

    async def get_user_history(self, user_id: str, limit: int = 20) -> list[QueryHistory]:
        """Get user's query history."""
        return await self.prisma.queryhistory.find_many(
            where={"user_id": user_id},
            order={"created_at": "desc"},
            take=limit
        )
```

---

#### **Neo4jRepository**

**Module**: `app/repositories/neo4j_repository.py`

**Responsibilities**: Neo4j graph operations (CRUD, vector search, traversal)

**Key Methods**:
```python
from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any

class Neo4jRepository:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def create_skill_node(self, skill_data: dict) -> None:
        """Create Skill node in Neo4j."""
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (s:Skill {
                    id: $id, name: $name, level: $level, type: $type,
                    is_software: $is_software, is_language: $is_language,
                    description: $description, description_source: $description_source,
                    version: $version, latest_version: $latest_version,
                    wiki_link: $wiki_link, wiki_extract: $wiki_extract,
                    embedding: $embedding, created_at: datetime()
                })
                """,
                **skill_data
            )

    async def vector_search_skills(
        self, query_embedding: List[float], k: int = 10
    ) -> List[Dict[str, Any]]:
        """Vector similarity search for skills."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes('skill_embedding_idx', $k, $query_embedding)
                YIELD node, score
                MATCH (node:Skill)
                OPTIONAL MATCH (node)-[:BELONGS_TO_CATEGORY]->(cat:Category)
                OPTIONAL MATCH (node)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
                RETURN node.id AS skill_id, node.name AS skill_name,
                       node.description AS description, score,
                       cat.category_name AS category, sub.subcategory_name AS subcategory
                ORDER BY score DESC
                """,
                k=k, query_embedding=query_embedding
            )
            return [dict(record) async for record in result]

    async def traverse_skill_context(
        self, skill_id: str, depth: int = 2
    ) -> Dict[str, Any]:
        """Traverse skill relationships."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (s:Skill {id: $skill_id})
                OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
                OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
                OPTIONAL MATCH (s)-[:SIMILAR_TO]-(similar:Skill)
                OPTIONAL MATCH (j:Job)-[req:REQUIRES]->(s)
                RETURN s, cat, sub,
                       collect(distinct similar)[0..5] as related_skills,
                       collect(distinct {job: j, similarity: req.similarity_score})[0..3] as requiring_jobs
                """,
                skill_id=skill_id
            )
            return dict(await result.single())
```

---

### 5.5 Middleware Components

#### **CORS Middleware**

**Module**: `app/middleware/cors.py`

```python
from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    """Add CORS middleware for frontend communication."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],  # React dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
```

---

#### **Authentication Middleware**

**Module**: `app/middleware/auth.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends()
) -> str:
    """Validate JWT and return user_id."""
    token = credentials.credentials
    try:
        user_id = await auth_service.verify_token(token)
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
```

---

#### **Error Handling Middleware**

**Module**: `app/middleware/error_handler.py`

```python
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc)
        }
    )
```

---

## Source Tree

This section defines the complete directory structure and file organization for the backend monorepo.

---

### 6.1 Project Structure Overview

```
backend/
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Configuration management
│   ├── dependencies.py           # Dependency injection setup
│   │
│   ├── api/                      # API layer (FastAPI routers)
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication endpoints
│   │   ├── ingest.py             # CSV ingestion endpoints
│   │   └── query.py              # Query/RAG endpoint
│   │
│   ├── agents/                   # LangGraph agent layer
│   │   ├── __init__.py
│   │   ├── graph.py              # StateGraph definition
│   │   └── nodes/                # LangGraph node implementations
│   │       ├── __init__.py
│   │       ├── query_understanding.py
│   │       ├── vector_search.py
│   │       ├── graph_traversal.py
│   │       ├── context_construction.py
│   │       └── response_generation.py
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py       # User auth & JWT management
│   │   ├── ingestion_service.py  # CSV processing
│   │   ├── langgraph_service.py  # RAG workflow orchestration
│   │   ├── embedding_service.py  # HuggingFace embeddings
│   │   └── openrouter_service.py # LLM API client
│   │
│   ├── repositories/             # Data access layer
│   │   ├── __init__.py
│   │   ├── user_repository.py    # PostgreSQL user operations
│   │   ├── ingestion_job_repository.py
│   │   ├── query_history_repository.py
│   │   └── neo4j_repository.py   # Neo4j graph operations
│   │
│   ├── models/                   # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── user.py               # User schemas
│   │   ├── ingestion.py          # Ingestion schemas
│   │   └── query.py              # Query schemas
│   │
│   ├── middleware/               # FastAPI middleware
│   │   ├── __init__.py
│   │   ├── cors.py               # CORS configuration
│   │   ├── auth.py               # JWT authentication
│   │   └── error_handler.py      # Global error handling
│   │
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── password.py           # Password hashing (bcrypt)
│       ├── jwt.py                # JWT encode/decode
│       ├── csv_validator.py      # CSV validation utilities
│       └── logger.py             # Logging configuration
│
├── prisma/                       # Prisma ORM (PostgreSQL)
│   ├── schema.prisma             # Database schema definition
│   └── migrations/               # Database migrations
│       └── migration_lock.toml
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   │
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_auth_service.py
│   │   ├── test_embedding_service.py
│   │   └── test_csv_validator.py
│   │
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api_auth.py
│   │   ├── test_api_ingestion.py
│   │   ├── test_api_query.py
│   │   └── test_neo4j_operations.py
│   │
│   └── e2e/                      # End-to-end tests
│       ├── __init__.py
│       ├── test_full_ingestion_flow.py
│       └── test_full_query_flow.py
│
├── scripts/                      # Utility scripts
│   ├── seed_neo4j.py             # Seed Neo4j with sample data
│   ├── setup_indexes.py          # Create Neo4j indexes
│   └── reset_databases.py        # Reset both databases (dev only)
│
├── docs/                         # Project documentation
│   ├── architecture.md           # This document
│   ├── api.md                    # API documentation
│   └── deployment.md             # Deployment guide
│
├── .github/                      # GitHub configuration
│   └── workflows/
│       ├── ci.yml                # CI pipeline (tests, lint)
│       └── cd.yml                # CD pipeline (deploy)
│
├── .env.example                  # Example environment variables
├── .env                          # Environment variables (gitignored)
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Python project metadata
├── pytest.ini                    # Pytest configuration
├── Dockerfile                    # Docker container definition
├── docker-compose.yml            # Multi-container orchestration
└── README.md                     # Project README
```

---

### 6.2 Core Files

#### **`app/main.py`** - FastAPI Application Entry Point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prisma import Prisma
from neo4j import AsyncGraphDatabase

from app.config import settings
from app.api import auth, ingest, query
from app.middleware.cors import add_cors_middleware
from app.middleware.error_handler import (
    validation_exception_handler,
    global_exception_handler
)
from fastapi.exceptions import RequestValidationError

# Global database clients
prisma_client = Prisma()
neo4j_driver = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage database connections lifecycle."""
    global neo4j_driver

    # Startup: Connect to databases
    await prisma_client.connect()
    neo4j_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
    )

    yield

    # Shutdown: Close connections
    await prisma_client.disconnect()
    await neo4j_driver.close()

# Create FastAPI app
app = FastAPI(
    title="Graph RAG API",
    description="Knowledge Graph RAG System for Skills & Jobs",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
add_cors_middleware(app)

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Register routers
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(query.router)

# Health check endpoint
@app.get("/health")
async def health_check():
    """API health check."""
    return {
        "status": "healthy",
        "service": "graph-rag-api",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Development only
    )
```

---

#### **`app/config.py`** - Configuration Management

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_ENV: str = "development"  # development, staging, production

    # Database - PostgreSQL
    DATABASE_URL: str

    # Database - Neo4j
    NEO4J_URI: str
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str

    # Security
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # OpenRouter API
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-8b-instruct:free"

    # Embedding Model
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # Ingestion Settings
    BATCH_SIZE: int = 1000
    MAX_CSV_SIZE_MB: int = 100

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

settings = get_settings()
```

---

#### **`app/dependencies.py`** - Dependency Injection

```python
from functools import lru_cache
from prisma import Prisma
from neo4j import AsyncGraphDatabase

from app.config import settings
from app.repositories.user_repository import UserRepository
from app.repositories.ingestion_job_repository import IngestionJobRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.auth_service import AuthService
from app.services.ingestion_service import IngestionService
from app.services.langgraph_service import LangGraphService
from app.services.embedding_service import EmbeddingService
from app.services.openrouter_service import OpenRouterService
from app.agents.graph import create_rag_workflow

# Database clients (singleton pattern)
_prisma_client = None
_neo4j_driver = None

def get_prisma() -> Prisma:
    """Get Prisma client singleton."""
    global _prisma_client
    if _prisma_client is None:
        _prisma_client = Prisma()
    return _prisma_client

def get_neo4j_driver():
    """Get Neo4j driver singleton."""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
    return _neo4j_driver

# Repository dependencies
def get_user_repository() -> UserRepository:
    return UserRepository(get_prisma())

def get_ingestion_job_repository() -> IngestionJobRepository:
    return IngestionJobRepository(get_prisma())

def get_query_history_repository() -> QueryHistoryRepository:
    return QueryHistoryRepository(get_prisma())

def get_neo4j_repository() -> Neo4jRepository:
    return Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )

# Service dependencies
def get_auth_service() -> AuthService:
    return AuthService(get_user_repository())

def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(model_name=settings.EMBEDDING_MODEL)

def get_openrouter_service() -> OpenRouterService:
    return OpenRouterService(
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.OPENROUTER_MODEL
    )

def get_ingestion_service() -> IngestionService:
    return IngestionService(
        neo4j_repo=get_neo4j_repository(),
        ingestion_repo=get_ingestion_job_repository(),
        embedding_service=get_embedding_service()
    )

@lru_cache()
def get_rag_workflow():
    """Get compiled LangGraph workflow (cached)."""
    return create_rag_workflow()

def get_langgraph_service() -> LangGraphService:
    return LangGraphService(
        query_repo=get_query_history_repository(),
        rag_workflow=get_rag_workflow()
    )
```

---

### 6.3 Configuration Files

#### **`.env.example`** - Environment Variables Template

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development

# PostgreSQL Database
DATABASE_URL=postgresql://user:password@localhost:5432/graph_rag_db

# Neo4j Database
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-generate-with-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-api-key
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Ingestion Settings
BATCH_SIZE=1000
MAX_CSV_SIZE_MB=100

# CORS Origins (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

#### **`requirements.txt`** - Python Dependencies

```txt
# Core Backend
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
python-multipart==0.0.6  # File upload support

# LangGraph & LangChain
langgraph==0.0.60
langchain==0.1.0
langchain-core==0.1.0

# Database - PostgreSQL
prisma==0.11.0
asyncpg==0.29.0

# Database - Neo4j
neo4j==5.15.0

# AI/ML
openai==1.10.0  # OpenRouter uses OpenAI SDK
transformers==4.36.0
sentence-transformers==2.2.2
torch==2.1.0

# Authentication & Security
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4  # Password hashing
bcrypt==4.1.2

# Utilities
python-dotenv==1.0.0
httpx==0.26.0  # Async HTTP client
pandas==2.1.4  # CSV processing
```

---

#### **`pyproject.toml`** - Python Project Metadata

```toml
[tool.poetry]
name = "graph-rag-backend"
version = "1.0.0"
description = "Knowledge Graph RAG System for Skills & Jobs"
authors = ["Your Team <team@example.com>"]
readme = "README.md"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.3"
pydantic-settings = "^2.1.0"
langgraph = "^0.0.60"
langchain = "^0.1.0"
prisma = "^0.11.0"
neo4j = "^5.15.0"
transformers = "^4.36.0"
sentence-transformers = "^2.2.2"
torch = "^2.1.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
httpx = "^0.26.0"
pandas = "^2.1.4"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
black = "^23.12.1"
ruff = "^0.1.9"
mypy = "^1.8.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

---

#### **`pytest.ini`** - Pytest Configuration

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
```

---

#### **`prisma/schema.prisma`** - Prisma Schema

```prisma
generator client {
  provider = "prisma-client-py"
  interface = "asyncio"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id            String   @id @default(uuid())
  email         String   @unique
  password_hash String
  created_at    DateTime @default(now())
  updated_at    DateTime @updatedAt

  query_history  QueryHistory[]
  ingestion_jobs IngestionJob[]

  @@map("users")
}

model IngestionJob {
  id                String   @id @default(uuid())
  user_id           String
  file_type         String   // "skills" or "jobs"
  status            String   // "pending", "processing", "completed", "failed"
  total_records     Int      @default(0)
  processed_records Int      @default(0)
  batch_number      Int?
  error_message     String?
  created_at        DateTime @default(now())
  updated_at        DateTime @updatedAt

  user User @relation(fields: [user_id], references: [id], onDelete: Cascade)

  @@map("ingestion_jobs")
  @@index([user_id])
  @@index([status])
}

model QueryHistory {
  id            String   @id @default(uuid())
  user_id       String
  query_text    String
  response_text String
  metadata      String   // JSON string
  created_at    DateTime @default(now())

  user User @relation(fields: [user_id], references: [id], onDelete: Cascade)

  @@map("query_history")
  @@index([user_id])
  @@index([created_at])
}
```

---

#### **`Dockerfile`** - Container Definition

```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY prisma/ ./prisma/
COPY scripts/ ./scripts/

# Generate Prisma client
RUN prisma generate

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

#### **`docker-compose.yml`** - Multi-Container Orchestration

```yaml
version: '3.8'

services:
  backend:
    build: .
    container_name: graph-rag-backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/graph_rag_db
      - NEO4J_URI=neo4j://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    volumes:
      - ./app:/app/app
    networks:
      - graph-rag-network

  postgres:
    image: postgres:15-alpine
    container_name: graph-rag-postgres
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=graph_rag_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - graph-rag-network

  neo4j:
    image: neo4j:5.15-enterprise
    container_name: graph-rag-neo4j
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p ${NEO4J_PASSWORD} 'RETURN 1'"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - graph-rag-network

volumes:
  postgres_data:
  neo4j_data:
  neo4j_logs:

networks:
  graph-rag-network:
    driver: bridge
```

---

#### **`.gitignore`** - Git Ignore Rules

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Database
*.db
*.sqlite3

# Prisma
prisma/migrations/

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Docker
*.tar
docker-compose.override.yml
```

---

### 6.4 Key Scripts

#### **`scripts/setup_indexes.py`** - Neo4j Index Setup

```python
"""
Script to create Neo4j indexes and constraints.
Run this after initial Neo4j deployment.
"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

def setup_neo4j_indexes():
    """Create all required Neo4j indexes and constraints."""

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    queries = [
        # Skill constraints & indexes
        "CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE",
        "CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)",
        """CREATE VECTOR INDEX skill_embedding_idx IF NOT EXISTS
           FOR (s:Skill) ON (s.embedding)
           OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}""",

        # Job constraints & indexes
        "CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE",
        "CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.job_title)",
        """CREATE VECTOR INDEX job_embedding_idx IF NOT EXISTS
           FOR (j:Job) ON (j.embedding)
           OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}""",

        # Company, Location, Category constraints
        "CREATE CONSTRAINT company_name_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_name IS UNIQUE",
        "CREATE CONSTRAINT location_name_unique IF NOT EXISTS FOR (l:Location) REQUIRE l.location_name IS UNIQUE",
        "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.category_id IS UNIQUE",
        "CREATE CONSTRAINT subcategory_id_unique IF NOT EXISTS FOR (sub:Subcategory) REQUIRE sub.subcategory_id IS UNIQUE",
    ]

    with driver.session() as session:
        for query in queries:
            print(f"Executing: {query[:80]}...")
            session.run(query)
            print("✓ Success")

    driver.close()
    print("\n✅ All Neo4j indexes and constraints created successfully!")

if __name__ == "__main__":
    setup_neo4j_indexes()
```

---

#### **`scripts/seed_neo4j.py`** - Sample Data Seeding

```python
"""
Script to seed Neo4j with sample data for testing.
"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

def seed_sample_data():
    """Insert sample skills and jobs into Neo4j."""

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
    )

    sample_skills = [
        {
            "id": "python-001",
            "name": "python",
            "level": 3,
            "type": "programming_language",
            "is_software": False,
            "is_language": True,
            "description": "High-level programming language",
            "embedding": [0.1] * 384  # Placeholder
        },
        {
            "id": "react-001",
            "name": "react",
            "level": 3,
            "type": "framework",
            "is_software": True,
            "is_language": False,
            "description": "JavaScript library for building user interfaces",
            "embedding": [0.2] * 384  # Placeholder
        }
    ]

    with driver.session() as session:
        for skill in sample_skills:
            session.run(
                """
                CREATE (s:Skill {
                    id: $id, name: $name, level: $level, type: $type,
                    is_software: $is_software, is_language: $is_language,
                    description: $description, embedding: $embedding,
                    created_at: datetime()
                })
                """,
                **skill
            )
        print("✅ Sample skills seeded successfully!")

    driver.close()

if __name__ == "__main__":
    seed_sample_data()
```

---

### 6.5 Module Import Pattern

All modules follow consistent import organization:

```python
# Standard library imports
import os
import json
from typing import List, Dict, Any
from datetime import datetime

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from neo4j import AsyncGraphDatabase

# Local application imports
from app.config import settings
from app.models.user import UserCreate, UserResponse
from app.services.auth_service import AuthService
from app.utils.logger import logger
```

**Import Order Rules**:
1. Standard library imports
2. Third-party library imports
3. Local application imports
4. Alphabetize within each group

---

### 6.6 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| **Files** | `snake_case.py` | `auth_service.py` |
| **Classes** | `PascalCase` | `AuthService` |
| **Functions** | `snake_case()` | `get_user_by_id()` |
| **Constants** | `UPPER_SNAKE_CASE` | `MAX_BATCH_SIZE` |
| **Private** | `_leading_underscore` | `_validate_token()` |
| **Async** | `async def func()` | `async def create_user()` |
| **Pydantic Models** | `PascalCase` | `UserCreate`, `TokenResponse` |
| **API Routes** | `kebab-case` | `/auth/reset-password` |

---

This completes the **Source Tree** section with comprehensive project structure, configuration files, and organizational patterns.

---

## Infrastructure & Deployment

This section covers the **MVP deployment strategy** - keeping things simple and focused on getting the system running quickly for development and testing.

---

### 7.1 Development Environment Setup

#### **Prerequisites**

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Poetry | 1.7+ | Dependency management (optional) |
| Node.js | 18+ | Prisma CLI |
| Docker | 24+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.40+ | Version control |

---

#### **Local Setup Steps**

**1. Clone Repository**
```bash
git clone https://github.com/your-org/graph-rag-backend.git
cd graph-rag-backend
```

**2. Create Virtual Environment**
```bash
# Using venv
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# OR using Poetry
poetry install
poetry shell
```

**3. Install Dependencies**
```bash
# Using pip
pip install -r requirements.txt

# OR using Poetry
poetry install
```

**4. Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

**5. Start Databases with Docker Compose**
```bash
docker-compose up -d postgres neo4j
```

**6. Run Database Migrations**
```bash
# Generate Prisma client
prisma generate

# Run migrations
prisma migrate dev --name init
```

**7. Setup Neo4j Indexes**
```bash
python scripts/setup_indexes.py
```

**8. (Optional) Seed Sample Data**
```bash
python scripts/seed_neo4j.py
```

**9. Start Development Server**
```bash
# With uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# OR with Python
python -m app.main
```

**10. Verify Setup**
```bash
# Health check
curl http://localhost:8000/health

# API docs (Swagger UI)
open http://localhost:8000/docs
```

---

### 7.2 Docker Deployment

#### **Single Container Deployment**

**Build Image**
```bash
docker build -t graph-rag-backend:latest .
```

**Run Container**
```bash
docker run -d \
  --name graph-rag-api \
  -p 8000:8000 \
  --env-file .env \
  graph-rag-backend:latest
```

---

#### **Multi-Container Deployment with Docker Compose**

**Full Stack (Backend + PostgreSQL + Neo4j)**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Stop and remove volumes (data will be lost)
docker-compose down -v
```

**Service URLs**:
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `bolt://localhost:7687`

---

**Run tests locally**:
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term
```

**Optional: GitHub Actions for basic CI**:

Create `.github/workflows/test.yml`:
```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pytest pytest-asyncio
      - run: pytest tests/ -v
```

---

### 7.4 Basic Monitoring (MVP)

#### **Health Check Endpoint**

**Add to `app/main.py`**:
```python
@app.get("/health")
async def health_check():
    """Simple health check for MVP."""
    return {
        "status": "healthy",
        "service": "graph-rag-api",
        "version": "1.0.0"
    }
```

Test it: `curl http://localhost:8000/health`

---

#### **Simple Logging**

**`app/utils/logger.py`**:
```python
import logging
import sys

def setup_logger():
    """Basic console logging."""
    logger = logging.getLogger("graph-rag-api")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = setup_logger()
```

**Usage**:
```python
from app.utils.logger import logger

logger.info("CSV ingestion started")
logger.error(f"Database connection failed: {error}")
```

---

### 7.5 MVP Deployment Notes

**For MVP, keep it simple**:

1. **Local Development**: Use `docker-compose up` - that's it
2. **No CI/CD needed yet**: Manual testing is fine for MVP
3. **No monitoring stack**: Basic health check + console logs are enough
4. **No backup strategy**: Focus on building features first
5. **No scaling concerns**: Single instance is fine for MVP
6. **No production hosting yet**: Run locally or use free tiers (Railway, Render) when ready

**When to add production infrastructure**:
- After MVP validation with real users
- When you have consistent traffic
- When downtime becomes costly
- When you need to scale beyond single instance

---

This completes the **Infrastructure & Deployment** section with MVP-focused, simple setup.

---

## 8. Error Handling & Logging

### 8.1 Error Handling Philosophy

**MVP Approach**: Keep error handling simple, clear, and consistent. Focus on:
- Meaningful error messages for frontend integration
- Standard HTTP status codes
- Basic exception handling (no complex error tracking systems)
- User-friendly error responses
- Developer-friendly logging for debugging

**No Over-Engineering**:
- ❌ No Sentry or error tracking services (yet)
- ❌ No complex retry mechanisms
- ❌ No distributed tracing
- ✅ Simple FastAPI exception handlers
- ✅ Standard HTTP responses
- ✅ Console logging with timestamps

---

### 8.2 HTTP Status Codes

**Standard Codes Used**:

| Status Code | Usage | Example |
|-------------|-------|---------|
| `200 OK` | Successful request | Query response, get status |
| `201 Created` | Resource created | User registration |
| `400 Bad Request` | Validation error | Invalid CSV format, missing fields |
| `401 Unauthorized` | Authentication failed | Invalid credentials, missing token |
| `403 Forbidden` | Insufficient permissions | Access to other user's data |
| `404 Not Found` | Resource doesn't exist | Unknown job ID |
| `409 Conflict` | Resource conflict | Email already exists |
| `422 Unprocessable Entity` | Validation error (FastAPI default) | Pydantic validation failures |
| `500 Internal Server Error` | Unexpected server error | Database connection failed |
| `503 Service Unavailable` | External service down | Neo4j unreachable, OpenRouter API down |

---

### 8.3 Custom Exception Types

**`app/exceptions.py`**:
```python
"""Custom exceptions for Graph RAG API."""

class GraphRAGException(Exception):
    """Base exception for all Graph RAG errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(GraphRAGException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class AuthorizationError(GraphRAGException):
    """Raised when user lacks permissions."""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)

class ValidationError(GraphRAGException):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)

class ResourceNotFoundError(GraphRAGException):
    """Raised when resource doesn't exist."""
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} with ID '{identifier}' not found"
        super().__init__(message, status_code=404)

class ResourceConflictError(GraphRAGException):
    """Raised when resource already exists."""
    def __init__(self, message: str):
        super().__init__(message, status_code=409)

class DatabaseError(GraphRAGException):
    """Raised when database operation fails."""
    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(f"Database error: {message}", status_code=500)

class ExternalServiceError(GraphRAGException):
    """Raised when external service (Neo4j, OpenRouter) fails."""
    def __init__(self, service: str, message: str):
        super().__init__(f"{service} error: {message}", status_code=503)

class CSVProcessingError(GraphRAGException):
    """Raised when CSV parsing/validation fails."""
    def __init__(self, message: str, row_number: int = None):
        if row_number:
            message = f"CSV error at row {row_number}: {message}"
        super().__init__(message, status_code=400)
```

---

### 8.4 FastAPI Exception Handlers

**`app/middleware/error_handlers.py`**:
```python
"""Global exception handlers for FastAPI."""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.exceptions import GraphRAGException
from app.utils.logger import logger
import traceback

async def graph_rag_exception_handler(request: Request, exc: GraphRAGException):
    """Handle custom Graph RAG exceptions."""
    logger.error(f"{exc.__class__.__name__}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "path": str(request.url)
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "Request validation failed",
            "details": exc.errors(),
            "path": str(request.url)
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected errors."""
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(traceback.format_exc())

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "path": str(request.url)
        }
    )
```

**Register handlers in `app/main.py`**:
```python
from app.middleware.error_handlers import (
    graph_rag_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)
from app.exceptions import GraphRAGException
from fastapi.exceptions import RequestValidationError

app.add_exception_handler(GraphRAGException, graph_rag_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
```

---

### 8.5 Error Response Format

**Standard Error Response**:
```json
{
  "error": "ResourceNotFoundError",
  "message": "IngestionJob with ID '123e4567' not found",
  "path": "/ingest/status/123e4567"
}
```

**Validation Error Response**:
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "path": "/auth/register"
}
```

**CSV Processing Error Response**:
```json
{
  "error": "CSVProcessingError",
  "message": "CSV error at row 42: Missing required column 'CATEGORY'",
  "path": "/ingest/skills"
}
```

---

### 8.6 Common Error Scenarios

#### **1. Authentication Errors**

**Scenario**: Invalid credentials during login
```python
# app/api/auth.py
from app.exceptions import AuthenticationError

async def login(credentials: LoginRequest):
    user = await auth_service.verify_credentials(
        credentials.email,
        credentials.password
    )
    if not user:
        raise AuthenticationError("Invalid email or password")

    return {"access_token": token, "token_type": "bearer"}
```

**Response**:
```json
{
  "error": "AuthenticationError",
  "message": "Invalid email or password",
  "path": "/auth/login"
}
```

---

#### **2. Resource Not Found**

**Scenario**: Fetching non-existent ingestion job
```python
# app/api/ingest.py
from app.exceptions import ResourceNotFoundError

async def get_ingestion_status(job_id: str):
    job = await ingestion_service.get_job_status(job_id)
    if not job:
        raise ResourceNotFoundError("IngestionJob", job_id)

    return job
```

**Response**:
```json
{
  "error": "ResourceNotFoundError",
  "message": "IngestionJob with ID 'abc123' not found",
  "path": "/ingest/status/abc123"
}
```

---

#### **3. Database Connection Failure**

**Scenario**: PostgreSQL or Neo4j unreachable
```python
# app/repositories/user_repository.py
from app.exceptions import DatabaseError

async def create_user(user_data: dict):
    try:
        user = await prisma.user.create(data=user_data)
        return user
    except PrismaError as e:
        raise DatabaseError("Failed to create user", original_error=e)
```

**Response**:
```json
{
  "error": "DatabaseError",
  "message": "Database error: Failed to create user",
  "path": "/auth/register"
}
```

---

#### **4. CSV Validation Failure**

**Scenario**: Uploaded CSV missing required columns
```python
# app/services/ingestion_service.py
from app.exceptions import CSVProcessingError

async def validate_skills_csv(df):
    required_columns = ["ID", "NAME", "LEVEL", "CATEGORY", "TYPE"]
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise CSVProcessingError(
            f"Missing required columns: {', '.join(missing)}"
        )

    # Validate row data
    for idx, row in df.iterrows():
        if pd.isna(row["NAME"]):
            raise CSVProcessingError(
                "NAME cannot be empty",
                row_number=idx + 2  # +2 because idx is 0-based and header is row 1
            )
```

**Response**:
```json
{
  "error": "CSVProcessingError",
  "message": "CSV error at row 15: NAME cannot be empty",
  "path": "/ingest/skills"
}
```

---

#### **5. External Service Failure**

**Scenario**: OpenRouter API unavailable
```python
# app/services/llm_service.py
from app.exceptions import ExternalServiceError
import httpx

async def generate_response(prompt: str):
    try:
        response = await httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "meta-llama/llama-3.3-8b-instruct:free", "messages": [...]}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        raise ExternalServiceError("OpenRouter", str(e))
```

**Response**:
```json
{
  "error": "ExternalServiceError",
  "message": "OpenRouter error: Connection timeout",
  "path": "/query/ask"
}
```

---

### 8.7 Logging Standards

**Log Levels**:

| Level | Usage | Example |
|-------|-------|---------|
| `DEBUG` | Development debugging (not used in MVP) | Variable values, function calls |
| `INFO` | Normal operations | "CSV ingestion started", "User registered" |
| `WARNING` | Unexpected but handled | "Slow query detected (>5s)" |
| `ERROR` | Error conditions | "Database connection failed", "CSV parsing error" |
| `CRITICAL` | System failure (rarely used) | "Unable to start server" |

---

**Logging Best Practices**:

1. **Log at Service Layer**: Log business logic operations (not in repositories or models)
2. **Include Context**: User ID, job ID, request ID when relevant
3. **No Sensitive Data**: Never log passwords, tokens, or PII
4. **Structured Messages**: Use consistent format for easier searching

**Example Logging Patterns**:

```python
# app/services/ingestion_service.py
from app.utils.logger import logger

class IngestionService:
    async def start_skills_ingestion(self, file: UploadFile, user_id: str):
        logger.info(f"[Ingestion] Starting skills CSV upload for user={user_id}")

        try:
            # Process CSV
            job_id = await self._create_job(user_id, "skills")
            logger.info(f"[Ingestion] Created job_id={job_id} for user={user_id}")

            df = await self._parse_csv(file)
            logger.info(f"[Ingestion] Parsed {len(df)} rows from CSV, job_id={job_id}")

            await self._process_skills(df, job_id)
            logger.info(f"[Ingestion] Completed job_id={job_id}, status=SUCCESS")

        except CSVProcessingError as e:
            logger.error(f"[Ingestion] CSV validation failed, user={user_id}, error={e.message}")
            raise
        except Exception as e:
            logger.error(f"[Ingestion] Unexpected error, job_id={job_id}, error={str(e)}")
            raise DatabaseError("Ingestion failed", original_error=e)
```

**Log Output** (Console):
```
2025-10-22 14:32:15 | INFO | [Ingestion] Starting skills CSV upload for user=abc123
2025-10-22 14:32:16 | INFO | [Ingestion] Created job_id=xyz789 for user=abc123
2025-10-22 14:32:18 | INFO | [Ingestion] Parsed 5000 rows from CSV, job_id=xyz789
2025-10-22 14:32:45 | INFO | [Ingestion] Completed job_id=xyz789, status=SUCCESS
```

---

**Query Logging Example**:

```python
# app/agents/query_orchestrator.py
from app.utils.logger import logger

async def handle_query(state: GraphRAGState):
    user_query = state["user_query"]
    user_id = state["user_id"]

    logger.info(f"[Query] Received query from user={user_id}, query='{user_query[:50]}...'")

    # Process through LangGraph
    result = await graph.ainvoke(state)

    logger.info(f"[Query] Generated response for user={user_id}, confidence={result['metadata'].get('confidence')}")

    return result
```

---

### 8.8 Error Handling in LangGraph Nodes

**Pattern**: Use try-except in each node, return error state instead of raising

**Example**: Vector search node with error handling

```python
# app/agents/nodes/vector_search.py
from app.utils.logger import logger

async def vector_search_node(state: GraphRAGState) -> GraphRAGState:
    """Search Neo4j for similar skills/jobs using embeddings."""
    try:
        query_embedding = await embedding_service.generate_embedding(
            state["user_query"]
        )

        results = await neo4j_repo.vector_similarity_search(
            query_embedding,
            top_k=10
        )

        logger.info(f"[VectorSearch] Found {len(results)} similar nodes")

        return {
            **state,
            "vector_results": results,
            "metadata": {**state.get("metadata", {}), "vector_count": len(results)}
        }

    except ExternalServiceError as e:
        logger.error(f"[VectorSearch] Neo4j connection failed: {e.message}")
        return {
            **state,
            "vector_results": [],
            "metadata": {**state.get("metadata", {}), "error": "vector_search_failed"}
        }
    except Exception as e:
        logger.error(f"[VectorSearch] Unexpected error: {str(e)}")
        return {
            **state,
            "vector_results": [],
            "metadata": {**state.get("metadata", {}), "error": "unknown_error"}
        }
```

**Why This Pattern?**:
- LangGraph nodes should not raise exceptions (breaks graph execution)
- Return error information in state for conditional routing
- Log errors for debugging
- Allow graceful degradation (e.g., fall back to graph traversal if vector search fails)

---

### 8.9 MVP Logging Setup

**Simple Console Logging** (already defined in Infrastructure section):

**`app/utils/logger.py`**:
```python
import logging
import sys

def setup_logger():
    """Basic console logging for MVP."""
    logger = logging.getLogger("graph-rag-api")
    logger.setLevel(logging.INFO)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = setup_logger()
```

**Usage Across Application**:
```python
from app.utils.logger import logger

# In any file
logger.info("Operation started")
logger.error(f"Failed: {error}")
```

---

### 8.10 When to Add Advanced Error Handling

**After MVP validation, consider adding**:

1. **Error Tracking Service** (Sentry): When you have real users and need to track errors in production
2. **Structured Logging** (JSON logs): When you deploy to cloud and need log aggregation
3. **Request Tracing**: When debugging distributed systems or performance issues
4. **Retry Mechanisms**: When external services have transient failures
5. **Circuit Breakers**: When protecting against cascading failures

**For MVP**: Basic console logs + standard exception handling is sufficient.

---

This completes the **Error Handling & Logging** section with MVP-focused, practical patterns.

---

## 9. Coding Standards

### 9.1 Python Style Guide

**Follow PEP 8** with practical adaptations for FastAPI/LangGraph:

| Rule | Standard | Example |
|------|----------|---------|
| **Line Length** | 88 characters (Black default) | Use Black formatter |
| **Indentation** | 4 spaces (no tabs) | Standard Python |
| **Imports** | Grouped: stdlib → third-party → local | See import order below |
| **Naming** | snake_case for functions/variables, PascalCase for classes | `def get_user()`, `class UserService` |
| **Docstrings** | Use for public functions/classes | `"""Brief description."""` |
| **Type Hints** | Required for function signatures | `async def get_user(user_id: str) -> User:` |

---

### 9.2 Import Order

**Standard Import Organization**:

```python
# 1. Standard library imports
import os
import sys
from typing import List, Dict, Optional
from datetime import datetime

# 2. Third-party imports
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import pandas as pd

# 3. Local application imports
from app.models.user import User
from app.services.auth_service import AuthService
from app.utils.logger import logger
```

**Use absolute imports** (not relative):
```python
# ✅ Good
from app.services.ingestion_service import IngestionService

# ❌ Bad
from ..services.ingestion_service import IngestionService
```

---

### 9.3 Naming Conventions

#### **Files and Directories**

| Type | Convention | Example |
|------|------------|---------|
| **Modules** | snake_case | `auth_service.py`, `user_repository.py` |
| **Directories** | snake_case, plural for collections | `api/`, `services/`, `models/` |
| **Test files** | `test_*.py` | `test_auth_service.py` |

#### **Code Elements**

| Element | Convention | Example |
|---------|------------|---------|
| **Variables** | snake_case | `user_id`, `query_result` |
| **Functions** | snake_case, verb-based | `get_user()`, `create_skill()` |
| **Classes** | PascalCase, noun-based | `UserService`, `SkillRepository` |
| **Constants** | UPPER_SNAKE_CASE | `MAX_BATCH_SIZE`, `DEFAULT_TIMEOUT` |
| **Private** | Leading underscore | `_internal_helper()`, `_cache` |
| **Pydantic Models** | PascalCase, end with Request/Response | `LoginRequest`, `UserResponse` |
| **Routers** | snake_case | `auth_router`, `query_router` |

---

### 9.4 Function and Class Standards

#### **Type Hints Required**

```python
# ✅ Good - explicit types
async def get_user(user_id: str) -> Optional[User]:
    """Fetch user by ID."""
    return await user_repository.find_by_id(user_id)

# ❌ Bad - no type hints
async def get_user(user_id):
    return await user_repository.find_by_id(user_id)
```

#### **Docstrings for Public Functions**

```python
async def start_skills_ingestion(
    file: UploadFile,
    user_id: str
) -> IngestionJobResponse:
    """
    Start asynchronous ingestion of skills CSV.

    Args:
        file: Uploaded CSV file
        user_id: ID of user initiating ingestion

    Returns:
        IngestionJobResponse with job_id and status

    Raises:
        CSVProcessingError: If CSV validation fails
        DatabaseError: If job creation fails
    """
    # Implementation
```

**For internal/private functions**: Docstrings optional (keep code simple for MVP).

---

### 9.5 FastAPI Patterns

#### **Router Definition**

```python
# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> UserResponse:
    """Register a new user."""
    return await auth_service.register_user(request)
```

**Standards**:
- Use `prefix` and `tags` for router organization
- Explicit `status_code` for non-200 responses
- Type-hinted request/response models
- Dependency injection with `Depends()`

#### **Request/Response Models**

```python
# app/models/auth.py
from pydantic import BaseModel, EmailStr, Field, validator
import re

class RegisterRequest(BaseModel):
    """User registration request with secure password requirements."""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Password must be at least 12 characters with complexity requirements"
    )

    @validator('password')
    def validate_password_complexity(cls, v):
        """Enforce password complexity requirements."""
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError("Password must contain at least one special character (@$!%*?&#)")
        return v

class UserResponse(BaseModel):
    """User data response (no password)."""
    id: str
    email: str
    created_at: str

    class Config:
        from_attributes = True  # For Prisma models
```

**Standards**:
- Separate request/response models (don't reuse)
- Use Pydantic validators (`EmailStr`, `Field`)
- Add `Config.from_attributes` for ORM models
- No sensitive data in response models

---

### 9.6 Service Layer Patterns

**Single Responsibility**: Each service handles one domain

```python
# app/services/auth_service.py
class AuthService:
    """Handles user authentication and JWT generation."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, request: RegisterRequest) -> UserResponse:
        """Create new user account."""
        # Check email uniqueness
        existing = await self.user_repo.find_by_email(request.email)
        if existing:
            raise ResourceConflictError("Email already registered")

        # Hash password
        password_hash = bcrypt.hashpw(
            request.password.encode(),
            bcrypt.gensalt()
        ).decode()

        # Create user
        user = await self.user_repo.create({
            "email": request.email,
            "password_hash": password_hash
        })

        return UserResponse.model_validate(user)
```

**Standards**:
- Constructor injection for dependencies
- Raise custom exceptions (not HTTPException)
- Business logic in service layer (not in routers)
- Use repository pattern for database access

---

### 9.7 Repository Layer Patterns

**Encapsulate Data Access**:

```python
# app/repositories/user_repository.py
from prisma import Prisma
from app.exceptions import DatabaseError

class UserRepository:
    """Database operations for User model."""

    def __init__(self, db: Prisma):
        self.db = db

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email address."""
        try:
            return await self.db.user.find_unique(where={"email": email})
        except Exception as e:
            raise DatabaseError(f"Failed to find user: {email}", original_error=e)

    async def create(self, data: dict) -> User:
        """Create new user."""
        try:
            return await self.db.user.create(data=data)
        except Exception as e:
            raise DatabaseError("Failed to create user", original_error=e)
```

**Standards**:
- Repository = one entity (User, Skill, Job)
- Wrap database exceptions in custom exceptions
- Simple methods (find, create, update, delete)
- No business logic in repositories

---

### 9.8 LangGraph Node Patterns

**Consistent Node Structure**:

```python
# app/agents/nodes/query_understanding.py
from app.agents.state import GraphRAGState
from app.utils.logger import logger

async def query_understanding_node(state: GraphRAGState) -> GraphRAGState:
    """
    Analyze user query to extract intent and entities.

    Args:
        state: Current graph state with user_query

    Returns:
        Updated state with intent and entities
    """
    try:
        user_query = state["user_query"]
        logger.info(f"[QueryUnderstanding] Processing query: {user_query[:50]}...")

        # Call LLM for intent classification
        intent = await llm_service.classify_intent(user_query)
        entities = await llm_service.extract_entities(user_query)

        logger.info(f"[QueryUnderstanding] Detected intent={intent}, entities={len(entities)}")

        return {
            **state,
            "intent": intent,
            "entities": entities,
            "metadata": {**state.get("metadata", {}), "intent_confidence": 0.85}
        }

    except Exception as e:
        logger.error(f"[QueryUnderstanding] Failed: {str(e)}")
        return {
            **state,
            "intent": "unknown",
            "entities": [],
            "metadata": {**state.get("metadata", {}), "error": "intent_classification_failed"}
        }
```

**Standards**:
- Always return updated state (never raise exceptions)
- Use try-except for error handling
- Log entry/exit with context
- Update metadata for debugging
- Descriptive function names ending in `_node`

---

### 9.9 Configuration Management

**Use Pydantic Settings**:

```python
# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    # API Keys
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")

    # JWT
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)

    # Application
    app_name: str = Field(default="Graph RAG API")
    debug: bool = Field(default=False)

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**`.env` file**:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/graphrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# API Keys
OPENROUTER_API_KEY=your_api_key_here

# JWT
JWT_SECRET=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Application
APP_NAME=Graph RAG API
DEBUG=True
```

**Standards**:
- All configuration in `app/config.py`
- Use environment variables (never hardcode secrets)
- Provide defaults for non-sensitive values
- Single `settings` instance imported everywhere

---

### 9.10 Code Organization Rules

#### **File Size Limits**

| File Type | Max Lines | Rationale |
|-----------|-----------|-----------|
| **Routers** | 200 lines | Split into multiple routers if larger |
| **Services** | 300 lines | Split into multiple services by domain |
| **Repositories** | 200 lines | One repository per entity |
| **Nodes** | 100 lines | Each node should be focused |

#### **Function Complexity**

- **Max function length**: 50 lines (ideally <30)
- **Max parameters**: 5 (use Pydantic models for more)
- **Max nesting depth**: 3 levels (extract helper functions)

```python
# ✅ Good - simple function
async def create_skill_node(skill_data: dict) -> dict:
    """Create skill node in Neo4j."""
    query = """
    CREATE (s:Skill {id: $id, name: $name})
    RETURN s
    """
    result = await neo4j_repo.execute_write(query, skill_data)
    return result

# ❌ Bad - too complex, too nested
async def process_csv_with_validation_and_embedding_generation(file, user_id, batch_size):
    # 80+ lines of nested if-else statements
    # Multiple responsibilities
    # Hard to test
```

---

### 9.11 Comment Guidelines

**When to Comment**:
- ✅ Complex algorithms or business logic
- ✅ Non-obvious design decisions
- ✅ Workarounds for external library quirks

**When NOT to Comment**:
- ❌ Obvious code (e.g., `# Create user` above `create_user()`)
- ❌ Commented-out code (delete instead)
- ❌ TODOs for missing features (complete it or don't start)

```python
# ✅ Good comment - explains WHY
# Use +2 offset because CSV row index is 0-based and row 1 is header
row_number = idx + 2

# ❌ Bad comment - explains WHAT (obvious from code)
# Loop through dataframe rows
for idx, row in df.iterrows():
    pass
```

---

### 9.12 Error Handling Standards

**Always be specific with exceptions**:

```python
# ✅ Good - specific exception
if not user:
    raise ResourceNotFoundError("User", user_id)

# ❌ Bad - generic exception
if not user:
    raise Exception("User not found")
```

**Catch specific exceptions**:

```python
# ✅ Good
try:
    result = await external_api_call()
except httpx.TimeoutException:
    raise ExternalServiceError("API", "Timeout after 30s")
except httpx.HTTPStatusError as e:
    raise ExternalServiceError("API", f"HTTP {e.response.status_code}")

# ❌ Bad - catch-all
try:
    result = await external_api_call()
except Exception:
    raise ExternalServiceError("API", "Failed")
```

---

### 9.13 Testing Naming Conventions

**Test File Structure**:
```
tests/
├── unit/
│   ├── test_auth_service.py
│   ├── test_ingestion_service.py
│   └── test_user_repository.py
├── integration/
│   ├── test_auth_flow.py
│   └── test_csv_ingestion.py
└── e2e/
    └── test_query_api.py
```

**Test Function Naming**:
```python
# Pattern: test_<function>_<scenario>_<expected_result>

def test_register_user_valid_email_creates_user():
    """Test successful user registration."""
    pass

def test_register_user_duplicate_email_raises_conflict():
    """Test duplicate email raises ResourceConflictError."""
    pass

def test_login_invalid_password_raises_authentication_error():
    """Test wrong password raises AuthenticationError."""
    pass
```

---

### 9.14 Dependency Injection Pattern

**Use FastAPI Depends for all dependencies**:

```python
# app/dependencies.py
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from prisma import Prisma

# Singletons
_prisma_client = None
_neo4j_driver = None

async def get_prisma() -> Prisma:
    """Get Prisma database client."""
    global _prisma_client
    if not _prisma_client:
        _prisma_client = Prisma()
        await _prisma_client.connect()
    return _prisma_client

def get_user_repository(db: Prisma = Depends(get_prisma)) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(db)

def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository)
) -> AuthService:
    """Get authentication service instance."""
    return AuthService(user_repo)
```

**Use in routers**:
```python
@router.post("/register")
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.register_user(request)
```

---

### 9.15 Async/Await Standards

**Always use async for I/O operations**:

```python
# ✅ Good - async database calls
async def get_user(user_id: str) -> User:
    return await prisma.user.find_unique(where={"id": user_id})

# ❌ Bad - blocking call in async function
async def get_user(user_id: str) -> User:
    return prisma.user.find_unique(where={"id": user_id})  # Missing await
```

**Don't use async for pure computation**:

```python
# ✅ Good - synchronous for CPU-bound work
def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity (pure computation)."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# ❌ Bad - unnecessary async
async def calculate_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
```

---

### 9.16 Code Formatting Tools

**Use Black for automatic formatting**:

```bash
# Install
pip install black

# Format all files
black app/

# Check without modifying
black --check app/
```

**Use isort for import sorting**:

```bash
# Install
pip install isort

# Sort imports
isort app/

# Configure in pyproject.toml
[tool.isort]
profile = "black"
line_length = 88
```

**Use mypy for type checking** (optional for MVP, recommended later):

```bash
# Install
pip install mypy

# Run type checker
mypy app/
```

---

### 9.17 MVP Coding Standards Summary

**For MVP, focus on**:

1. ✅ **Consistent naming**: snake_case functions, PascalCase classes
2. ✅ **Type hints**: Required for function signatures
3. ✅ **Error handling**: Use custom exceptions with clear messages
4. ✅ **Dependency injection**: Use FastAPI Depends pattern
5. ✅ **Simple structure**: Service → Repository layers
6. ✅ **Console logging**: Basic info/error logs with context

**Skip for MVP** (add later if needed):

1. ❌ **Comprehensive docstrings**: Only for public APIs
2. ❌ **Type checking with mypy**: Manual review is fine for MVP
3. ❌ **100% test coverage**: Focus on critical paths
4. ❌ **Complex design patterns**: KISS principle for MVP

---

This completes the **Coding Standards** section with practical, MVP-appropriate guidelines.

---

## 10. Test Strategy

### 10.1 MVP Testing Philosophy

**For MVP, focus on critical paths**:
- ✅ **Unit tests**: Core business logic (services, utilities)
- ✅ **Integration tests**: API endpoints with database
- ❌ **E2E tests**: Skip for MVP (add after validation)
- ❌ **100% coverage**: Focus on critical paths (~60-70% coverage is fine)

**Test What Matters**:
1. Authentication flow (register, login, token validation)
2. CSV ingestion (validation, parsing, Neo4j creation)
3. Query processing (LangGraph workflow)
4. Error handling (custom exceptions, HTTP responses)

**Skip for MVP**:
- UI/frontend tests (separate frontend testing)
- Load/performance tests (add after scaling)
- Comprehensive mocking (use real databases in test containers)

---

### 10.2 Test Framework Setup

**Install pytest and dependencies**:

```bash
# requirements-dev.txt
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2  # For FastAPI test client
faker==20.1.0  # For test data generation
```

**pytest Configuration**:

**`pytest.ini`**:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    --verbose
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
```

---

### 10.3 Test Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/
│   ├── test_auth_service.py
│   ├── test_ingestion_service.py
│   ├── test_embedding_service.py
│   └── test_jwt_utils.py
├── integration/
│   ├── test_auth_api.py
│   ├── test_ingest_api.py
│   └── test_query_api.py
└── fixtures/
    ├── skills_sample.csv
    └── jobs_sample.csv
```

---

### 10.4 Shared Test Fixtures

**`tests/conftest.py`**:

```python
"""Shared pytest fixtures for all tests."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from prisma import Prisma
from neo4j import AsyncGraphDatabase

from app.main import app
from app.config import settings

# ===== Database Fixtures =====

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def db():
    """Provide clean Prisma database for each test."""
    prisma = Prisma()
    await prisma.connect()

    yield prisma

    # Cleanup
    await prisma.user.delete_many()
    await prisma.ingestionjob.delete_many()
    await prisma.queryhistory.delete_many()
    await prisma.disconnect()

@pytest.fixture(scope="function")
async def neo4j_driver():
    """Provide Neo4j driver for graph database tests."""
    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password)
    )

    yield driver

    # Cleanup - delete all nodes
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await driver.close()

# ===== API Client Fixtures =====

@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)

@pytest.fixture
async def authenticated_client(client, db):
    """Provide test client with authenticated user token."""
    # Create test user
    test_user = {
        "email": "test@example.com",
        "password": "testpassword123"
    }

    # Register user
    response = client.post("/auth/register", json=test_user)
    assert response.status_code == 201

    # Login to get token
    response = client.post("/auth/login", json=test_user)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Add auth header to client
    client.headers["Authorization"] = f"Bearer {token}"

    return client

# ===== Test Data Fixtures =====

@pytest.fixture
def sample_user_data():
    """Provide sample user data for tests."""
    return {
        "email": "user@example.com",
        "password": "securepassword123"
    }

@pytest.fixture
def sample_skill_row():
    """Provide sample skill CSV row."""
    return {
        "ID": "1",
        "NAME": "Python",
        "LEVEL": "advanced",
        "SUBCATEGORY": "Programming",
        "CATEGORY": "Technology",
        "TYPE": "Hard Skill",
        "IS_SOFTWARE": "TRUE",
        "IS_LANGUAGE": "TRUE",
        "WIKI_LINK": "https://en.wikipedia.org/wiki/Python_(programming_language)",
        "DESCRIPTION": "High-level programming language",
        "DESCRIPTION_SOURCE": "Wikipedia",
        "VERSION": "3.11",
        "LATEST_VERSION": "3.12"
    }

@pytest.fixture
def sample_skills_csv(tmp_path, sample_skill_row):
    """Create temporary skills CSV file."""
    import csv

    csv_path = tmp_path / "skills.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=sample_skill_row.keys())
        writer.writeheader()
        writer.writerow(sample_skill_row)

    return csv_path
```

---

### 10.5 Unit Tests

#### **Test Authentication Service**

**`tests/unit/test_auth_service.py`**:

```python
"""Unit tests for AuthService."""
import pytest
from unittest.mock import Mock, AsyncMock

from app.services.auth_service import AuthService
from app.exceptions import AuthenticationError, ResourceConflictError

@pytest.mark.unit
class TestAuthService:
    """Tests for user authentication logic."""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository."""
        return Mock()

    @pytest.fixture
    def auth_service(self, mock_user_repo):
        """Create AuthService with mocked repository."""
        return AuthService(user_repo=mock_user_repo)

    async def test_register_user_success(self, auth_service, mock_user_repo):
        """Test successful user registration."""
        # Arrange
        mock_user_repo.find_by_email = AsyncMock(return_value=None)
        mock_user_repo.create = AsyncMock(return_value={
            "id": "user-123",
            "email": "test@example.com",
            "created_at": "2025-10-22T10:00:00"
        })

        request = {"email": "test@example.com", "password": "password123"}

        # Act
        result = await auth_service.register_user(request)

        # Assert
        assert result["email"] == "test@example.com"
        mock_user_repo.find_by_email.assert_called_once_with("test@example.com")
        mock_user_repo.create.assert_called_once()

    async def test_register_user_duplicate_email_raises_conflict(
        self, auth_service, mock_user_repo
    ):
        """Test registration with existing email raises ResourceConflictError."""
        # Arrange
        mock_user_repo.find_by_email = AsyncMock(return_value={"id": "existing-user"})

        request = {"email": "existing@example.com", "password": "password123"}

        # Act & Assert
        with pytest.raises(ResourceConflictError) as exc_info:
            await auth_service.register_user(request)

        assert "already registered" in str(exc_info.value.message).lower()

    async def test_verify_credentials_invalid_password_returns_none(
        self, auth_service, mock_user_repo
    ):
        """Test login with wrong password returns None."""
        # Arrange
        mock_user_repo.find_by_email = AsyncMock(return_value={
            "id": "user-123",
            "password_hash": "$2b$12$hashedpassword"
        })

        # Act
        result = await auth_service.verify_credentials(
            "test@example.com",
            "wrongpassword"
        )

        # Assert
        assert result is None
```

---

#### **Test CSV Ingestion Service**

**`tests/unit/test_ingestion_service.py`**:

```python
"""Unit tests for IngestionService."""
import pytest
import pandas as pd
from unittest.mock import Mock, AsyncMock

from app.services.ingestion_service import IngestionService
from app.exceptions import CSVProcessingError

@pytest.mark.unit
class TestIngestionService:
    """Tests for CSV ingestion logic."""

    @pytest.fixture
    def mock_repos(self):
        """Mock repositories."""
        return {
            "ingestion_repo": Mock(),
            "neo4j_repo": Mock(),
            "embedding_service": Mock()
        }

    @pytest.fixture
    def ingestion_service(self, mock_repos):
        """Create IngestionService with mocks."""
        return IngestionService(**mock_repos)

    def test_validate_skills_csv_success(self, ingestion_service, sample_skill_row):
        """Test validation passes for valid skills CSV."""
        # Arrange
        df = pd.DataFrame([sample_skill_row])

        # Act & Assert (should not raise)
        ingestion_service.validate_skills_csv(df)

    def test_validate_skills_csv_missing_columns_raises_error(self, ingestion_service):
        """Test validation fails when required columns missing."""
        # Arrange
        df = pd.DataFrame([{"ID": "1", "NAME": "Python"}])  # Missing other columns

        # Act & Assert
        with pytest.raises(CSVProcessingError) as exc_info:
            ingestion_service.validate_skills_csv(df)

        assert "Missing required columns" in exc_info.value.message

    def test_validate_skills_csv_empty_name_raises_error(
        self, ingestion_service, sample_skill_row
    ):
        """Test validation fails when NAME is empty."""
        # Arrange
        sample_skill_row["NAME"] = None
        df = pd.DataFrame([sample_skill_row])

        # Act & Assert
        with pytest.raises(CSVProcessingError) as exc_info:
            ingestion_service.validate_skills_csv(df)

        assert "NAME cannot be empty" in exc_info.value.message
        assert "row 2" in exc_info.value.message.lower()
```

---

### 10.6 Integration Tests

#### **Test Authentication API**

**`tests/integration/test_auth_api.py`**:

```python
"""Integration tests for auth endpoints."""
import pytest

@pytest.mark.integration
class TestAuthAPI:
    """Tests for /auth endpoints with real database."""

    async def test_register_creates_user(self, client, db):
        """Test POST /auth/register creates user in database."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "password": "securepassword123"
        }

        # Act
        response = client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password" not in data  # Should not expose password

        # Verify in database
        user = await db.user.find_unique(where={"email": user_data["email"]})
        assert user is not None
        assert user.email == user_data["email"]

    async def test_register_duplicate_email_returns_409(self, client, db):
        """Test registering same email twice returns conflict error."""
        # Arrange
        user_data = {"email": "duplicate@example.com", "password": "password123"}
        client.post("/auth/register", json=user_data)

        # Act
        response = client.post("/auth/register", json=user_data)

        # Assert
        assert response.status_code == 409
        error = response.json()
        assert error["error"] == "ResourceConflictError"

    async def test_login_valid_credentials_returns_token(self, client, db):
        """Test POST /auth/login with correct credentials returns JWT."""
        # Arrange
        user_data = {"email": "login@example.com", "password": "password123"}
        client.post("/auth/register", json=user_data)

        # Act
        response = client.post("/auth/login", json=user_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password_returns_401(self, client, db):
        """Test login with wrong password returns unauthorized."""
        # Arrange
        user_data = {"email": "user@example.com", "password": "correctpassword"}
        client.post("/auth/register", json=user_data)

        # Act
        response = client.post("/auth/login", json={
            "email": user_data["email"],
            "password": "wrongpassword"
        })

        # Assert
        assert response.status_code == 401
        error = response.json()
        assert error["error"] == "AuthenticationError"
```

---

#### **Test CSV Ingestion API**

**`tests/integration/test_ingest_api.py`**:

```python
"""Integration tests for ingestion endpoints."""
import pytest
from io import BytesIO

@pytest.mark.integration
class TestIngestAPI:
    """Tests for /ingest endpoints with database and Neo4j."""

    async def test_upload_skills_csv_creates_job(
        self, authenticated_client, db, sample_skills_csv
    ):
        """Test POST /ingest/skills creates ingestion job."""
        # Arrange
        with open(sample_skills_csv, "rb") as f:
            files = {"file": ("skills.csv", f, "text/csv")}

            # Act
            response = authenticated_client.post("/ingest/skills", files=files)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "processing"

        # Verify job in database
        job = await db.ingestionjob.find_unique(where={"id": data["job_id"]})
        assert job is not None
        assert job.type == "skills"
        assert job.status == "processing"

    async def test_upload_invalid_csv_returns_400(self, authenticated_client, tmp_path):
        """Test uploading CSV with missing columns returns validation error."""
        # Arrange - Create invalid CSV
        invalid_csv = tmp_path / "invalid.csv"
        invalid_csv.write_text("ID,NAME\n1,Python")  # Missing required columns

        with open(invalid_csv, "rb") as f:
            files = {"file": ("invalid.csv", f, "text/csv")}

            # Act
            response = authenticated_client.post("/ingest/skills", files=files)

        # Assert
        assert response.status_code == 400
        error = response.json()
        assert error["error"] == "CSVProcessingError"
        assert "Missing required columns" in error["message"]

    async def test_get_ingestion_status_returns_job_details(
        self, authenticated_client, db
    ):
        """Test GET /ingest/status/{job_id} returns job info."""
        # Arrange - Create job in database
        job = await db.ingestionjob.create(data={
            "id": "test-job-123",
            "user_id": "user-123",
            "type": "skills",
            "status": "completed",
            "total_rows": 100,
            "processed_rows": 100
        })

        # Act
        response = authenticated_client.get(f"/ingest/status/{job.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job.id
        assert data["status"] == "completed"
        assert data["progress"] == 100.0

    async def test_get_status_nonexistent_job_returns_404(self, authenticated_client):
        """Test fetching non-existent job returns not found error."""
        # Act
        response = authenticated_client.get("/ingest/status/nonexistent-id")

        # Assert
        assert response.status_code == 404
        error = response.json()
        assert error["error"] == "ResourceNotFoundError"
```

---

### 10.7 Testing LangGraph Nodes

**`tests/unit/test_query_understanding_node.py`**:

```python
"""Unit tests for query understanding node."""
import pytest
from unittest.mock import AsyncMock

from app.agents.nodes.query_understanding import query_understanding_node
from app.agents.state import GraphRAGState

@pytest.mark.unit
async def test_query_understanding_extracts_intent(monkeypatch):
    """Test node correctly extracts intent from query."""
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.classify_intent.return_value = "job_search"
    mock_llm.extract_entities.return_value = ["Python", "Machine Learning"]

    monkeypatch.setattr("app.agents.nodes.query_understanding.llm_service", mock_llm)

    state: GraphRAGState = {
        "user_query": "Find jobs requiring Python and Machine Learning",
        "user_id": "user-123",
        "metadata": {}
    }

    # Act
    result = await query_understanding_node(state)

    # Assert
    assert result["intent"] == "job_search"
    assert result["entities"] == ["Python", "Machine Learning"]
    assert "intent_confidence" in result["metadata"]

async def test_query_understanding_handles_llm_failure(monkeypatch):
    """Test node gracefully handles LLM failure."""
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.classify_intent.side_effect = Exception("OpenRouter API down")

    monkeypatch.setattr("app.agents.nodes.query_understanding.llm_service", mock_llm)

    state: GraphRAGState = {
        "user_query": "Find Python jobs",
        "user_id": "user-123",
        "metadata": {}
    }

    # Act
    result = await query_understanding_node(state)

    # Assert
    assert result["intent"] == "unknown"
    assert result["entities"] == []
    assert result["metadata"]["error"] == "intent_classification_failed"
```

---

### 10.8 Running Tests

**Run all tests**:
```bash
pytest
```

**Run specific test types**:
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Specific test file
pytest tests/unit/test_auth_service.py

# Specific test function
pytest tests/unit/test_auth_service.py::TestAuthService::test_register_user_success
```

**With coverage report**:
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

**Parallel execution** (install pytest-xdist):
```bash
pip install pytest-xdist
pytest -n auto  # Use all CPU cores
```

---

### 10.9 Test Data Management

**Use fixtures for sample CSV files**:

**`tests/fixtures/skills_sample.csv`**:
```csv
ID,NAME,LEVEL,SUBCATEGORY,CATEGORY,TYPE,IS_SOFTWARE,IS_LANGUAGE,WIKI_LINK,DESCRIPTION,DESCRIPTION_SOURCE,VERSION,LATEST_VERSION
1,Python,advanced,Programming,Technology,Hard Skill,TRUE,TRUE,https://en.wikipedia.org/wiki/Python_(programming_language),High-level programming language,Wikipedia,3.11,3.12
2,Machine Learning,intermediate,AI/ML,Technology,Hard Skill,FALSE,FALSE,https://en.wikipedia.org/wiki/Machine_learning,Algorithms that improve through experience,Wikipedia,,
```

**Load in tests**:
```python
@pytest.fixture
def skills_csv_path():
    """Return path to sample skills CSV."""
    return Path(__file__).parent / "fixtures" / "skills_sample.csv"
```

---

### 10.10 MVP Testing Checklist

**Critical Paths to Test**:

- [x] **Authentication**
  - User registration
  - Login with valid/invalid credentials
  - JWT token generation and validation

- [x] **CSV Ingestion**
  - CSV validation (required columns, data types)
  - Skills ingestion creates Neo4j nodes
  - Jobs ingestion creates Neo4j nodes
  - Ingestion status tracking

- [x] **Query Processing**
  - Query understanding node
  - Vector similarity search
  - Graph traversal
  - Response generation

- [x] **Error Handling**
  - Custom exceptions raised correctly
  - HTTP status codes returned correctly
  - Error responses follow standard format

**Skip for MVP**:
- [ ] Load testing (add after scaling needs)
- [ ] E2E browser tests (frontend responsibility)
- [ ] Comprehensive edge cases (focus on happy path + critical errors)

---

### 10.11 Continuous Testing

**For MVP, manual testing is fine**:

```bash
# Before committing changes
pytest -m unit  # Fast unit tests (~5 seconds)

# Before pushing to main
pytest  # All tests (~30 seconds)
```

**After MVP validation, consider adding**:
- GitHub Actions CI (run tests on every commit)
- Pre-commit hooks (run unit tests before commit)
- Nightly integration tests (test against real external services)

---

This completes the **Test Strategy** section with practical, MVP-focused testing approach.

---

## 11. Security

### 11.1 MVP Security Philosophy

**For MVP, focus on essential security**:
- ✅ **Authentication**: JWT-based with secure password hashing
- ✅ **Input validation**: Pydantic models with type checking
- ✅ **CORS**: Configured for frontend origin
- ✅ **Environment secrets**: Never hardcode credentials
- ❌ **HTTPS/SSL**: Skip for local dev (add for production)
- ❌ **Rate limiting**: Add after scaling
- ❌ **WAF/DDoS protection**: Cloud provider handles this

**Security Mindset**:
- Prevent common attacks (SQL injection, XSS)
- Protect user credentials
- Validate all inputs
- Keep dependencies updated

---

### 11.2 Authentication & Authorization

#### **JWT-Based Authentication**

**Token Generation**:

**`app/utils/jwt.py`**:
```python
"""JWT token utilities."""
import jwt
from datetime import datetime, timedelta
from app.config import settings

def create_access_token(user_id: str) -> str:
    """
    Generate JWT access token for authenticated user.

    Args:
        user_id: Unique user identifier

    Returns:
        Encoded JWT token string
    """
    payload = {
        "sub": user_id,  # Subject (user ID)
        "iat": datetime.utcnow(),  # Issued at
        "exp": datetime.utcnow() + timedelta(
            minutes=settings.jwt_expiration_minutes
        )  # Expiration
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return token

def verify_access_token(token: str) -> str:
    """
    Verify JWT token and extract user ID.

    Args:
        token: JWT token string

    Returns:
        User ID from token payload

    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Token invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")

        if not user_id:
            raise jwt.InvalidTokenError("Missing user ID in token")

        return user_id

    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidTokenError:
        raise
```

---

#### **Authentication Dependency**

**`app/middleware/auth.py`**:
```python
"""Authentication middleware for protected endpoints."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from app.utils.jwt import verify_access_token
from app.exceptions import AuthenticationError

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security)
) -> str:
    """
    Extract and verify JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        User ID from verified token

    Raises:
        AuthenticationError: If token invalid or expired
    """
    token = credentials.credentials

    try:
        user_id = verify_access_token(token)
        return user_id

    except Exception as e:
        raise AuthenticationError(f"Invalid or expired token: {str(e)}")
```

**Usage in Protected Endpoints**:

```python
# app/api/ingest.py
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("/skills")
async def upload_skills_csv(
    file: UploadFile,
    user_id: str = Depends(get_current_user),  # Require authentication
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Upload skills CSV (authenticated users only)."""
    return await ingestion_service.start_skills_ingestion(file, user_id)
```

---

### 11.3 Password Security

**Use bcrypt for password hashing**:

**`app/services/auth_service.py`**:
```python
"""Authentication service with secure password handling."""
import bcrypt

class AuthService:
    """Handles user authentication."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with salt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        # Generate salt (cost factor = 12 rounds, good balance of security/performance)
        salt = bcrypt.gensalt(rounds=12)

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            salt
        )

        return password_hash.decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Plain text password from login
            password_hash: Stored bcrypt hash

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
```

**Password Validation** (Pydantic):

```python
# app/models/auth.py
from pydantic import BaseModel, EmailStr, Field, validator
import re

class RegisterRequest(BaseModel):
    """
    User registration with comprehensive password validation.

    Password Requirements:
    - Minimum 12 characters (increased from 8 for better security)
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character (@$!%*?&#)
    """
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Secure password with complexity requirements"
    )

    @validator('password')
    def validate_password_strength(cls, v):
        """
        Enforce password complexity requirements.

        This validator ensures strong passwords to prevent:
        - Brute force attacks (length requirement)
        - Dictionary attacks (complexity requirement)
        - Simple password guessing (mixed character types)

        Args:
            v: Password string to validate

        Returns:
            Validated password string

        Raises:
            ValueError: If password doesn't meet security requirements
        """
        # Length check (Pydantic Field handles this, but double-check)
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        # Uppercase letter requirement
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")

        # Lowercase letter requirement
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")

        # Digit requirement
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit (0-9)")

        # Special character requirement
        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError(
                "Password must contain at least one special character (@$!%*?&#)"
            )

        # Optional: Check for common weak patterns (can add more)
        weak_patterns = [
            r'password', r'12345', r'qwerty', r'abc123',
            r'admin', r'letmein', r'welcome'
        ]
        for pattern in weak_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError(
                    f"Password contains weak pattern '{pattern}'. Choose a stronger password."
                )

        return v
```

**Password Strength Examples**:

```python
# ✅ Valid passwords (meet all requirements)
"SecurePass123!"    # 15 chars, all requirements met
"MyApp@2025Secure"  # 16 chars, all requirements met
"P@ssw0rdStr0ng!"   # 15 chars, all requirements met

# ❌ Invalid passwords (fail requirements)
"short123!"         # Only 9 chars (< 12)
"nouppercase123!"   # Missing uppercase letter
"NOLOWERCASE123!"   # Missing lowercase letter
"NoSpecialChar123"  # Missing special character
"NoDigits@Here!"    # Missing digit
"Password123!"      # Contains weak pattern 'password'
```

**API Error Response**:

```json
// POST /api/auth/register
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter (A-Z)",
      "type": "value_error"
    }
  ]
}
```

---

### 11.4 Input Validation & Sanitization

**Pydantic Automatic Validation**:

```python
# app/models/query.py
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    """User query with validation."""
    query: str = Field(..., min_length=1, max_length=500)

    @validator('query')
    def sanitize_query(cls, v):
        """Remove dangerous characters from query."""
        # Strip leading/trailing whitespace
        v = v.strip()

        # Prevent empty queries
        if not v:
            raise ValueError("Query cannot be empty")

        return v
```

**CSV File Validation** (🔴 CRITICAL Security):

#### **Dependencies for File Upload Security**

Add to `requirements.txt`:
```txt
python-magic==0.4.27    # MIME type detection (libmagic wrapper)
```

**For macOS** (install libmagic):
```bash
brew install libmagic
```

**For Ubuntu/Debian**:
```bash
apt-get install libmagic1
```

#### **Comprehensive CSV Validation**

```python
# app/services/ingestion_service.py
from fastapi import UploadFile, HTTPException, status
import magic  # python-magic library
import csv
import io
import re
from pathlib import Path

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CSV_ROWS = 100_000  # CSV bomb protection
ALLOWED_EXTENSIONS = {'.csv'}  # Extension whitelist
ALLOWED_MIME_TYPES = {'text/csv', 'text/plain', 'application/csv'}  # Valid MIME types

async def validate_csv_file(file: UploadFile) -> bytes:
    """
    Comprehensive CSV file validation with security checks.

    Security Protections:
    1. File Extension Whitelist - Prevents disguised malicious files
    2. MIME Type Validation - Uses libmagic (not client-provided Content-Type)
    3. Filename Sanitization - Prevents path traversal attacks
    4. File Size Limit - Prevents memory exhaustion
    5. CSV Bomb Protection - Limits row count to prevent DoS

    Args:
        file: Uploaded file from FastAPI

    Returns:
        bytes: Validated file content

    Raises:
        HTTPException: If validation fails
    """
    # 1. Validate filename is not None
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    # 2. Sanitize filename (prevent path traversal)
    sanitized_filename = sanitize_filename(file.filename)
    if sanitized_filename != file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Only alphanumeric, hyphens, underscores, and dots allowed."
        )

    # 3. Validate file extension (whitelist)
    file_extension = Path(sanitized_filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{file_extension}'. Only .csv files are allowed."
        )

    # 4. Read file content
    content = await file.read()
    await file.seek(0)  # Reset file pointer for later use

    # 5. Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # 6. Validate MIME type using libmagic (not client-provided Content-Type)
    mime = magic.Magic(mime=True)
    detected_mime = mime.from_buffer(content)

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Detected MIME type: {detected_mime}. Expected: CSV file."
        )

    # 7. Validate CSV structure and row count (CSV bomb protection)
    try:
        csv_content = content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))

        # Count rows
        row_count = sum(1 for row in csv_reader)

        if row_count > MAX_CSV_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV file too large. Max {MAX_CSV_ROWS:,} rows allowed. Found {row_count:,} rows."
            )

        # Validate CSV has at least a header row
        if row_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty or has no header row."
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV encoding. File must be UTF-8 encoded."
        )
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )

    return content


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and injection attacks.

    Security Rules:
    - Remove path separators (/, \\)
    - Remove null bytes
    - Allow only: alphanumeric, hyphens, underscores, dots
    - Limit length to 255 characters

    Args:
        filename: Original filename from client

    Returns:
        str: Sanitized filename (safe for filesystem)
    """
    # Remove path components (prevent ../../../etc/passwd attacks)
    filename = Path(filename).name

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Only allow safe characters: alphanumeric, hyphen, underscore, dot
    safe_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
    if not safe_pattern.match(filename):
        # Replace unsafe characters with underscores
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Limit length
    if len(filename) > 255:
        # Keep extension, truncate name
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255 - len(ext)] + ext

    return filename
```

#### **Usage in Ingestion Service**

```python
# app/services/ingestion_service.py
class IngestionService:
    """Handles CSV ingestion with security validation."""

    async def start_skills_ingestion(
        self,
        file: UploadFile,
        user_id: str
    ) -> IngestionResponse:
        """
        Ingest skills CSV file with comprehensive validation.

        Args:
            file: Uploaded CSV file
            user_id: Current authenticated user ID

        Returns:
            IngestionResponse: Job status with job_id
        """
        # Validate file (comprehensive security checks)
        content = await validate_csv_file(file)

        # Parse CSV
        csv_data = self._parse_skills_csv(content.decode('utf-8'))

        # Create ingestion job in PostgreSQL
        job = await self.create_ingestion_job(
            user_id=user_id,
            filename=sanitize_filename(file.filename),  # Use sanitized filename
            row_count=len(csv_data)
        )

        # Process asynchronously (background task)
        await self.process_skills_batch(job.id, csv_data)

        return IngestionResponse(
            job_id=job.id,
            status="processing",
            message=f"Started processing {len(csv_data)} skills"
        )
```

#### **Transaction Rollback Strategy** (🟠 HIGH - Data Integrity)

**Why Transaction Management is Critical**:
- Prevents partial data corruption when batch processing fails
- Maintains graph consistency (no orphan nodes or broken relationships)
- Allows safe retry of failed batches
- Tracks exactly which batches succeeded/failed

##### **Neo4j Transaction Context Manager**

```python
# app/repositories/neo4j_repository.py
from neo4j import AsyncGraphDatabase, AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class Neo4jRepository:
    """Neo4j repository with transaction support."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for Neo4j transactions.

        Usage:
            async with neo4j_repo.transaction() as tx:
                await tx.run("CREATE (n:Node {name: $name})", name="test")
                # If exception occurs here, transaction is rolled back
                await tx.run("MATCH (n:Node) RETURN n")
        """
        async with self.driver.session() as session:
            async with session.begin_transaction() as tx:
                try:
                    yield tx
                    await tx.commit()
                except Exception as e:
                    await tx.rollback()
                    raise

    async def create_skills_batch_transactional(
        self,
        skills: list[dict],
        tx: AsyncSession
    ) -> dict:
        """
        Create skill nodes in a single transaction.

        Args:
            skills: List of skill dictionaries with name, embedding, etc.
            tx: Neo4j transaction session

        Returns:
            dict: Result with created_count, failed_count
        """
        query = """
        UNWIND $skills AS skill
        CREATE (s:Skill {
            id: skill.id,
            name: skill.name,
            description: skill.description,
            embedding: skill.embedding
        })
        RETURN count(s) as created_count
        """

        try:
            result = await tx.run(query, skills=skills)
            record = await result.single()
            return {"created_count": record["created_count"], "failed_count": 0}
        except Exception as e:
            # Transaction will be rolled back by context manager
            return {"created_count": 0, "failed_count": len(skills), "error": str(e)}
```

##### **Batch Processing with Rollback Strategy**

```python
# app/services/ingestion_service.py
from app.config import settings
from app.exceptions import IngestionError

class IngestionService:
    """Ingestion service with transaction management."""

    BATCH_SIZE = 1000  # Process 1000 rows per batch
    FAILURE_THRESHOLD = 0.10  # Rollback if >10% of batch fails

    async def process_skills_batch(
        self,
        job_id: str,
        csv_data: list[dict]
    ) -> None:
        """
        Process skills CSV in batches with transaction rollback.

        Rollback Strategy:
        - Each batch is processed in a Neo4j transaction
        - If >10% of rows in a batch fail, rollback entire batch
        - Track successful/failed batches in PostgreSQL
        - Allow resume from last successful batch on retry

        Args:
            job_id: IngestionJob ID for tracking
            csv_data: Parsed CSV data (list of dicts)
        """
        total_rows = len(csv_data)
        total_batches = (total_rows + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        successful_batches = 0
        failed_batch_number = None

        try:
            for batch_num in range(total_batches):
                # Update progress
                await self.ingestion_repo.update_job_progress(
                    job_id=job_id,
                    current_batch=batch_num + 1,
                    total_batches=total_batches,
                    status="processing"
                )

                # Extract current batch
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, total_rows)
                batch_data = csv_data[start_idx:end_idx]

                # Process batch with transaction
                result = await self._process_single_batch_transactional(
                    batch_data,
                    batch_num
                )

                # Check failure threshold
                failure_rate = result["failed_count"] / len(batch_data)
                if failure_rate > self.FAILURE_THRESHOLD:
                    failed_batch_number = batch_num + 1
                    raise IngestionError(
                        f"Batch {batch_num + 1} failed: {failure_rate*100:.1f}% failure rate "
                        f"(threshold: {self.FAILURE_THRESHOLD*100}%). "
                        f"Transaction rolled back."
                    )

                successful_batches += 1

            # Mark job as completed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="completed",
                successful_batches=successful_batches,
                error_batch=None
            )

        except IngestionError as e:
            # Mark job as partially completed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="partially_completed",
                successful_batches=successful_batches,
                error_batch=failed_batch_number,
                error_message=str(e)
            )
            raise

        except Exception as e:
            # Unexpected error - mark as failed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="failed",
                successful_batches=successful_batches,
                error_batch=failed_batch_number or (successful_batches + 1),
                error_message=str(e)
            )
            raise

    async def _process_single_batch_transactional(
        self,
        batch_data: list[dict],
        batch_num: int
    ) -> dict:
        """
        Process a single batch within a Neo4j transaction.

        Args:
            batch_data: Rows for this batch
            batch_num: Batch number (for logging)

        Returns:
            dict: {created_count, failed_count, error?}
        """
        # Generate embeddings for batch
        embeddings = await self.embedding_service.generate_batch_embeddings(
            [row["name"] + " " + row.get("description", "") for row in batch_data]
        )

        # Add embeddings to batch data
        for idx, row in enumerate(batch_data):
            row["embedding"] = embeddings[idx]

        # Create nodes in transaction
        async with self.neo4j_repo.transaction() as tx:
            result = await self.neo4j_repo.create_skills_batch_transactional(
                batch_data,
                tx
            )

        return result

    async def resume_failed_ingestion(
        self,
        job_id: str
    ) -> None:
        """
        Resume a partially completed ingestion from last successful batch.

        Args:
            job_id: IngestionJob ID to resume
        """
        job = await self.ingestion_repo.get_job_by_id(job_id)

        if job.status != "partially_completed":
            raise IngestionError(
                f"Cannot resume job {job_id}: status is {job.status}, expected 'partially_completed'"
            )

        # Re-read original CSV
        csv_data = await self._load_csv_from_storage(job.filename, job.user_id)

        # Skip already processed batches
        start_batch = job.successful_batches
        remaining_data = csv_data[start_batch * self.BATCH_SIZE:]

        # Process remaining batches
        await self.process_skills_batch(job_id, remaining_data)
```

##### **PostgreSQL Job Status Schema Update**

Add fields to track batch-level progress:

```python
# prisma/schema.prisma
model IngestionJob {
  id              String   @id @default(uuid())
  user_id         String
  filename        String
  status          String   // "processing", "completed", "failed", "partially_completed"
  total_rows      Int
  total_batches   Int?
  current_batch   Int?
  successful_batches Int?   // NEW: Track successful batches
  error_batch     Int?     // NEW: Which batch failed
  error_message   String?  // NEW: Error details
  created_at      DateTime @default(now())
  updated_at      DateTime @updatedAt

  user User @relation(fields: [user_id], references: [id])
}
```

##### **API Response with Batch Status**

```json
// GET /api/ingest/status/{job_id}
{
  "job_id": "abc-123",
  "status": "partially_completed",
  "total_rows": 50000,
  "total_batches": 50,
  "current_batch": 23,
  "successful_batches": 22,
  "error_batch": 23,
  "error_message": "Batch 23 failed: 15.2% failure rate (threshold: 10%). Transaction rolled back.",
  "can_resume": true,
  "created_at": "2025-10-22T14:30:00Z"
}
```

##### **Retry Logic for Transient Failures**

```python
# app/services/ingestion_service.py
import asyncio

async def _process_single_batch_with_retry(
    self,
    batch_data: list[dict],
    batch_num: int,
    max_retries: int = 3
) -> dict:
    """
    Process batch with exponential backoff retry for transient errors.

    Args:
        batch_data: Rows for this batch
        batch_num: Batch number
        max_retries: Maximum retry attempts

    Returns:
        dict: Processing result
    """
    for attempt in range(max_retries):
        try:
            return await self._process_single_batch_transactional(
                batch_data,
                batch_num
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Batch {batch_num} failed (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {wait_time}s... Error: {str(e)}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Batch {batch_num} failed after {max_retries} attempts. "
                    f"Error: {str(e)}"
                )
                raise
```

##### **Transaction Rollback Summary**

| Scenario | Action | PostgreSQL Status | Neo4j State |
|----------|--------|------------------|-------------|
| Batch succeeds | Commit transaction | Update progress | Nodes created |
| Batch <10% failure | Commit transaction | Update progress | Partial nodes created |
| Batch >10% failure | Rollback transaction | Mark "partially_completed" | No nodes created |
| Unexpected error | Rollback transaction | Mark "failed" | No nodes created |
| Resume requested | Process from error_batch | Update status to "processing" | Continue from last successful |

**Key Benefits**:
- **Atomicity**: Each batch is all-or-nothing (Neo4j transaction)
- **Consistency**: PostgreSQL tracks exact state for debugging
- **Resumable**: Can continue from last successful batch
- **Predictable**: Clear failure thresholds (10% rule)

#### **Security Test Cases**

```python
# tests/security/test_file_upload_security.py
import pytest
from fastapi.testclient import TestClient

def test_reject_non_csv_extension(client: TestClient, auth_token: str):
    """Test that non-CSV extensions are rejected."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("malicious.exe", b"fake content", "application/octet-stream")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Only .csv files are allowed" in response.json()["detail"]


def test_reject_fake_csv_mime_type(client: TestClient, auth_token: str):
    """Test that files with fake CSV MIME types are rejected."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Executable disguised as CSV
    files = {"file": ("fake.csv", b"\x4d\x5a\x90\x00", "text/csv")}  # MZ header (exe)

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_reject_csv_bomb(client: TestClient, auth_token: str):
    """Test CSV bomb protection (too many rows)."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Generate CSV with 100,001 rows
    large_csv = "name,description\n" + "\n".join(f"skill{i},desc{i}" for i in range(100001))
    files = {"file": ("bomb.csv", large_csv.encode(), "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "100,000 rows allowed" in response.json()["detail"]


def test_reject_path_traversal_filename(client: TestClient, auth_token: str):
    """Test that path traversal attacks in filename are prevented."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("../../../etc/passwd.csv", b"name,description\n", "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid filename" in response.json()["detail"]


def test_reject_oversized_file(client: TestClient, auth_token: str):
    """Test file size limit enforcement."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # 51MB file
    large_content = b"a" * (51 * 1024 * 1024)
    files = {"file": ("large.csv", large_content, "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]
```

#### **File Upload Security Summary**

| Security Check | Protection Against | Implementation |
|---------------|-------------------|----------------|
| Extension Whitelist | Malicious file types | Only `.csv` allowed |
| MIME Type Validation | Disguised malicious files | `python-magic` (libmagic) |
| Filename Sanitization | Path traversal attacks | Remove `../`, null bytes |
| File Size Limit | Memory exhaustion DoS | Max 50MB |
| CSV Row Limit | CSV bomb attacks | Max 100K rows |
| Encoding Validation | Injection attacks | UTF-8 only |

**Why python-magic?**
- Client-provided `Content-Type` headers are **untrusted** (easily spoofed)
- `python-magic` uses libmagic to analyze file content (same as `file` command)
- Detects actual file type by inspecting binary signatures and content
- Example: Detects `.exe` file even if client claims `Content-Type: text/csv`

---

### 11.5 Rate Limiting (🔴 CRITICAL for MVP)

**Why Rate Limiting is Critical**:
- Prevents brute force attacks on authentication endpoints
- Protects against API abuse and DoS attacks
- Prevents credential stuffing attacks
- Limits resource consumption from malicious users

#### **Dependencies**

Add to `requirements.txt`:
```txt
slowapi==0.1.9        # Rate limiting for FastAPI
redis==5.0.1          # Optional: Redis backend for distributed rate limiting
```

Install dependencies:
```bash
pip install slowapi redis
```

#### **Configuration in main.py**

**`app/main.py`**:
```python
"""FastAPI application with rate limiting."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=["100/minute"],  # Global default: 100 requests/minute
    storage_uri="memory://",  # Use in-memory storage (or redis:// for production)
)

app = FastAPI(title="Graph RAG API")

# Add rate limiter to app state
app.state.limiter = limiter

# Add custom rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail)
        },
        headers=exc.headers  # Include rate limit headers
    )
```

#### **Rate Limits for Authentication Endpoints**

**`app/api/auth.py`**:
```python
"""Authentication endpoints with rate limiting."""
from fastapi import APIRouter, Depends, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/hour")  # Max 3 registrations per hour per IP
async def register(
    request: Request,  # Required for slowapi
    user_data: UserCreate,
    auth_service: AuthService = Depends()
):
    """
    Register a new user account.

    Rate Limit: 3 registrations per hour per IP address
    Rationale: Prevents automated account creation and spam
    """
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(
    request: Request,  # Required for slowapi
    credentials: UserLogin,
    auth_service: AuthService = Depends()
):
    """
    User login with JWT token generation.

    Rate Limit: 5 login attempts per minute per IP address
    Rationale: Prevents brute force password attacks and credential stuffing
    """
    return await auth_service.authenticate_user(credentials)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")  # Max 10 token refreshes per minute
async def refresh_token(
    request: Request,
    refresh_token: str,
    auth_service: AuthService = Depends()
):
    """
    Refresh JWT access token.

    Rate Limit: 10 refreshes per minute per IP address
    Rationale: Normal usage rarely needs frequent refreshes
    """
    return await auth_service.refresh_access_token(refresh_token)
```

#### **Rate Limits for CSV Upload**

**`app/api/ingestion.py`**:
```python
"""Ingestion endpoints with rate limiting."""
from fastapi import APIRouter, Depends, UploadFile, File, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.ingestion_service import IngestionService
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/skills",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("3/hour")  # Max 3 CSV uploads per hour per user
async def ingest_skills_csv(
    request: Request,  # Required for slowapi
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """
    Upload and process skills CSV file.

    Rate Limit: 3 uploads per hour per user
    Rationale:
    - CSV processing is resource-intensive (embedding generation)
    - Prevents abuse of expensive LLM API calls
    - Normal users rarely need more than 3 uploads/hour
    """
    return await ingestion_service.start_skills_ingestion(file, user_id)


@router.post(
    "/jobs",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("3/hour")  # Max 3 CSV uploads per hour per user
async def ingest_jobs_csv(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """
    Upload and process jobs CSV file.

    Rate Limit: 3 uploads per hour per user
    """
    return await ingestion_service.start_jobs_ingestion(file, user_id)
```

#### **Rate Limit Response Headers**

When rate limits are applied, responses include standard headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1640000000
```

**Header Descriptions**:
- `X-RateLimit-Limit`: Maximum requests allowed in time window
- `X-RateLimit-Remaining`: Number of requests remaining
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

#### **Rate Limit Exceeded Response**

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640000060
Retry-After: 60

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "detail": "5 per 1 minute"
}
```

#### **Production: Redis Backend**

For production with multiple backend instances, use Redis for shared rate limit state:

**`app/main.py` (Production)**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Use Redis for distributed rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=f"redis://{settings.redis_host}:6379/0"  # Redis connection
)
```

**Add to `.env`**:
```bash
# Rate Limiting (Production)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

#### **Testing Rate Limits**

**Unit Test Example**:
```python
# tests/api/test_rate_limiting.py
import pytest
from fastapi.testclient import TestClient

def test_login_rate_limit(client: TestClient):
    """Test login endpoint rate limiting."""
    credentials = {"email": "test@example.com", "password": "wrong"}

    # Make 5 login attempts (should succeed)
    for i in range(5):
        response = client.post("/api/auth/login", json=credentials)
        assert response.status_code in [200, 401]  # 200 success or 401 invalid creds

    # 6th attempt should be rate limited
    response = client.post("/api/auth/login", json=credentials)
    assert response.status_code == 429
    assert "rate_limit_exceeded" in response.json()["error"]
    assert "X-RateLimit-Limit" in response.headers


def test_csv_upload_rate_limit(client: TestClient, auth_token: str):
    """Test CSV upload rate limiting."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("skills.csv", "name,description\nPython,Programming", "text/csv")}

    # Make 3 uploads (should succeed)
    for i in range(3):
        response = client.post("/api/ingest/skills", files=files, headers=headers)
        assert response.status_code == 202

    # 4th upload should be rate limited
    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 429
```

#### **Rate Limiting Summary**

| Endpoint | Rate Limit | Key | Rationale |
|----------|-----------|-----|-----------|
| `POST /auth/register` | 3/hour | IP | Prevent automated account creation |
| `POST /auth/login` | 5/minute | IP | Prevent brute force attacks |
| `POST /auth/refresh` | 10/minute | IP | Normal usage pattern |
| `POST /ingest/skills` | 3/hour | User | Expensive LLM operations |
| `POST /ingest/jobs` | 3/hour | User | Expensive LLM operations |
| Global default | 100/minute | IP | General API abuse prevention |

**Why These Limits?**
- **Login (5/min)**: Enough for legitimate users, too slow for brute force
- **Registration (3/hour)**: Prevents spam, allows genuine users
- **CSV Upload (3/hour)**: Each upload triggers expensive embedding generation
- **Global (100/min)**: Generous default for normal API usage

---

### 11.6 CORS Configuration

**Configure CORS for frontend**:

**`app/main.py`**:
```python
"""FastAPI application with CORS middleware."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(title="Graph RAG API")

# CORS Configuration
origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    # Add production frontend URL here when deploying
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specific origins (not "*" for production)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**For MVP development** (more permissive):

```python
# Only for local development - NEVER in production
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

### 11.6 Environment Variable Security

**Never commit secrets to version control**:

#### **JWT Secret Generation (CRITICAL)**

**Generate secure JWT secret** (minimum 64 characters hex):

```bash
# Generate cryptographically secure secret
openssl rand -hex 32

# Example output (64 characters):
# 3f7a8b2c9d4e1f0a6b5c8d7e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a
```

**Why 64 characters?**
- 32 bytes = 256 bits of entropy
- Prevents brute force attacks
- Meets OWASP recommendations

**NEVER use weak secrets like**:
- ❌ `"secret"`, `"mysecretkey"`, `"your-secret-here"`
- ❌ Dictionary words or common phrases
- ❌ Less than 64 characters

---

#### **Configuration File with Validation**

**`app/config.py`** - Add JWT secret validation:

```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Application configuration with security validation."""

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    # API Keys
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")

    # JWT - With Security Validation
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)

    # Application
    app_name: str = Field(default="Graph RAG API")
    debug: bool = Field(default=False)

    @validator('jwt_secret')
    def validate_jwt_secret_strength(cls, v):
        """Ensure JWT secret meets minimum security requirements."""
        if len(v) < 64:
            raise ValueError(
                'JWT_SECRET must be at least 64 characters '
                '(generate with: openssl rand -hex 32)'
            )

        # Check for common weak patterns
        weak_patterns = ['secret', 'password', 'test', 'demo', 'your-']
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                'JWT_SECRET contains weak pattern. '
                'Use cryptographically secure random key.'
            )

        return v

    @validator('openrouter_api_key')
    def validate_openrouter_key(cls, v):
        """Ensure OpenRouter API key is set."""
        if v.startswith('<') or v.startswith('your-'):
            raise ValueError(
                'OPENROUTER_API_KEY not set. '
                'Get API key from https://openrouter.ai'
            )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
```

**On Startup Validation**:
```python
# app/main.py
from app.config import settings

@app.on_event("startup")
async def validate_configuration():
    """Validate configuration on startup."""
    try:
        # Settings validation runs automatically via Pydantic
        logger.info("✅ Configuration validation passed")
        logger.info(f"JWT expiration: {settings.jwt_expiration_minutes} minutes")
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise SystemExit(1)
```

---

#### **Environment Files**

**`.env`** (add to `.gitignore` - NEVER commit):
```bash
# Database credentials
DATABASE_URL=postgresql://user:password@localhost:5432/graphrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# API Keys
OPENROUTER_API_KEY=sk-or-v1-abc123...

# JWT Secret - GENERATE NEW KEY (openssl rand -hex 32)
JWT_SECRET=3f7a8b2c9d4e1f0a6b5c8d7e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Application
DEBUG=True
```

**`.gitignore`**:
```
# Environment files
.env
.env.local
.env.production
.env.*.local

# Secrets
*.pem
*.key
secrets/
```

**`.env.example`** (commit this for documentation):
```bash
# ===============================================
# Graph RAG API Environment Configuration
# ===============================================

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/graphrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<set-secure-password>

# API Keys
OPENROUTER_API_KEY=<get-from-https://openrouter.ai>

# JWT Configuration
# CRITICAL: Generate with: openssl rand -hex 32
# NEVER use example keys in production!
JWT_SECRET=<GENERATE_WITH_OPENSSL_RAND_HEX_32>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Application Settings
DEBUG=False
APP_NAME=Graph RAG API

# ===============================================
# Setup Instructions:
# 1. Copy this file: cp .env.example .env
# 2. Generate JWT secret: openssl rand -hex 32
# 3. Set OpenRouter API key from https://openrouter.ai
# 4. Set secure database passwords
# 5. NEVER commit .env to version control
# ===============================================
```

---

#### **JWT Secret Rotation Strategy**

**When to rotate JWT secret**:
1. **Suspected compromise** - Rotate immediately
2. **Employee departure** - If they had access
3. **Scheduled rotation** - Every 90 days (production best practice)
4. **Before production launch** - Always use fresh secret

**How to rotate**:

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update .env
echo "JWT_SECRET=$NEW_SECRET" >> .env

# 3. Restart application
docker-compose restart backend

# 4. All users must re-login (tokens invalidated)
```

**Rotation impact**:
- ✅ Old tokens become invalid (secure)
- ⚠️ All users forced to re-login (expected)
- ⚠️ Active sessions terminated (security feature)

---

### 11.7 SQL Injection Prevention

**Prisma ORM handles parameterization automatically**:

```python
# ✅ Safe - Prisma uses parameterized queries
user = await prisma.user.find_unique(
    where={"email": user_email}  # Automatically sanitized
)

# ❌ NEVER do this (example of unsafe code)
# raw_query = f"SELECT * FROM users WHERE email = '{user_email}'"
# This is vulnerable to SQL injection
```

**Neo4j Cypher Queries with Parameters**:

```python
# ✅ Safe - Use parameters
query = """
CREATE (s:Skill {
    id: $id,
    name: $name,
    level: $level
})
RETURN s
"""
result = await neo4j_session.run(query, parameters={
    "id": skill_id,
    "name": skill_name,
    "level": skill_level
})

# ❌ NEVER do this (example of unsafe code)
# query = f"CREATE (s:Skill {{name: '{skill_name}'}}) RETURN s"
# This is vulnerable to Cypher injection
```

---

### 11.8 API Security Best Practices

#### **1. No Sensitive Data in Responses**

```python
# ✅ Good - Exclude password from response
class UserResponse(BaseModel):
    """User response (no password)."""
    id: str
    email: str
    created_at: str

    class Config:
        from_attributes = True

# ❌ Bad - Exposing password hash
class UserResponse(BaseModel):
    id: str
    email: str
    password_hash: str  # NEVER expose this!
```

#### **2. Authorization Checks**

```python
# app/api/ingest.py
@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Get ingestion status (only for job owner)."""
    job = await ingestion_service.get_job_status(job_id)

    # Authorization check - users can only access their own jobs
    if job.user_id != user_id:
        raise AuthorizationError("Access denied to this job")

    return job
```

#### **3. Error Message Safety**

```python
# ✅ Good - Generic error message
if not user:
    raise AuthenticationError("Invalid email or password")

# ❌ Bad - Reveals if email exists
if not user:
    raise AuthenticationError("Email not found in system")
```

---

### 11.9 Dependency Security

**Keep dependencies updated**:

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade fastapi prisma neo4j
```

**Pin versions in `requirements.txt`**:

```txt
fastapi==0.109.0
prisma==0.11.0
neo4j==5.15.0
bcrypt==4.1.2
pyjwt==2.8.0
```

**Use `requirements-dev.txt` for dev-only packages**:

```txt
pytest==7.4.3
black==23.12.1
isort==5.13.2
safety==2.3.5
```

---

### 11.10 Logging Security

**Never log sensitive data**:

```python
# ✅ Good
logger.info(f"User registered: user_id={user.id}, email={user.email}")

# ❌ Bad - NEVER log passwords, tokens, or API keys
logger.info(f"User registered with password: {password}")
logger.info(f"JWT token: {token}")
logger.info(f"API key: {api_key}")
```

**Log security events**:

```python
# app/services/auth_service.py
async def verify_credentials(self, email: str, password: str):
    """Verify login credentials and log attempts."""
    user = await self.user_repo.find_by_email(email)

    if not user:
        logger.warning(f"Failed login attempt for non-existent email: {email}")
        return None

    if not self.verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {user.id}")
        return None

    logger.info(f"Successful login: user_id={user.id}")
    return user
```

---

### 11.11 MVP Security Checklist

**Implemented for MVP**:

- [x] **JWT Authentication**: Secure token-based auth with strong secret generation
- [x] **Password Hashing**: bcrypt with 12 rounds
- [x] **Password Policy**: 12+ chars with complexity requirements (uppercase, lowercase, digit, special char)
- [x] **Input Validation**: Pydantic models for all inputs
- [x] **Rate Limiting**: 🔴 CRITICAL - Prevents brute force, DoS, and API abuse
  - Login: 5 attempts/minute per IP
  - Registration: 3 attempts/hour per IP
  - CSV Upload: 3 uploads/hour per user
- [x] **CORS Configuration**: Restrict to frontend origin
- [x] **Environment Secrets**: No hardcoded credentials, validated on startup
- [x] **SQL Injection Prevention**: Prisma parameterized queries
- [x] **Authorization Checks**: Users access only their own data
- [x] **Secure Logging**: No sensitive data in logs

**Skip for MVP** (add after validation):

- [ ] **HTTPS/SSL**: Local dev uses HTTP (add for production)
- [ ] **API Key Rotation**: Add after initial deployment
- [ ] **MFA (Two-Factor Auth)**: Add for production
- [ ] **Security Audits**: Schedule after MVP validation
- [ ] **WAF/DDoS Protection**: Cloud provider handles this

---

### 11.12 Pre-Production Security Additions

**When moving from MVP to production, add**:

1. **HTTPS/SSL Certificate**:
   ```bash
   # Using Let's Encrypt (free)
   certbot --nginx -d api.yourdomain.com
   ```

2. **Redis Backend for Rate Limiting**:
   ```python
   # Upgrade from in-memory to Redis for distributed rate limiting
   # See Section 11.5 for full configuration
   limiter = Limiter(
       key_func=get_remote_address,
       storage_uri=f"redis://{settings.redis_host}:6379/0"
   )
   ```

3. **Security Headers**:
   ```python
   from fastapi.middleware.trustedhost import TrustedHostMiddleware

   app.add_middleware(
       TrustedHostMiddleware,
       allowed_hosts=["api.yourdomain.com"]
   )
   ```

4. **Content Security Policy**:
   ```python
   @app.middleware("http")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["X-XSS-Protection"] = "1; mode=block"
       return response
   ```

---

### 11.13 Security Incident Response

**For MVP, keep it simple**:

1. **Monitor logs** for suspicious activity (failed login attempts, unusual query patterns)
2. **Revoke compromised tokens** by changing JWT secret (forces re-login)
3. **Reset user password** if account compromised
4. **Update dependencies** immediately if security vulnerability discovered

**After MVP validation, implement**:
- Automated security monitoring (Sentry, DataDog)
- Incident response playbook
- Security contact email
- Vulnerability disclosure policy

---

This completes the **Security** section with MVP-appropriate security measures.

---

## 12. Conclusion

### 12.1 Architecture Summary

This architecture document defines a **complete backend system** for the Graph RAG application:

- **FastAPI REST API** with JWT authentication
- **LangGraph agent workflow** for intelligent query processing
- **Neo4j graph database** for skills and jobs knowledge graph
- **PostgreSQL** for user management and ingestion tracking
- **MVP-focused approach** prioritizing functionality over production complexity

---

### 12.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Monolithic Architecture** | Simpler to develop and deploy for MVP |
| **Synchronous Processing** | No Celery needed - simple polling for ingestion status |
| **JWT Stateless Auth** | No session storage, scales horizontally |
| **Prisma ORM** | Type-safe database access for PostgreSQL |
| **LangGraph StateGraph** | Flexible agent workflow with conditional routing |
| **OpenRouter API** | Free LLM access for MVP (Llama 3.3 8B) |
| **Local Embeddings** | HuggingFace Transformers (no external API costs) |
| **Docker Compose** | Simple local development and deployment |

---

### 12.3 Next Steps

**Immediate Implementation Order**:

1. **Setup Infrastructure** (Day 1)
   - Initialize FastAPI project
   - Configure Docker Compose (PostgreSQL + Neo4j)
   - Setup Prisma schema and migrations

2. **Core Authentication** (Day 2-3)
   - Implement user registration and login
   - JWT token generation and validation
   - Test auth endpoints

3. **CSV Ingestion** (Day 4-6)
   - Skills CSV parsing and validation
   - Neo4j node creation with embeddings
   - Jobs CSV ingestion
   - Ingestion status tracking

4. **LangGraph Query Workflow** (Day 7-10)
   - Query understanding node
   - Vector similarity search
   - Graph traversal
   - Response generation
   - StateGraph orchestration

5. **Testing & Refinement** (Day 11-12)
   - Unit tests for critical paths
   - Integration tests for API endpoints
   - Manual testing with frontend

6. **Documentation & Deployment** (Day 13-14)
   - API documentation (OpenAPI/Swagger)
   - Deployment guide
   - Environment setup instructions

---

### 12.4 Success Criteria

**MVP is complete when**:

- ✅ Users can register and login
- ✅ Skills and Jobs CSVs can be uploaded and processed
- ✅ Knowledge graph is created in Neo4j with embeddings
- ✅ Users can ask natural language queries
- ✅ System returns relevant skills/jobs based on query
- ✅ Frontend can integrate with all API endpoints
- ✅ Basic error handling and logging works
- ✅ Critical paths have test coverage

**Post-MVP Enhancements**:
- Advanced query features (filters, sorting)
- Query history and saved searches
- Analytics and insights
- Performance optimization
- Production infrastructure (CI/CD, monitoring, backups)

---

### 12.5 Maintenance & Evolution

**Regular Maintenance**:
- Update dependencies monthly (security patches)
- Review logs for errors and anomalies
- Monitor database growth (Neo4j, PostgreSQL)
- Backup user data and ingestion jobs

**Future Enhancements** (after MVP validation):
- Multi-tenancy for organizations
- Advanced LLM features (query refinement, follow-ups)
- Real-time collaboration (WebSockets)
- Mobile app support
- Expanded knowledge graph (courses, certifications, companies)

---

## 13. Scalability Considerations

**Purpose**: This section addresses how the system will handle growth in users, data volume, and query load beyond MVP scale.

### 13.1 Scale Assumptions

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

### 13.2 Database Scalability

**Neo4j Scaling Strategy**:
1. **Immediate**: Query optimization (indexes, traversal limits)
2. **Short-term**: Vertical scaling (upgrade Aura tier)
3. **Long-term**: Read replicas, query result caching

**PostgreSQL Scaling Strategy**:
1. **Immediate**: Connection pooling (PgBouncer)
2. **Short-term**: Indexes, partition old data
3. **Long-term**: Read replicas for analytics

### 13.3 API Scalability

**Solutions**:
1. Horizontal scaling (2-5 FastAPI instances)
2. Background job processing (Celery + Redis)
3. Rate limiting (100 req/min per user)
4. Query result caching (Redis, 1-hour TTL)

**Impact**: Handle 1000+ concurrent users

### 13.4 LLM & Embedding Costs

**Cost Optimization**:
1. Query caching → 60-80% cache hit rate → 80% cost reduction
2. Upgrade to paid tier when free tier exhausted ($100-500/month)
3. GPU instance for embeddings → 10-50x faster generation

### 13.5 Performance Targets

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
