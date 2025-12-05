# Career Intelligence AI System

A conversational AI system for career guidance, powered by knowledge graphs and LangGraph.

## Overview

This system allows users to:
- Upload skills and job market data (CSV format)
- Ask natural language questions about careers, skills, and jobs
- Receive intelligent responses backed by a knowledge graph
- See source citations for all information

The system combines graph database technology with large language models to provide intelligent query responses about skills and job relationships using a RAG (Retrieval-Augmented Generation) workflow.

## Features

- 🔍 Intelligent query understanding with intent classification
- 📊 Graph-based knowledge representation using Neo4j
- 🤖 LangGraph-powered RAG workflow orchestration
- 🔐 JWT-based authentication and user management
- 📁 CSV data ingestion for skills and jobs with validation
- 🎯 Vector similarity search with embeddings
- 💬 Natural language query processing
- 📚 Source citation and attribution

## Technology Stack

### Frontend
- **React** 18 with TypeScript
- **Vite** - Modern build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client for API calls

### Backend
- **FastAPI** (Python 3.11+) - Modern web framework
- **LangGraph** 0.2.47 - Agent orchestration for RAG workflow
- **LangChain** 0.3.7 - LLM framework
- **OpenRouter API** - LLM completions
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation

### Databases
- **Neo4j** 5.x - Graph database for skills, jobs, and relationships
- **PostgreSQL** 15.x - Relational database for user data and query history
- **Prisma** - Python ORM for PostgreSQL

### AI/ML
- **HuggingFace Transformers** 4.45.0 - For embeddings
- **Sentence Transformers** 3.2.0 - Embedding generation
- **PyTorch** 2.5.0 - ML framework
- **OpenRouter** - LLM API gateway

### Authentication & Security
- **JWT** (PyJWT 2.9.0) - Token-based authentication
- **Passlib** with bcrypt - Password hashing
- **SlowAPI** - Rate limiting

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher (3.12 recommended for best compatibility)
- **Node.js**: 18.0 or higher (22+ recommended)
- **pip**: Latest version (upgrade with `pip install --upgrade pip`)
- **npm**: Latest version (comes with Node.js)

### External Services

- **Neo4j Database**: Cloud (Neo4j Aura) or local instance
- **PostgreSQL Database**: Cloud provider (Supabase/Render/Railway) or local instance
- **OpenRouter Account**: For LLM API access (free tier available)

### Optional Tools

- **Git**: For version control
- **Docker Desktop**: For containerized deployment (optional)
- **Virtual Environment Tool**: venv (included with Python) or virtualenv

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd Dev
```

### 2. Backend Setup

```bash
cd backend

# Create Python virtual environment (Python 3.11+ required)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/Mac
# OR
.venv\Scripts\activate  # On Windows

# Upgrade pip to latest version
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (testing, linting)
pip install -r requirements-dev.txt

# Copy environment variables template
cp .env.example .env
# Now edit .env with your actual credentials (see Environment Variables section)
```

### 3. Frontend Setup

```bash
cd frontend

# Install all dependencies
npm install

# Create environment file
cp .env.example .env
# Edit .env and set VITE_API_URL (default: http://localhost:8000)

# Verify installation
npm run dev  # Should start dev server on http://localhost:5173
```

### 4. Database Setup

```bash
# Configure your database credentials in backend/.env:
# - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# - DATABASE_URL (PostgreSQL connection string)

# Navigate to backend directory
cd backend

# Activate virtual environment
source .venv/bin/activate  # Unix/Mac

# Push Prisma schema to PostgreSQL (creates tables)
prisma db push

# Generate Prisma Python client
prisma generate
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` in both backend and frontend directories and configure:

**Backend (backend/.env)**:

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:password@host:5432/db` |
| `NEO4J_URI` | Neo4j connection URI | `neo4j+s://xxxxx.databases.neo4j.io` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Your Neo4j password | `your-password-here` |
| `JWT_SECRET_KEY` | Secret for JWT tokens | Generate with `openssl rand -hex 32` |
| `OPENROUTER_API_KEY` | Your OpenRouter API key | `sk-or-v1-xxxxx` |
| `OPENROUTER_MODEL` | LLM model to use | `meta-llama/llama-3.3-8b-instruct:free` |
| `EMBEDDING_MODEL` | HuggingFace embedding model | `sentence-transformers/all-MiniLM-L6-v2` |

**Frontend (frontend/.env)**:

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

### Getting API Keys and Credentials

**Neo4j Database:**
1. Sign up for free at https://neo4j.com/cloud/aura/
2. Create a new database instance (Free tier)
3. Copy the connection URI, username, and generated password
4. Use `neo4j+s://` protocol for secure cloud connections

**PostgreSQL Database:**
1. Use a cloud provider (Supabase, Render, Railway) or local PostgreSQL
2. For Supabase: Create project at https://supabase.com → Get connection string
3. For local: Install PostgreSQL and create a database
4. Format: `postgresql://username:password@host:port/database_name`

**OpenRouter API:**
1. Create account at https://openrouter.ai
2. Navigate to API Keys section: https://openrouter.ai/keys
3. Create a new API key
4. Copy the key (starts with `sk-or-v1-`)
5. Free tier available with models like `meta-llama/llama-3.3-8b-instruct:free`

**JWT Secret:**
```bash
# Generate a secure JWT secret
openssl rand -hex 32
```

## Running the Application

### Start Backend

```bash
cd backend
source .venv/bin/activate  # Activate virtual environment
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API documentation: http://localhost:8000/docs

### Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## Usage Guide

### 1. Register and Login

1. Navigate to http://localhost:5173
2. Click "Register" and create an account with:
   - Email address
   - Password (minimum 8 characters)
   - Full name
3. After registration, you'll be automatically logged in
4. Your JWT token is stored securely in browser localStorage

### 2. Upload Data

**Upload Skills CSV:**
1. Navigate to "Upload Data" from the navigation bar
2. Click "Upload Skills CSV" button
3. Select your skills CSV file (must have columns: `skill_id`, `skill_name`, `category`, etc.)
4. Wait for validation to complete
5. Review any warnings or errors
6. Click "Confirm Upload" to ingest data into Neo4j

**Upload Jobs CSV:**
1. After skills are uploaded, click "Upload Jobs CSV"
2. Select your jobs CSV file (must have columns: `job_id`, `job_title`, `required_skills`, etc.)
3. Wait for validation
4. Click "Confirm Upload"
5. Monitor ingestion progress

**Expected CSV Formats:**

Skills CSV:
```csv
skill_id,skill_name,category,proficiency_level
1,Python,Programming,Advanced
2,Machine Learning,Data Science,Intermediate
```

Jobs CSV:
```csv
job_id,job_title,required_skills,salary_range
1,Data Scientist,"Python,Machine Learning,Statistics",80000-120000
2,Software Engineer,"Python,JavaScript,SQL",70000-110000
```

### 3. Ask Questions

1. Navigate to "Chat" from the navigation bar
2. Type your question in natural language:
   - "What skills do I need for Data Scientist roles?"
   - "Which jobs require Python and Machine Learning?"
   - "What's the salary range for Software Engineers?"
3. Press Enter or click Send
4. Wait for the AI to process your query

### 4. Interpret Responses

The AI response includes:
- **Answer**: Natural language response to your question
- **Sources**: Citations showing where the information came from
  - Skills graph nodes
  - Job postings
  - Relationship connections
- **Confidence**: Query processing metrics
- **Related Skills**: Suggested related skills to explore

**Example Response:**
```
Question: "What skills are needed for Data Scientist roles?"

Answer: For Data Scientist roles, you typically need skills in Python,
Machine Learning, Statistics, and SQL. Advanced proficiency in Python
and intermediate knowledge of ML frameworks are commonly required.

Sources:
• Job: Data Scientist (ID: 1) - Required: Python, Machine Learning
• Skill: Python (Category: Programming, Level: Advanced)
• Skill: Machine Learning (Category: Data Science, Level: Intermediate)

Related: Deep Learning, Data Visualization, Big Data
```

## API Documentation

The backend provides an interactive API documentation interface powered by FastAPI.

**Access API docs**: http://localhost:8000/docs (Swagger UI)
**Alternative docs**: http://localhost:8000/redoc (ReDoc)

### Key Endpoints

**Health Check**:
- `GET /health` - Check service and database connectivity

**Authentication**:
- `POST /api/auth/register` - Register new user
  - Request: `{email, password, full_name}`
  - Response: `{access_token, user_id}`
- `POST /api/auth/login` - Login and get JWT token
  - Request: `{email, password}`
  - Response: `{access_token, token_type}`

**Data Ingestion**:
- `POST /api/ingest/skills` - Upload skills CSV (requires JWT)
  - Request: Multipart form with CSV file
  - Response: `{job_id, status, message}`
- `POST /api/ingest/jobs` - Upload jobs CSV (requires JWT)
  - Request: Multipart form with CSV file
  - Response: `{job_id, status, message}`
- `GET /api/ingest/status/{job_id}` - Check ingestion status
  - Response: `{status, progress, errors}`

**Query**:
- `POST /api/query/ask` - Send natural language query (requires JWT)
  - Request: `{query: string}`
  - Response: `{answer, sources, metadata, query_id}`

**Admin**:
- `GET /api/admin/stats` - Get system statistics (requires admin JWT)

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```bash
# Example with curl
curl -H "Authorization: Bearer your-jwt-token" \
  http://localhost:8000/api/query/ask \
  -d '{"query": "What skills are needed for data science?"}'
```

## Architecture

### High-Level System Diagram

```mermaid
graph TB
    A[React Frontend<br/>Port 5173] -->|HTTP + JWT| B[FastAPI Backend<br/>Port 8000]
    B --> C[Neo4j<br/>Graph DB]
    B --> D[PostgreSQL<br/>Relational DB]
    B --> E[LangGraph<br/>RAG Workflow]
    E --> F[OpenRouter<br/>LLM API]
    E --> G[HuggingFace<br/>Embeddings]

    style A fill:#61dafb
    style B fill:#009688
    style C fill:#008cc1
    style D fill:#336791
    style E fill:#1c3c3c
    style F fill:#ff6b6b
    style G fill:#ffd93d
```

### Data Flow

**1. CSV Upload Flow:**
```
User uploads CSV → Backend validates format → Stores in Neo4j graph
→ Creates vector embeddings → Indexes for fast search
```

**2. Query Processing Flow:**
```
User asks question → LangGraph workflow:
├─ Query understanding (classify intent)
├─ Vector search in Neo4j (find relevant nodes)
├─ Graph traversal for context (relationships)
├─ LLM response generation via OpenRouter
└─ Source attribution and citation
```

### Project Structure

```
project-root/
├── backend/              # FastAPI backend application
│   ├── app/
│   │   ├── api/          # FastAPI routes (auth, ingest, query, admin)
│   │   ├── agents/       # LangGraph nodes and workflow
│   │   ├── services/     # Business logic (auth, langgraph, neo4j)
│   │   ├── repositories/ # Database access (users, query_history)
│   │   ├── models/       # Pydantic request/response models
│   │   ├── utils/        # Utilities (logger, metrics, validation)
│   │   └── main.py       # FastAPI application entry point
│   ├── prisma/           # Database schema and migrations
│   ├── tests/            # Test suite
│   └── scripts/          # Utility scripts
├── frontend/             # React frontend application
│   └── src/
│       ├── pages/        # React pages (Home, Chat, Upload, Auth)
│       ├── components/   # React components
│       ├── hooks/        # Custom hooks
│       └── utils/        # Utilities (API client, auth)
├── data/                 # Sample data and CSV files
├── docs/                 # Project documentation
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Troubleshooting

### Port Already in Use

**Error**: `Address already in use`

**Solution**:
```bash
# Find process using port 8000 (backend)
lsof -i :8000
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Database Connection Failed

**Error**: `Could not connect to Neo4j` or `PostgreSQL connection refused`

**Neo4j Solutions**:
- Verify Neo4j is running and accessible
- Check NEO4J_URI in .env (use `neo4j+s://` for Aura)
- Verify credentials (username is usually `neo4j`)
- For Aura: Check if instance is active in console

**PostgreSQL Solutions**:
- Verify DATABASE_URL format is correct
- For cloud providers: Check if database is active
- For local: Ensure PostgreSQL service is running
- Test connection: `psql "postgresql://user:pass@host:5432/db"`

### Module Not Found

**Error**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Unix/Mac
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.11+
```

### JWT Authentication Error

**Error**: `401 Unauthorized` or `Invalid token`

**Solution**:
- Verify JWT token is stored in localStorage
- Token may have expired (24h default) - login again
- Check JWT_SECRET_KEY matches between backend instances
- Clear browser localStorage and login again

### Neo4j Vector Index Error

**Error**: `No index found for vector search` or `Index not ready`

**Solution**:
```bash
# Indexes are created automatically on first skill upload
# If you need to manually recreate indexes:
# 1. Access Neo4j Browser
# 2. Run: CREATE VECTOR INDEX skill_embeddings FOR (n:Skill) ON (n.embedding)
```

### CSV Upload Validation Errors

**Error**: `Invalid CSV format` or `Missing required columns`

**Solution**:
- Verify CSV has required columns (see Usage Guide above)
- Check for UTF-8 encoding
- Remove special characters from headers
- Ensure no empty rows
- Maximum file size: 100MB

### Frontend Build Errors

**Error**: `npm run dev fails` or TailwindCSS not working

**Solution**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev

# Verify Tailwind config
# - tailwind.config.js should have content: ["./src/**/*.{js,jsx,ts,tsx}"]
# - src/index.css should have @tailwind directives
```

### Python Package Installation Failures

**Error**: `pip install` fails on Windows (bcrypt, cryptography)

**Solution**:
```bash
# Install Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or use pre-built wheels
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Development

### Running Tests

**Backend**:
```bash
cd backend
source .venv/bin/activate
pytest                    # Run all tests
pytest tests/test_auth.py # Run specific test file
pytest -v                 # Verbose output
pytest --cov=app          # With coverage report
```

**Frontend**:
```bash
cd frontend
npm test                  # Run all tests
npm test -- --coverage    # With coverage
```

### Code Quality

**Backend Linting**:
```bash
cd backend
ruff check app/           # Fast Python linter
black app/                # Code formatter
mypy app/                 # Type checking
```

**Frontend Linting**:
```bash
cd frontend
npm run lint              # ESLint
npm run format            # Prettier
```

### Adding New Features

1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes following existing patterns
3. Write tests for new functionality
4. Update documentation
5. Run linting and tests
6. Submit pull request

## Performance Considerations

- **Embeddings**: Generated on first upload, cached in Neo4j (384-dimensional vectors)
- **Vector Search**: Optimized with HNSW index for sub-second queries
- **Rate Limiting**: 100 requests per minute per user (configurable)
- **Database Connection Pooling**: Automatic with Prisma and Neo4j driver
- **Async Processing**: All I/O operations use async/await for better concurrency

## Security

- Passwords hashed with bcrypt (12 rounds)
- JWT tokens with 24-hour expiration
- CORS configured for frontend origin only
- Rate limiting on all API endpoints
- Input validation with Pydantic
- SQL injection protection via Prisma ORM
- Cypher injection protection via parameterized queries

## License

Proprietary - All rights reserved

## Contributing

Please read the contribution guidelines before submitting pull requests.

## Recent Updates

### Conversation History Support (October 25, 2025)
Added full conversation context support for natural follow-up questions. System now maintains session history across multiple queries. See `docs/Updates/conversation-history-implementation.md` for implementation guide.

### Intent Detection Fix (October 25, 2025)
Framework and technology queries now properly trigger graph traversal. See `docs/Updates/intent-detection-fix-summary.md` for details.

### Frontend API Changes (October 25, 2025)
Enhanced response format with Graph Insights section and detailed error handling. See `docs/Updates/frontend-changes-needed.md` for implementation guide.

## Support

For issues and questions:
- Create an issue in the GitHub repository
- Check existing documentation in `/docs`
- Review API docs at http://localhost:8000/docs
- Check recent updates in `/docs/Updates` for latest fixes and features

---

**Version**: 1.0.0
**Last Updated**: 2025-10-25
# SkillSoule-graphRag
