# Story 2.3: CSV Preview & Confirmation Flow

**Status**: ✅ Implemented and Tested (101/101 tests passing)
**Implementation Date**: October 2025
**Related Stories**: Story 2.2 (CSV Upload & Validation)

---

## Overview

Story 2.3 introduces a two-step CSV upload workflow that allows users to preview their data before confirming ingestion. This replaces the previous direct ingestion model with a preview-then-confirm pattern, improving user confidence and reducing accidental uploads.

### Key Changes

- **Before (Story 2.2)**: Upload CSV → Immediate ingestion job creation (202 Accepted)
- **After (Story 2.3)**: Upload CSV → Preview with first 10 rows (200 OK) → User confirms → Ingestion job creation (202 Accepted)

---

## Architecture Changes

### 1. Two-Step Upload Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Story 2.3 Workflow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Upload & Preview                                      │
│  ┌──────────┐                    ┌──────────────────┐         │
│  │  Client  │ ─── POST CSV ────> │  POST /ingest/   │         │
│  │          │                     │  skills or jobs  │         │
│  └──────────┘                     └──────────────────┘         │
│                                            │                    │
│                                            ▼                    │
│                                   ┌─────────────────┐          │
│                                   │ Validate CSV    │          │
│                                   │ Structure       │          │
│                                   └─────────────────┘          │
│                                            │                    │
│                                            ▼                    │
│                                   ┌─────────────────┐          │
│                                   │ Generate        │          │
│                                   │ Preview (10     │          │
│                                   │ rows)           │          │
│                                   └─────────────────┘          │
│                                            │                    │
│                                            ▼                    │
│                                   ┌─────────────────┐          │
│                                   │ Cache file      │          │
│                                   │ (SHA-256 hash)  │          │
│                                   │ TTL: 1 hour     │          │
│                                   └─────────────────┘          │
│                                            │                   │
│                                            ▼                   │
│  ┌──────────┐                    ┌──────────────────┐          │
│  │  Client  │ <─── 200 OK ────── │  Return preview  │          │
│  │          │      + file_hash   │  + file_hash     │          │
│  └──────────┘                    └──────────────────┘          │
│                                                                │
│  Step 2: Confirm & Ingest                                      │
│  ┌──────────┐                    ┌──────────────────┐          │
│  │  Client  │ ─── POST ────────> │  POST /ingest/   │          │
│  │          │     file_hash       │  confirm         │         │
│  └──────────┘                     └──────────────────┘         │
│                                            │                   │
│                                            ▼                   │
│                                   ┌─────────────────┐          │
│                                   │ Retrieve file   │          │
│                                   │ from cache      │          │
│                                   └─────────────────┘          │
│                                            │                   │
│                                            ▼                    │
│                                   ┌─────────────────┐           │
│                                   │ Create          │           │
│                                   │ IngestionJob    │           │
│                                   └─────────────────┘           │
│                                            │                    │
│                                            ▼                    │
│                                   ┌─────────────────┐           │
│                                   │ Delete cached   │           │
│                                   │ file            │           │
│                                   └─────────────────┘           │
│                                            │                    │
│                                            ▼                    │
│  ┌──────────┐                    ┌──────────────────┐           │
│  │  Client  │ <─── 202 ────────  │  Return job_id   │           │
│  │          │     Accepted       │                  │           │
│  └──────────┘                    └──────────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. File Caching System

**Implementation**: In-memory dictionary cache (MVP)
**Location**: `app/utils/file_cache.py`

```python
_file_cache: Dict[str, Dict[str, Any]] = {
    "file_hash_sha256": {
        "content": bytes,
        "file_type": str,
        "filename": str,
        "file_size_mb": float,
        "expires_at": datetime
    }
}
```

**Key Features**:
- SHA-256 content-based hashing for deduplication
- 1-hour TTL (configurable)
- Automatic expiry checking on retrieval
- Background cleanup via APScheduler (every 15 minutes)

**Production Recommendation**: Replace with Redis for distributed systems

### 3. Background Cleanup Scheduler

**Implementation**: APScheduler AsyncIOScheduler
**Location**: `app/main.py` (lifespan management)

```python
file_cleanup_scheduler = AsyncIOScheduler()

file_cleanup_scheduler.add_job(
    cleanup_task,
    'interval',
    minutes=15,
    id='file_cleanup',
    replace_existing=True
)
```

**Cleanup Logic**:
- Runs every 15 minutes
- Removes expired files from cache
- Logs cleanup statistics
- Prevents memory leaks from unconfirmed uploads

---

## API Changes

### 1. POST /ingest/skills

**Before (Story 2.2)**:
```http
POST /ingest/skills
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<skills.csv>

Response: 202 Accepted
{
    "ingestion_job_id": "job_123",
    "status": "pending",
    "file_name": "skills.csv"
}
```

**After (Story 2.3)**:
```http
POST /ingest/skills
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<skills.csv>

Response: 200 OK
{
    "file_hash": "a3f5b8c9d2e1...",  // SHA-256 hash (64 chars)
    "file_type": "skills",
    "columns": ["ID", "NAME", "DESCRIPTION", "CATEGORY", "SUBCATEGORY"],
    "preview_rows": [
        {"ID": 1, "NAME": "Python", "DESCRIPTION": "Programming language", ...},
        {"ID": 2, "NAME": "JavaScript", "DESCRIPTION": "Web language", ...},
        // ... up to 10 rows
    ],
    "total_rows": 150,
    "has_more": true
}
```

### 2. POST /ingest/jobs

**Before (Story 2.2)**:
```http
POST /ingest/jobs
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<jobs.csv>

Response: 202 Accepted
{
    "ingestion_job_id": "job_456",
    "status": "pending",
    "file_name": "jobs.csv"
}
```

**After (Story 2.3)**:
```http
POST /ingest/jobs
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<jobs.csv>

Response: 200 OK
{
    "file_hash": "b4e6c7d3a2f1...",  // SHA-256 hash (64 chars)
    "file_type": "jobs",
    "columns": ["Job ID", "Job Title", "Company Name", "Location", "standardized_skills"],
    "preview_rows": [
        {"Job ID": 1, "Job Title": "Software Engineer", ...},
        {"Job ID": 2, "Job Title": "Data Scientist", ...},
        // ... up to 10 rows
    ],
    "total_rows": 75,
    "has_more": true
}
```

### 3. POST /ingest/confirm (NEW)

```http
POST /ingest/confirm
Authorization: Bearer <token>
Content-Type: application/json

{
    "file_hash": "a3f5b8c9d2e1...",
    "file_type": "skills"
}

Response: 202 Accepted
{
    "ingestion_job_id": "job_123",
    "status": "pending",
    "message": "CSV ingestion job created successfully"
}
```

**Error Cases**:
```http
# File not found or expired (1 hour TTL)
Response: 404 Not Found
{
    "detail": "File not found or expired. Please upload the file again."
}

# File type mismatch (security check)
Response: 400 Bad Request
{
    "detail": "File type mismatch. Expected skills, got jobs."
}
```

---

## New Components

### 1. `app/utils/file_cache.py`

**Purpose**: Temporary file storage with TTL and metadata

**Functions**:

```python
def store_temp_file(
    content: bytes,
    file_type: str,
    filename: str,
    ttl_hours: int = 1
) -> str:
    """
    Store file temporarily and return SHA-256 hash.

    Args:
        content: Raw file bytes
        file_type: "skills" or "jobs"
        filename: Original filename
        ttl_hours: Time to live (default 1 hour)

    Returns:
        SHA-256 hash (64 character hex string)
    """
```

```python
def retrieve_temp_file(file_hash: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve file from cache.

    Args:
        file_hash: SHA-256 hash

    Returns:
        {
            "content": bytes,
            "file_type": str,
            "filename": str,
            "file_size_mb": float
        }
        or None if not found/expired
    """
```

```python
def delete_temp_file(file_hash: str) -> bool:
    """
    Delete file from cache.

    Args:
        file_hash: SHA-256 hash

    Returns:
        True if deleted, False if not found
    """
```

```python
def cleanup_expired_files() -> int:
    """
    Remove all expired files from cache.

    Returns:
        Number of files cleaned up
    """
```

```python
def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        {
            "total_files": int,
            "total_size_mb": float,
            "oldest_expires_at": datetime,
            "newest_expires_at": datetime
        }
    """
```

### 2. `app/utils/csv_parser.py` (Enhanced)

**New Function**:

```python
def parse_csv_preview(
    content: bytes,
    preview_rows: int = 10
) -> Dict[str, Any]:
    """
    Parse CSV and return preview data.

    Args:
        content: CSV file bytes
        preview_rows: Number of preview rows (default 10)

    Returns:
        {
            "columns": List[str],
            "preview_rows": List[Dict],  # First N rows
            "total_rows": int,           # Total row count
            "has_more": bool             # True if total > preview
        }

    Features:
        - UTF-8 encoding with latin-1 fallback
        - CSV injection sanitization (=, +, -, @, |, %)
        - Pandas DataFrame operations for preview
    """
```

### 3. `app/services/csv_validation_service.py` (Enhanced)

**New Methods**:

```python
def validate_and_preview_skills(
    self,
    content: bytes,
    preview_rows: int = 10
) -> Dict[str, Any]:
    """
    Validate skills CSV and return preview.

    Validates:
        - Required columns (case-insensitive)
        - Non-empty data
        - CSV structure

    Returns preview data if valid.
    Raises CSVValidationError if invalid.
    """
```

```python
def validate_and_preview_jobs(
    self,
    content: bytes,
    preview_rows: int = 10
) -> Dict[str, Any]:
    """
    Validate jobs CSV and return preview.

    Validates:
        - Required columns (case-insensitive)
        - Non-empty data
        - CSV structure

    Returns preview data if valid.
    Raises CSVValidationError if invalid.
    """
```

### 4. `app/services/ingestion_service.py` (Enhanced)

**New Method**:

```python
async def start_ingestion_from_cache(
    self,
    content: bytes,
    file_type: str,
    filename: str,
    file_size_mb: float,
    user_id: str
) -> IngestionJobResponse:
    """
    Create ingestion job from cached file data.

    Args:
        content: File bytes from cache
        file_type: "skills" or "jobs"
        filename: Original filename
        file_size_mb: File size
        user_id: User ID from JWT

    Returns:
        IngestionJobResponse with job_id
    """
```

### 5. Pydantic Models (New)

**Location**: `app/models/ingestion.py`

```python
class CSVPreviewResponse(BaseModel):
    """Response for CSV preview (Story 2.3)."""
    file_hash: str  # SHA-256 hash
    file_type: str  # "skills" or "jobs"
    columns: List[str]
    preview_rows: List[Dict[str, Any]]
    total_rows: int
    has_more: bool

class ConfirmUploadRequest(BaseModel):
    """Request to confirm CSV upload (Story 2.3)."""
    file_hash: str  # SHA-256 hash
    file_type: str  # "skills" or "jobs"
```

---

## Security Enhancements

### 1. CSV Injection Sanitization

**Threat**: Malicious CSV formulas (e.g., `=cmd|'/c calc'`)

**Protection**: Automatic sanitization in `parse_csv()` and `parse_csv_preview()`

```python
# Dangerous characters: = + - @ | %
if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '|', '%')):
    row[col] = f"'{value}"  # Prefix with single quote
```

**Example**:
```csv
ID,NAME,DESCRIPTION
1,Python,=1+1
2,Java,+cmd|calc
```

**Sanitized Output**:
```python
[
    {"ID": 1, "NAME": "Python", "DESCRIPTION": "'=1+1"},
    {"ID": 2, "NAME": "Java", "DESCRIPTION": "'+cmd|calc"}
]
```

### 2. File Type Verification

The `/ingest/confirm` endpoint verifies that the requested `file_type` matches the cached file's `file_type` to prevent type confusion attacks:

```python
if file_data["file_type"] != confirmation.file_type:
    raise HTTPException(
        status_code=400,
        detail=f"File type mismatch. Expected {file_data['file_type']}, got {confirmation.file_type}."
    )
```

### 3. TTL-Based Expiry

Files expire after 1 hour, limiting exposure window for cached data:
- Automatic expiry checking on retrieval
- Background cleanup every 15 minutes
- Users must re-upload if they wait too long

---

## Testing Coverage

### Test Summary: 101/101 Passing ✅

#### Unit Tests

**`tests/unit/test_csv_parser.py`**: 16 tests
- `test_parse_csv_preview_basic` - Basic preview generation
- `test_parse_csv_preview_exact_count` - Preview equals total rows
- `test_parse_csv_preview_less_than_requested` - Fewer rows than requested
- `test_parse_csv_preview_has_more_flag` - has_more accuracy
- `test_parse_csv_preview_default_rows` - Default 10 rows
- `test_parse_csv_preview_sanitizes_formulas` - CSV injection protection
- `test_parse_csv_preview_safe_content_unchanged` - Normal content unmodified
- `test_parse_csv_preview_utf8_encoding` - UTF-8 support
- `test_parse_csv_preview_latin1_fallback` - Latin-1 fallback
- `test_parse_csv_preview_empty_raises_error` - Empty CSV error
- `test_parse_csv_preview_corrupted_raises_error` - Corrupted CSV error
- `test_parse_csv_preview_header_only` - Header-only CSV
- `test_parse_csv_preview_preserves_column_names` - Column name preservation
- `test_parse_csv_preview_special_characters` - Special character handling
- `test_parse_csv_preview_large_file` - Large file efficiency
- `test_parse_csv_preview_numeric_values` - Numeric value preservation

**`tests/unit/test_csv_validation.py`**: 15 tests
- `test_validate_and_preview_skills_success` - Skills validation success
- `test_validate_and_preview_skills_default_preview_rows` - Default preview
- `test_validate_and_preview_skills_custom_preview_rows` - Custom preview
- `test_validate_and_preview_skills_missing_columns` - Missing column error
- `test_validate_and_preview_skills_empty_data` - Empty data error
- `test_validate_and_preview_skills_case_insensitive` - Case-insensitive columns
- `test_validate_and_preview_skills_sanitizes_formulas` - Formula sanitization
- `test_validate_and_preview_skills_preview_structure` - Preview structure
- `test_validate_and_preview_jobs_success` - Jobs validation success
- `test_validate_and_preview_jobs_default_preview_rows` - Default preview
- `test_validate_and_preview_jobs_custom_preview_rows` - Custom preview
- `test_validate_and_preview_jobs_missing_columns` - Missing column error
- `test_validate_and_preview_jobs_empty_data` - Empty data error
- `test_validate_and_preview_jobs_case_insensitive` - Case-insensitive columns
- `test_validate_and_preview_jobs_sanitizes_formulas` - Formula sanitization

**`tests/unit/test_file_cache.py`**: 18 tests
- `test_store_temp_file_basic` - Basic file storage
- `test_store_temp_file_metadata` - Metadata storage
- `test_store_temp_file_ttl` - TTL configuration
- `test_store_temp_file_default_ttl` - Default 1-hour TTL
- `test_retrieve_temp_file_success` - Successful retrieval
- `test_retrieve_temp_file_not_found` - Non-existent file
- `test_retrieve_temp_file_expired` - Expired file removal
- `test_retrieve_temp_file_not_expired` - Non-expired retrieval
- `test_delete_temp_file_success` - Successful deletion
- `test_delete_temp_file_not_found` - Delete non-existent file
- `test_cleanup_expired_files_none_expired` - No files expired
- `test_cleanup_expired_files_some_expired` - Partial cleanup
- `test_cleanup_expired_files_all_expired` - Full cleanup
- `test_get_cache_stats_empty` - Empty cache stats
- `test_get_cache_stats_with_files` - Cache stats with files
- `test_store_temp_file_sha256_deterministic` - SHA-256 determinism
- `test_store_temp_file_different_content` - Different content hashing
- `test_file_size_calculation` - File size calculation

#### Integration Tests

**`tests/integration/test_ingest_api.py`**: 22 tests (updated for Story 2.3)
- `test_upload_skills_csv_success` - Skills upload returns preview
- `test_upload_skills_csv_creates_db_record` - Two-step job creation
- `test_upload_jobs_csv_success` - Jobs upload returns preview
- `test_upload_jobs_csv_creates_db_record` - Two-step job creation
- `test_upload_csv_with_unsafe_filename` - Filename sanitization
- `test_get_job_status_success` - Job status retrieval
- `test_get_user_jobs_success` - User jobs listing
- `test_upload_csv_case_insensitive_columns` - Case-insensitive columns
- `test_upload_csv_stores_total_records` - Total records storage
- And 13 other existing integration tests...

#### Other Tests

**Existing Tests**: ~30 tests
- CSV validation tests
- CSV parsing tests
- Authentication tests
- Database tests
- File validation tests

---

## Database Changes

**No schema changes required for Story 2.3**

The existing `IngestionJob` model already has `file_name` and `file_size_mb` fields (added in Story 2.2), which are now populated from cached file metadata during confirmation.

---

## Dependencies Added

```txt
apscheduler==3.10.4  # Background task scheduling
```

**Installation**:
```bash
pip install apscheduler
```

---

## Usage Examples

### Frontend Integration Example

```javascript
// Step 1: Upload CSV and get preview
const uploadSkillsCSV = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/ingest/skills', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    });

    if (response.ok) {
        const preview = await response.json();
        /*
        {
            "file_hash": "a3f5b8c9...",
            "file_type": "skills",
            "columns": ["ID", "NAME", ...],
            "preview_rows": [{...}, {...}],
            "total_rows": 150,
            "has_more": true
        }
        */
        return preview;
    }
};

// Step 2: Show preview to user
const showPreview = (preview) => {
    // Display columns
    console.log("Columns:", preview.columns);

    // Display first 10 rows
    preview.preview_rows.forEach(row => {
        console.log(row);
    });

    // Show total count
    console.log(`Total rows: ${preview.total_rows}`);
    if (preview.has_more) {
        console.log(`Showing first 10 of ${preview.total_rows} rows`);
    }
};

// Step 3: User confirms, start ingestion
const confirmIngestion = async (fileHash, fileType) => {
    const response = await fetch('/ingest/confirm', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            file_hash: fileHash,
            file_type: fileType
        })
    });

    if (response.ok) {
        const result = await response.json();
        /*
        {
            "ingestion_job_id": "job_123",
            "status": "pending",
            "message": "CSV ingestion job created successfully"
        }
        */
        return result.ingestion_job_id;
    } else if (response.status === 404) {
        alert("File expired. Please upload again.");
    }
};

// Complete workflow
const handleCSVUpload = async (file) => {
    // Step 1: Upload and preview
    const preview = await uploadSkillsCSV(file);

    // Step 2: Show preview to user
    showPreview(preview);

    // Step 3: User confirms (after reviewing preview)
    const userConfirmed = await showConfirmDialog(preview);
    if (userConfirmed) {
        const jobId = await confirmIngestion(preview.file_hash, preview.file_type);
        console.log(`Ingestion started: ${jobId}`);
    }
};
```

---

## Migration Guide (Story 2.2 → Story 2.3)

### For API Clients

**Before (Story 2.2)**:
```javascript
// Single-step upload
const response = await fetch('/ingest/skills', {
    method: 'POST',
    body: formData
});
const { ingestion_job_id } = await response.json();  // 202 Accepted
```

**After (Story 2.3)**:
```javascript
// Two-step upload
// Step 1: Preview
const uploadResponse = await fetch('/ingest/skills', {
    method: 'POST',
    body: formData
});
const preview = await uploadResponse.json();  // 200 OK

// Step 2: Confirm (after user reviews)
const confirmResponse = await fetch('/ingest/confirm', {
    method: 'POST',
    body: JSON.stringify({
        file_hash: preview.file_hash,
        file_type: preview.file_type
    })
});
const { ingestion_job_id } = await confirmResponse.json();  // 202 Accepted
```

### Backward Compatibility

**Breaking Change**: Yes - API behavior changed

Clients expecting 202 status from `/ingest/skills` or `/ingest/jobs` will now receive 200 status with preview data. They must be updated to use the two-step flow.

---

## Performance Considerations

### Memory Usage

**In-Memory Cache**: Current MVP implementation stores files in Python dictionary
- Typical CSV: 1-10 MB per file
- 1-hour TTL + 15-minute cleanup cycle
- Estimate: ~50-100 concurrent files = 50-1000 MB memory

**Scaling Recommendation**:
- For >100 concurrent users, migrate to Redis
- Redis provides distributed caching for horizontal scaling
- Implement Redis with same interface for drop-in replacement

### Preview Generation

**Pandas `.head(n)` Operation**: O(n) where n = preview_rows (default 10)
- Very fast for preview-only operations
- No need to load entire CSV into memory
- Efficient for large files (1000+ rows)

### Background Cleanup

**APScheduler Overhead**: Minimal
- Runs every 15 minutes
- O(n) iteration over cached files
- Typical cleanup: <100ms for 50 files

---

## Troubleshooting

### Issue: Files expire before user confirms

**Symptom**: User gets 404 error when confirming upload

**Cause**: 1-hour TTL expired

**Solutions**:
1. Increase TTL: Change `ttl_hours` parameter in `store_temp_file()` calls
2. Frontend warning: Show countdown timer to user
3. Auto-retry: Frontend automatically re-uploads if confirmation fails with 404

### Issue: Memory usage growing over time

**Symptom**: Application memory increases steadily

**Cause**: Cleanup task not running or failing

**Solutions**:
1. Check APScheduler logs: `logger.info()` in `cleanup_task()`
2. Verify scheduler started: Look for "File cleanup scheduler started" in startup logs
3. Manual cleanup: Call `cleanup_expired_files()` manually
4. Check for exceptions: Review `logger.error()` messages

### Issue: Preview shows incorrect data

**Symptom**: Preview rows don't match CSV content

**Cause**: Encoding issues (UTF-8 vs latin-1)

**Solutions**:
1. Check CSV encoding: Verify file is UTF-8 or latin-1
2. Review parser logs: Check for encoding fallback messages
3. Test with different encodings: Try re-saving CSV as UTF-8

---

## Future Enhancements

### Short-Term (Next Sprint)

1. **Redis Migration**: Replace in-memory cache with Redis
   - Distributed caching for horizontal scaling
   - Persistence across application restarts
   - Better performance for high-concurrency scenarios

2. **Preview Customization**: Allow clients to specify preview_rows count
   - Query parameter: `/ingest/skills?preview_rows=20`
   - Validate reasonable limits (e.g., 1-50 rows)

3. **File Hash Validation**: Add checksum validation on frontend
   - Client calculates SHA-256 before upload
   - Compare with server hash for integrity verification

### Medium-Term (Future Stories)

1. **Progressive Upload**: Stream large files during upload
   - Chunked upload for files >50 MB
   - Progress indicators for user

2. **Preview Pagination**: Allow users to view more rows beyond initial 10
   - Endpoint: `GET /ingest/preview/{file_hash}?page=2`
   - Cache full CSV data for pagination

3. **Advanced Preview**: Show data quality metrics
   - Duplicate detection
   - Missing value analysis
   - Data type inference
   - Column statistics (min, max, avg)

---

## Related Documentation

- **Story 2.2**: CSV Upload & Validation (prerequisite)
- **API Reference**: `/docs` (FastAPI Swagger UI)
- **Database Schema**: `prisma/schema.prisma`
- **Testing Guide**: `tests/README.md`

---

## Changelog

### Version 1.0 (October 2025)
- ✅ Two-step upload workflow implemented
- ✅ In-memory file cache with SHA-256 hashing
- ✅ APScheduler background cleanup
- ✅ CSV injection sanitization in preview
- ✅ 101/101 tests passing
- ✅ POST /ingest/confirm endpoint added
- ✅ CSVPreviewResponse and ConfirmUploadRequest models added

---

*Document Version: 1.0*
*Last Updated: October 23, 2025*
*Author: Development Team*
