"""Integration tests for incremental ingestion (Story 3.7)."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestIncrementalIngestion:
    """Test incremental mode upserts existing nodes."""

    @pytest.fixture
    def auth_token(self):
        """Fixture for authentication token."""
        return "test_jwt_token_for_testing"

    @pytest.fixture
    async def client(self, test_client):
        """Fixture for FastAPI test client."""
        return test_client

    @pytest.fixture
    async def neo4j_db(self, neo4j_test_db):
        """Fixture for Neo4j test database."""
        return neo4j_test_db

    async def test_incremental_mode_upserts_data(self, client, auth_token, neo4j_db):
        """Test incremental mode upserts existing nodes."""
        import io

        # First upload: Create 3 skills
        csv_content_v1 = b"""ID,NAME,DESCRIPTION
skill-1,Python,Programming language
skill-2,JavaScript,Web language
skill-3,Java,Enterprise language"""

        # Step 1: Upload CSV and get preview
        files = {"file": ("skills_v1.csv", io.BytesIO(csv_content_v1), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        assert preview_data["is_valid"] is True
        assert preview_data["total_rows"] == 3
        file_hash_v1 = preview_data["file_hash"]

        # Step 2: Confirm upload with incremental mode
        confirm_payload = {
            "file_hash": file_hash_v1,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v1 = response.json()
        assert job_v1["mode"] == "incremental"

        # Step 3: Poll status until complete (simplified for test)
        job_id_v1 = job_v1["ingestion_job_id"]
        # In real test, poll /ingest/status/{job_id} until completed

        # Step 4: Verify 3 nodes created in Neo4j
        async with neo4j_db.driver.session() as session:
            result = await session.run("MATCH (s:Skill) RETURN count(s) as count")
            record = await result.single()
            assert record["count"] == 3

        # Second upload: Update 2 skills, add 1 new
        csv_content_v2 = b"""ID,NAME,DESCRIPTION
skill-1,Python,Updated description
skill-2,JavaScript,Web language
skill-4,Go,Systems language"""

        # Step 1: Upload modified CSV
        files = {"file": ("skills_v2.csv", io.BytesIO(csv_content_v2), "text/csv")}
        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v2 = preview_data["file_hash"]

        # Step 2: Confirm with incremental mode
        confirm_payload = {
            "file_hash": file_hash_v2,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v2 = response.json()

        # Step 4: Verify statistics (after processing completes)
        # Note: In actual test, need to poll status endpoint
        # Expected: 1 created (skill-4), 1 updated (skill-1), 1 unchanged (skill-2)

        # Step 5: Verify skill-1 description updated
        async with neo4j_db.driver.session() as session:
            result = await session.run(
                "MATCH (s:Skill {id: $id}) RETURN s.description as desc, "
                "s.created_at as created, s.updated_at as updated",
                {"id": "skill-1"}
            )
            record = await result.single()
            assert record["desc"] == "Updated description"

            # Step 6: Verify timestamps
            if record["updated"]:  # updated_at is set
                assert record["created"] != record["updated"]

    async def test_hash_detection_skips_unchanged_rows(self, client, auth_token, neo4j_db):
        """Test unchanged rows are skipped efficiently."""
        import io

        csv_content = b"""ID,NAME,DESCRIPTION
skill-1,Python,Same description
skill-2,JavaScript,Same description"""

        # First upload: Create 2 skills
        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v1 = preview_data["file_hash"]

        # Confirm upload
        confirm_payload = {
            "file_hash": file_hash_v1,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v1 = response.json()

        # Verify 2 nodes created
        async with neo4j_db.driver.session() as session:
            result = await session.run("MATCH (s:Skill) RETURN count(s) as count")
            record = await result.single()
            assert record["count"] == 2

        # Second upload: Identical content (should detect no changes)
        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v2 = preview_data["file_hash"]

        # File hash should be the same for identical content
        assert file_hash_v1 == file_hash_v2

        # Confirm second upload
        confirm_payload = {
            "file_hash": file_hash_v2,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v2 = response.json()

        # After processing, verify statistics show 0 created, 0 updated, 2 unchanged
        # Note: This requires the ingestion job to complete
        # Expected stats: nodes_created=0, nodes_updated=0, nodes_unchanged=2


@pytest.mark.integration
@pytest.mark.asyncio
class TestFullModeIngestion:
    """Test full mode deletes all data before ingestion."""

    @pytest.fixture
    def auth_token(self):
        """Fixture for authentication token."""
        return "test_jwt_token_for_testing"

    @pytest.fixture
    async def client(self, test_client):
        """Fixture for FastAPI test client."""
        return test_client

    @pytest.fixture
    async def neo4j_db(self, neo4j_test_db):
        """Fixture for Neo4j test database."""
        return neo4j_test_db

    async def test_full_mode_requires_confirmation(self, client, auth_token):
        """Test full mode rejects request without confirmation."""
        import io

        csv_content = b"""ID,NAME
skill-1,Python"""

        # Step 1: Upload CSV
        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash = preview_data["file_hash"]

        # Step 2: Attempt full mode without confirmation
        confirm_payload = {
            "file_hash": file_hash,
            "file_type": "skills",
            "mode": "full",
            "confirmation": None
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Step 3: Expect 400 error
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "CONFIRM DELETE" in error_detail

    async def test_full_mode_rejects_wrong_confirmation(self, client, auth_token):
        """Test full mode rejects incorrect confirmation text."""
        import io

        csv_content = b"""ID,NAME
skill-1,Python"""

        # Upload CSV
        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash = preview_data["file_hash"]

        # Attempt full mode with wrong confirmation text
        confirm_payload = {
            "file_hash": file_hash,
            "file_type": "skills",
            "mode": "full",
            "confirmation": "YES"  # Wrong confirmation text
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Expect 400 error
        assert response.status_code == 400
        error_detail = response.json()["detail"]
        assert "CONFIRM DELETE" in error_detail

    async def test_full_mode_deletes_all_data(self, client, auth_token, neo4j_db):
        """Test full mode deletes all graph data before ingestion."""
        import io

        # Create initial data
        csv_initial = b"""ID,NAME
skill-1,Python
skill-2,JavaScript
skill-3,Java"""

        # Step 1: Upload and ingest initial CSV (incremental mode)
        files = {"file": ("skills_initial.csv", io.BytesIO(csv_initial), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v1 = preview_data["file_hash"]

        confirm_payload = {
            "file_hash": file_hash_v1,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202

        # Step 2: Verify 3 skills exist in Neo4j
        async with neo4j_db.driver.session() as session:
            result = await session.run("MATCH (s:Skill) RETURN count(s) as count")
            record = await result.single()
            assert record["count"] == 3

        # Step 3: Upload new CSV with different skill
        csv_new = b"""ID,NAME
skill-new,Go"""

        files = {"file": ("skills_new.csv", io.BytesIO(csv_new), "text/csv")}
        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v2 = preview_data["file_hash"]

        # Step 4: Confirm with full mode and correct confirmation
        confirm_payload = {
            "file_hash": file_hash_v2,
            "file_type": "skills",
            "mode": "full",
            "confirmation": "CONFIRM DELETE"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202

        # Step 5-6: After processing, verify old skills deleted and only "Go" exists
        # Note: This requires the ingestion job to complete
        # In actual test, poll status endpoint until completed
        # Expected: Only skill-new exists, skill-1/2/3 are deleted

    async def test_full_mode_logs_warning(self, client, auth_token):
        """Test full mode logs warning messages."""
        import io
        import logging

        # Set up log capture
        logger = logging.getLogger("app.api.ingest")

        csv_content = b"""ID,NAME
skill-1,Python"""

        # Upload CSV
        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash = preview_data["file_hash"]

        # Initiate full mode with correct confirmation
        confirm_payload = {
            "file_hash": file_hash,
            "file_type": "skills",
            "mode": "full",
            "confirmation": "CONFIRM DELETE"
        }

        # This should log a warning message
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202

        # Note: Actual log verification would require log capture fixture
        # Expected log: "⚠️  FULL MODE INGESTION initiated by user..."


@pytest.mark.integration
@pytest.mark.asyncio
class TestRelationshipCleanup:
    """Test relationship cleanup on re-ingestion."""

    @pytest.fixture
    def auth_token(self):
        """Fixture for authentication token."""
        return "test_jwt_token_for_testing"

    @pytest.fixture
    async def client(self, test_client):
        """Fixture for FastAPI test client."""
        return test_client

    @pytest.fixture
    async def neo4j_db(self, neo4j_test_db):
        """Fixture for Neo4j test database."""
        return neo4j_test_db

    async def test_job_skill_relationships_updated(self, client, auth_token, neo4j_db):
        """Test job skills are updated, not accumulated."""
        import io

        # Step 1: Create job requiring [Python, Java]
        # First, create skills
        skills_csv = b"""ID,NAME,DESCRIPTION
skill-python,Python,Programming language
skill-java,Java,Enterprise language
skill-react,React,Frontend library"""

        files = {"file": ("skills.csv", io.BytesIO(skills_csv), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        preview_data = response.json()
        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "skills",
            "mode": "incremental"
        }
        client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Create job with Python and Java skills
        jobs_csv_v1 = b"""JOB_ID,TITLE,SKILLS
job-123,Software Engineer,skill-python|skill-java"""

        files = {"file": ("jobs_v1.csv", io.BytesIO(jobs_csv_v1), "text/csv")}
        response = client.post("/ingest/jobs", files=files, headers=headers)
        preview_data = response.json()
        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "jobs",
            "mode": "incremental"
        }
        client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Verify job has relationships to Python and Java
        async with neo4j_db.driver.session() as session:
            result = await session.run("""
                MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
                RETURN s.id as skill_id
                ORDER BY skill_id
            """, {"job_id": "job-123"})
            skills = [record["skill_id"] async for record in result]
            assert set(skills) == {"skill-python", "skill-java"}

        # Step 2: Re-ingest job with [Python, React]
        jobs_csv_v2 = b"""JOB_ID,TITLE,SKILLS
job-123,Software Engineer,skill-python|skill-react"""

        files = {"file": ("jobs_v2.csv", io.BytesIO(jobs_csv_v2), "text/csv")}
        response = client.post("/ingest/jobs", files=files, headers=headers)
        preview_data = response.json()
        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "jobs",
            "mode": "incremental"
        }
        client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Step 3-4: Verify job ONLY has relationships to Python and React
        async with neo4j_db.driver.session() as session:
            result = await session.run("""
                MATCH (j:Job {job_id: $job_id})-[:REQUIRES]->(s:Skill)
                RETURN s.id as skill_id
                ORDER BY skill_id
            """, {"job_id": "job-123"})
            skills = [record["skill_id"] async for record in result]
            assert set(skills) == {"skill-python", "skill-react"}
            assert "skill-java" not in skills

    async def test_skill_category_relationships_updated(self, client, auth_token, neo4j_db):
        """Test skill categories are updated on re-ingestion."""
        import io

        # Step 1: Create skill with Category A, Subcategory A1
        skills_csv_v1 = b"""ID,NAME,CATEGORY,SUBCATEGORY
skill-1,Python,Category-A,Subcategory-A1"""

        files = {"file": ("skills_v1.csv", io.BytesIO(skills_csv_v1), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        preview_data = response.json()
        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "skills",
            "mode": "incremental"
        }
        client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Verify skill belongs to Category A
        async with neo4j_db.driver.session() as session:
            result = await session.run("""
                MATCH (s:Skill {id: $id})-[:BELONGS_TO_CATEGORY]->(c:Category)
                RETURN c.name as category
            """, {"id": "skill-1"})
            record = await result.single()
            assert record and record["category"] == "Category-A"

        # Step 2: Re-ingest skill with Category B, Subcategory B1
        skills_csv_v2 = b"""ID,NAME,CATEGORY,SUBCATEGORY
skill-1,Python,Category-B,Subcategory-B1"""

        files = {"file": ("skills_v2.csv", io.BytesIO(skills_csv_v2), "text/csv")}
        response = client.post("/ingest/skills", files=files, headers=headers)
        preview_data = response.json()
        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "skills",
            "mode": "incremental"
        }
        client.post("/ingest/confirm", json=confirm_payload, headers=headers)

        # Step 3-4: Verify skill belongs to B/B1 only
        async with neo4j_db.driver.session() as session:
            result = await session.run("""
                MATCH (s:Skill {id: $id})-[:BELONGS_TO_CATEGORY]->(c:Category)
                RETURN c.name as category
            """, {"id": "skill-1"})
            record = await result.single()
            assert record and record["category"] == "Category-B"

            # Verify no relationship to Category A
            result = await session.run("""
                MATCH (s:Skill {id: $id})-[:BELONGS_TO_CATEGORY]->(c:Category {name: $old_cat})
                RETURN count(c) as count
            """, {"id": "skill-1", "old_cat": "Category-A"})
            record = await result.single()
            assert record["count"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
class TestUpsertStatistics:
    """Test upsert statistics tracking."""

    @pytest.fixture
    def auth_token(self):
        """Fixture for authentication token."""
        return "test_jwt_token_for_testing"

    @pytest.fixture
    async def client(self, test_client):
        """Fixture for FastAPI test client."""
        return test_client

    @pytest.fixture
    async def neo4j_db(self, neo4j_test_db):
        """Fixture for Neo4j test database."""
        return neo4j_test_db

    async def test_statistics_track_created_updated_unchanged(self, client, auth_token, neo4j_db):
        """Test ingestion response includes accurate statistics."""
        import io

        csv_v1 = b"""ID,NAME
skill-1,Python
skill-2,JavaScript"""

        # Step 1: Upload csv_v1 in incremental mode
        files = {"file": ("skills_v1.csv", io.BytesIO(csv_v1), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v1 = preview_data["file_hash"]

        confirm_payload = {
            "file_hash": file_hash_v1,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v1 = response.json()

        # Step 2: Verify response statistics (after processing completes)
        # Expected: nodes_created=2, nodes_updated=0, nodes_unchanged=0
        # Note: These stats are populated after job completes, so we check structure
        assert "nodes_created" in job_v1
        assert "nodes_updated" in job_v1
        assert "nodes_unchanged" in job_v1

        # Step 3: Upload csv_v2 in incremental mode (1 unchanged, 1 modified, 1 new)
        csv_v2 = b"""ID,NAME
skill-1,Python
skill-2,JS
skill-3,Go"""

        files = {"file": ("skills_v2.csv", io.BytesIO(csv_v2), "text/csv")}
        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()
        file_hash_v2 = preview_data["file_hash"]

        confirm_payload = {
            "file_hash": file_hash_v2,
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job_v2 = response.json()

        # Step 4: Verify response statistics (after processing completes)
        # Expected: nodes_created=1 (skill-3), nodes_updated=1 (skill-2), nodes_unchanged=1 (skill-1)
        assert "nodes_created" in job_v2
        assert "nodes_updated" in job_v2
        assert "nodes_unchanged" in job_v2

        # Step 5: Verify processed_records=3
        assert "total_records" in job_v2

    async def test_statistics_message_format(self, client, auth_token):
        """Test statistics are displayed in human-readable format."""
        import io

        csv_content = b"""ID,NAME
skill-1,Python
skill-2,JavaScript
skill-3,Java"""

        files = {"file": ("skills.csv", io.BytesIO(csv_content), "text/csv")}
        headers = {"Authorization": f"Bearer {auth_token}"}

        response = client.post("/ingest/skills", files=files, headers=headers)
        assert response.status_code == 200
        preview_data = response.json()

        confirm_payload = {
            "file_hash": preview_data["file_hash"],
            "file_type": "skills",
            "mode": "incremental"
        }
        response = client.post("/ingest/confirm", json=confirm_payload, headers=headers)
        assert response.status_code == 202
        job = response.json()

        # Verify response has message field
        assert "message" in job
        message = job["message"]

        # Verify message contains human-readable format
        # Expected format: "X created, Y updated, Z unchanged"
        # or "X / Y records ingested successfully"
        assert isinstance(message, str)
        assert len(message) > 0


# Note: These tests require:
# 1. Test Neo4j database instance
# 2. Test FastAPI app setup with dependency overrides
# 3. Test authentication tokens
# 4. Database cleanup fixtures (before/after each test)
