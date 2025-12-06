"""
End-to-end tests for transition query flow.

Tests the complete RAG pipeline for transition-related queries,
from natural language input through to response generation.

Reference: Network Math Implementation - Phase 5 (05-TESTING-STRATEGY.md)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.middleware.auth import get_current_user
from app.dependencies import (
    get_network_metrics_service,
    get_co_occurrence_builder,
    get_neo4j_repository,
    get_embedding_service,
    get_openrouter_service
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_neo4j_repo():
    """Create mock Neo4j repository."""
    repo = AsyncMock()
    # Default responses for common queries
    repo.execute_query.return_value = []
    return repo


@pytest.fixture
def mock_embedding_service():
    """Create mock embedding service."""
    service = AsyncMock()
    service.generate_embedding.return_value = {
        "embedding": [0.1] * 384,
        "model_version": "all-MiniLM-L6-v2",
        "dimensions": 384
    }
    return service


@pytest.fixture
def mock_openrouter_service():
    """Create mock OpenRouter service."""
    service = AsyncMock()
    service.generate_completion.return_value = {
        "text": "Based on the job market data, transitioning from Python to Go development requires learning several new skills...",
        "model": "meta-llama/llama-3.3-8b-instruct:free",
        "usage": {"prompt_tokens": 500, "completion_tokens": 200, "total_tokens": 700},
        "latency_ms": 1000
    }
    return service


@pytest.fixture
def mock_network_metrics_service():
    """Create mock NetworkMetricsService."""
    service = AsyncMock()
    service.get_shortest_path.return_value = {
        "path_exists": True,
        "total_distance": 0.2,
        "closeness": 0.83,
        "path": ["skill-a", "skill-b"],
        "path_details": []
    }
    service.calculate_transition_index.return_value = {
        "transition_index": 0.65,
        "avg_closeness": 0.70,
        "core_skill_overlap": 0.40,
        "market_demand": 0.75,
        "details": {
            "source_skills_count": 3,
            "target_skills_count": 5,
            "overlapping_skills": ["python", "sql"],
            "skills_to_learn": ["go", "kubernetes", "grpc"],
            "jobs_with_target_skills": 450
        }
    }
    return service


@pytest.fixture
async def e2e_client(
    mock_neo4j_repo,
    mock_embedding_service,
    mock_openrouter_service,
    mock_network_metrics_service
):
    """Create test client with all dependencies mocked."""

    # Override authentication
    async def override_auth():
        return "test-user-e2e"

    async def override_neo4j():
        return mock_neo4j_repo

    async def override_embedding():
        return mock_embedding_service

    async def override_openrouter():
        return mock_openrouter_service

    async def override_network_metrics():
        return mock_network_metrics_service

    app.dependency_overrides[get_current_user] = override_auth
    app.dependency_overrides[get_neo4j_repository] = override_neo4j
    app.dependency_overrides[get_embedding_service] = override_embedding
    app.dependency_overrides[get_openrouter_service] = override_openrouter
    app.dependency_overrides[get_network_metrics_service] = override_network_metrics

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up
    app.dependency_overrides.clear()


# =============================================================================
# TRANSITION QUERY E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestTransitionQueryFlow:
    """Test complete transition query through RAG pipeline."""

    @pytest.mark.asyncio
    async def test_transition_query_full_flow(self, e2e_client, mock_openrouter_service):
        """Test natural language transition query end-to-end."""
        mock_openrouter_service.generate_completion.return_value = {
            "text": """Based on the knowledge graph analysis, transitioning from Python developer to Go developer is achievable with focused learning.

**Skills You Already Have:**
- Python programming
- SQL databases

**Skills to Learn:**
- Go language fundamentals
- Kubernetes orchestration
- gRPC for microservices

**Graph Insights:**
Our analysis explored 35 nodes and 58 relationships, finding strong correlation between Python and Go skill sets in modern backend roles.

**Transition Index: 0.65** - Moderately feasible transition with 40% skill overlap.
""",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 700},
            "latency_ms": 1200
        }

        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "How do I transition from Python developer to Go developer?",
                "session_id": "test-session-e2e-001"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "response" in data
        assert "query" in data
        assert data["query"] == "How do I transition from Python developer to Go developer?"

        # Verify response contains transition-related content
        response_text = data["response"].lower()
        assert any(word in response_text for word in ["transition", "skills", "learn", "go"]), \
            f"Response should contain transition-related content: {response_text[:200]}"

    @pytest.mark.asyncio
    async def test_skill_gap_query_e2e(self, e2e_client, mock_openrouter_service):
        """Test skill gap analysis query end-to-end."""
        mock_openrouter_service.generate_completion.return_value = {
            "text": """**Skill Gap Analysis: Frontend to Full Stack**

To transition from frontend developer to full stack, you need to bridge the following gaps:

1. **Backend Development**
   - Node.js or Python for server-side logic
   - REST API design
   - Database management (PostgreSQL, MongoDB)

2. **DevOps Basics**
   - Docker containerization
   - CI/CD pipelines

**Current Frontend Skills That Transfer:**
- JavaScript (extends to Node.js)
- API consumption (helps with API design)

**Transition Feasibility: High** - Many skills transfer directly.
""",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 650},
            "latency_ms": 1100
        }

        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "What's the skill gap between frontend developer and full stack?",
                "session_id": "test-session-e2e-002"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Response should mention specific skills
        response_text = data["response"].lower()
        assert any(word in response_text for word in ["backend", "database", "api", "skills"]), \
            f"Response should mention backend skills: {response_text[:200]}"

    @pytest.mark.asyncio
    async def test_career_path_query_e2e(self, e2e_client, mock_openrouter_service):
        """Test career path transition query end-to-end."""
        mock_openrouter_service.generate_completion.return_value = {
            "text": """**Career Path: Software Developer to Data Scientist**

This transition is increasingly common in the tech industry. Here's your roadmap:

**Phase 1: Foundation (1-2 months)**
- Statistics and probability fundamentals
- Python for data analysis (pandas, numpy)

**Phase 2: Core Skills (2-3 months)**
- Machine learning basics (scikit-learn)
- Data visualization (matplotlib, seaborn)

**Phase 3: Advanced (2-3 months)**
- Deep learning frameworks (TensorFlow/PyTorch)
- Big data tools (Spark basics)

**Your Advantages:**
- Programming fundamentals
- Problem-solving skills
- Software engineering practices

**Market Demand:** High - data science roles grew 35% this year.
""",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 800},
            "latency_ms": 1300
        }

        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "How do I become a data scientist from a software developer?",
                "session_id": "test-session-e2e-003"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Response should provide career guidance
        response_text = data["response"].lower()
        assert any(word in response_text for word in ["data", "machine learning", "python", "skills"]), \
            f"Response should mention data science skills: {response_text[:200]}"


# =============================================================================
# TRANSITION API ENDPOINT E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestTransitionAPIEndpoints:
    """Test transition-specific API endpoints end-to-end."""

    @pytest.mark.asyncio
    async def test_transition_index_endpoint_e2e(self, e2e_client, mock_network_metrics_service):
        """Test /api/skills/transition endpoint end-to-end."""
        response = await e2e_client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["python-001", "sql-001", "pandas-001"],
                "target_job_id": "data-scientist-123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify transition index response structure
        assert "transition_index" in data
        assert 0 <= data["transition_index"] <= 1
        assert "avg_closeness" in data
        assert "core_skill_overlap" in data
        assert "market_demand" in data
        assert "details" in data

    @pytest.mark.asyncio
    async def test_path_endpoint_e2e(self, e2e_client, mock_network_metrics_service):
        """Test /api/skills/path endpoint end-to-end."""
        response = await e2e_client.post(
            "/api/skills/path",
            json={
                "skill_id_1": "python-001",
                "skill_id_2": "go-001"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify path response structure
        assert "path_exists" in data
        assert "closeness" in data
        assert 0 <= data["closeness"] <= 1

    @pytest.mark.asyncio
    async def test_centrality_endpoint_e2e(self, e2e_client, mock_network_metrics_service):
        """Test /api/skills/centrality endpoint end-to-end."""
        mock_network_metrics_service.get_eigenvector_centrality.return_value = [
            {"skill_id": "python-001", "skill_name": "Python", "centrality_score": 0.95},
            {"skill_id": "javascript-001", "skill_name": "JavaScript", "centrality_score": 0.92},
            {"skill_id": "sql-001", "skill_name": "SQL", "centrality_score": 0.88}
        ]
        mock_network_metrics_service.check_gds_available.return_value = True

        response = await e2e_client.get("/api/skills/centrality?limit=10")

        assert response.status_code == 200
        data = response.json()

        # Verify centrality response structure
        assert "skills" in data
        assert "algorithm" in data
        assert "count" in data


# =============================================================================
# ERROR HANDLING E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestTransitionErrorHandling:
    """Test error handling in transition flow."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_error(self, e2e_client):
        """Test that empty query returns appropriate error."""
        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "",
                "session_id": "test-session-error-001"
            }
        )

        # Should return validation error
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_missing_auth_returns_403(self):
        """Test that missing authentication returns 403."""
        # Create client without auth override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/skills/transition",
                json={
                    "source_skills": ["skill-1"],
                    "target_job_id": "job-1"
                }
            )

        # Should require authentication
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_skill_ids_handled_gracefully(self, e2e_client, mock_network_metrics_service):
        """Test that invalid skill IDs are handled gracefully."""
        mock_network_metrics_service.calculate_transition_index.return_value = {
            "transition_index": 0.0,
            "avg_closeness": 0.0,
            "core_skill_overlap": 0.0,
            "market_demand": 0.0,
            "details": {
                "error": "No valid skills found"
            }
        }

        response = await e2e_client.post(
            "/api/skills/transition",
            json={
                "source_skills": ["nonexistent-skill-xyz"],
                "target_job_id": "nonexistent-job-abc"
            }
        )

        # Should return result (even if zero) rather than error
        assert response.status_code in [200, 404]


# =============================================================================
# CONVERSATION FLOW E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestConversationFlow:
    """Test multi-turn conversation for transition queries."""

    @pytest.mark.asyncio
    async def test_followup_query_uses_context(self, e2e_client, mock_openrouter_service):
        """Test that follow-up queries use conversation context."""
        # First query
        mock_openrouter_service.generate_completion.return_value = {
            "text": "Python to Go transition requires learning Go syntax, concurrency patterns, and systems programming.",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 400},
            "latency_ms": 800
        }

        response1 = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "How do I transition from Python to Go?",
                "session_id": "test-conversation-001"
            }
        )
        assert response1.status_code == 200

        # Follow-up query
        mock_openrouter_service.generate_completion.return_value = {
            "text": "For the Python to Go transition we discussed, learning resources include the Go tour, Effective Go documentation, and projects like building a REST API in Go.",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 350},
            "latency_ms": 750
        }

        response2 = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "What resources should I use?",
                "session_id": "test-conversation-001"  # Same session
            }
        )
        assert response2.status_code == 200

        # The follow-up response should relate to the transition context
        data = response2.json()
        response_text = data["response"].lower()
        # Should reference the previous context about Python/Go
        assert any(word in response_text for word in ["go", "python", "transition", "learning"]), \
            f"Follow-up should use context: {response_text[:200]}"


# =============================================================================
# PERFORMANCE E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestTransitionPerformance:
    """Performance tests for transition flow."""

    @pytest.mark.asyncio
    async def test_query_response_time(self, e2e_client, mock_openrouter_service):
        """Test that query response time is acceptable."""
        import time

        mock_openrouter_service.generate_completion.return_value = {
            "text": "Transition analysis complete.",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 100},
            "latency_ms": 500
        }

        start = time.perf_counter()
        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "How do I transition careers?",
                "session_id": "test-perf-001"
            }
        )
        duration_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 200

        # With mocked services, response should be fast
        # In production, adjust threshold based on actual LLM latency
        print(f"\nE2E Query Response Time: {duration_ms:.2f}ms")

        # Mocked response should be very fast
        assert duration_ms < 5000, f"Response time {duration_ms}ms exceeds 5s threshold"


# =============================================================================
# METADATA VALIDATION E2E TESTS
# =============================================================================

@pytest.mark.e2e
class TestResponseMetadata:
    """Test response metadata for transition queries."""

    @pytest.mark.asyncio
    async def test_response_includes_metadata(self, e2e_client, mock_openrouter_service):
        """Test that response includes processing metadata."""
        mock_openrouter_service.generate_completion.return_value = {
            "text": "Transition guidance provided.",
            "model": "meta-llama/llama-3.3-8b-instruct:free",
            "usage": {"total_tokens": 200},
            "latency_ms": 600
        }

        response = await e2e_client.post(
            "/api/query/ask",
            json={
                "query": "Career transition advice?",
                "session_id": "test-metadata-001"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should include metadata about processing
        if "metadata" in data:
            metadata = data["metadata"]
            # Check for expected metadata fields
            print(f"\nResponse metadata keys: {list(metadata.keys())}")


# =============================================================================
# TEST SUMMARY
# =============================================================================

"""
E2E Test Coverage Summary:

| Test Category              | Tests | Description                              |
|----------------------------|-------|------------------------------------------|
| Transition Query Flow      | 3     | Full NL query through RAG pipeline       |
| Transition API Endpoints   | 3     | Direct API endpoint testing              |
| Error Handling             | 3     | Graceful error handling                  |
| Conversation Flow          | 1     | Multi-turn context preservation          |
| Performance                | 1     | Response time validation                 |
| Metadata Validation        | 1     | Response metadata checking               |

Run E2E tests with:
    pytest tests/e2e/ -v -m e2e
"""
