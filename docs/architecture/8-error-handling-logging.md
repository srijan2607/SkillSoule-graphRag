# 8. Error Handling & Logging

## 8.1 Error Handling Philosophy

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

## 8.2 HTTP Status Codes

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

## 8.3 Custom Exception Types

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

## 8.4 FastAPI Exception Handlers

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

## 8.5 Error Response Format

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

## 8.6 Common Error Scenarios

### **1. Authentication Errors**

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

### **2. Resource Not Found**

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

### **3. Database Connection Failure**

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

### **4. CSV Validation Failure**

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

### **5. External Service Failure**

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

## 8.7 Logging Standards

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

## 8.8 Error Handling in LangGraph Nodes

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

## 8.9 MVP Logging Setup

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

## 8.10 When to Add Advanced Error Handling

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
