# 10. Test Strategy

## 10.1 MVP Testing Philosophy

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

## 10.2 Test Framework Setup

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

## 10.3 Test Directory Structure

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

## 10.4 Shared Test Fixtures

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

## 10.5 Unit Tests

### **Test Authentication Service**

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

### **Test CSV Ingestion Service**

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

## 10.6 Integration Tests

### **Test Authentication API**

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

### **Test CSV Ingestion API**

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

## 10.7 Testing LangGraph Nodes

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

## 10.8 Running Tests

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

## 10.9 Test Data Management

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

## 10.10 MVP Testing Checklist

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

## 10.11 Continuous Testing

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
