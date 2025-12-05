# Graph RAG Backend

Backend API for the Knowledge Graph RAG System for Skills & Jobs.

## Prerequisites

- Python 3.11+
- Neo4j 5.x (Cloud or local)
- PostgreSQL 15.x

## Setup

### 1. Create Virtual Environment

**IMPORTANT**: Always use the virtual environment to ensure correct dependency versions.

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

### 2. Install Dependencies

```bash
# Ensure virtual environment is activated first
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Generate Prisma client
prisma generate
```

### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, JWT_SECRET, OPENROUTER_API_KEY
```

### 4. Run Tests

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/integration/test_langgraph_workflow.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

### 5. Run Development Server

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
├── app/
│   ├── agents/          # LangGraph workflow and nodes
│   ├── api/             # FastAPI routers
│   ├── models/          # Pydantic models
│   ├── repositories/    # Database access layer
│   ├── services/        # Business logic
│   ├── middleware/      # FastAPI middleware
│   └── utils/           # Utility functions
├── tests/
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   └── e2e/             # End-to-end tests
├── prisma/              # Prisma schema and migrations
└── scripts/             # Utility scripts
```

## Key Technologies

- **FastAPI** - Web framework
- **LangGraph** - Agent workflow orchestration
- **Neo4j** - Graph database
- **PostgreSQL** - Relational database
- **Prisma** - ORM for PostgreSQL
- **Pydantic** - Data validation

## Important Notes

### Virtual Environment Required

**All development and testing MUST be done within the virtual environment.**

The system Python may have different or outdated package versions. To verify you're in the correct environment:

```bash
# Check you're in venv
which python
# Should output: /path/to/backend/.venv/bin/python

# Verify LangGraph version
pip list | grep langgraph
# Should show: langgraph 0.2.47
```

If tests fail with ImportError, ensure you've activated the virtual environment first.

## Development Workflow

1. **Always activate venv first**: `source .venv/bin/activate`
2. **Run tests before committing**: `pytest`
3. **Run linting**: `ruff check app/`
4. **Format code**: `black app/`
5. **Type checking**: `mypy app/` (optional)

## Common Issues

### ImportError: cannot import name 'CheckpointAt'

This means you're not using the virtual environment or have an outdated LangGraph version.

**Fix**:
```bash
source .venv/bin/activate
pip install --upgrade langgraph==0.2.47
pytest tests/integration/test_langgraph_workflow.py -v
```

### Tests fail outside venv

**Solution**: Always activate the virtual environment before running tests or starting the server.

## Documentation

- [Architecture Documentation](../docs/architecture/)
- [API Documentation](http://localhost:8000/docs) (when server is running)
- [Tech Stack Details](../docs/architecture/tech-stack.md)
- [Coding Standards](../docs/architecture/coding-standards.md)
