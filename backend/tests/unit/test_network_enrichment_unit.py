"""
Unit tests for Network Enrichment Node - Story 7.4 (TEST-001)

Mocked tests that don't require live Neo4j connection for CI/CD reliability.
Uses unittest.mock to mock dependencies.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.agents.graph import GraphRAGState
from app.agents.nodes.network_enrichment import network_enrichment_node


class TestNetworkEnrichmentUnit:
    """Unit tests with mocked dependencies."""

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_skips_when_no_network_intents(
        self, mock_pipeline_service, mock_network_service
    ):
        """Test that node skips enrichment when no network intents detected."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        state = GraphRAGState(
            user_query="What is Python?",
            user_id="test-user-123",
            intent="general",
            intents=["general"],
            entities=[],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        assert enrichment["skill_paths"] == []
        assert enrichment["top_skills_by_centrality"] == []
        assert enrichment["similar_jobs"] == []
        assert enrichment["transition_metrics"] is None
        assert result["metadata"]["network_enrichment_skipped"] is True

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_neo4j_repository")
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_skill_importance_intent(
        self, mock_pipeline_service, mock_network_service, mock_neo4j_repo
    ):
        """Test enrichment with skill_importance intent (mocked)."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        mock_service = AsyncMock()
        mock_service.get_eigenvector_centrality = AsyncMock(return_value=[
            {"skill_id": "skill_python", "skill_name": "Python", "centrality_score": 0.95},
            {"skill_id": "skill_java", "skill_name": "Java", "centrality_score": 0.87}
        ])
        mock_network_service.return_value = mock_service

        state = GraphRAGState(
            user_query="What are the most important skills?",
            user_id="test-user-456",
            intent="skill_importance",
            intents=["skill_importance"],
            entities=[],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        assert len(enrichment["top_skills_by_centrality"]) == 2
        assert enrichment["top_skills_by_centrality"][0]["skill_name"] == "Python"
        assert result["metadata"]["network_enrichment_completed"] is True

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_skill_bridge_intent(
        self, mock_pipeline_service, mock_network_service
    ):
        """Test enrichment with skill_bridge intent (mocked)."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        mock_service = AsyncMock()
        mock_service.get_shortest_path = AsyncMock(return_value={
            "path_exists": True,
            "total_distance": 2.5,
            "closeness": 0.8,
            "path": ["skill_python", "skill_django", "skill_ml"],
            "path_details": [
                {"from": "skill_python", "to": "skill_django", "weight": 1.2},
                {"from": "skill_django", "to": "skill_ml", "weight": 1.3}
            ]
        })
        mock_network_service.return_value = mock_service

        state = GraphRAGState(
            user_query="Show me the skill path from Python to Machine Learning",
            user_id="test-user-789",
            intent="skill_bridge",
            intents=["skill_bridge"],
            entities=[
                {"type": "skill", "value": "python", "confidence": 0.9, "graph_node_id": "skill_python"},
                {"type": "skill", "value": "machine learning", "confidence": 0.8, "graph_node_id": "skill_ml"}
            ],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        assert len(enrichment["skill_paths"]) == 1
        assert enrichment["skill_paths"][0]["from_skill"] == "skill_python"
        assert enrichment["skill_paths"][0]["to_skill"] == "skill_ml"
        assert enrichment["skill_paths"][0]["distance"] == 2.5

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_career_transition_intent(
        self, mock_pipeline_service, mock_network_service
    ):
        """Test enrichment with career_transition intent (mocked)."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        mock_service = AsyncMock()
        mock_service.calculate_transition_index = AsyncMock(return_value={
            "transition_index": 0.75,
            "skill_gap": 3,
            "required_skills": ["Django", "PostgreSQL", "AWS"],
            "existing_skills": ["Python"]
        })
        mock_network_service.return_value = mock_service

        state = GraphRAGState(
            user_query="How do I transition from Python developer to Data Scientist?",
            user_id="test-user-101",
            intent="career_transition",
            intents=["career_transition"],
            entities=[
                {"type": "skill", "value": "python", "confidence": 0.9, "graph_node_id": "skill_python"},
                {"type": "job", "value": "data scientist", "confidence": 0.85, "graph_node_id": "job_ds"}
            ],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        assert enrichment["transition_metrics"] is not None
        assert enrichment["transition_metrics"]["transition_index"] == 0.75

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_neo4j_repository")
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_job_similarity_intent(
        self, mock_pipeline_service, mock_network_service, mock_neo4j_repo
    ):
        """Test enrichment with job_similarity intent (mocked)."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        mock_network_service.return_value = AsyncMock()

        mock_repo = AsyncMock()
        mock_repo.execute_query = AsyncMock(return_value=[
            {
                "job_id": "job_backend_dev",
                "job_title": "Backend Developer",
                "jaccard_score": 0.85,
                "shared_count": 8
            },
            {
                "job_id": "job_fullstack",
                "job_title": "Full Stack Developer",
                "jaccard_score": 0.72,
                "shared_count": 6
            }
        ])
        mock_repo.close = AsyncMock()
        mock_neo4j_repo.return_value = mock_repo

        state = GraphRAGState(
            user_query="What jobs are similar to Software Engineer?",
            user_id="test-user-202",
            intent="job_similarity",
            intents=["job_similarity"],
            entities=[
                {"type": "job", "value": "software engineer", "confidence": 0.9, "graph_node_id": "job_se"}
            ],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        assert len(enrichment["similar_jobs"]) == 2
        assert enrichment["similar_jobs"][0]["job_title"] == "Backend Developer"
        assert enrichment["similar_jobs"][0]["jaccard_score"] == 0.85
        # Verify repo.close() was called
        mock_repo.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.agents.nodes.network_enrichment.get_network_metrics_service")
    @patch("app.agents.nodes.network_enrichment.get_pipeline_monitoring_service")
    async def test_handles_service_unavailable_gracefully(
        self, mock_pipeline_service, mock_network_service
    ):
        """Test graceful handling when NetworkMetricsService is unavailable."""
        # Arrange
        mock_pipeline = Mock()
        mock_pipeline.emit_network_enrichment = AsyncMock()
        mock_pipeline_service.return_value = mock_pipeline

        # Simulate service unavailable
        mock_network_service.side_effect = Exception("Service unavailable")

        state = GraphRAGState(
            user_query="What are the most important skills?",
            user_id="test-user-500",
            intent="skill_importance",
            intents=["skill_importance"],
            entities=[],
            vector_results=[],
            graph_context=[],
            metadata={"metrics": Mock()}
        )

        # Act
        result = await network_enrichment_node(state)

        # Assert
        assert "network_enrichment" in result
        enrichment = result["network_enrichment"]
        # Should return empty enrichment, not crash
        assert enrichment["skill_paths"] == []
        assert enrichment["top_skills_by_centrality"] == []
        assert result["metadata"]["network_enrichment_error"] == "service_unavailable"
