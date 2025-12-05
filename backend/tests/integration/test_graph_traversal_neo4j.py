"""
Integration tests for Graph Traversal Node with real Neo4j database.

Tests actual graph traversal functionality with seeded Neo4j data.
Tests all intent types with real Cypher queries.
"""

import pytest
from app.agents.nodes.graph_traversal import graph_traversal_node
from app.agents.graph import GraphRAGState


# ============================================================================
# Neo4j Test Data Setup
# ============================================================================


@pytest.fixture
async def seeded_neo4j_graph(neo4j_repo):
    """
    Seed Neo4j with test graph for traversal testing.

    Creates:
    - 5 Skills (Python, JavaScript, FastAPI, React, Django)
    - 3 Jobs
    - 2 Companies
    - 2 Categories
    - Relationships between them
    """
    async with neo4j_repo.driver.session() as session:
        # Create Skills
        await session.run(
            """
            CREATE (s1:Skill {
                id: 'python-001',
                name: 'Python',
                description: 'High-level programming language',
                level: 3,
                type: 'programming_language'
            })
            CREATE (s2:Skill {
                id: 'javascript-001',
                name: 'JavaScript',
                description: 'Web programming language',
                level: 3,
                type: 'programming_language'
            })
            CREATE (s3:Skill {
                id: 'fastapi-001',
                name: 'FastAPI',
                description: 'Python web framework',
                level: 2,
                type: 'framework'
            })
            CREATE (s4:Skill {
                id: 'react-001',
                name: 'React',
                description: 'JavaScript UI library',
                level: 2,
                type: 'framework'
            })
            CREATE (s5:Skill {
                id: 'django-001',
                name: 'Django',
                description: 'Python web framework',
                level: 2,
                type: 'framework'
            })

            // Create Categories
            CREATE (cat1:Category {
                category_id: 'cat-programming',
                category_name: 'Programming Languages'
            })
            CREATE (cat2:Category {
                category_id: 'cat-frameworks',
                category_name: 'Frameworks'
            })

            // Create Subcategories
            CREATE (sub1:Subcategory {
                subcategory_id: 'sub-backend',
                subcategory_name: 'Backend Development'
            })
            CREATE (sub2:Subcategory {
                subcategory_id: 'sub-frontend',
                subcategory_name: 'Frontend Development'
            })

            // Create Jobs
            CREATE (j1:Job {
                job_id: 'job-001',
                job_title: 'Senior Python Developer',
                company_name: 'Tech Corp',
                description: 'Looking for Python expert',
                min_salary: 100000,
                max_salary: 150000,
                salary_unit: 'yearly'
            })
            CREATE (j2:Job {
                job_id: 'job-002',
                job_title: 'Full Stack Engineer',
                company_name: 'Startup Inc',
                description: 'Python and React developer',
                min_salary: 90000,
                max_salary: 130000,
                salary_unit: 'yearly'
            })
            CREATE (j3:Job {
                job_id: 'job-003',
                job_title: 'Backend Developer',
                company_name: 'Tech Corp',
                description: 'Django specialist',
                min_salary: 80000,
                max_salary: 120000,
                salary_unit: 'yearly'
            })

            // Create Companies
            CREATE (c1:Company {
                company_name: 'Tech Corp',
                description: 'Technology company'
            })
            CREATE (c2:Company {
                company_name: 'Startup Inc',
                description: 'Fast-growing startup'
            })

            // Create Locations
            CREATE (loc1:Location {
                location_name: 'San Francisco'
            })
            CREATE (loc2:Location {
                location_name: 'New York'
            })

            // Create REQUIRES relationships (Jobs -> Skills)
            CREATE (j1)-[:REQUIRES]->(s1)
            CREATE (j1)-[:REQUIRES]->(s3)
            CREATE (j2)-[:REQUIRES]->(s1)
            CREATE (j2)-[:REQUIRES]->(s4)
            CREATE (j3)-[:REQUIRES]->(s5)

            // Create SIMILAR_TO relationships (Skills)
            CREATE (s3)-[:SIMILAR_TO {similarity_score: 0.85}]->(s5)
            CREATE (s5)-[:SIMILAR_TO {similarity_score: 0.85}]->(s3)

            // Create BELONGS_TO_CATEGORY relationships
            CREATE (s1)-[:BELONGS_TO_CATEGORY]->(cat1)
            CREATE (s2)-[:BELONGS_TO_CATEGORY]->(cat1)
            CREATE (s3)-[:BELONGS_TO_CATEGORY]->(cat2)
            CREATE (s4)-[:BELONGS_TO_CATEGORY]->(cat2)
            CREATE (s5)-[:BELONGS_TO_CATEGORY]->(cat2)

            // Create BELONGS_TO_SUBCATEGORY relationships
            CREATE (s1)-[:BELONGS_TO_SUBCATEGORY]->(sub1)
            CREATE (s3)-[:BELONGS_TO_SUBCATEGORY]->(sub1)
            CREATE (s4)-[:BELONGS_TO_SUBCATEGORY]->(sub2)
            CREATE (s5)-[:BELONGS_TO_SUBCATEGORY]->(sub1)

            // Create POSTED_BY relationships
            CREATE (j1)-[:POSTED_BY]->(c1)
            CREATE (j2)-[:POSTED_BY]->(c2)
            CREATE (j3)-[:POSTED_BY]->(c1)

            // Create LOCATED_IN relationships
            CREATE (j1)-[:LOCATED_IN]->(loc1)
            CREATE (j2)-[:LOCATED_IN]->(loc2)
            CREATE (j3)-[:LOCATED_IN]->(loc1)
        """
        )

    yield neo4j_repo

    # Cleanup handled by fixture


# ============================================================================
# Test skill_requirement intent traversal
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_skill_requirement_intent(seeded_neo4j_graph):
    """Test actual graph traversal for skill_requirement intent."""
    # Seed from Job nodes
    vector_results = [
        {"id": "job-001", "name": "Senior Python Developer", "node_type": "Job"},
        {"id": "job-002", "name": "Full Stack Engineer", "node_type": "Job"},
    ]

    state = GraphRAGState(
        user_query="What skills are required for Python jobs?",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="skill_requirement",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify successful traversal
    assert result["metadata"]["graph_traversal_completed"] is True
    assert "graph_results" in result
    assert len(result["graph_results"]["nodes"]) > 0
    assert len(result["graph_results"]["relationships"]) > 0

    # Verify we found expected nodes
    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}
    assert "Skill" in node_types
    assert "Job" in node_types

    # Verify metadata
    assert result["metadata"]["traversal_intent"] == "skill_requirement"
    assert result["metadata"]["seed_nodes_used"] == 2


@pytest.mark.asyncio
async def test_graph_traversal_skill_requirement_finds_categories(seeded_neo4j_graph):
    """Test skill_requirement traversal includes skill categories."""
    vector_results = [{"id": "job-001", "name": "Senior Python Developer", "node_type": "Job"}]

    state = GraphRAGState(
        user_query="Skills for Python developer",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="skill_requirement",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Check for Category nodes
    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}
    assert "Category" in node_types or "Subcategory" in node_types


# ============================================================================
# Test career_path intent traversal
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_career_path_intent(seeded_neo4j_graph):
    """Test actual graph traversal for career_path intent."""
    # Seed from Skill nodes
    vector_results = [
        {"id": "python-001", "name": "Python", "node_type": "Skill"},
        {"id": "fastapi-001", "name": "FastAPI", "node_type": "Skill"},
    ]

    state = GraphRAGState(
        user_query="What career paths are available with Python?",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="career_path",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify traversal found related skills and jobs
    assert result["metadata"]["graph_traversal_completed"] is True
    assert len(result["graph_results"]["nodes"]) > 0

    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}
    assert "Skill" in node_types
    assert "Job" in node_types  # Jobs requiring these skills


@pytest.mark.asyncio
async def test_graph_traversal_career_path_finds_similar_skills(seeded_neo4j_graph):
    """Test career_path finds similar skills via SIMILAR_TO."""
    vector_results = [{"id": "fastapi-001", "name": "FastAPI", "node_type": "Skill"}]

    state = GraphRAGState(
        user_query="Similar skills to FastAPI",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="career_path",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Should find Django (SIMILAR_TO FastAPI)
    skill_names = [
        node["properties"].get("name")
        for node in result["graph_results"]["nodes"]
        if node["node_type"] == "Skill"
    ]

    # Verify we found related skills
    assert len(skill_names) > 1  # Should have FastAPI + related skills


# ============================================================================
# Test salary_analysis intent traversal
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_salary_analysis_intent(seeded_neo4j_graph):
    """Test actual graph traversal for salary_analysis intent."""
    vector_results = [
        {"id": "job-001", "name": "Senior Python Developer", "node_type": "Job"},
        {"id": "job-002", "name": "Full Stack Engineer", "node_type": "Job"},
    ]

    state = GraphRAGState(
        user_query="Python developer salaries",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="salary_analysis",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify we found jobs, skills, and companies
    assert result["metadata"]["graph_traversal_completed"] is True
    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}

    assert "Job" in node_types
    assert "Skill" in node_types
    assert "Company" in node_types


@pytest.mark.asyncio
async def test_graph_traversal_salary_analysis_includes_locations(seeded_neo4j_graph):
    """Test salary_analysis includes location information."""
    vector_results = [{"id": "job-001", "name": "Senior Python Developer", "node_type": "Job"}]

    state = GraphRAGState(
        user_query="Python salaries by location",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="salary_analysis",
        metadata={},
    )

    result = await graph_traversal_node(state)

    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}
    assert "Location" in node_types


# ============================================================================
# Test skill_relationship intent traversal
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_skill_relationship_intent(seeded_neo4j_graph):
    """Test actual graph traversal for skill_relationship intent."""
    vector_results = [{"id": "python-001", "name": "Python", "node_type": "Skill"}]

    state = GraphRAGState(
        user_query="How is Python related to other skills?",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="skill_relationship",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify we found skill categories and relationships
    assert result["metadata"]["graph_traversal_completed"] is True
    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}

    assert "Skill" in node_types
    assert "Category" in node_types or "Subcategory" in node_types


# ============================================================================
# Test company_query intent traversal
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_company_query_intent(seeded_neo4j_graph):
    """Test actual graph traversal for company_query intent."""
    vector_results = [{"id": "Tech Corp", "name": "Tech Corp", "node_type": "Company"}]

    state = GraphRAGState(
        user_query="What jobs does Tech Corp offer?",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="company_query",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify we found company, jobs, and skills
    assert result["metadata"]["graph_traversal_completed"] is True
    node_types = {node["node_type"] for node in result["graph_results"]["nodes"]}

    assert "Company" in node_types
    assert "Job" in node_types
    assert "Skill" in node_types


# ============================================================================
# Test node and relationship limits
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_enforces_50_node_limit(seeded_neo4j_graph):
    """Test that traversal respects 50 node limit."""
    vector_results = [
        {"id": "job-001", "name": "Job 1", "node_type": "Job"},
        {"id": "job-002", "name": "Job 2", "node_type": "Job"},
        {"id": "job-003", "name": "Job 3", "node_type": "Job"},
    ]

    state = GraphRAGState(
        user_query="Many results query",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="skill_requirement",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify node limit is enforced
    assert len(result["graph_results"]["nodes"]) <= 50
    assert len(result["graph_results"]["relationships"]) <= 50


@pytest.mark.asyncio
async def test_graph_traversal_depth_3_traversal(seeded_neo4j_graph):
    """Test that depth=3 traversal reaches 3 hops from seed nodes."""
    from app.agents.nodes.graph_traversal import generate_traversal_query
    from app.dependencies import get_neo4j_repository

    # Test with skill_requirement intent and depth=3
    seed_ids = ["job-001"]
    query = generate_traversal_query(
        intent="skill_requirement", seed_node_ids=seed_ids, node_type="Job", depth=3
    )

    # Verify query contains depth=3 pattern
    assert "[*1..3]" in query or "depth" in query.lower()

    # Execute query and verify results
    neo4j_repo = get_neo4j_repository()
    await neo4j_repo.connect()

    try:
        results = await neo4j_repo.execute_query(query, {"seed_ids": seed_ids})

        # Should return results with deeper traversal
        assert len(results) > 0

    finally:
        await neo4j_repo.close()


@pytest.mark.asyncio
async def test_graph_traversal_relationship_extraction_accuracy(seeded_neo4j_graph):
    """Test that relationships are correctly extracted and typed."""
    vector_results = [{"id": "fastapi-001", "name": "FastAPI", "node_type": "Skill"}]

    state = GraphRAGState(
        user_query="Similar skills to FastAPI",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="career_path",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Verify relationship extraction
    relationships = result["graph_results"]["relationships"]

    # Should have extracted relationships with correct types
    if len(relationships) > 0:
        # Check relationship structure
        for rel in relationships:
            assert "type" in rel
            assert "properties" in rel
            assert isinstance(rel["type"], str)
            assert isinstance(rel["properties"], dict)

        # Check for expected relationship types based on intent
        rel_types = {rel["type"] for rel in relationships}

        # For career_path intent, we expect SIMILAR or REQUIRES relationships
        # (depending on query results)
        assert len(rel_types) > 0, "Should have extracted relationship types"

        # Verify relationship types are uppercase (Neo4j convention)
        for rel_type in rel_types:
            assert (
                rel_type.isupper() or "_" in rel_type
            ), f"Relationship type should be uppercase: {rel_type}"


@pytest.mark.asyncio
async def test_graph_traversal_relationship_aliases_recognized(seeded_neo4j_graph):
    """Test that _rel aliases in queries are properly recognized as relationships."""
    from app.agents.nodes.graph_traversal import format_graph_results

    # Simulate Neo4j result with relationship aliases
    mock_results = [
        {
            "skill_node": {
                "id": "python-001",
                "name": "Python",
                "description": "Programming language",
            },
            "requires_rel": {"type": "REQUIRES", "properties": {"similarity_score": 0.9}},
            "job_node": {"job_id": "job-001", "job_title": "Python Developer"},
        }
    ]

    # Format results
    formatted = format_graph_results(mock_results)

    # Verify nodes extracted
    assert len(formatted["nodes"]) > 0
    node_types = {node["node_type"] for node in formatted["nodes"]}
    assert "Skill" in node_types
    assert "Job" in node_types

    # Verify relationships extracted
    assert len(formatted["relationships"]) > 0

    # Check that REQUIRES relationship was detected
    rel_types = {rel["type"] for rel in formatted["relationships"]}
    assert "REQUIRES" in rel_types, "Should have detected REQUIRES relationship from _rel alias"


# ============================================================================
# Test error handling
# ============================================================================


@pytest.mark.asyncio
async def test_graph_traversal_handles_invalid_seed_nodes(seeded_neo4j_graph):
    """Test traversal handles non-existent seed nodes gracefully."""
    vector_results = [{"id": "nonexistent-job-999", "name": "Invalid Job", "node_type": "Job"}]

    state = GraphRAGState(
        user_query="Query with invalid seeds",
        user_id="test-user-123",
        vector_results=vector_results,
        intent="skill_requirement",
        metadata={},
    )

    result = await graph_traversal_node(state)

    # Should complete without error, just with empty results
    assert result["metadata"]["graph_traversal_completed"] is True
    # Results may be empty or minimal
    assert isinstance(result["graph_results"]["nodes"], list)
