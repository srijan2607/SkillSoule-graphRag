"""Unit tests for query models (NetworkInsights, etc.)."""

import pytest
from pydantic import ValidationError

from app.models.query import (
    SkillPathResult,
    SimilarJobResult,
    TopSkillResult,
    NetworkInsights,
    QueryResponse,
    SourceNode,
)


class TestSkillPathResult:
    """Test SkillPathResult model."""

    def test_skill_path_result_valid(self):
        """Test SkillPathResult with valid data."""
        path_result = SkillPathResult(
            from_skill="Python",
            to_skill="Machine Learning",
            path=["Python", "Data Analysis", "Machine Learning"],
            total_cost=2.5,
            closeness=0.85,
        )

        assert path_result.from_skill == "Python"
        assert path_result.to_skill == "Machine Learning"
        assert len(path_result.path) == 3
        assert path_result.total_cost == 2.5
        assert path_result.closeness == 0.85

    def test_skill_path_result_missing_fields(self):
        """Test SkillPathResult with missing required fields."""
        with pytest.raises(ValidationError):
            SkillPathResult(
                from_skill="Python",
                # Missing to_skill, path, total_cost, closeness
            )


class TestSimilarJobResult:
    """Test SimilarJobResult model."""

    def test_similar_job_result_valid(self):
        """Test SimilarJobResult with valid data."""
        job_result = SimilarJobResult(
            job_id="job_123",
            job_title="Backend Developer",
            company="Google",
            jaccard_score=0.78,
            shared_skills=["Python", "Django", "PostgreSQL"],
        )

        assert job_result.job_id == "job_123"
        assert job_result.job_title == "Backend Developer"
        assert job_result.company == "Google"
        assert job_result.jaccard_score == 0.78
        assert len(job_result.shared_skills) == 3

    def test_similar_job_result_optional_company(self):
        """Test SimilarJobResult with optional company field."""
        job_result = SimilarJobResult(
            job_id="job_456",
            job_title="Python Developer",
            jaccard_score=0.65,
            shared_skills=["Python"],
        )

        assert job_result.company is None
        assert len(job_result.shared_skills) == 1


class TestTopSkillResult:
    """Test TopSkillResult model."""

    def test_top_skill_result_valid(self):
        """Test TopSkillResult with valid data."""
        skill_result = TopSkillResult(
            skill_name="python",
            canonical_name="Python",
            centrality=0.92,
            demand_count=150,
        )

        assert skill_result.skill_name == "python"
        assert skill_result.canonical_name == "Python"
        assert skill_result.centrality == 0.92
        assert skill_result.demand_count == 150


class TestNetworkInsights:
    """Test NetworkInsights model."""

    def test_network_insights_empty(self):
        """Test NetworkInsights with no data (all defaults)."""
        insights = NetworkInsights()

        assert insights.skill_paths == []
        assert insights.similar_jobs == []
        assert insights.top_skills == []
        assert insights.transition_feasibility is None
        assert insights.graph_stats is None

    def test_network_insights_full(self):
        """Test NetworkInsights with complete data."""
        insights = NetworkInsights(
            skill_paths=[
                SkillPathResult(
                    from_skill="Python",
                    to_skill="Machine Learning",
                    path=["Python", "Data Analysis", "Machine Learning"],
                    total_cost=2.5,
                    closeness=0.85,
                )
            ],
            similar_jobs=[
                SimilarJobResult(
                    job_id="job_123",
                    job_title="Backend Developer",
                    company="Google",
                    jaccard_score=0.78,
                    shared_skills=["Python", "Django"],
                )
            ],
            top_skills=[
                TopSkillResult(
                    skill_name="python",
                    canonical_name="Python",
                    centrality=0.92,
                    demand_count=150,
                )
            ],
            transition_feasibility=0.75,
            graph_stats={"nodes": 35, "edges": 58, "density": 0.045},
        )

        assert len(insights.skill_paths) == 1
        assert len(insights.similar_jobs) == 1
        assert len(insights.top_skills) == 1
        assert insights.transition_feasibility == 0.75
        assert insights.graph_stats["nodes"] == 35

    def test_network_insights_serialization(self):
        """Test NetworkInsights serialization to dict."""
        insights = NetworkInsights(
            top_skills=[
                TopSkillResult(
                    skill_name="python",
                    canonical_name="Python",
                    centrality=0.92,
                    demand_count=150,
                )
            ],
            transition_feasibility=0.75,
        )

        data = insights.model_dump()

        assert "skill_paths" in data
        assert "similar_jobs" in data
        assert "top_skills" in data
        assert data["transition_feasibility"] == 0.75
        assert len(data["top_skills"]) == 1
        assert data["top_skills"][0]["skill_name"] == "python"


class TestQueryResponseWithNetworkInsights:
    """Test QueryResponse model with network_insights field."""

    def test_query_response_with_network_insights(self):
        """Test QueryResponse includes network_insights field."""
        response = QueryResponse(
            query="What skills do I need?",
            response="You need Python and SQL.",
            sources=[
                SourceNode(
                    node_type="Skill",
                    node_id="skill_python",
                    properties={"name": "Python"},
                )
            ],
            processing_time_ms=1234.5,
            metadata={"intent": "skill_requirement"},
            network_insights=NetworkInsights(
                top_skills=[
                    TopSkillResult(
                        skill_name="python",
                        canonical_name="Python",
                        centrality=0.92,
                        demand_count=150,
                    )
                ]
            ),
        )

        assert response.network_insights is not None
        assert len(response.network_insights.top_skills) == 1
        assert response.network_insights.top_skills[0].skill_name == "python"

    def test_query_response_without_network_insights(self):
        """Test QueryResponse works without network_insights (backward compatibility)."""
        response = QueryResponse(
            query="What skills do I need?",
            response="You need Python and SQL.",
            sources=[],
            processing_time_ms=1234.5,
            metadata={"intent": "skill_requirement"},
        )

        assert response.network_insights is None

    def test_query_response_serialization_with_network_insights(self):
        """Test QueryResponse serialization includes network_insights."""
        response = QueryResponse(
            query="What skills do I need?",
            response="You need Python and SQL.",
            sources=[],
            processing_time_ms=1234.5,
            metadata={"intent": "skill_requirement"},
            network_insights=NetworkInsights(
                transition_feasibility=0.75,
                graph_stats={"nodes": 35},
            ),
        )

        data = response.model_dump()

        assert "network_insights" in data
        assert data["network_insights"]["transition_feasibility"] == 0.75
        assert data["network_insights"]["graph_stats"]["nodes"] == 35

    def test_query_response_serialization_null_network_insights(self):
        """Test QueryResponse serialization with null network_insights."""
        response = QueryResponse(
            query="What skills do I need?",
            response="You need Python and SQL.",
            sources=[],
            processing_time_ms=1234.5,
        )

        data = response.model_dump()

        assert "network_insights" in data
        assert data["network_insights"] is None
