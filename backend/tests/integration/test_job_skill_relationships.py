"""
Integration tests for Job-Skill relationship creation.

Tests the full workflow:
1. Skill matching with fuzzy logic
2. REQUIRES relationship creation
3. Orphan logging to PostgreSQL
4. Admin review dashboard queries
"""

import pytest
from app.services.skill_matching_service import SkillMatchingService
from app.services.job_skill_relationship_service import JobSkillRelationshipService


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_skill_relationship_creation_exact_matches(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test job-skill relationship creation with exact matches."""
    # Setup: Create skill taxonomy in Neo4j
    await neo4j_repo.execute_query(
        """
        CREATE (s1:Skill {id: 'python-001', name: 'Python'})
        CREATE (s2:Skill {id: 'fastapi-001', name: 'FastAPI'})
        CREATE (s3:Skill {id: 'neo4j-001', name: 'Neo4j'})
        """,
        {}
    )

    # Create test job
    await neo4j_repo.execute_query(
        """
        CREATE (j:Job {
            job_id: 'job-001',
            job_title: 'Backend Engineer',
            company_name: 'TestCorp'
        })
        """,
        {}
    )

    # Create services
    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Create relationships with exact skill matches
    jobs_data = [
        {
            "Job ID": "job-001",
            "standardized_skills": "Python, FastAPI, Neo4j",
            "similarity_scores": "0.95, 0.87, 0.92"
        }
    ]

    stats = await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-001"
    )

    # Verify statistics
    assert stats["relationships_created"] == 3
    assert stats["exact_matches"] == 3
    assert stats["fuzzy_matches"] == 0
    assert stats["orphans_created"] == 0

    # Verify relationships in Neo4j
    relationships = await neo4j_repo.execute_query(
        """
        MATCH (j:Job {job_id: 'job-001'})-[r:REQUIRES]->(s:Skill)
        RETURN s.name as skill_name, r.similarity_score as score, r.match_confidence as confidence
        ORDER BY s.name
        """,
        {}
    )

    assert len(relationships) == 3

    # Check Python relationship
    python_rel = next(r for r in relationships if r["skill_name"] == "Python")
    assert python_rel["score"] == 0.95
    assert python_rel["confidence"] == 1.0

    # Check FastAPI relationship
    fastapi_rel = next(r for r in relationships if r["skill_name"] == "FastAPI")
    assert fastapi_rel["score"] == 0.87
    assert fastapi_rel["confidence"] == 1.0

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_skill_relationship_with_fuzzy_match(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test relationship creation with fuzzy matching for typos."""
    # Setup: Create skill taxonomy
    await neo4j_repo.execute_query(
        """
        CREATE (s1:Skill {id: 'python-001', name: 'Python'})
        CREATE (s2:Skill {id: 'react-001', name: 'React'})
        CREATE (j:Job {job_id: 'job-002', job_title: 'Full Stack Developer'})
        """,
        {}
    )

    # Create services
    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Create relationships with typos
    jobs_data = [
        {
            "Job ID": "job-002",
            "standardized_skills": "Python, Pyton, React",  # "Pyton" is typo
            "similarity_scores": None
        }
    ]

    stats = await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-002"
    )

    # Verify statistics
    assert stats["relationships_created"] == 3
    assert stats["exact_matches"] == 2  # Python (first), React
    assert stats["fuzzy_matches"] == 1  # Pyton → Python
    assert stats["orphans_created"] == 0

    # Verify fuzzy match created relationship to Python
    relationships = await neo4j_repo.execute_query(
        """
        MATCH (j:Job {job_id: 'job-002'})-[r:REQUIRES]->(s:Skill)
        RETURN s.name as skill_name, r.match_confidence as confidence
        ORDER BY s.name
        """,
        {}
    )

    assert len(relationships) == 2  # Only 2 unique skills (Python, React)

    # Check Python has 2 relationships (exact + fuzzy)
    # Note: MERGE prevents duplicates, so only 1 relationship exists
    python_rels = [r for r in relationships if r["skill_name"] == "Python"]
    assert len(python_rels) == 1

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orphan_creation_and_logging(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test orphan creation for unknown skills and PostgreSQL logging."""
    # Setup: Create minimal skill taxonomy
    await neo4j_repo.execute_query(
        """
        CREATE (s1:Skill {id: 'python-001', name: 'Python'})
        CREATE (j:Job {job_id: 'job-003', job_title: 'Blockchain Engineer'})
        """,
        {}
    )

    # Create services
    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Create relationships with unknown skill
    jobs_data = [
        {
            "Job ID": "job-003",
            "standardized_skills": "Python, NewFramework2025",  # Unknown skill
            "similarity_scores": None
        }
    ]

    stats = await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-003"
    )

    # Verify statistics
    assert stats["relationships_created"] == 2
    assert stats["exact_matches"] == 1
    assert stats["fuzzy_matches"] == 0
    assert stats["orphans_created"] == 1

    # Verify orphan skill created in Neo4j
    orphan_skills = await neo4j_repo.execute_query(
        """
        MATCH (s:Skill)
        WHERE s.requires_manual_review = true
        RETURN s.name as skill_name, s.orphan_reason as reason, s.created_from_job as from_job
        """,
        {}
    )

    assert len(orphan_skills) == 1
    assert orphan_skills[0]["skill_name"] == "newframework2025"
    assert orphan_skills[0]["reason"] == "no_match"
    assert orphan_skills[0]["from_job"] is True

    # Verify orphan logged to PostgreSQL
    orphan_logs = await prisma_client.orphanskilllog.find_many(
        where={"orphan_reason": "no_match"}
    )

    assert len(orphan_logs) == 1
    assert orphan_logs[0].skill_name == "newframework2025"
    assert orphan_logs[0].job_id == "job-003"
    assert orphan_logs[0].status == "pending_review"

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})
    await prisma_client.orphanskilllog.delete_many()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ambiguous_fuzzy_match_creates_orphan(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test ambiguous fuzzy matches create orphan with suggested candidates."""
    # Setup: Create similar skills
    await neo4j_repo.execute_query(
        """
        CREATE (s1:Skill {id: 'react-001', name: 'React'})
        CREATE (s2:Skill {id: 'reactjs-001', name: 'ReactJS'})
        CREATE (j:Job {job_id: 'job-004', job_title: 'Frontend Developer'})
        """,
        {}
    )

    # Create services
    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Match ambiguous skill name
    jobs_data = [
        {
            "Job ID": "job-004",
            "standardized_skills": "Reactjs",  # Could be React or ReactJS
            "similarity_scores": None
        }
    ]

    stats = await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-004"
    )

    # Verify orphan created
    assert stats["orphans_created"] == 1

    # Verify orphan has fuzzy candidates
    orphan_skills = await neo4j_repo.execute_query(
        """
        MATCH (s:Skill)
        WHERE s.requires_manual_review = true AND s.orphan_reason = 'ambiguous_fuzzy_match'
        RETURN s.name as skill_name, s.fuzzy_candidates as candidates
        """,
        {}
    )

    assert len(orphan_skills) == 1
    candidates = orphan_skills[0]["candidates"]
    assert set(candidates) == {"React", "ReactJS"}

    # Verify logged to PostgreSQL with candidates
    orphan_logs = await prisma_client.orphanskilllog.find_many(
        where={"orphan_reason": "ambiguous_fuzzy_match"}
    )

    assert len(orphan_logs) == 1
    log_candidates = orphan_logs[0].fuzzy_candidates
    assert set(log_candidates) == {"React", "ReactJS"}

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})
    await prisma_client.orphanskilllog.delete_many()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_review_dashboard_query(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test admin review dashboard query returns orphan skills sorted by usage."""
    # Setup: Create skills and jobs
    await neo4j_repo.execute_query(
        """
        CREATE (j1:Job {job_id: 'job-005', job_title: 'Job 1'})
        CREATE (j2:Job {job_id: 'job-006', job_title: 'Job 2'})
        CREATE (j3:Job {job_id: 'job-007', job_title: 'Job 3'})

        CREATE (orphan1:Skill {
            id: 'orphan-001',
            name: 'newframework',
            requires_manual_review: true,
            orphan_reason: 'no_match',
            fuzzy_candidates: [],
            created_at: datetime()
        })

        CREATE (orphan2:Skill {
            id: 'orphan-002',
            name: 'pyton',
            requires_manual_review: true,
            orphan_reason: 'ambiguous_fuzzy_match',
            fuzzy_candidates: ['python', 'cython'],
            created_at: datetime()
        })

        CREATE (j1)-[:REQUIRES]->(orphan1)
        CREATE (j2)-[:REQUIRES]->(orphan1)
        CREATE (j3)-[:REQUIRES]->(orphan1)
        CREATE (j1)-[:REQUIRES]->(orphan2)
        """,
        {}
    )

    # Execute admin review query
    results = await neo4j_repo.execute_query(
        """
        MATCH (s:Skill)
        WHERE s.requires_manual_review = true
        OPTIONAL MATCH (j:Job)-[r:REQUIRES]->(s)
        RETURN s.name as skill_name,
               s.orphan_reason as reason,
               s.fuzzy_candidates as suggested_matches,
               count(j) as jobs_requiring_skill
        ORDER BY jobs_requiring_skill DESC
        """,
        {}
    )

    # Verify results
    assert len(results) == 2

    # First result should be "newframework" (3 jobs)
    assert results[0]["skill_name"] == "newframework"
    assert results[0]["jobs_requiring_skill"] == 3
    assert results[0]["reason"] == "no_match"

    # Second result should be "pyton" (1 job)
    assert results[1]["skill_name"] == "pyton"
    assert results[1]["jobs_requiring_skill"] == 1
    assert results[1]["reason"] == "ambiguous_fuzzy_match"
    assert set(results[1]["suggested_matches"]) == {"python", "cython"}

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_1000_relationships(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test batch processing creates 1000 relationships per transaction."""
    # Setup: Create 1 skill and 2000 jobs
    await neo4j_repo.execute_query(
        """
        CREATE (s:Skill {id: 'python-001', name: 'Python'})
        """,
        {}
    )

    # Create 2000 jobs
    for i in range(2000):
        await neo4j_repo.execute_query(
            f"""
            CREATE (j:Job {{job_id: 'job-{i:04d}', job_title: 'Job {i}'}})
            """,
            {}
        )

    # Create services
    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Create 2000 relationships (should process in 2 batches)
    jobs_data = [
        {
            "Job ID": f"job-{i:04d}",
            "standardized_skills": "Python",
            "similarity_scores": None
        }
        for i in range(2000)
    ]

    stats = await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-batch"
    )

    # Verify all relationships created
    assert stats["relationships_created"] == 2000
    assert stats["exact_matches"] == 2000

    # Verify count in Neo4j
    result = await neo4j_repo.execute_query(
        """
        MATCH ()-[r:REQUIRES]->()
        RETURN count(r) as total_relationships
        """,
        {}
    )

    assert result[0]["total_relationships"] == 2000

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_similarity_scores_alignment(
    neo4j_repo,
    ingestion_repo,
    prisma_client
):
    """Test similarity_scores field aligns with standardized_skills."""
    # Setup
    await neo4j_repo.execute_query(
        """
        CREATE (s1:Skill {id: 'python-001', name: 'Python'})
        CREATE (s2:Skill {id: 'react-001', name: 'React'})
        CREATE (s3:Skill {id: 'neo4j-001', name: 'Neo4j'})
        CREATE (j:Job {job_id: 'job-008', job_title: 'Full Stack Engineer'})
        """,
        {}
    )

    skill_matcher = SkillMatchingService(neo4j_repo, ingestion_repo)
    relationship_service = JobSkillRelationshipService(neo4j_repo, skill_matcher)

    # Execute: Scores should align with skills (same order)
    jobs_data = [
        {
            "Job ID": "job-008",
            "standardized_skills": "Python, React, Neo4j",
            "similarity_scores": "0.95, 0.87, 0.92"
        }
    ]

    await relationship_service.create_job_skill_relationships(
        jobs_data,
        ingestion_job_id="test-ingestion-008"
    )

    # Verify scores match skills
    relationships = await neo4j_repo.execute_query(
        """
        MATCH (j:Job {job_id: 'job-008'})-[r:REQUIRES]->(s:Skill)
        RETURN s.name as skill_name, r.similarity_score as score
        ORDER BY s.name
        """,
        {}
    )

    # Check scores aligned correctly
    neo4j_rel = next(r for r in relationships if r["skill_name"] == "Neo4j")
    python_rel = next(r for r in relationships if r["skill_name"] == "Python")
    react_rel = next(r for r in relationships if r["skill_name"] == "React")

    assert python_rel["score"] == 0.95
    assert react_rel["score"] == 0.87
    assert neo4j_rel["score"] == 0.92

    # Cleanup
    await neo4j_repo.execute_query("MATCH (n) DETACH DELETE n", {})
