# Source Tree

This section defines the complete directory structure and file organization for the backend monorepo.

---

## 6.1 Project Structure Overview

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

## 6.2 Core Files

### **`app/main.py`** - FastAPI Application Entry Point

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

### **`app/config.py`** - Configuration Management

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

### **`app/dependencies.py`** - Dependency Injection

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

## 6.3 Configuration Files

### **`.env.example`** - Environment Variables Template

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

### **`requirements.txt`** - Python Dependencies

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

### **`pyproject.toml`** - Python Project Metadata

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

### **`pytest.ini`** - Pytest Configuration

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

### **`prisma/schema.prisma`** - Prisma Schema

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

### **`Dockerfile`** - Container Definition

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

### **`docker-compose.yml`** - Multi-Container Orchestration

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

### **`.gitignore`** - Git Ignore Rules

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

## 6.4 Key Scripts

### **`scripts/setup_indexes.py`** - Neo4j Index Setup

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

### **`scripts/seed_neo4j.py`** - Sample Data Seeding

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

## 6.5 Module Import Pattern

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

## 6.6 Naming Conventions

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
