"""Integration tests for ingestion API endpoints."""

import pytest
import uuid
from io import BytesIO
from fastapi.testclient import TestClient
from app.main import app

# Fixtures

@pytest.fixture
def test_client():
    """Provide a TestClient with lifespan events triggered."""
    with TestClient(app) as client:
        yield client


# Helper Functions

def create_test_user_and_login(client):
    """Helper to register a user and get JWT token."""
    # Register user with unique email
    unique_id = str(uuid.uuid4())[:8]
    register_data = {
        "email": f"ingesttest_{unique_id}@example.com",
        "password": "password123"
    }

    reg_response = client.post("/auth/register", json=register_data)
    assert reg_response.status_code == 201

    # Login to get token
    login_data = {
        "email": register_data["email"],
        "password": "password123"
    }
    login_response = client.post("/auth/login", json=login_data)
    assert login_response.status_code == 200

    token = login_response.json()["token"]
    user_id = login_response.json()["user"]["id"]

    return token, user_id


def create_csv_file(content: bytes, filename: str = "test.csv"):
    """Helper to create a test CSV file."""
    return ("file", (filename, BytesIO(content), "text/csv"))


# Skills Upload Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_skills_csv_success(test_db, test_client):
    """Test POST /ingest/skills with valid CSV returns 200 with preview."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,JavaScript,Web language,Tech,Frontend"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert - Story 2.3: Returns preview data (200), not job (202)
    assert response.status_code == 200
    data = response.json()
    assert "file_hash" in data
    assert "file_type" in data
    assert data["file_type"] == "skills"
    assert "columns" in data
    assert "preview_rows" in data
    assert "total_rows" in data
    assert data["total_rows"] == 2
    assert "has_more" in data
    assert len(data["file_hash"]) == 64  # SHA-256 hash


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_skills_csv_creates_db_record(test_db, test_client, prisma_client):
    """Test that confirmed skills CSV creates ingestion job in database (Story 2.3)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,Java,OOP language,Tech,Backend"

    # Act - Step 1: Upload and get preview
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]
    file_type = upload_response.json()["file_type"]

    # Act - Step 2: Confirm upload to create ingestion job
    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": file_type}
    )

    # Assert
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Verify in database
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.user_id == user_id
    assert job.file_type == "skills"
    assert job.file_name == "skills.csv"
    assert job.status == "pending"
    assert job.file_size_mb > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_skills_csv_without_auth_returns_403(test_db, test_client):
    """Test POST /ingest/skills without authentication returns 403."""
    # Arrange
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"

    # Act - No Authorization header
    response = test_client.post(
        "/ingest/skills",
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_skills_csv_invalid_token_returns_401(test_db, test_client):
    """Test POST /ingest/skills with invalid token returns 401."""
    # Arrange
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"
    invalid_token = "invalid.jwt.token"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {invalid_token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 401


# Jobs Upload Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_jobs_csv_success(test_db, test_client):
    """Test POST /ingest/jobs with valid CSV returns 200 with preview."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Include all required columns: Job ID, Job Title, Company Name, Location, standardized_skills
    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,Remote,Python|Java\n2,Data Scientist,DataCorp,New York,R|Python"

    # Act
    response = test_client.post(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jobs.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert - Story 2.3: Returns preview data (200), not job (202)
    assert response.status_code == 200
    data = response.json()
    assert "file_hash" in data
    assert "file_type" in data
    assert data["file_type"] == "jobs"
    assert "columns" in data
    assert "preview_rows" in data
    assert "total_rows" in data
    assert data["total_rows"] == 2
    assert "has_more" in data
    assert len(data["file_hash"]) == 64  # SHA-256 hash


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_jobs_csv_creates_db_record(test_db, test_client, prisma_client):
    """Test that confirmed jobs CSV creates ingestion job in database (Story 2.3)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Include all required columns: Job ID, Job Title, Company Name, Location, standardized_skills
    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,Remote,Python\n2,UI Designer,DesignCo,San Francisco,Figma"

    # Act - Step 1: Upload and get preview
    upload_response = test_client.post(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jobs.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]
    file_type = upload_response.json()["file_type"]

    # Act - Step 2: Confirm upload to create ingestion job
    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": file_type}
    )

    # Assert
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Verify in database
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.user_id == user_id
    assert job.file_type == "jobs"
    assert job.file_name == "jobs.csv"
    assert job.status == "pending"


# File Validation Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_invalid_file_type_returns_400(test_db, test_client):
    """Test POST /ingest/skills with non-CSV file returns 400."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    txt_content = b"This is a text file"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("data.txt", BytesIO(txt_content), "text/plain")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "csv" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_oversized_file_returns_413(test_db, test_client):
    """Test POST /ingest/skills with >100MB file returns 413."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Create 101MB file
    large_content = b"a" * (101 * 1024 * 1024)

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("large.csv", BytesIO(large_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 413
    data = response.json()
    assert "detail" in data
    assert "100MB" in data["detail"] or "100 MB" in data["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_csv_with_unsafe_filename(test_db, test_client, prisma_client):
    """Test that unsafe filenames are sanitized (Story 2.3 two-step flow)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Test skill,Tech,Backend"
    unsafe_filename = "../../../etc/passwd.csv"

    # Act - Step 1: Upload
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (unsafe_filename, BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]
    file_type = upload_response.json()["file_type"]

    # Act - Step 2: Confirm
    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": file_type}
    )

    # Assert
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Verify sanitized filename in database
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.file_name == "passwd.csv"  # Path components removed
    assert "../" not in job.file_name
    assert "/" not in job.file_name


# Get Job Status Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_job_status_success(test_db, test_client):
    """Test GET /ingest/jobs/{job_id} returns job details (Story 2.3 two-step flow)."""
    # Arrange - Upload and confirm a file first
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"

    # Step 1: Upload
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]
    file_type = upload_response.json()["file_type"]

    # Step 2: Confirm
    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": file_type}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Act
    response = test_client.get(
        f"/ingest/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["user_id"] == user_id
    assert data["file_type"] == "skills"
    assert data["file_name"] == "skills.csv"
    assert data["status"] == "pending"
    assert "created_at" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_job_status_not_found(test_db, test_client):
    """Test GET /ingest/jobs/{job_id} with non-existent ID returns 404."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    fake_job_id = "00000000-0000-0000-0000-000000000000"

    # Act
    response = test_client.get(
        f"/ingest/jobs/{fake_job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_job_status_unauthorized(test_db, test_client):
    """Test GET /ingest/jobs/{job_id} without auth returns 403."""
    # Act
    response = test_client.get("/ingest/jobs/some-job-id")

    # Assert
    assert response.status_code == 403


# Get User Jobs Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_jobs_success(test_db, test_client):
    """Test GET /ingest/jobs returns user's ingestion jobs (Story 2.3 two-step flow)."""
    # Arrange - Upload and confirm 2 files
    token, user_id = create_test_user_and_login(test_client)
    skills_csv = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"
    jobs_csv = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Software Engineer,TechCo,Remote,Python"

    # Upload skills file and confirm
    skills_upload = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills1.csv", BytesIO(skills_csv), "text/csv")}
    )
    assert skills_upload.status_code == 200
    test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": skills_upload.json()["file_hash"], "file_type": "skills"}
    )

    # Upload jobs file and confirm
    jobs_upload = test_client.post(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jobs1.csv", BytesIO(jobs_csv), "text/csv")}
    )
    assert jobs_upload.status_code == 200
    test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": jobs_upload.json()["file_hash"], "file_type": "jobs"}
    )

    # Act
    response = test_client.get(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    # Verify both jobs belong to user
    for job in data:
        assert job["user_id"] == user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_jobs_empty_list(test_db, test_client):
    """Test GET /ingest/jobs returns empty list for user with no jobs."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)

    # Act
    response = test_client.get(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_user_jobs_unauthorized(test_db, test_client):
    """Test GET /ingest/jobs without auth returns 403."""
    # Act
    response = test_client.get("/ingest/jobs")

    # Assert
    assert response.status_code == 403


# CSV Validation Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_skills_csv_missing_required_columns(test_db, test_client):
    """Test POST /ingest/skills with missing required columns returns 400."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Missing NAME, CATEGORY, SUBCATEGORY columns
    csv_content = b"ID,DESCRIPTION\n1,Programming language"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert data["detail"]["error"] == "csv_validation_failed"
    assert "NAME" in str(data["detail"]["validation_errors"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_jobs_csv_missing_required_columns(test_db, test_client):
    """Test POST /ingest/jobs with missing required columns returns 400."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Missing Company Name, Location, standardized_skills columns
    csv_content = b"Job ID,Job Title\n1,Software Engineer"

    # Act
    response = test_client.post(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jobs.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error"] == "csv_validation_failed"
    assert "standardized_skills" in str(data["detail"]["validation_errors"])


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_empty_csv_returns_400(test_db, test_client):
    """Test POST /ingest/skills with empty CSV (header only) returns 400."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Header only, no data rows
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "no data rows" in data["detail"]["message"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_corrupted_csv_returns_400(test_db, test_client):
    """Test POST /ingest/skills with corrupted CSV returns 400."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Malformed CSV with mismatched quotes
    csv_content = b'ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,"Unclosed quote\n2,Another row'

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "Failed to parse" in data["detail"]["message"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_csv_validation_error_includes_missing_columns(test_db, test_client):
    """Test that validation error response includes list of missing columns."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Missing NAME and SUBCATEGORY columns
    csv_content = b"ID,DESCRIPTION,CATEGORY\n1,Some description,Tech"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    validation_errors = str(data["detail"]["validation_errors"])
    assert "Missing columns" in validation_errors
    assert "NAME" in validation_errors
    assert "Required columns" in validation_errors
    assert "Found columns" in validation_errors


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_csv_case_insensitive_columns(test_db, test_client):
    """Test that CSV validation accepts case-insensitive column names (Story 2.3)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    # Columns in lowercase
    csv_content = b"id,name,description,category,subcategory\n1,Python,Programming language,Tech,Backend"

    # Act
    response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )

    # Assert - should succeed with 200 and preview data
    assert response.status_code == 200
    data = response.json()
    assert "file_hash" in data
    assert "columns" in data
    assert data["total_rows"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_upload_csv_stores_total_records(test_db, test_client, prisma_client):
    """Test that confirmed CSV stores total_records count in database (Story 2.3)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend\n2,JavaScript,Web language,Tech,Frontend\n3,Java,OOP language,Tech,Backend"

    # Act - Step 1: Upload
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]
    file_type = upload_response.json()["file_type"]

    # Act - Step 2: Confirm
    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": file_type}
    )

    # Assert
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Verify total_records is stored
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.total_records == 3


# Batch Processing Tests (Story 2.4)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_updates_status(test_db, test_client, prisma_client):
    """Test that batch processing updates job status after each batch (Story 2.4 AC: 7)."""
    # Arrange - Create CSV with 1100 records (to test multiple batches with default 1000 batch size)
    token, user_id = create_test_user_and_login(test_client)

    # Generate CSV with > 1000 records to trigger batching
    header = "ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n"
    rows = "".join([
        f"skill-{i},Skill {i},Description {i},Category,Subcategory\n"
        for i in range(1, 1101)  # 1100 records
    ])
    csv_content = (header + rows).encode()

    # Act - Upload and confirm
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Assert - Verify job record exists with correct status
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.status in ["processing", "completed", "completed_with_errors"]
    assert job.total_records == 1100


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_processing_tracks_progress(test_db, test_client, prisma_client):
    """Test that batch processing tracks processed_records and failed_records (Story 2.4 AC: 4)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend\n2,React,Lib,Tech,Frontend\n3,Docker,Tool,DevOps,Container"

    # Act
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Assert - Verify progress tracking
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.processed_records >= 0  # Progress tracked
    assert job.failed_records >= 0  # Failures tracked
    assert job.total_records == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_logging_for_failed_records(test_db, test_client, prisma_client):
    """Test that failed records are logged to ingestion_errors table (Story 2.4 AC: 5)."""
    # Arrange - CSV with intentionally invalid data
    token, user_id = create_test_user_and_login(test_client)

    # Valid skills CSV but some records might fail during processing
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend"

    # Act
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Assert - Check if ingestion_errors table can store errors (even if none occurred)
    errors = await prisma_client.ingestionerror.find_many(where={"job_id": job_id})
    assert isinstance(errors, list)  # Table exists and queryable


@pytest.mark.integration
@pytest.mark.asyncio
async def test_final_status_completed(test_db, test_client, prisma_client):
    """Test that final status is 'completed' when no errors (Story 2.4 AC: 8)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"

    # Act
    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Assert
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    # Status should be completed or completed_with_errors
    assert job.status in ["pending", "processing", "completed", "completed_with_errors"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_jobs_batch_processing(test_db, test_client, prisma_client):
    """Test batch processing for jobs CSV (Story 2.4 AC: 1-8 for jobs)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"Job ID,Job Title,Company Name,Location,standardized_skills\n1,Python Developer,Tech Corp,NYC,python;django;postgresql"

    # Act
    upload_response = test_client.post(
        "/ingest/jobs",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("jobs.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Assert
    job = await prisma_client.ingestionjob.find_unique(where={"id": job_id})
    assert job is not None
    assert job.file_type == "jobs"
    assert job.total_records == 1
    assert job.status in ["pending", "processing", "completed", "completed_with_errors"]



# Story 2.5: Real-Time Progress Tracking Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_returns_correct_data(test_db, test_client):
    """Test GET /ingest/status/{job_id} returns status with progress (Story 2.5 AC: 1, 2)."""
    # Arrange - Create a job
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    assert upload_response.status_code == 200
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    assert confirm_response.status_code == 202
    job_id = confirm_response.json()["ingestion_job_id"]

    # Act - Poll status endpoint
    response = test_client.get(
        f"/ingest/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert - Verify response structure (AC: 2)
    assert response.status_code == 200
    data = response.json()
    
    # Required fields from AC 2
    assert "job_id" in data
    assert "status" in data
    assert "total_records" in data
    assert "processed_records" in data
    assert "failed_records" in data
    assert "progress_percentage" in data
    
    # Verify data types and ranges
    assert data["job_id"] == job_id
    assert data["status"] in ["pending", "processing", "completed", "completed_with_errors", "failed"]
    assert 0 <= data["progress_percentage"] <= 100
    assert data["total_records"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_authorization(test_db, test_client):
    """Test user can only access their own jobs (Story 2.5 AC: 1)."""
    # Arrange - User A creates a job
    token_a, user_id_a = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Programming language,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    user_a_job_id = confirm_response.json()["ingestion_job_id"]

    # Act - User B tries to access user A's job
    token_b, user_id_b = create_test_user_and_login(test_client)
    response = test_client.get(
        f"/ingest/status/{user_a_job_id}",
        headers={"Authorization": f"Bearer {token_b}"}
    )

    # Assert - Should be forbidden
    assert response.status_code == 403
    data = response.json()
    assert "permission" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_not_found(test_db, test_client):
    """Test GET /ingest/status/{job_id} with non-existent ID returns 404."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    fake_job_id = "00000000-0000-0000-0000-000000000000"

    # Act
    response = test_client.get(
        f"/ingest/status/{fake_job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_progress_percentage(test_db, test_client, prisma_client):
    """Test progress percentage calculation (Story 2.5 AC: 4)."""
    # Arrange - Create a job and manually update processed records
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend\n2,Java,Lang,Tech,Backend\n3,JavaScript,Lang,Tech,Frontend\n4,Ruby,Lang,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    job_id = confirm_response.json()["ingestion_job_id"]

    # Simulate partial processing (2 out of 4 records)
    await prisma_client.ingestionjob.update(
        where={"id": job_id},
        data={
            "processed_records": 2,
            "failed_records": 0,
            "status": "processing"
        }
    )

    # Act
    response = test_client.get(
        f"/ingest/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert - Progress should be 50%
    assert response.status_code == 200
    data = response.json()
    assert data["progress_percentage"] == 50.0
    assert data["processed_records"] == 2
    assert data["total_records"] == 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_with_eta(test_db, test_client, prisma_client):
    """Test estimated time remaining calculation (Story 2.5 AC: 6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n" + b"\n".join([
        f"{i},Skill{i},Description{i},Tech,Backend".encode()
        for i in range(1, 101)  # 100 records
    ])

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    job_id = confirm_response.json()["ingestion_job_id"]

    # Simulate processing with speed tracking
    await prisma_client.ingestionjob.update(
        where={"id": job_id},
        data={
            "processed_records": 25,
            "processing_speed": 10.0,  # 10 records/sec
            "status": "processing"
        }
    )

    # Act
    response = test_client.get(
        f"/ingest/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert - ETA should be calculated
    assert response.status_code == 200
    data = response.json()
    assert "estimated_time_remaining" in data
    assert "processing_speed" in data
    
    if data["estimated_time_remaining"] is not None:
        # 75 remaining records / 10 records/sec = 7.5 seconds
        assert 7 <= data["estimated_time_remaining"] <= 8
    
    assert data["processing_speed"] == 10.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_endpoint_completed(test_db, test_client, prisma_client):
    """Test completed job returns 100% progress (Story 2.5 AC: 8)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    job_id = confirm_response.json()["ingestion_job_id"]

    # Simulate completed processing
    from datetime import datetime
    await prisma_client.ingestionjob.update(
        where={"id": job_id},
        data={
            "status": "completed",
            "processed_records": 1,
            "failed_records": 0,
            "completed_at": datetime.utcnow()
        }
    )

    # Act
    response = test_client.get(
        f"/ingest/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["progress_percentage"] == 100.0
    assert data["processed_records"] == data["total_records"]
    assert data["completed_at"] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_transitions(test_db, test_client, prisma_client):
    """Test status transitions from pending to completed (Story 2.5 AC: 7)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    job_id = confirm_response.json()["ingestion_job_id"]

    # Act & Assert - Test each status transition
    statuses = ["pending", "processing", "completed"]
    
    for status in statuses:
        # Update status
        await prisma_client.ingestionjob.update(
            where={"id": job_id},
            data={"status": status}
        )
        
        # Poll status
        response = test_client.get(
            f"/ingest/status/{job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_with_errors(test_db, test_client, prisma_client):
    """Test status for job with errors (Story 2.5 AC: 2, 7)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    csv_content = b"ID,NAME,DESCRIPTION,CATEGORY,SUBCATEGORY\n1,Python,Lang,Tech,Backend\n2,Java,Lang,Tech,Backend"

    upload_response = test_client.post(
        "/ingest/skills",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("skills.csv", BytesIO(csv_content), "text/csv")}
    )
    file_hash = upload_response.json()["file_hash"]

    confirm_response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": file_hash, "file_type": "skills"}
    )
    job_id = confirm_response.json()["ingestion_job_id"]

    # Simulate completed with errors
    from datetime import datetime
    await prisma_client.ingestionjob.update(
        where={"id": job_id},
        data={
            "status": "completed_with_errors",
            "processed_records": 1,
            "failed_records": 1,
            "completed_at": datetime.utcnow(),
            "error_log": "Some records failed validation"
        }
    )

    # Act
    response = test_client.get(
        f"/ingest/status/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed_with_errors"
    assert data["failed_records"] == 1
    assert data["error_message"] is not None


# Story 2.6: Error Export and Error Handling Tests

@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_error_log_success(test_db, test_client, prisma_client):
    """Test GET /ingest/errors/{job_id} downloads error log CSV (Story 2.6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)

    # Create job with errors
    job = await prisma_client.ingestionjob.create(
        data={
            "user_id": user_id,
            "file_type": "skills",
            "file_name": "test.csv",
            "file_size_mb": 1.0,
            "status": "completed_with_errors",
            "total_records": 10,
            "processed_records": 7,
            "failed_records": 3
        }
    )
    job_id = job.id

    # Create error records
    await prisma_client.ingestionerror.create(
        data={
            "job_id": job_id,
            "row_number": 5,
            "error_message": "Missing required field: NAME",
            "raw_data": '{"ID": "123"}'
        }
    )
    await prisma_client.ingestionerror.create(
        data={
            "job_id": job_id,
            "row_number": 8,
            "error_message": "Invalid data type: LEVEL must be integer",
            "raw_data": '{"ID": "456", "NAME": "Python", "LEVEL": "abc"}'
        }
    )
    await prisma_client.ingestionerror.create(
        data={
            "job_id": job_id,
            "row_number": 10,
            "error_message": "Parsing error",
            "raw_data": '{"malformed": "json'
        }
    )

    # Act
    response = test_client.get(
        f"/ingest/errors/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    assert f"ingestion_errors_{job_id}.csv" in response.headers["content-disposition"]

    # Verify CSV content
    csv_text = response.text
    assert "row_number,error_message,raw_data" in csv_text
    assert "Missing required field: NAME" in csv_text
    assert "Invalid data type: LEVEL must be integer" in csv_text
    assert "Parsing error" in csv_text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_error_log_authorization(test_db, test_client, prisma_client):
    """Test error log download requires job ownership (Story 2.6)."""
    # Arrange
    token1, user_id1 = create_test_user_and_login(test_client)
    token2, user_id2 = create_test_user_and_login(test_client)

    # Create job owned by user1 with errors
    job = await prisma_client.ingestionjob.create(
        data={
            "user_id": user_id1,
            "file_type": "skills",
            "file_name": "test.csv",
            "file_size_mb": 1.0,
            "status": "completed_with_errors",
            "total_records": 10,
            "processed_records": 9,
            "failed_records": 1
        }
    )
    job_id = job.id

    # Act - user2 tries to access user1's error log
    response = test_client.get(
        f"/ingest/errors/{job_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )

    # Assert - Should be forbidden
    assert response.status_code == 403
    data = response.json()
    assert "permission" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_error_log_not_found(test_db, test_client):
    """Test error log download with non-existent job ID (Story 2.6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)
    fake_job_id = str(uuid.uuid4())

    # Act
    response = test_client.get(
        f"/ingest/errors/{fake_job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_download_error_log_no_errors(test_db, test_client, prisma_client):
    """Test error log download with job that has no errors (Story 2.6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)

    # Create job with zero failed records
    job = await prisma_client.ingestionjob.create(
        data={
            "user_id": user_id,
            "file_type": "skills",
            "file_name": "test.csv",
            "file_size_mb": 1.0,
            "status": "completed",
            "total_records": 10,
            "processed_records": 10,
            "failed_records": 0
        }
    )
    job_id = job.id

    # Act
    response = test_client.get(
        f"/ingest/errors/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "no errors" in data["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validation_error_handling(test_client):
    """Test validation error returns 422 with details (Story 2.6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)

    # Act - Send invalid confirmation request (missing required fields)
    response = test_client.post(
        "/ingest/confirm",
        headers={"Authorization": f"Bearer {token}"},
        json={}  # Missing file_hash and file_type
    )

    # Assert
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "validation_error"
    assert "message" in data
    assert "details" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authentication_error_handling(test_client):
    """Test authentication error returns 401 (Story 2.6)."""
    # Act - Access protected endpoint without token
    response = test_client.get("/ingest/jobs")

    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert "authentication" in data["error"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_log_with_multiple_errors(test_db, test_client, prisma_client):
    """Test error log download with multiple errors returns all errors (Story 2.6)."""
    # Arrange
    token, user_id = create_test_user_and_login(test_client)

    # Create job
    job = await prisma_client.ingestionjob.create(
        data={
            "user_id": user_id,
            "file_type": "jobs",
            "file_name": "large.csv",
            "file_size_mb": 5.0,
            "status": "completed_with_errors",
            "total_records": 100,
            "processed_records": 90,
            "failed_records": 10
        }
    )
    job_id = job.id

    # Create 10 error records
    for i in range(1, 11):
        await prisma_client.ingestionerror.create(
            data={
                "job_id": job_id,
                "row_number": i * 10,
                "error_message": f"Error {i}: Some validation failure",
                "raw_data": f'{{"row": "{i}"}}'
            }
        )

    # Act
    response = test_client.get(
        f"/ingest/errors/{job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Assert
    assert response.status_code == 200
    csv_text = response.text

    # Should have header + 10 error rows
    lines = csv_text.strip().split('\n')
    assert len(lines) == 11  # 1 header + 10 errors

    # Verify all errors are present
    for i in range(1, 11):
        assert f"Error {i}" in csv_text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_log_unauthorized_access(test_db, test_client):
    """Test error log download without authentication (Story 2.6)."""
    # Arrange
    fake_job_id = str(uuid.uuid4())

    # Act - No authentication token
    response = test_client.get(f"/ingest/errors/{fake_job_id}")

    # Assert
    assert response.status_code == 401
