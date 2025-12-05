"""Integration tests for job graph construction."""
import pytest
import os
from neo4j import AsyncGraphDatabase
from app.services.job_graph_service import JobGraphService
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from prisma import Prisma


@pytest.fixture
async def prisma_client():
    """Setup Prisma client for tests."""
    client = Prisma()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
async def neo4j_repo():
    """Setup Neo4j repository for tests."""
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    repo = Neo4jRepository(uri=uri, user=user, password=password)

    yield repo

    # Cleanup: Delete test data
    async with driver.session() as session:
        await session.run(
            "MATCH (j:Job) WHERE j.job_id STARTS WITH 'test-' DETACH DELETE j"
        )
        await session.run(
            "MATCH (c:Company) WHERE c.company_name STARTS WITH 'Test ' "
            "DETACH DELETE c"
        )
        await session.run(
            "MATCH (l:Location) WHERE l.location_name STARTS WITH 'Test ' "
            "DETACH DELETE l"
        )

    await driver.close()


@pytest.fixture
def embedding_service():
    """Setup embedding service for tests."""
    return EmbeddingService(model_name="sentence-transformers/all-MiniLM-L6-v2")


@pytest.fixture
async def ingestion_repo(prisma_client):
    """Setup ingestion repository for tests."""
    return IngestionRepository(prisma_client)


@pytest.fixture
async def job_graph_service(embedding_service, neo4j_repo, ingestion_repo):
    """Setup job graph service for tests."""
    return JobGraphService(
        embedding_service=embedding_service,
        neo4j_repo=neo4j_repo,
        ingestion_repo=ingestion_repo
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_job_graph_creation(job_graph_service, neo4j_repo, prisma_client):
    """Test complete job graph creation flow."""
    # Create test ingestion job
    ingestion_job = await prisma_client.ingestionjob.create(
        data={
            "user_id": "test-user-123",
            "file_type": "jobs",
            "status": "processing",
            "total_records": 5
        }
    )

    # Sample job data
    jobs_data = [
        {
            "Job ID": "test-job-1",
            "Job Title": "Senior Python Developer",
            "Job Description": "Looking for experienced Python developer with FastAPI knowledge",
            "Description": "Backup description",
            "Company Name": "Test Tech Corp",
            "Company Description": "Leading technology company specializing in AI solutions",
            "CIN": "U72900KA2020PTC123456",
            "CompanyIndustrialClassification": "Information Technology",
            "NIC_Code_algo": "62.01",
            "nic_code_2_2008": "6201",
            "Location": "Test Bangalore",
            "District": "Bangalore Urban",
            "Via": "LinkedIn",
            "Salary": "15-20 LPA",
            "Minimum Salary": 1500000,
            "Maximum Salary": 2000000,
            "Mean Salary": 1750000,
            "Unit of Measure": "per annum",
            "Schedule Type": "Full-time",
            "Work From Home": 1,
            "Posted At": "2025-10-23T10:00:00",
            "Apply Options": "Apply on website",
            "Exact Matched Company": 1,
            "NCO_Code_algo": "2512.10",
            "Description Token Count": 50,
            "Company Description Token Count": 100,
            "Job Description Token Count": 200
        },
        {
            "Job ID": "test-job-2",
            "Job Title": "Frontend Developer",
            "Job Description": "React and TypeScript expert needed",
            "Company Name": "Test Tech Corp",  # Same company
            "Company Description": "Leading technology company specializing in AI solutions",
            "Location": "Test Mumbai",
            "District": "Mumbai Suburban"
        },
        {
            "Job ID": "test-job-3",
            "Job Title": "Data Scientist",
            "Description": "Machine learning and data analysis",  # Using fallback Description
            "Job Description": "",  # Empty Job Description
            "Company Name": "Test AI Startup",
            "Company Description": "AI startup working on NLP solutions",
            "Location": "Test Bangalore",  # Same location as job-1
            "District": "Bangalore Urban"
        },
        {
            "Job ID": "test-job-4",
            "Job Title": "Backend Engineer",
            "Job Description": None,  # NULL fields
            "Description": None,
            "Company Name": None,
            "Location": None
        },
        {
            "Job ID": "test-job-5",
            "Job Title": "DevOps Engineer",
            "Job Description": "Kubernetes and Docker experience required",
            "Company Name": "Test Cloud Services",
            "Company Description": None,  # NULL company description
            "Location": "Test Delhi",
            "District": None  # NULL district
        }
    ]

    # Execute job graph creation
    stats = await job_graph_service.create_job_graph(
        jobs_data=jobs_data,
        job_id=ingestion_job.id
    )

    # Verify statistics
    assert stats["jobs_created"] == 5
    assert stats["companies_created"] == 3  # Tech Corp, AI Startup, Cloud Services (NULL excluded)
    assert stats["locations_created"] == 3  # Bangalore, Mumbai, Delhi (NULL excluded)
    assert stats["relationships_created"] >= 7  # Some jobs have both company and location
    assert len(stats["errors"]) == 0

    # Verify nodes exist in Neo4j
    async with neo4j_repo.driver.session() as session:
        # Check Job nodes
        result = await session.run(
            "MATCH (j:Job) WHERE j.job_id STARTS WITH 'test-job-' RETURN count(j) as count"
        )
        record = await result.single()
        assert record["count"] == 5

        # Check Company nodes
        result = await session.run(
            "MATCH (c:Company) WHERE c.company_name STARTS WITH 'Test ' RETURN count(c) as count"
        )
        record = await result.single()
        assert record["count"] == 3

        # Check Location nodes
        result = await session.run(
            "MATCH (l:Location) WHERE l.location_name STARTS WITH 'Test ' RETURN count(l) as count"
        )
        record = await result.single()
        assert record["count"] == 3

        # Check POSTED_BY relationships
        result = await session.run(
            "MATCH (j:Job)-[r:POSTED_BY]->(c:Company) "
            "WHERE j.job_id STARTS WITH 'test-job-' "
            "RETURN count(r) as count"
        )
        record = await result.single()
        assert record["count"] == 4  # job-1, job-2, job-3, job-5 have companies

        # Check LOCATED_IN relationships
        result = await session.run(
            "MATCH (j:Job)-[r:LOCATED_IN]->(l:Location) "
            "WHERE j.job_id STARTS WITH 'test-job-' "
            "RETURN count(r) as count"
        )
        record = await result.single()
        assert record["count"] == 4  # job-1, job-2, job-3, job-5 have locations

        # Verify job-1 has all 30 fields
        result = await session.run(
            "MATCH (j:Job {job_id: 'test-job-1'}) RETURN j"
        )
        record = await result.single()
        job_node = record["j"]

        assert job_node["job_title"] == "Senior Python Developer"
        assert job_node["location"] == "Test Bangalore"
        assert job_node["district"] == "Bangalore Urban"
        assert job_node["via"] == "LinkedIn"
        assert job_node["salary"] == "15-20 LPA"
        assert job_node["min_salary"] == 1500000
        assert job_node["max_salary"] == 2000000
        assert job_node["mean_salary"] == 1750000
        assert job_node["salary_unit"] == "per annum"
        assert job_node["schedule_type"] == "Full-time"
        assert job_node["work_from_home"] is True
        assert job_node["description"] == "Backup description"
        assert "Looking for experienced" in job_node["job_description"]
        assert job_node["nco_code"] == "2512.10"
        assert job_node["embedding"] is not None
        assert len(job_node["embedding"]) == 384

        # Verify company has embedding
        result = await session.run(
            "MATCH (c:Company {company_name: 'Test Tech Corp'}) RETURN c"
        )
        record = await result.single()
        company_node = record["c"]

        assert company_node["cin"] == "U72900KA2020PTC123456"
        assert "technology company" in company_node["company_description"]
        assert company_node["embedding"] is not None
        assert len(company_node["embedding"]) == 384

    # Cleanup test ingestion job
    await prisma_client.ingestionjob.delete(where={"id": ingestion_job.id})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_transaction_1000_jobs(job_graph_service, neo4j_repo, prisma_client):
    """Test batch processing with 1000 jobs in single transaction."""
    # Create test ingestion job
    ingestion_job = await prisma_client.ingestionjob.create(
        data={
            "user_id": "test-user-batch",
            "file_type": "jobs",
            "status": "processing",
            "total_records": 1000
        }
    )

    # Generate 1000 jobs
    jobs_data = [
        {
            "Job ID": f"test-batch-job-{i}",
            "Job Title": f"Developer {i}",
            "Job Description": f"Job description for position {i}",
            "Company Name": f"Test Company {i % 10}",  # 10 unique companies
            "Company Description": f"Company description {i % 10}",
            "Location": f"Test City {i % 5}",  # 5 unique locations
            "District": f"District {i % 5}"
        }
        for i in range(1000)
    ]

    # Execute batch processing
    stats = await job_graph_service.create_job_graph(
        jobs_data=jobs_data,
        job_id=ingestion_job.id
    )

    # Verify all jobs processed
    assert stats["jobs_created"] == 1000
    assert stats["companies_created"] == 10
    assert stats["locations_created"] == 5
    assert len(stats["errors"]) == 0

    # Verify in Neo4j
    async with neo4j_repo.driver.session() as session:
        result = await session.run(
            "MATCH (j:Job) WHERE j.job_id STARTS WITH 'test-batch-job-' RETURN count(j) as count"
        )
        record = await result.single()
        assert record["count"] == 1000

    # Cleanup
    async with neo4j_repo.driver.session() as session:
        await session.run(
            "MATCH (j:Job) WHERE j.job_id STARTS WITH 'test-batch-job-' DETACH DELETE j"
        )
        await session.run(
            "MATCH (c:Company) WHERE c.company_name STARTS WITH 'Test Company ' DETACH DELETE c"
        )
        await session.run(
            "MATCH (l:Location) WHERE l.location_name STARTS WITH 'Test City ' DETACH DELETE l"
        )

    await prisma_client.ingestionjob.delete(where={"id": ingestion_job.id})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reingest_merge_updates(job_graph_service, neo4j_repo, prisma_client):
    """Test re-ingestion updates existing nodes (MERGE behavior)."""
    # Create test ingestion job
    ingestion_job = await prisma_client.ingestionjob.create(
        data={
            "user_id": "test-user-merge",
            "file_type": "jobs",
            "status": "processing",
            "total_records": 2
        }
    )

    # First ingestion
    jobs_data_v1 = [
        {
            "Job ID": "test-merge-1",
            "Job Title": "Python Developer V1",
            "Job Description": "Original description",
            "Company Name": "Test Merge Corp",
            "Company Description": "Original company description",
            "Location": "Test Merge City"
        }
    ]

    stats_v1 = await job_graph_service.create_job_graph(jobs_data_v1, ingestion_job.id)
    assert stats_v1["jobs_created"] == 1

    # Second ingestion (same job_id, updated data)
    jobs_data_v2 = [
        {
            "Job ID": "test-merge-1",  # Same ID
            "Job Title": "Senior Python Developer V2",  # Updated title
            "Job Description": "Updated description with more details",
            "Company Name": "Test Merge Corp",
            "Company Description": "Updated company description",
            "Location": "Test Merge City"
        }
    ]

    stats_v2 = await job_graph_service.create_job_graph(jobs_data_v2, ingestion_job.id)
    assert stats_v2["jobs_created"] == 1

    # Verify only 1 job node exists (updated, not duplicated)
    async with neo4j_repo.driver.session() as session:
        result = await session.run(
            "MATCH (j:Job {job_id: 'test-merge-1'}) RETURN count(j) as count, j.job_title as title"
        )
        record = await result.single()
        assert record["count"] == 1
        assert record["title"] == "Senior Python Developer V2"  # Updated

        # Verify company also updated
        result = await session.run(
            "MATCH (c:Company {company_name: 'Test Merge Corp'}) "
            "RETURN count(c) as count, c.company_description as desc"
        )
        record = await result.single()
        assert record["count"] == 1
        assert "Updated company description" in record["desc"]

    # Cleanup
    async with neo4j_repo.driver.session() as session:
        await session.run("MATCH (j:Job {job_id: 'test-merge-1'}) DETACH DELETE j")
        await session.run("MATCH (c:Company {company_name: 'Test Merge Corp'}) DETACH DELETE c")
        await session.run("MATCH (l:Location {location_name: 'Test Merge City'}) DETACH DELETE l")

    await prisma_client.ingestionjob.delete(where={"id": ingestion_job.id})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
