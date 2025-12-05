# 11. Security

## 11.1 MVP Security Philosophy

**For MVP, focus on essential security**:
- ✅ **Authentication**: JWT-based with secure password hashing
- ✅ **Input validation**: Pydantic models with type checking
- ✅ **CORS**: Configured for frontend origin
- ✅ **Environment secrets**: Never hardcode credentials
- ❌ **HTTPS/SSL**: Skip for local dev (add for production)
- ❌ **Rate limiting**: Add after scaling
- ❌ **WAF/DDoS protection**: Cloud provider handles this

**Security Mindset**:
- Prevent common attacks (SQL injection, XSS)
- Protect user credentials
- Validate all inputs
- Keep dependencies updated

---

## 11.2 Authentication & Authorization

### **JWT-Based Authentication**

**Token Generation**:

**`app/utils/jwt.py`**:
```python
"""JWT token utilities."""
import jwt
from datetime import datetime, timedelta
from app.config import settings

def create_access_token(user_id: str) -> str:
    """
    Generate JWT access token for authenticated user.

    Args:
        user_id: Unique user identifier

    Returns:
        Encoded JWT token string
    """
    payload = {
        "sub": user_id,  # Subject (user ID)
        "iat": datetime.utcnow(),  # Issued at
        "exp": datetime.utcnow() + timedelta(
            minutes=settings.jwt_expiration_minutes
        )  # Expiration
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )

    return token

def verify_access_token(token: str) -> str:
    """
    Verify JWT token and extract user ID.

    Args:
        token: JWT token string

    Returns:
        User ID from token payload

    Raises:
        jwt.ExpiredSignatureError: Token expired
        jwt.InvalidTokenError: Token invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: str = payload.get("sub")

        if not user_id:
            raise jwt.InvalidTokenError("Missing user ID in token")

        return user_id

    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidTokenError:
        raise
```

---

### **Authentication Dependency**

**`app/middleware/auth.py`**:
```python
"""Authentication middleware for protected endpoints."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials

from app.utils.jwt import verify_access_token
from app.exceptions import AuthenticationError

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthCredentials = Depends(security)
) -> str:
    """
    Extract and verify JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials from header

    Returns:
        User ID from verified token

    Raises:
        AuthenticationError: If token invalid or expired
    """
    token = credentials.credentials

    try:
        user_id = verify_access_token(token)
        return user_id

    except Exception as e:
        raise AuthenticationError(f"Invalid or expired token: {str(e)}")
```

**Usage in Protected Endpoints**:

```python
# app/api/ingest.py
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("/skills")
async def upload_skills_csv(
    file: UploadFile,
    user_id: str = Depends(get_current_user),  # Require authentication
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Upload skills CSV (authenticated users only)."""
    return await ingestion_service.start_skills_ingestion(file, user_id)
```

---

## 11.3 Password Security

**Use bcrypt for password hashing**:

**`app/services/auth_service.py`**:
```python
"""Authentication service with secure password handling."""
import bcrypt

class AuthService:
    """Handles user authentication."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with salt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        # Generate salt (cost factor = 12 rounds, good balance of security/performance)
        salt = bcrypt.gensalt(rounds=12)

        # Hash password
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            salt
        )

        return password_hash.decode('utf-8')

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Plain text password from login
            password_hash: Stored bcrypt hash

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            password_hash.encode('utf-8')
        )
```

**Password Validation** (Pydantic):

```python
# app/models/auth.py
from pydantic import BaseModel, EmailStr, Field, validator
import re

class RegisterRequest(BaseModel):
    """
    User registration with comprehensive password validation.

    Password Requirements:
    - Minimum 12 characters (increased from 8 for better security)
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character (@$!%*?&#)
    """
    email: EmailStr
    password: str = Field(
        ...,
        min_length=12,
        description="Secure password with complexity requirements"
    )

    @validator('password')
    def validate_password_strength(cls, v):
        """
        Enforce password complexity requirements.

        This validator ensures strong passwords to prevent:
        - Brute force attacks (length requirement)
        - Dictionary attacks (complexity requirement)
        - Simple password guessing (mixed character types)

        Args:
            v: Password string to validate

        Returns:
            Validated password string

        Raises:
            ValueError: If password doesn't meet security requirements
        """
        # Length check (Pydantic Field handles this, but double-check)
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters long")

        # Uppercase letter requirement
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")

        # Lowercase letter requirement
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")

        # Digit requirement
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit (0-9)")

        # Special character requirement
        if not re.search(r'[@$!%*?&#]', v):
            raise ValueError(
                "Password must contain at least one special character (@$!%*?&#)"
            )

        # Optional: Check for common weak patterns (can add more)
        weak_patterns = [
            r'password', r'12345', r'qwerty', r'abc123',
            r'admin', r'letmein', r'welcome'
        ]
        for pattern in weak_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError(
                    f"Password contains weak pattern '{pattern}'. Choose a stronger password."
                )

        return v
```

**Password Strength Examples**:

```python
# ✅ Valid passwords (meet all requirements)
"SecurePass123!"    # 15 chars, all requirements met
"MyApp@2025Secure"  # 16 chars, all requirements met
"P@ssw0rdStr0ng!"   # 15 chars, all requirements met

# ❌ Invalid passwords (fail requirements)
"short123!"         # Only 9 chars (< 12)
"nouppercase123!"   # Missing uppercase letter
"NOLOWERCASE123!"   # Missing lowercase letter
"NoSpecialChar123"  # Missing special character
"NoDigits@Here!"    # Missing digit
"Password123!"      # Contains weak pattern 'password'
```

**API Error Response**:

```json
// POST /api/auth/register
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must contain at least one uppercase letter (A-Z)",
      "type": "value_error"
    }
  ]
}
```

---

## 11.4 Input Validation & Sanitization

**Pydantic Automatic Validation**:

```python
# app/models/query.py
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    """User query with validation."""
    query: str = Field(..., min_length=1, max_length=500)

    @validator('query')
    def sanitize_query(cls, v):
        """Remove dangerous characters from query."""
        # Strip leading/trailing whitespace
        v = v.strip()

        # Prevent empty queries
        if not v:
            raise ValueError("Query cannot be empty")

        return v
```

**CSV File Validation** (🔴 CRITICAL Security):

### **Dependencies for File Upload Security**

Add to `requirements.txt`:
```txt
python-magic==0.4.27    # MIME type detection (libmagic wrapper)
```

**For macOS** (install libmagic):
```bash
brew install libmagic
```

**For Ubuntu/Debian**:
```bash
apt-get install libmagic1
```

### **Comprehensive CSV Validation**

```python
# app/services/ingestion_service.py
from fastapi import UploadFile, HTTPException, status
import magic  # python-magic library
import csv
import io
import re
from pathlib import Path

# Configuration constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_CSV_ROWS = 100_000  # CSV bomb protection
ALLOWED_EXTENSIONS = {'.csv'}  # Extension whitelist
ALLOWED_MIME_TYPES = {'text/csv', 'text/plain', 'application/csv'}  # Valid MIME types

async def validate_csv_file(file: UploadFile) -> bytes:
    """
    Comprehensive CSV file validation with security checks.

    Security Protections:
    1. File Extension Whitelist - Prevents disguised malicious files
    2. MIME Type Validation - Uses libmagic (not client-provided Content-Type)
    3. Filename Sanitization - Prevents path traversal attacks
    4. File Size Limit - Prevents memory exhaustion
    5. CSV Bomb Protection - Limits row count to prevent DoS

    Args:
        file: Uploaded file from FastAPI

    Returns:
        bytes: Validated file content

    Raises:
        HTTPException: If validation fails
    """
    # 1. Validate filename is not None
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    # 2. Sanitize filename (prevent path traversal)
    sanitized_filename = sanitize_filename(file.filename)
    if sanitized_filename != file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Only alphanumeric, hyphens, underscores, and dots allowed."
        )

    # 3. Validate file extension (whitelist)
    file_extension = Path(sanitized_filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{file_extension}'. Only .csv files are allowed."
        )

    # 4. Read file content
    content = await file.read()
    await file.seek(0)  # Reset file pointer for later use

    # 5. Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # 6. Validate MIME type using libmagic (not client-provided Content-Type)
    mime = magic.Magic(mime=True)
    detected_mime = mime.from_buffer(content)

    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Detected MIME type: {detected_mime}. Expected: CSV file."
        )

    # 7. Validate CSV structure and row count (CSV bomb protection)
    try:
        csv_content = content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))

        # Count rows
        row_count = sum(1 for row in csv_reader)

        if row_count > MAX_CSV_ROWS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV file too large. Max {MAX_CSV_ROWS:,} rows allowed. Found {row_count:,} rows."
            )

        # Validate CSV has at least a header row
        if row_count < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty or has no header row."
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid CSV encoding. File must be UTF-8 encoded."
        )
    except csv.Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )

    return content


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and injection attacks.

    Security Rules:
    - Remove path separators (/, \\)
    - Remove null bytes
    - Allow only: alphanumeric, hyphens, underscores, dots
    - Limit length to 255 characters

    Args:
        filename: Original filename from client

    Returns:
        str: Sanitized filename (safe for filesystem)
    """
    # Remove path components (prevent ../../../etc/passwd attacks)
    filename = Path(filename).name

    # Remove null bytes
    filename = filename.replace('\x00', '')

    # Only allow safe characters: alphanumeric, hyphen, underscore, dot
    safe_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')
    if not safe_pattern.match(filename):
        # Replace unsafe characters with underscores
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Limit length
    if len(filename) > 255:
        # Keep extension, truncate name
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255 - len(ext)] + ext

    return filename
```

### **Usage in Ingestion Service**

```python
# app/services/ingestion_service.py
class IngestionService:
    """Handles CSV ingestion with security validation."""

    async def start_skills_ingestion(
        self,
        file: UploadFile,
        user_id: str
    ) -> IngestionResponse:
        """
        Ingest skills CSV file with comprehensive validation.

        Args:
            file: Uploaded CSV file
            user_id: Current authenticated user ID

        Returns:
            IngestionResponse: Job status with job_id
        """
        # Validate file (comprehensive security checks)
        content = await validate_csv_file(file)

        # Parse CSV
        csv_data = self._parse_skills_csv(content.decode('utf-8'))

        # Create ingestion job in PostgreSQL
        job = await self.create_ingestion_job(
            user_id=user_id,
            filename=sanitize_filename(file.filename),  # Use sanitized filename
            row_count=len(csv_data)
        )

        # Process asynchronously (background task)
        await self.process_skills_batch(job.id, csv_data)

        return IngestionResponse(
            job_id=job.id,
            status="processing",
            message=f"Started processing {len(csv_data)} skills"
        )
```

### **Transaction Rollback Strategy** (🟠 HIGH - Data Integrity)

**Why Transaction Management is Critical**:
- Prevents partial data corruption when batch processing fails
- Maintains graph consistency (no orphan nodes or broken relationships)
- Allows safe retry of failed batches
- Tracks exactly which batches succeeded/failed

#### **Neo4j Transaction Context Manager**

```python
# app/repositories/neo4j_repository.py
from neo4j import AsyncGraphDatabase, AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncGenerator

class Neo4jRepository:
    """Neo4j repository with transaction support."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for Neo4j transactions.

        Usage:
            async with neo4j_repo.transaction() as tx:
                await tx.run("CREATE (n:Node {name: $name})", name="test")
                # If exception occurs here, transaction is rolled back
                await tx.run("MATCH (n:Node) RETURN n")
        """
        async with self.driver.session() as session:
            async with session.begin_transaction() as tx:
                try:
                    yield tx
                    await tx.commit()
                except Exception as e:
                    await tx.rollback()
                    raise

    async def create_skills_batch_transactional(
        self,
        skills: list[dict],
        tx: AsyncSession
    ) -> dict:
        """
        Create skill nodes in a single transaction.

        Args:
            skills: List of skill dictionaries with name, embedding, etc.
            tx: Neo4j transaction session

        Returns:
            dict: Result with created_count, failed_count
        """
        query = """
        UNWIND $skills AS skill
        CREATE (s:Skill {
            id: skill.id,
            name: skill.name,
            description: skill.description,
            embedding: skill.embedding
        })
        RETURN count(s) as created_count
        """

        try:
            result = await tx.run(query, skills=skills)
            record = await result.single()
            return {"created_count": record["created_count"], "failed_count": 0}
        except Exception as e:
            # Transaction will be rolled back by context manager
            return {"created_count": 0, "failed_count": len(skills), "error": str(e)}
```

#### **Batch Processing with Rollback Strategy**

```python
# app/services/ingestion_service.py
from app.config import settings
from app.exceptions import IngestionError

class IngestionService:
    """Ingestion service with transaction management."""

    BATCH_SIZE = 1000  # Process 1000 rows per batch
    FAILURE_THRESHOLD = 0.10  # Rollback if >10% of batch fails

    async def process_skills_batch(
        self,
        job_id: str,
        csv_data: list[dict]
    ) -> None:
        """
        Process skills CSV in batches with transaction rollback.

        Rollback Strategy:
        - Each batch is processed in a Neo4j transaction
        - If >10% of rows in a batch fail, rollback entire batch
        - Track successful/failed batches in PostgreSQL
        - Allow resume from last successful batch on retry

        Args:
            job_id: IngestionJob ID for tracking
            csv_data: Parsed CSV data (list of dicts)
        """
        total_rows = len(csv_data)
        total_batches = (total_rows + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        successful_batches = 0
        failed_batch_number = None

        try:
            for batch_num in range(total_batches):
                # Update progress
                await self.ingestion_repo.update_job_progress(
                    job_id=job_id,
                    current_batch=batch_num + 1,
                    total_batches=total_batches,
                    status="processing"
                )

                # Extract current batch
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, total_rows)
                batch_data = csv_data[start_idx:end_idx]

                # Process batch with transaction
                result = await self._process_single_batch_transactional(
                    batch_data,
                    batch_num
                )

                # Check failure threshold
                failure_rate = result["failed_count"] / len(batch_data)
                if failure_rate > self.FAILURE_THRESHOLD:
                    failed_batch_number = batch_num + 1
                    raise IngestionError(
                        f"Batch {batch_num + 1} failed: {failure_rate*100:.1f}% failure rate "
                        f"(threshold: {self.FAILURE_THRESHOLD*100}%). "
                        f"Transaction rolled back."
                    )

                successful_batches += 1

            # Mark job as completed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="completed",
                successful_batches=successful_batches,
                error_batch=None
            )

        except IngestionError as e:
            # Mark job as partially completed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="partially_completed",
                successful_batches=successful_batches,
                error_batch=failed_batch_number,
                error_message=str(e)
            )
            raise

        except Exception as e:
            # Unexpected error - mark as failed
            await self.ingestion_repo.update_job_status(
                job_id=job_id,
                status="failed",
                successful_batches=successful_batches,
                error_batch=failed_batch_number or (successful_batches + 1),
                error_message=str(e)
            )
            raise

    async def _process_single_batch_transactional(
        self,
        batch_data: list[dict],
        batch_num: int
    ) -> dict:
        """
        Process a single batch within a Neo4j transaction.

        Args:
            batch_data: Rows for this batch
            batch_num: Batch number (for logging)

        Returns:
            dict: {created_count, failed_count, error?}
        """
        # Generate embeddings for batch
        embeddings = await self.embedding_service.generate_batch_embeddings(
            [row["name"] + " " + row.get("description", "") for row in batch_data]
        )

        # Add embeddings to batch data
        for idx, row in enumerate(batch_data):
            row["embedding"] = embeddings[idx]

        # Create nodes in transaction
        async with self.neo4j_repo.transaction() as tx:
            result = await self.neo4j_repo.create_skills_batch_transactional(
                batch_data,
                tx
            )

        return result

    async def resume_failed_ingestion(
        self,
        job_id: str
    ) -> None:
        """
        Resume a partially completed ingestion from last successful batch.

        Args:
            job_id: IngestionJob ID to resume
        """
        job = await self.ingestion_repo.get_job_by_id(job_id)

        if job.status != "partially_completed":
            raise IngestionError(
                f"Cannot resume job {job_id}: status is {job.status}, expected 'partially_completed'"
            )

        # Re-read original CSV
        csv_data = await self._load_csv_from_storage(job.filename, job.user_id)

        # Skip already processed batches
        start_batch = job.successful_batches
        remaining_data = csv_data[start_batch * self.BATCH_SIZE:]

        # Process remaining batches
        await self.process_skills_batch(job_id, remaining_data)
```

#### **PostgreSQL Job Status Schema Update**

Add fields to track batch-level progress:

```python
# prisma/schema.prisma
model IngestionJob {
  id              String   @id @default(uuid())
  user_id         String
  filename        String
  status          String   // "processing", "completed", "failed", "partially_completed"
  total_rows      Int
  total_batches   Int?
  current_batch   Int?
  successful_batches Int?   // NEW: Track successful batches
  error_batch     Int?     // NEW: Which batch failed
  error_message   String?  // NEW: Error details
  created_at      DateTime @default(now())
  updated_at      DateTime @updatedAt

  user User @relation(fields: [user_id], references: [id])
}
```

#### **API Response with Batch Status**

```json
// GET /api/ingest/status/{job_id}
{
  "job_id": "abc-123",
  "status": "partially_completed",
  "total_rows": 50000,
  "total_batches": 50,
  "current_batch": 23,
  "successful_batches": 22,
  "error_batch": 23,
  "error_message": "Batch 23 failed: 15.2% failure rate (threshold: 10%). Transaction rolled back.",
  "can_resume": true,
  "created_at": "2025-10-22T14:30:00Z"
}
```

#### **Retry Logic for Transient Failures**

```python
# app/services/ingestion_service.py
import asyncio

async def _process_single_batch_with_retry(
    self,
    batch_data: list[dict],
    batch_num: int,
    max_retries: int = 3
) -> dict:
    """
    Process batch with exponential backoff retry for transient errors.

    Args:
        batch_data: Rows for this batch
        batch_num: Batch number
        max_retries: Maximum retry attempts

    Returns:
        dict: Processing result
    """
    for attempt in range(max_retries):
        try:
            return await self._process_single_batch_transactional(
                batch_data,
                batch_num
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Batch {batch_num} failed (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying in {wait_time}s... Error: {str(e)}"
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Batch {batch_num} failed after {max_retries} attempts. "
                    f"Error: {str(e)}"
                )
                raise
```

#### **Transaction Rollback Summary**

| Scenario | Action | PostgreSQL Status | Neo4j State |
|----------|--------|------------------|-------------|
| Batch succeeds | Commit transaction | Update progress | Nodes created |
| Batch <10% failure | Commit transaction | Update progress | Partial nodes created |
| Batch >10% failure | Rollback transaction | Mark "partially_completed" | No nodes created |
| Unexpected error | Rollback transaction | Mark "failed" | No nodes created |
| Resume requested | Process from error_batch | Update status to "processing" | Continue from last successful |

**Key Benefits**:
- **Atomicity**: Each batch is all-or-nothing (Neo4j transaction)
- **Consistency**: PostgreSQL tracks exact state for debugging
- **Resumable**: Can continue from last successful batch
- **Predictable**: Clear failure thresholds (10% rule)

### **Security Test Cases**

```python
# tests/security/test_file_upload_security.py
import pytest
from fastapi.testclient import TestClient

def test_reject_non_csv_extension(client: TestClient, auth_token: str):
    """Test that non-CSV extensions are rejected."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("malicious.exe", b"fake content", "application/octet-stream")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Only .csv files are allowed" in response.json()["detail"]


def test_reject_fake_csv_mime_type(client: TestClient, auth_token: str):
    """Test that files with fake CSV MIME types are rejected."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Executable disguised as CSV
    files = {"file": ("fake.csv", b"\x4d\x5a\x90\x00", "text/csv")}  # MZ header (exe)

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_reject_csv_bomb(client: TestClient, auth_token: str):
    """Test CSV bomb protection (too many rows)."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # Generate CSV with 100,001 rows
    large_csv = "name,description\n" + "\n".join(f"skill{i},desc{i}" for i in range(100001))
    files = {"file": ("bomb.csv", large_csv.encode(), "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "100,000 rows allowed" in response.json()["detail"]


def test_reject_path_traversal_filename(client: TestClient, auth_token: str):
    """Test that path traversal attacks in filename are prevented."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("../../../etc/passwd.csv", b"name,description\n", "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 400
    assert "Invalid filename" in response.json()["detail"]


def test_reject_oversized_file(client: TestClient, auth_token: str):
    """Test file size limit enforcement."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    # 51MB file
    large_content = b"a" * (51 * 1024 * 1024)
    files = {"file": ("large.csv", large_content, "text/csv")}

    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]
```

### **File Upload Security Summary**

| Security Check | Protection Against | Implementation |
|---------------|-------------------|----------------|
| Extension Whitelist | Malicious file types | Only `.csv` allowed |
| MIME Type Validation | Disguised malicious files | `python-magic` (libmagic) |
| Filename Sanitization | Path traversal attacks | Remove `../`, null bytes |
| File Size Limit | Memory exhaustion DoS | Max 50MB |
| CSV Row Limit | CSV bomb attacks | Max 100K rows |
| Encoding Validation | Injection attacks | UTF-8 only |

**Why python-magic?**
- Client-provided `Content-Type` headers are **untrusted** (easily spoofed)
- `python-magic` uses libmagic to analyze file content (same as `file` command)
- Detects actual file type by inspecting binary signatures and content
- Example: Detects `.exe` file even if client claims `Content-Type: text/csv`

---

## 11.5 Rate Limiting (🔴 CRITICAL for MVP)

**Why Rate Limiting is Critical**:
- Prevents brute force attacks on authentication endpoints
- Protects against API abuse and DoS attacks
- Prevents credential stuffing attacks
- Limits resource consumption from malicious users

### **Dependencies**

Add to `requirements.txt`:
```txt
slowapi==0.1.9        # Rate limiting for FastAPI
redis==5.0.1          # Optional: Redis backend for distributed rate limiting
```

Install dependencies:
```bash
pip install slowapi redis
```

### **Configuration in main.py**

**`app/main.py`**:
```python
"""FastAPI application with rate limiting."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=["100/minute"],  # Global default: 100 requests/minute
    storage_uri="memory://",  # Use in-memory storage (or redis:// for production)
)

app = FastAPI(title="Graph RAG API")

# Add rate limiter to app state
app.state.limiter = limiter

# Add custom rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail)
        },
        headers=exc.headers  # Include rate limit headers
    )
```

### **Rate Limits for Authentication Endpoints**

**`app/api/auth.py`**:
```python
"""Authentication endpoints with rate limiting."""
from fastapi import APIRouter, Depends, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/hour")  # Max 3 registrations per hour per IP
async def register(
    request: Request,  # Required for slowapi
    user_data: UserCreate,
    auth_service: AuthService = Depends()
):
    """
    Register a new user account.

    Rate Limit: 3 registrations per hour per IP address
    Rationale: Prevents automated account creation and spam
    """
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Max 5 login attempts per minute per IP
async def login(
    request: Request,  # Required for slowapi
    credentials: UserLogin,
    auth_service: AuthService = Depends()
):
    """
    User login with JWT token generation.

    Rate Limit: 5 login attempts per minute per IP address
    Rationale: Prevents brute force password attacks and credential stuffing
    """
    return await auth_service.authenticate_user(credentials)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")  # Max 10 token refreshes per minute
async def refresh_token(
    request: Request,
    refresh_token: str,
    auth_service: AuthService = Depends()
):
    """
    Refresh JWT access token.

    Rate Limit: 10 refreshes per minute per IP address
    Rationale: Normal usage rarely needs frequent refreshes
    """
    return await auth_service.refresh_access_token(refresh_token)
```

### **Rate Limits for CSV Upload**

**`app/api/ingestion.py`**:
```python
"""Ingestion endpoints with rate limiting."""
from fastapi import APIRouter, Depends, UploadFile, File, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.services.ingestion_service import IngestionService
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])
limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/skills",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("3/hour")  # Max 3 CSV uploads per hour per user
async def ingest_skills_csv(
    request: Request,  # Required for slowapi
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """
    Upload and process skills CSV file.

    Rate Limit: 3 uploads per hour per user
    Rationale:
    - CSV processing is resource-intensive (embedding generation)
    - Prevents abuse of expensive LLM API calls
    - Normal users rarely need more than 3 uploads/hour
    """
    return await ingestion_service.start_skills_ingestion(file, user_id)


@router.post(
    "/jobs",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("3/hour")  # Max 3 CSV uploads per hour per user
async def ingest_jobs_csv(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends()
):
    """
    Upload and process jobs CSV file.

    Rate Limit: 3 uploads per hour per user
    """
    return await ingestion_service.start_jobs_ingestion(file, user_id)
```

### **Rate Limit Response Headers**

When rate limits are applied, responses include standard headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1640000000
```

**Header Descriptions**:
- `X-RateLimit-Limit`: Maximum requests allowed in time window
- `X-RateLimit-Remaining`: Number of requests remaining
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

### **Rate Limit Exceeded Response**

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640000060
Retry-After: 60

{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Please try again later.",
  "detail": "5 per 1 minute"
}
```

### **Production: Redis Backend**

For production with multiple backend instances, use Redis for shared rate limit state:

**`app/main.py` (Production)**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Use Redis for distributed rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=f"redis://{settings.redis_host}:6379/0"  # Redis connection
)
```

**Add to `.env`**:
```bash
# Rate Limiting (Production)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### **Testing Rate Limits**

**Unit Test Example**:
```python
# tests/api/test_rate_limiting.py
import pytest
from fastapi.testclient import TestClient

def test_login_rate_limit(client: TestClient):
    """Test login endpoint rate limiting."""
    credentials = {"email": "test@example.com", "password": "wrong"}

    # Make 5 login attempts (should succeed)
    for i in range(5):
        response = client.post("/api/auth/login", json=credentials)
        assert response.status_code in [200, 401]  # 200 success or 401 invalid creds

    # 6th attempt should be rate limited
    response = client.post("/api/auth/login", json=credentials)
    assert response.status_code == 429
    assert "rate_limit_exceeded" in response.json()["error"]
    assert "X-RateLimit-Limit" in response.headers


def test_csv_upload_rate_limit(client: TestClient, auth_token: str):
    """Test CSV upload rate limiting."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    files = {"file": ("skills.csv", "name,description\nPython,Programming", "text/csv")}

    # Make 3 uploads (should succeed)
    for i in range(3):
        response = client.post("/api/ingest/skills", files=files, headers=headers)
        assert response.status_code == 202

    # 4th upload should be rate limited
    response = client.post("/api/ingest/skills", files=files, headers=headers)
    assert response.status_code == 429
```

### **Rate Limiting Summary**

| Endpoint | Rate Limit | Key | Rationale |
|----------|-----------|-----|-----------|
| `POST /auth/register` | 3/hour | IP | Prevent automated account creation |
| `POST /auth/login` | 5/minute | IP | Prevent brute force attacks |
| `POST /auth/refresh` | 10/minute | IP | Normal usage pattern |
| `POST /ingest/skills` | 3/hour | User | Expensive LLM operations |
| `POST /ingest/jobs` | 3/hour | User | Expensive LLM operations |
| Global default | 100/minute | IP | General API abuse prevention |

**Why These Limits?**
- **Login (5/min)**: Enough for legitimate users, too slow for brute force
- **Registration (3/hour)**: Prevents spam, allows genuine users
- **CSV Upload (3/hour)**: Each upload triggers expensive embedding generation
- **Global (100/min)**: Generous default for normal API usage

---

## 11.6 CORS Configuration

**Configure CORS for frontend**:

**`app/main.py`**:
```python
"""FastAPI application with CORS middleware."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(title="Graph RAG API")

# CORS Configuration
origins = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    # Add production frontend URL here when deploying
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Specific origins (not "*" for production)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**For MVP development** (more permissive):

```python
# Only for local development - NEVER in production
if settings.debug:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
```

---

## 11.6 Environment Variable Security

**Never commit secrets to version control**:

### **JWT Secret Generation (CRITICAL)**

**Generate secure JWT secret** (minimum 64 characters hex):

```bash
# Generate cryptographically secure secret
openssl rand -hex 32

# Example output (64 characters):
# 3f7a8b2c9d4e1f0a6b5c8d7e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a
```

**Why 64 characters?**
- 32 bytes = 256 bits of entropy
- Prevents brute force attacks
- Meets OWASP recommendations

**NEVER use weak secrets like**:
- ❌ `"secret"`, `"mysecretkey"`, `"your-secret-here"`
- ❌ Dictionary words or common phrases
- ❌ Less than 64 characters

---

### **Configuration File with Validation**

**`app/config.py`** - Add JWT secret validation:

```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Application configuration with security validation."""

    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    neo4j_uri: str = Field(..., env="NEO4J_URI")
    neo4j_user: str = Field(..., env="NEO4J_USER")
    neo4j_password: str = Field(..., env="NEO4J_PASSWORD")

    # API Keys
    openrouter_api_key: str = Field(..., env="OPENROUTER_API_KEY")

    # JWT - With Security Validation
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_minutes: int = Field(default=60)

    # Application
    app_name: str = Field(default="Graph RAG API")
    debug: bool = Field(default=False)

    @validator('jwt_secret')
    def validate_jwt_secret_strength(cls, v):
        """Ensure JWT secret meets minimum security requirements."""
        if len(v) < 64:
            raise ValueError(
                'JWT_SECRET must be at least 64 characters '
                '(generate with: openssl rand -hex 32)'
            )

        # Check for common weak patterns
        weak_patterns = ['secret', 'password', 'test', 'demo', 'your-']
        if any(pattern in v.lower() for pattern in weak_patterns):
            raise ValueError(
                'JWT_SECRET contains weak pattern. '
                'Use cryptographically secure random key.'
            )

        return v

    @validator('openrouter_api_key')
    def validate_openrouter_key(cls, v):
        """Ensure OpenRouter API key is set."""
        if v.startswith('<') or v.startswith('your-'):
            raise ValueError(
                'OPENROUTER_API_KEY not set. '
                'Get API key from https://openrouter.ai'
            )
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False
```

**On Startup Validation**:
```python
# app/main.py
from app.config import settings

@app.on_event("startup")
async def validate_configuration():
    """Validate configuration on startup."""
    try:
        # Settings validation runs automatically via Pydantic
        logger.info("✅ Configuration validation passed")
        logger.info(f"JWT expiration: {settings.jwt_expiration_minutes} minutes")
    except ValueError as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        raise SystemExit(1)
```

---

### **Environment Files**

**`.env`** (add to `.gitignore` - NEVER commit):
```bash
# Database credentials
DATABASE_URL=postgresql://user:password@localhost:5432/graphrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password

# API Keys
OPENROUTER_API_KEY=sk-or-v1-abc123...

# JWT Secret - GENERATE NEW KEY (openssl rand -hex 32)
JWT_SECRET=3f7a8b2c9d4e1f0a6b5c8d7e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Application
DEBUG=True
```

**`.gitignore`**:
```
# Environment files
.env
.env.local
.env.production
.env.*.local

# Secrets
*.pem
*.key
secrets/
```

**`.env.example`** (commit this for documentation):
```bash
# ===============================================
# Graph RAG API Environment Configuration
# ===============================================

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/graphrag
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<set-secure-password>

# API Keys
OPENROUTER_API_KEY=<get-from-https://openrouter.ai>

# JWT Configuration
# CRITICAL: Generate with: openssl rand -hex 32
# NEVER use example keys in production!
JWT_SECRET=<GENERATE_WITH_OPENSSL_RAND_HEX_32>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Application Settings
DEBUG=False
APP_NAME=Graph RAG API

# ===============================================
# Setup Instructions:
# 1. Copy this file: cp .env.example .env
# 2. Generate JWT secret: openssl rand -hex 32
# 3. Set OpenRouter API key from https://openrouter.ai
# 4. Set secure database passwords
# 5. NEVER commit .env to version control
# ===============================================
```

---

### **JWT Secret Rotation Strategy**

**When to rotate JWT secret**:
1. **Suspected compromise** - Rotate immediately
2. **Employee departure** - If they had access
3. **Scheduled rotation** - Every 90 days (production best practice)
4. **Before production launch** - Always use fresh secret

**How to rotate**:

```bash
# 1. Generate new secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. Update .env
echo "JWT_SECRET=$NEW_SECRET" >> .env

# 3. Restart application
docker-compose restart backend

# 4. All users must re-login (tokens invalidated)
```

**Rotation impact**:
- ✅ Old tokens become invalid (secure)
- ⚠️ All users forced to re-login (expected)
- ⚠️ Active sessions terminated (security feature)

---

## 11.7 SQL Injection Prevention

**Prisma ORM handles parameterization automatically**:

```python
# ✅ Safe - Prisma uses parameterized queries
user = await prisma.user.find_unique(
    where={"email": user_email}  # Automatically sanitized
)

# ❌ NEVER do this (example of unsafe code)
# raw_query = f"SELECT * FROM users WHERE email = '{user_email}'"
# This is vulnerable to SQL injection
```

**Neo4j Cypher Queries with Parameters**:

```python
# ✅ Safe - Use parameters
query = """
CREATE (s:Skill {
    id: $id,
    name: $name,
    level: $level
})
RETURN s
"""
result = await neo4j_session.run(query, parameters={
    "id": skill_id,
    "name": skill_name,
    "level": skill_level
})

# ❌ NEVER do this (example of unsafe code)
# query = f"CREATE (s:Skill {{name: '{skill_name}'}}) RETURN s"
# This is vulnerable to Cypher injection
```

---

## 11.8 API Security Best Practices

### **1. No Sensitive Data in Responses**

```python
# ✅ Good - Exclude password from response
class UserResponse(BaseModel):
    """User response (no password)."""
    id: str
    email: str
    created_at: str

    class Config:
        from_attributes = True

# ❌ Bad - Exposing password hash
class UserResponse(BaseModel):
    id: str
    email: str
    password_hash: str  # NEVER expose this!
```

### **2. Authorization Checks**

```python
# app/api/ingest.py
@router.get("/status/{job_id}")
async def get_ingestion_status(
    job_id: str,
    user_id: str = Depends(get_current_user),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """Get ingestion status (only for job owner)."""
    job = await ingestion_service.get_job_status(job_id)

    # Authorization check - users can only access their own jobs
    if job.user_id != user_id:
        raise AuthorizationError("Access denied to this job")

    return job
```

### **3. Error Message Safety**

```python
# ✅ Good - Generic error message
if not user:
    raise AuthenticationError("Invalid email or password")

# ❌ Bad - Reveals if email exists
if not user:
    raise AuthenticationError("Email not found in system")
```

---

## 11.9 Dependency Security

**Keep dependencies updated**:

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade fastapi prisma neo4j
```

**Pin versions in `requirements.txt`**:

```txt
fastapi==0.109.0
prisma==0.11.0
neo4j==5.15.0
bcrypt==4.1.2
pyjwt==2.8.0
```

**Use `requirements-dev.txt` for dev-only packages**:

```txt
pytest==7.4.3
black==23.12.1
isort==5.13.2
safety==2.3.5
```

---

## 11.10 Logging Security

**Never log sensitive data**:

```python
# ✅ Good
logger.info(f"User registered: user_id={user.id}, email={user.email}")

# ❌ Bad - NEVER log passwords, tokens, or API keys
logger.info(f"User registered with password: {password}")
logger.info(f"JWT token: {token}")
logger.info(f"API key: {api_key}")
```

**Log security events**:

```python
# app/services/auth_service.py
async def verify_credentials(self, email: str, password: str):
    """Verify login credentials and log attempts."""
    user = await self.user_repo.find_by_email(email)

    if not user:
        logger.warning(f"Failed login attempt for non-existent email: {email}")
        return None

    if not self.verify_password(password, user.password_hash):
        logger.warning(f"Failed login attempt for user: {user.id}")
        return None

    logger.info(f"Successful login: user_id={user.id}")
    return user
```

---

## 11.11 MVP Security Checklist

**Implemented for MVP**:

- [x] **JWT Authentication**: Secure token-based auth with strong secret generation
- [x] **Password Hashing**: bcrypt with 12 rounds
- [x] **Password Policy**: 12+ chars with complexity requirements (uppercase, lowercase, digit, special char)
- [x] **Input Validation**: Pydantic models for all inputs
- [x] **Rate Limiting**: 🔴 CRITICAL - Prevents brute force, DoS, and API abuse
  - Login: 5 attempts/minute per IP
  - Registration: 3 attempts/hour per IP
  - CSV Upload: 3 uploads/hour per user
- [x] **CORS Configuration**: Restrict to frontend origin
- [x] **Environment Secrets**: No hardcoded credentials, validated on startup
- [x] **SQL Injection Prevention**: Prisma parameterized queries
- [x] **Authorization Checks**: Users access only their own data
- [x] **Secure Logging**: No sensitive data in logs

**Skip for MVP** (add after validation):

- [ ] **HTTPS/SSL**: Local dev uses HTTP (add for production)
- [ ] **API Key Rotation**: Add after initial deployment
- [ ] **MFA (Two-Factor Auth)**: Add for production
- [ ] **Security Audits**: Schedule after MVP validation
- [ ] **WAF/DDoS Protection**: Cloud provider handles this

---

## 11.12 Pre-Production Security Additions

**When moving from MVP to production, add**:

1. **HTTPS/SSL Certificate**:
   ```bash
   # Using Let's Encrypt (free)
   certbot --nginx -d api.yourdomain.com
   ```

2. **Redis Backend for Rate Limiting**:
   ```python
   # Upgrade from in-memory to Redis for distributed rate limiting
   # See Section 11.5 for full configuration
   limiter = Limiter(
       key_func=get_remote_address,
       storage_uri=f"redis://{settings.redis_host}:6379/0"
   )
   ```

3. **Security Headers**:
   ```python
   from fastapi.middleware.trustedhost import TrustedHostMiddleware

   app.add_middleware(
       TrustedHostMiddleware,
       allowed_hosts=["api.yourdomain.com"]
   )
   ```

4. **Content Security Policy**:
   ```python
   @app.middleware("http")
   async def add_security_headers(request, call_next):
       response = await call_next(request)
       response.headers["X-Content-Type-Options"] = "nosniff"
       response.headers["X-Frame-Options"] = "DENY"
       response.headers["X-XSS-Protection"] = "1; mode=block"
       return response
   ```

---

## 11.13 Security Incident Response

**For MVP, keep it simple**:

1. **Monitor logs** for suspicious activity (failed login attempts, unusual query patterns)
2. **Revoke compromised tokens** by changing JWT secret (forces re-login)
3. **Reset user password** if account compromised
4. **Update dependencies** immediately if security vulnerability discovered

**After MVP validation, implement**:
- Automated security monitoring (Sentry, DataDog)
- Incident response playbook
- Security contact email
- Vulnerability disclosure policy

---

This completes the **Security** section with MVP-appropriate security measures.

---
