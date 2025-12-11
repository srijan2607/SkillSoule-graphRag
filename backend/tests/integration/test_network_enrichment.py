"""
Integration tests for Network Enrichment Node - Story 7.4

Tests network metrics enrichment functionality:
- career_transition: Transition index and skill gaps
- skill_bridge: Shortest paths between skills
- skill_importance: Top skills by centrality
- job_similarity: Similar jobs via SIMILAR_JOB relationships
"""
import pytest
from app.agents.graph import GraphRAGState
from app.agents.nodes.network_enrichment import network_enrichment_node


@pytest.mark.asyncio
async def test_network_enrichment_skips_when_no_network_intents():
    """Test that node skips enrichment when no network intents detected."""
    state = GraphRAGState(
        user_query="What is Python?",
        user_id="test-user-123",
        intent="general",
        intents=["general"],
        entities=[],
        vector_results=[],
        graph_context=[],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify node skipped enrichment
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]
    assert enrichment["skill_paths"] == []
    assert enrichment["top_skills_by_centrality"] == []
    assert enrichment["similar_jobs"] == []
    assert enrichment["transition_metrics"] is None

    # Verify metadata
    assert result["metadata"]["network_enrichment_skipped"] is True
    assert result["metadata"]["skip_reason"] == "no_network_intents"


@pytest.mark.asyncio
async def test_network_enrichment_handles_skill_importance_intent():
    """Test enrichment with skill_importance intent."""
    state = GraphRAGState(
        user_query="What are the most important skills for software development?",
        user_id="test-user-456",
        intent="skill_importance",
        intents=["skill_importance"],
        entities=[
            {"type": "skill", "value": "python", "confidence": 0.8}
        ],
        vector_results=[
            {"node_type": "Skill", "id": "skill_python", "name": "Python", "score": 0.9}
        ],
        graph_context=[],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify enrichment occurred
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]

    # Should have top skills (even if empty due to GDS unavailability)
    assert "top_skills_by_centrality" in enrichment
    assert isinstance(enrichment["top_skills_by_centrality"], list)

    # Verify metadata
    assert result["metadata"]["network_enrichment_completed"] is True
    assert "skill_importance" in result["metadata"]["enrichment_intents"]
    assert result["metadata"]["top_skills_count"] >= 0


@pytest.mark.asyncio
async def test_network_enrichment_handles_skill_bridge_intent():
    """Test enrichment with skill_bridge intent."""
    state = GraphRAGState(
        user_query="Show me the skill path from Python to Machine Learning",
        user_id="test-user-789",
        intent="skill_bridge",
        intents=["skill_bridge"],
        entities=[
            {"type": "skill", "value": "python", "confidence": 0.9, "graph_node_id": "skill_python"},
            {"type": "skill", "value": "machine learning", "confidence": 0.8, "graph_node_id": "skill_ml"}
        ],
        vector_results=[
            {"node_type": "Skill", "id": "skill_python", "name": "Python", "score": 0.95},
            {"node_type": "Skill", "id": "skill_ml", "name": "Machine Learning", "score": 0.90}
        ],
        graph_context=[],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify enrichment occurred
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]

    # Should have skill_paths field (may be empty if GDS/APOC unavailable)
    assert "skill_paths" in enrichment
    assert isinstance(enrichment["skill_paths"], list)

    # Verify metadata
    assert result["metadata"]["network_enrichment_completed"] is True
    assert "skill_bridge" in result["metadata"]["enrichment_intents"]
    assert result["metadata"]["skill_paths_count"] >= 0


@pytest.mark.asyncio
async def test_network_enrichment_handles_career_transition_intent():
    """Test enrichment with career_transition intent."""
    state = GraphRAGState(
        user_query="How do I transition from Python developer to Data Scientist?",
        user_id="test-user-101",
        intent="career_transition",
        intents=["career_transition"],
        entities=[
            {"type": "skill", "value": "python", "confidence": 0.9, "graph_node_id": "skill_python"},
            {"type": "job", "value": "data scientist", "confidence": 0.85, "graph_node_id": "job_ds"}
        ],
        vector_results=[
            {"node_type": "Skill", "id": "skill_python", "name": "Python", "score": 0.95},
            {"node_type": "Job", "id": "job_ds", "job_id": "job_ds", "name": "Data Scientist", "score": 0.90}
        ],
        graph_context=[
            {"node_type": "Job", "node_id": "job_ds", "name": "Data Scientist"}
        ],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify enrichment occurred
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]

    # Should attempt to calculate transition metrics (may fail gracefully if service unavailable)
    assert "transition_metrics" in enrichment

    # Verify metadata
    assert result["metadata"]["network_enrichment_completed"] is True
    assert "career_transition" in result["metadata"]["enrichment_intents"]


@pytest.mark.asyncio
async def test_network_enrichment_handles_job_similarity_intent():
    """Test enrichment with job_similarity intent."""
    state = GraphRAGState(
        user_query="What jobs are similar to Software Engineer?",
        user_id="test-user-202",
        intent="job_similarity",
        intents=["job_similarity"],
        entities=[
            {"type": "job", "value": "software engineer", "confidence": 0.9, "graph_node_id": "job_se"}
        ],
        vector_results=[
            {"node_type": "Job", "id": "job_se", "job_id": "job_se", "name": "Software Engineer", "score": 0.95}
        ],
        graph_context=[
            {"node_type": "Job", "node_id": "job_se", "job_id": "job_se", "name": "Software Engineer"}
        ],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify enrichment occurred
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]

    # Should have similar_jobs field (may be empty if no relationships exist)
    assert "similar_jobs" in enrichment
    assert isinstance(enrichment["similar_jobs"], list)

    # Verify metadata
    assert result["metadata"]["network_enrichment_completed"] is True
    assert "job_similarity" in result["metadata"]["enrichment_intents"]
    assert result["metadata"]["similar_jobs_count"] >= 0


@pytest.mark.asyncio
async def test_network_enrichment_handles_multiple_intents():
    """Test enrichment with multiple network intents."""
    state = GraphRAGState(
        user_query="What are the top skills and how do I transition to Data Science?",
        user_id="test-user-303",
        intent="skill_importance",
        intents=["skill_importance", "career_transition"],
        entities=[
            {"type": "skill", "value": "python", "confidence": 0.9, "graph_node_id": "skill_python"},
            {"type": "job", "value": "data scientist", "confidence": 0.8, "graph_node_id": "job_ds"}
        ],
        vector_results=[
            {"node_type": "Skill", "id": "skill_python", "name": "Python", "score": 0.95}
        ],
        graph_context=[],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Verify enrichment occurred
    assert "network_enrichment" in result

    # Verify metadata shows both intents processed
    assert result["metadata"]["network_enrichment_completed"] is True
    assert "skill_importance" in result["metadata"]["enrichment_intents"]
    assert "career_transition" in result["metadata"]["enrichment_intents"]


@pytest.mark.asyncio
async def test_network_enrichment_gracefully_handles_missing_entities():
    """Test that node handles missing entities gracefully."""
    state = GraphRAGState(
        user_query="What are the top skills?",
        user_id="test-user-404",
        intent="skill_importance",
        intents=["skill_importance"],
        entities=[],  # No entities
        vector_results=[],
        graph_context=[],
        metadata={}
    )

    result = await network_enrichment_node(state)

    # Should not crash, return empty/default enrichment
    assert "network_enrichment" in result
    enrichment = result["network_enrichment"]

    # Should attempt enrichment (may succeed for skill_importance which doesn't need entities)
    assert "top_skills_by_centrality" in enrichment
    assert isinstance(enrichment["top_skills_by_centrality"], list)

    # Verify metadata
    assert result["metadata"]["network_enrichment_completed"] is True


@pytest.mark.asyncio
async def test_network_enrichment_populates_state_correctly():
    """Test that enrichment properly updates state fields."""
    state = GraphRAGState(
        user_query="Show me important skills",
        user_id="test-user-505",
        intent="skill_importance",
        intents=["skill_importance"],
        entities=[],
        vector_results=[],
        graph_context=[],
        metadata={"existing_key": "existing_value"}
    )

    result = await network_enrichment_node(state)

    # Verify network_enrichment field added
    assert "network_enrichment" in result
    assert isinstance(result["network_enrichment"], dict)

    # Verify required enrichment keys
    assert "skill_paths" in result["network_enrichment"]
    assert "top_skills_by_centrality" in result["network_enrichment"]
    assert "similar_jobs" in result["network_enrichment"]
    assert "transition_metrics" in result["network_enrichment"]

    # Verify metadata preserved and extended
    assert "metadata" in result
    assert result["metadata"]["existing_key"] == "existing_value"
    assert "network_enrichment_completed" in result["metadata"]


@pytest.mark.asyncio
async def test_workflow_integration_with_network_enrichment():
    """Test that network enrichment integrates properly into full workflow."""
    from app.agents.graph import create_rag_workflow

    workflow = create_rag_workflow()

    initial_state = GraphRAGState(
        user_query="What are the most important skills for backend development?",
        user_id="test-user-workflow"
    )

    result = await workflow.ainvoke(initial_state)

    # Verify network enrichment executed
    assert "network_enrichment" in result
    assert isinstance(result["network_enrichment"], dict)

    # Verify metadata indicates completion
    assert result["metadata"].get("network_enrichment_completed") is True or \
           result["metadata"].get("network_enrichment_skipped") is True

    # Verify final response generated
    assert result["final_response"] is not None
    assert isinstance(result["final_response"], str)
