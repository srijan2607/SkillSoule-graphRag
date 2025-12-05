# Tech Stack

This section defines the complete technology stack with specific versions, installation requirements, and justifications aligned with the PRD's technical preferences.

## Core Backend Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Python** | 3.11+ | Backend language | - Excellent AI/ML ecosystem (LangGraph, Transformers)<br/>- FastAPI native support<br/>- Strong typing with type hints<br/>- Neo4j official driver support |
| **FastAPI** | 0.109+ | Web framework | - High performance (async support)<br/>- Automatic OpenAPI documentation<br/>- Native Pydantic integration<br/>- Built-in dependency injection<br/>- Excellent developer experience |
| **Uvicorn** | 0.27+ | ASGI server | - Production-ready async server<br/>- FastAPI recommended server<br/>- Hot reload for development |
| **Pydantic** | 2.5+ | Data validation | - Type-safe request/response models<br/>- Automatic validation<br/>- JSON schema generation<br/>- FastAPI integration |

## LangGraph & LLM Stack

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **LangGraph** | 0.0.60+ | Agent orchestration | - StateGraph for RAG workflows<br/>- Conditional routing for intent-based queries<br/>- Built-in state management<br/>- Debugging/visualization tools |
| **LangChain** | 0.1.0+ | LLM utilities | - Dependency for LangGraph<br/>- Prompt templates<br/>- Output parsers<br/>- Document loaders |
| **OpenAI SDK** | 1.10+ | LLM API client | - OpenRouter compatibility<br/>- Streaming support<br/>- Async operations<br/>- Error handling |

## Database Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Neo4j** | 5.x (Cloud) | Graph database | - Native graph data model<br/>- Vector similarity search (5.x)<br/>- Cypher query language<br/>- Cloud-hosted (Aura)<br/>- Excellent visualization tools |
| **neo4j-driver** | 5.15+ | Python Neo4j client | - Official Neo4j driver<br/>- Connection pooling<br/>- Transaction support<br/>- Async operations |
| **PostgreSQL** | 15.x (Cloud) | Relational database | - Robust ACID transactions<br/>- User authentication storage<br/>- Ingestion job tracking<br/>- Query history logging<br/>- Cloud-hosted (Supabase/Render) |
| **Prisma** | 5.8+ | PostgreSQL ORM | - Type-safe database queries<br/>- Automatic migrations<br/>- Python client generation<br/>- Database schema management |

## AI/ML Technologies

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **Transformers (HuggingFace)** | 4.36+ | Embedding generation | - `all-MiniLM-L6-v2` model support<br/>- Sentence embeddings (384-dim)<br/>- Local inference (no API cost)<br/>- Fast CPU inference |
| **sentence-transformers** | 2.2+ | Sentence embeddings | - Optimized embedding models<br/>- Batch processing<br/>- GPU acceleration support<br/>- Model caching |
| **torch** | 2.1+ | ML framework | - Dependency for Transformers<br/>- CPU inference for embeddings<br/>- No GPU required for MVP |
| **NumPy** | 1.24+ | Numerical computing | - Array operations<br/>- Embedding vector manipulation<br/>- Fast numerical computations |

## Authentication & Security

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **PyJWT** | 2.8+ | JWT tokens | - Token generation/verification<br/>- Expiration handling<br/>- HS256 signing<br/>- FastAPI integration |
| **passlib** | 1.7+ | Password hashing | - bcrypt hashing<br/>- Secure password storage<br/>- Salt generation<br/>- Verification utilities |
| **python-multipart** | 0.0.6+ | File upload | - FastAPI file upload support<br/>- Multipart form data parsing<br/>- Large file handling |

## Development & Utilities

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **python-dotenv** | 1.0+ | Environment config | - `.env` file loading<br/>- Environment variable management<br/>- Development/production separation |
| **pydantic-settings** | 2.1+ | Settings management | - Type-safe configuration<br/>- Environment validation<br/>- Settings inheritance |
| **httpx** | 0.26+ | HTTP client | - Async HTTP requests<br/>- OpenRouter API calls<br/>- Connection pooling<br/>- Timeout handling |
| **pandas** | 2.1+ | CSV processing | - CSV parsing and validation<br/>- Data transformation<br/>- Batch processing<br/>- Column validation |

## Testing & Quality

| Technology | Version | Purpose | Justification |
|------------|---------|---------|---------------|
| **pytest** | 7.4+ | Testing framework | - Unit and integration tests<br/>- Fixture support<br/>- Async test support<br/>- Coverage reporting |
| **pytest-asyncio** | 0.23+ | Async testing | - FastAPI async endpoint testing<br/>- Async fixture support |
| **black** | 23.12+ | Code formatting | - Consistent code style<br/>- PEP 8 compliance<br/>- Automatic formatting |
| **ruff** | 0.1+ | Linting | - Fast Python linter<br/>- Replaces flake8/pylint<br/>- Auto-fix support |
| **mypy** | 1.8+ | Type checking | - Static type validation<br/>- Catches type errors early<br/>- Better IDE support |

---

## External Services & APIs

| Service | Purpose | Configuration | Cost |
|---------|---------|---------------|------|
| **OpenRouter API** | LLM responses | - API key in `.env`<br/>- Model: `meta-llama/llama-3.3-8b-instruct:free`<br/>- Endpoint: `https://openrouter.ai/api/v1` | Free tier (MVP) |
| **Hugging Face Hub** | Embedding models | - Model: `sentence-transformers/all-MiniLM-L6-v2`<br/>- Local inference (no API key needed)<br/>- Model auto-download on first use | Free (local inference) |
| **Neo4j Aura** | Graph database hosting | - Connection URI in `.env`<br/>- Username/password auth<br/>- Free tier: 50K nodes, 175K relationships | Free tier (sufficient for MVP) |
| **PostgreSQL Cloud** | Relational database hosting | - Connection URI in `.env`<br/>- Supabase/Render/Railway<br/>- SSL connection required | Free tier |

---

## Technology Decision Rationale

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

## Dependencies Installation

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

## Environment Configuration

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

## Version Compatibility Matrix

| Python Version | FastAPI | LangGraph | Neo4j Driver | Prisma | Status |
|----------------|---------|-----------|--------------|--------|--------|
| 3.11 | ✅ 0.109+ | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | **Recommended** |
| 3.10 | ✅ 0.109+ | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | Supported |
| 3.9 | ⚠️ Limited | ⚠️ Limited | ✅ 5.15+ | ⚠️ 0.10 only | Not recommended |
| 3.12 | ⚠️ Beta | ✅ 0.0.60+ | ✅ 5.15+ | ✅ 0.11+ | Experimental |

**Recommendation**: Use **Python 3.11** for best compatibility and performance.

---
