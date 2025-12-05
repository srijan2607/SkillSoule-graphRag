# 9. Coding Standards

## 9.1 Python Style Guide

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

## 9.2 Import Order

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

## 9.3 Naming Conventions

### **Files and Directories**

| Type | Convention | Example |
|------|------------|---------|
| **Modules** | snake_case | `auth_service.py`, `user_repository.py` |
| **Directories** | snake_case, plural for collections | `api/`, `services/`, `models/` |
| **Test files** | `test_*.py` | `test_auth_service.py` |

### **Code Elements**

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

## 9.4 Function and Class Standards

### **Type Hints Required**

```python
# ✅ Good - explicit types
async def get_user(user_id: str) -> Optional[User]:
    """Fetch user by ID."""
    return await user_repository.find_by_id(user_id)

# ❌ Bad - no type hints
async def get_user(user_id):
    return await user_repository.find_by_id(user_id)
```

### **Docstrings for Public Functions**

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

## 9.5 FastAPI Patterns

### **Router Definition**

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

### **Request/Response Models**

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

## 9.6 Service Layer Patterns

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

## 9.7 Repository Layer Patterns

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

## 9.8 LangGraph Node Patterns

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

## 9.9 Configuration Management

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

## 9.10 Code Organization Rules

### **File Size Limits**

| File Type | Max Lines | Rationale |
|-----------|-----------|-----------|
| **Routers** | 200 lines | Split into multiple routers if larger |
| **Services** | 300 lines | Split into multiple services by domain |
| **Repositories** | 200 lines | One repository per entity |
| **Nodes** | 100 lines | Each node should be focused |

### **Function Complexity**

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

## 9.11 Comment Guidelines

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

## 9.12 Error Handling Standards

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

## 9.13 Testing Naming Conventions

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

## 9.14 Dependency Injection Pattern

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

## 9.15 Async/Await Standards

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

## 9.16 Code Formatting Tools

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

## 9.17 MVP Coding Standards Summary

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
