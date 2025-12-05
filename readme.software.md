# Software Engineer's Guide to Graph RAG System

**Target Audience**: Software Engineers, AI Coding Agents, New Developers
**Last Updated**: 2025-10-25
**Project Version**: 1.0.0

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Quick Start Guide](#quick-start-guide)
3. [Architecture Overview](#architecture-overview)
4. [Project Structure](#project-structure)
5. [Development Workflow](#development-workflow)
6. [Running the Application](#running-the-application)
7. [Testing Guide](#testing-guide)
8. [Important Documents](#important-documents)
9. [Common Tasks](#common-tasks)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)
12. [Database Schema](#database-schema)

---

## Project Overview

### What Is This Project?

This is a **Graph-based RAG (Retrieval-Augmented Generation) System** for career intelligence that:
- Processes skills and jobs data into a Neo4j knowledge graph
- Enables natural language queries about careers, skills, and job requirements
- Uses LangGraph to orchestrate hybrid search (vector + graph traversal)
- Generates intelligent responses using LLM (via OpenRouter API)

### Core Technologies

**Frontend**:
- React 19 + Vite
- TailwindCSS for styling
- React Router for navigation
- Axios for HTTP requests

**Backend**:
- FastAPI (Python 3.11+)
- LangGraph 0.2.47 for RAG workflow orchestration
- Neo4j 5.x for graph database
- PostgreSQL 15.x for user data
- OpenRouter API for LLM completions
- HuggingFace Transformers for embeddings

### System Capabilities

1. **User Authentication**: JWT-based login/registration
2. **CSV Data Ingestion**: Upload skills and jobs taxonomy
3. **Knowledge Graph Construction**: Automated graph building with embeddings
4. **Natural Language Queries**: Ask questions about careers and skills
5. **Intelligent Responses**: LLM-powered answers with source citations

---

## Quick Start Guide

### Prerequisites Checklist

- [ ] Python 3.11 or higher installed
- [ ] Node.js 18+ installed
- [ ] Git installed
- [ ] Access to Neo4j database (cloud or local)
- [ ] Access to PostgreSQL database (cloud or local)
- [ ] OpenRouter API key (get free at https://openrouter.ai)

### Installation (5 Minutes)

```bash
# 1. Clone the repository
git clone <repository-url>
cd Dev

# 2. Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Configure backend environment
cp .env.example .env
# Edit .env and add your credentials (see Environment Configuration section)

# 4. Initialize database
prisma db push
prisma generate

# 5. Frontend setup
cd ../frontend
npm install
cp .env.example .env
# Edit .env and set VITE_API_URL=http://localhost:8000

# 6. Verify installation
cd ../backend && source .venv/bin/activate
uvicorn app.main:app --reload  # Backend on http://localhost:8000

# In new terminal:
cd frontend && npm run dev  # Frontend on http://localhost:5173
```

### Environment Configuration

**Backend `.env` (required)**:
```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/database_name

# Neo4j (use neo4j+s:// for cloud Aura)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secret-key-here

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-api-key
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embedding Model (local inference, no API key needed)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Frontend `.env` (required)**:
```bash
VITE_API_URL=http://localhost:8000
```

---

## Architecture Overview

### High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  React Frontend (Port 5173) - Login, Upload CSV, Chat           │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP + JWT Auth
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (Port 8000)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Auth API     │  │ Ingest API   │  │ Query API    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         ▼                  ▼                  ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Auth Service │  │ Ingest Svc   │  │ LangGraph    │          │
│  └──────┬───────┘  └──────┬───────┘  │ RAG Workflow │          │
│         │                  │          └──────┬───────┘          │
│         │                  │                  │                  │
└─────────┼──────────────────┼──────────────────┼──────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │  │     Neo4j        │  │  OpenRouter API  │
│  (User Data)     │  │  (Knowledge      │  │  (LLM Responses) │
│  Port 5432       │  │   Graph)         │  └──────────────────┘
└──────────────────┘  │  Port 7687       │
                      └──────────────────┘
```

### Data Flow

**1. CSV Upload Flow**:
```
User uploads CSV → FastAPI validates format → Generates embeddings
→ Creates Neo4j nodes (Job, Skill, Company, Location)
→ Creates relationships (REQUIRES, POSTED_BY, SIMILAR_TO)
→ Creates vector indexes → Progress updates via polling
```

**2. Query Processing Flow (LangGraph)**:
```
User asks question → LangGraph StateGraph:
├─ Node 1: Query Understanding (classify intent, generate embedding)
├─ Node 2: Vector Search (find similar nodes in Neo4j)
├─ Node 3: Graph Traversal (explore relationships 2-3 hops)
├─ Node 4: Context Construction (combine results)
└─ Node 5: Response Generation (call OpenRouter LLM)
→ Return answer + source citations
```

### Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19 + Vite | User interface |
| **API** | FastAPI 0.115 | REST API server |
| **Orchestration** | LangGraph 0.2.47 | RAG workflow state machine |
| **Graph DB** | Neo4j 5.x | Skills/jobs knowledge graph |
| **Relational DB** | PostgreSQL 15.x | User accounts, query history |
| **Embeddings** | HuggingFace Transformers | Local semantic embeddings (384-dim) |
| **LLM** | OpenRouter API | Natural language generation |
| **Auth** | JWT (PyJWT 2.9) | Token-based authentication |

---

## Project Structure

### Directory Tree

```
Dev/
├── backend/                      # FastAPI backend application
│   ├── app/
│   │   ├── api/                  # FastAPI route handlers
│   │   │   ├── auth.py           # POST /auth/register, /auth/login
│   │   │   ├── ingest.py         # POST /ingest/skills, /ingest/jobs
│   │   │   └── query.py          # POST /query/ask
│   │   ├── agents/               # LangGraph workflow
│   │   │   ├── graph.py          # StateGraph definition
│   │   │   └── nodes/            # 5 RAG nodes (understanding, vector, traversal, context, generation)
│   │   ├── services/             # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── ingestion_service.py
│   │   │   ├── langgraph_service.py
│   │   │   ├── embedding_service.py
│   │   │   └── openrouter_service.py
│   │   ├── repositories/         # Database access layer
│   │   │   ├── user_repository.py
│   │   │   ├── ingestion_job_repository.py
│   │   │   ├── query_history_repository.py
│   │   │   └── neo4j_repository.py
│   │   ├── models/               # Pydantic request/response schemas
│   │   ├── middleware/           # CORS, auth, error handling
│   │   ├── utils/                # Helpers (JWT, password, CSV validation, logging)
│   │   ├── config.py             # Environment configuration
│   │   ├── dependencies.py       # Dependency injection
│   │   └── main.py               # FastAPI app entry point
│   ├── prisma/
│   │   ├── schema.prisma         # PostgreSQL schema (User, IngestionJob, QueryHistory)
│   │   └── migrations/
│   ├── tests/                    # Test suite (unit, integration, e2e)
│   ├── scripts/                  # Utility scripts (seed Neo4j, setup indexes)
│   ├── docs/                     # Backend documentation
│   ├── requirements.txt          # Production dependencies
│   ├── requirements-dev.txt      # Development dependencies
│   ├── .env.example              # Environment template
│   └── README.md                 # Backend-specific README
│
├── frontend/                     # React frontend application
│   ├── src/
│   │   ├── pages/                # React pages (Home, Login, Register, Chat, Upload)
│   │   ├── components/           # Reusable React components
│   │   ├── hooks/                # Custom React hooks
│   │   ├── utils/                # API client, auth helpers
│   │   ├── App.jsx               # Main app component
│   │   └── main.jsx              # React entry point
│   ├── public/                   # Static assets
│   ├── tests/                    # Frontend tests (Vitest, Playwright)
│   ├── package.json              # Node dependencies
│   ├── vite.config.js            # Vite configuration
│   ├── tailwind.config.js        # TailwindCSS configuration
│   ├── .env.example              # Environment template
│   └── README.md                 # Frontend-specific README
│
├── data/                         # Sample CSV files for testing
│   ├── skills_sample.csv
│   └── jobs_sample.csv
│
├── docs/                         # Project documentation
│   ├── prd.md                    # Product Requirements Document
│   ├── architecture.md           # Technical Architecture (150+ pages)
│   ├── architecture/             # Sharded architecture docs
│   │   ├── tech-stack.md         # Technology stack details
│   │   ├── source-tree.md        # Project structure details
│   │   └── coding-standards.md   # Code conventions
│   ├── prd/                      # Sharded PRD documents
│   ├── stories/                  # User stories and epics
│   ├── qa/                       # QA documentation
│   └── brief.md                  # Project brief
│
├── .bmad-core/                   # BMad framework (agent workflows)
├── .env.example                  # Root environment template
├── README.md                     # Main project README
└── readme.software.md            # THIS FILE - Software engineer's guide
```

### Key Files Every Developer Should Know

| File | Purpose | When to Edit |
|------|---------|--------------|
| `backend/app/main.py` | FastAPI app entry point | Add new routers or middleware |
| `backend/app/config.py` | Environment configuration | Add new environment variables |
| `backend/app/dependencies.py` | Dependency injection | Add new services or repositories |
| `backend/prisma/schema.prisma` | PostgreSQL schema | Add new database tables |
| `backend/app/agents/graph.py` | LangGraph RAG workflow | Modify query processing logic |
| `frontend/src/App.jsx` | React router setup | Add new routes |
| `frontend/src/utils/api.js` | API client configuration | Add new API endpoints |
| `docs/prd.md` | Product requirements | Understand feature requirements |
| `docs/architecture.md` | Technical architecture | Understand system design |

---

## Development Workflow

### Day-to-Day Development

```bash
# 1. Start your day - activate backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. In new terminal - start frontend
cd frontend
npm run dev

# 3. Make code changes
# - Backend: Changes auto-reload (uvicorn --reload)
# - Frontend: Changes auto-reload (Vite HMR)

# 4. Check API documentation
# Navigate to: http://localhost:8000/docs (Swagger UI)

# 5. Run tests before committing
cd backend && pytest
cd frontend && npm test

# 6. Lint and format
cd backend && ruff check app/ && black app/
cd frontend && npm run lint
```

### Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature-name

# 2. Make changes and commit regularly
git add .
git commit -m "feat: add skill similarity search endpoint"

# 3. Run tests before pushing
pytest                    # Backend tests
npm test                  # Frontend tests

# 4. Push to remote
git push origin feature/your-feature-name

# 5. Create pull request (review docs/architecture.md for design patterns)
```

### Adding a New API Endpoint

**Example: Add a new endpoint to get user statistics**

```python
# 1. Create request/response models (backend/app/models/user.py)
class UserStatsResponse(BaseModel):
    total_queries: int
    total_ingestions: int
    last_activity: datetime

# 2. Add repository method (backend/app/repositories/user_repository.py)
async def get_user_stats(self, user_id: str) -> UserStatsResponse:
    # Implementation here
    pass

# 3. Add service method (backend/app/services/auth_service.py)
async def get_user_stats(self, user_id: str) -> UserStatsResponse:
    return await self.user_repo.get_user_stats(user_id)

# 4. Add API endpoint (backend/app/api/auth.py)
@router.get("/users/me/stats", response_model=UserStatsResponse)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.get_user_stats(current_user.id)

# 5. Test the endpoint
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/auth/users/me/stats
```

### Database Migrations

**PostgreSQL (Prisma)**:
```bash
# 1. Modify schema
vim backend/prisma/schema.prisma

# 2. Push changes to database
cd backend
prisma db push

# 3. Regenerate Prisma client
prisma generate
```

**Neo4j (Manual)**:
```bash
# 1. Create migration script
vim backend/scripts/migration_add_skill_categories.py

# 2. Run migration
python backend/scripts/migration_add_skill_categories.py
```

---

## Running the Application

### Development Mode (Local)

**Terminal 1 - Backend**:
```bash
cd backend
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend**:
```bash
cd frontend
npm run dev
```

**Access Points**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- API Docs (ReDoc): http://localhost:8000/redoc

### Production Mode (Docker)

```bash
# 1. Build and start all services
docker-compose up -d

# 2. Check logs
docker-compose logs -f backend

# 3. Stop services
docker-compose down
```

### Connecting Frontend to Backend

The frontend connects to the backend via environment variable:

**frontend/.env**:
```bash
VITE_API_URL=http://localhost:8000
```

All API calls use this base URL (see `frontend/src/utils/api.js`):
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

---

## Testing Guide

### Backend Testing

**Run all tests**:
```bash
cd backend
source .venv/bin/activate
pytest
```

**Run specific test file**:
```bash
pytest tests/unit/test_auth_service.py
```

**Run with coverage**:
```bash
pytest --cov=app --cov-report=html
# View coverage: open htmlcov/index.html
```

**Test categories**:
- `tests/unit/` - Unit tests (services, utilities)
- `tests/integration/` - Integration tests (API endpoints, databases)
- `tests/e2e/` - End-to-end tests (full workflows)

### Frontend Testing

**Run all tests**:
```bash
cd frontend
npm test
```

**Run with UI**:
```bash
npm run test:ui
```

**Run E2E tests (Playwright)**:
```bash
npm run test:e2e
```

**Run E2E with UI**:
```bash
npm run test:e2e:ui
```

### Manual Testing Workflow

**1. Test User Registration & Login**:
```bash
# Register new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "full_name": "Test User"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

**2. Test CSV Upload**:
- Navigate to http://localhost:5173/upload
- Upload `data/skills_sample.csv`
- Wait for validation and confirmation
- Click "Confirm Upload" and monitor progress

**3. Test Query Pipeline**:
```bash
# Get JWT token from login response
TOKEN="your-jwt-token-here"

# Send query
curl -X POST http://localhost:8000/api/query/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What skills are needed for Data Scientist roles?"}'
```

---

## Important Documents

### Essential Reading (Priority Order)

1. **README.md** - Start here for project overview
2. **THIS FILE (readme.software.md)** - Comprehensive developer guide
3. **docs/prd.md** - Product requirements (understand WHAT to build)
4. **docs/architecture.md** - Technical architecture (understand HOW it's built)
5. **backend/README.md** - Backend-specific setup and conventions
6. **frontend/README.md** - Frontend-specific setup and conventions

### Documentation Index

| Document | Location | Purpose |
|----------|----------|---------|
| **Product Requirements** | `docs/prd.md` | Full PRD with functional/non-functional requirements |
| **Architecture Document** | `docs/architecture.md` | 150+ pages technical architecture |
| **Tech Stack** | `docs/architecture/tech-stack.md` | Technology choices and justifications |
| **Source Tree** | `docs/architecture/source-tree.md` | Project structure details |
| **Coding Standards** | `docs/architecture/coding-standards.md` | Code conventions and patterns |
| **API Documentation** | http://localhost:8000/docs | Auto-generated Swagger UI (when backend running) |
| **User Stories** | `docs/stories/` | Epic-based user stories |
| **QA Documentation** | `docs/qa/` | Testing documentation |
| **Known Issues** | `docs/known-issues-mvp-v1.0.md` | Current bugs and limitations |
| **Project Brief** | `docs/brief.md` | High-level project overview |

### Architecture Documents (Sharded)

The architecture.md is split into multiple focused documents:

```
docs/architecture/
├── tech-stack.md                # Technology stack details
├── source-tree.md               # Project structure
├── coding-standards.md          # Code conventions
├── api-design.md                # API endpoint design
├── database-schema.md           # PostgreSQL & Neo4j schemas
├── langgraph-workflow.md        # RAG workflow details
├── deployment.md                # Deployment guide
└── security.md                  # Security considerations
```

### Learning Path for New Developers

**Day 1**: Orientation
- [ ] Read README.md
- [ ] Read this file (readme.software.md)
- [ ] Set up development environment
- [ ] Run the application locally
- [ ] Test basic user flow (register → login → upload CSV → ask query)

**Day 2-3**: Architecture Understanding
- [ ] Read docs/prd.md (focus on "Goals" and "Requirements" sections)
- [ ] Read docs/architecture/tech-stack.md
- [ ] Read docs/architecture/source-tree.md
- [ ] Explore backend code (start with `app/main.py`)
- [ ] Explore frontend code (start with `src/App.jsx`)

**Day 4-5**: Deep Dive
- [ ] Read docs/architecture/langgraph-workflow.md
- [ ] Understand LangGraph RAG pipeline in `backend/app/agents/`
- [ ] Study Neo4j schema and Cypher queries
- [ ] Review API endpoints in `backend/app/api/`
- [ ] Make first code contribution (pick a user story from `docs/stories/`)

---

## Common Tasks

### Check Application Health

```bash
# Backend health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "neo4j": "connected",
  "postgres": "connected"
}
```

### View Logs

**Backend logs**:
```bash
# If running with uvicorn
tail -f backend/logs/app.log

# If using Docker
docker-compose logs -f backend
```

**Frontend logs**:
- Check browser console (F12 → Console tab)
- Check terminal running `npm run dev`

### Reset Databases (Development Only)

```bash
# Reset PostgreSQL
cd backend
prisma migrate reset

# Reset Neo4j (WARNING: Deletes all data)
python scripts/reset_neo4j.py
```

### Create Neo4j Indexes

```bash
cd backend
python scripts/setup_indexes.py
```

### Seed Sample Data

```bash
cd backend
python scripts/seed_neo4j.py
```

### Check Progress of CSV Ingestion

**Via API**:
```bash
# Get job status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/ingest/status/{job_id}
```

**Via UI**:
- Navigate to Upload page
- View progress bar and stats during ingestion

---

## Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.11+
```

#### 2. Database Connection Failed

**Error**: `Could not connect to Neo4j`

**Solution**:
```bash
# Check Neo4j URI in .env
# For cloud Aura: neo4j+s://xxxxx.databases.neo4j.io
# For local: neo4j://localhost:7687

# Test connection manually
python -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('$NEO4J_URI', auth=('$NEO4J_USER', '$NEO4J_PASSWORD')); driver.verify_connectivity(); print('Connected!')"
```

**Error**: `PostgreSQL connection refused`

**Solution**:
```bash
# Verify DATABASE_URL format
# Correct: postgresql://user:password@host:5432/database_name
# Incorrect: postgres:// (old format)

# Test connection
psql "$DATABASE_URL" -c "SELECT 1"
```

#### 3. Frontend Can't Reach Backend

**Error**: `Network Error` in browser console

**Solution**:
```bash
# 1. Verify backend is running
curl http://localhost:8000/health

# 2. Check VITE_API_URL in frontend/.env
cat frontend/.env
# Should be: VITE_API_URL=http://localhost:8000

# 3. Restart frontend dev server
cd frontend && npm run dev
```

#### 4. JWT Authentication Errors

**Error**: `401 Unauthorized` or `Invalid token`

**Solution**:
- Clear browser localStorage: `localStorage.clear()`
- Login again to get new token
- Verify JWT_SECRET_KEY is same across backend restarts

#### 5. CSV Upload Validation Errors

**Error**: `Invalid CSV format` or `Missing required columns`

**Solution**:
- Check CSV has required columns (see docs/prd.md section on CSV format)
- Ensure UTF-8 encoding
- Remove special characters from column headers
- Verify no empty rows

#### 6. Prisma Client Not Generated

**Error**: `Cannot find module '@prisma/client'`

**Solution**:
```bash
cd backend
prisma generate
```

#### 7. Port Already in Use

**Error**: `Address already in use: 8000` or `5173`

**Solution**:
```bash
# Find and kill process on port 8000
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Debug Mode

**Enable debug logging**:

**Backend**:
```bash
# In backend/.env
DEBUG=True
LOG_LEVEL=DEBUG

# Restart backend
uvicorn app.main:app --reload --log-level debug
```

**Frontend**:
```javascript
// Add to src/main.jsx
if (import.meta.env.DEV) {
  console.log('Debug mode enabled');
}
```

### Performance Issues

**Slow query responses**:
- Check Neo4j vector indexes exist: `python scripts/setup_indexes.py`
- Review LangGraph workflow performance metrics in logs
- Verify OpenRouter API is responding (check logs for API latency)

**Slow CSV ingestion**:
- Check batch size in `.env` (default: 1000, try reducing to 500)
- Verify embedding service is not rate-limited
- Monitor Neo4j memory usage

---

## API Reference

### Base URL

```
Development: http://localhost:8000
Production: <TBD>
```

### Authentication

All protected endpoints require JWT token in Authorization header:
```bash
Authorization: Bearer <jwt-token>
```

### Endpoints

#### Authentication

**Register User**:
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "full_name": "John Doe"
}

Response 201:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

**Login**:
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### Data Ingestion

**Upload Skills CSV**:
```http
POST /api/ingest/skills
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <skills.csv>

Response 202:
{
  "job_id": "uuid",
  "status": "pending",
  "message": "CSV upload started"
}
```

**Upload Jobs CSV**:
```http
POST /api/ingest/jobs
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: <jobs.csv>

Response 202:
{
  "job_id": "uuid",
  "status": "pending",
  "message": "CSV upload started"
}
```

**Check Ingestion Status**:
```http
GET /api/ingest/status/{job_id}
Authorization: Bearer <token>

Response 200:
{
  "job_id": "uuid",
  "status": "processing",
  "total_records": 10523,
  "processed_records": 5234,
  "failed_records": 12,
  "estimated_time_remaining_seconds": 120
}
```

#### Query

**Ask Natural Language Question**:
```http
POST /api/query/ask
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "What skills are needed for Data Scientist roles?"
}

Response 200:
{
  "query_id": "uuid",
  "query": "What skills are needed for Data Scientist roles?",
  "answer": "For Data Scientist roles, you typically need skills in Python, Machine Learning, Statistics, and SQL...",
  "sources": [
    {
      "node_type": "Job",
      "node_id": "job-123",
      "properties": {
        "job_title": "Data Scientist",
        "company_name": "Tech Corp"
      }
    },
    {
      "node_type": "Skill",
      "node_id": "skill-456",
      "properties": {
        "skill_name": "Python",
        "category": "Programming"
      }
    }
  ],
  "metadata": {
    "processing_time_ms": 2341,
    "vector_search_time_ms": 234,
    "graph_traversal_time_ms": 567,
    "llm_generation_time_ms": 1540
  }
}
```

### Error Responses

All errors follow this format:
```json
{
  "detail": "Error message here",
  "status_code": 400,
  "error_type": "ValidationError"
}
```

Common status codes:
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

---

## Database Schema

### PostgreSQL Schema (Prisma)

**User Table**:
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**IngestionJob Table**:
```sql
CREATE TABLE ingestion_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  file_type VARCHAR(50),  -- 'skills' or 'jobs'
  status VARCHAR(50),     -- 'pending', 'processing', 'completed', 'failed'
  total_records INTEGER DEFAULT 0,
  processed_records INTEGER DEFAULT 0,
  failed_records INTEGER DEFAULT 0,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

**QueryHistory Table**:
```sql
CREATE TABLE query_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  query_text TEXT NOT NULL,
  response_text TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Neo4j Schema

**Node Types**:
1. **Skill**: `{id, name, level, category, subcategory, description, embedding[384]}`
2. **Job**: `{job_id, job_title, company_name, location, salary, description, embedding[384]}`
3. **Company**: `{company_name, description, cin, nic_code, embedding[384]}`
4. **Location**: `{location_name, district}`
5. **Category**: `{category_id, category_name}`
6. **Subcategory**: `{subcategory_id, subcategory_name}`

**Relationship Types**:
1. `Job -[REQUIRES {similarity_score}]-> Skill`
2. `Job -[POSTED_BY]-> Company`
3. `Job -[LOCATED_IN]-> Location`
4. `Skill -[BELONGS_TO_CATEGORY]-> Category`
5. `Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory`
6. `Skill -[SIMILAR_TO {similarity_score}]-> Skill`

**Vector Indexes**:
```cypher
CREATE VECTOR INDEX skill_embedding_idx 
FOR (s:Skill) ON (s.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX job_embedding_idx 
FOR (j:Job) ON (j.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};

CREATE VECTOR INDEX company_embedding_idx 
FOR (c:Company) ON (c.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
```

---

## Additional Resources

### External Documentation

- **FastAPI**: https://fastapi.tiangolo.com
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Neo4j**: https://neo4j.com/docs/
- **React**: https://react.dev
- **Vite**: https://vitejs.dev
- **Prisma**: https://www.prisma.io/docs
- **OpenRouter**: https://openrouter.ai/docs

### Community & Support

- Internal documentation: `docs/` directory
- GitHub Issues: <repository-issues-url>
- Team Slack: <slack-channel>

### Development Tools

**Recommended VS Code Extensions**:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Prisma (Prisma.prisma)
- ESLint (dbaeumer.vscode-eslint)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)
- REST Client (humao.rest-client)

**Recommended Browser Extensions**:
- React Developer Tools
- Neo4j Browser (built-in at http://localhost:7474)

---

## Quick Reference Commands

### Daily Commands

```bash
# Start backend
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Run tests
cd backend && pytest
cd frontend && npm test

# View logs
tail -f backend/logs/app.log
```

### Database Commands

```bash
# PostgreSQL migrations
cd backend && prisma db push && prisma generate

# Neo4j setup
python backend/scripts/setup_indexes.py

# Reset databases (dev only)
prisma migrate reset
python backend/scripts/reset_neo4j.py
```

### Code Quality

```bash
# Backend
cd backend
ruff check app/           # Lint
black app/                # Format
mypy app/                 # Type check
pytest --cov=app          # Test with coverage

# Frontend
cd frontend
npm run lint              # ESLint
npm run format            # Prettier
npm test                  # Run tests
```

---

**Last Updated**: 2025-10-25
**Maintained By**: Development Team
**Version**: 1.0.0

For questions or issues, consult the documentation in `docs/` or create a GitHub issue.
