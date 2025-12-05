# Epic 2: CSV Ingestion Pipeline

**Epic Goal**: Build a robust CSV ingestion system that accepts skills and jobs taxonomy files, validates their format and content, processes them in batches with real-time progress tracking, and stores the raw data ready for graph construction. By the end of this epic, users can upload CSV files through the UI and see them successfully validated and stored.

## Story 2.1: CSV Upload API Endpoints

**As a** developer
**I want** FastAPI endpoints for CSV file uploads
**so that** frontend can send CSV files to the backend

### Acceptance Criteria

1. `POST /ingest/skills` endpoint created (protected by JWT middleware)
2. `POST /ingest/jobs` endpoint created (protected by JWT middleware)
3. Endpoints accept `multipart/form-data` with file field named `file`
4. File size limit enforced (e.g., 100MB max)
5. File type validation: only `.csv` files accepted
6. Invalid file type returns 400 with message "Only CSV files are allowed"
7. File too large returns 413 with message "File size exceeds 100MB limit"
8. Successful upload returns 202 (Accepted) with `{ingestion_job_id, status: "pending"}`
9. Ingestion job ID stored in PostgreSQL with user_id, filename, status, created_at

## Story 2.2: CSV Validation Logic

**As a** user
**I want** my CSV files validated before ingestion starts
**so that** I get immediate feedback on formatting issues

### Acceptance Criteria

1. CSV parser validates file can be read (not corrupted)
2. Skills CSV validation: Check for required columns (ID, NAME, DESCRIPTION, CATEGORY, SUBCATEGORY)
3. Jobs CSV validation: Check for required columns (Job ID, Job Title, Company Name, Location, standardized_skills)
4. Column name matching is case-insensitive
5. Validation checks for minimum 1 data row (not just headers)
6. Missing required columns returns 400 with list of missing column names
7. Empty CSV (header only) returns 400 with message "CSV file contains no data rows"
8. Validation successful: proceed to row preview
9. Unit tests written for validation logic (valid CSV, missing columns, empty CSV, corrupted file)

## Story 2.3: CSV Preview & Confirmation

**As a** user
**I want** to preview the first few rows of my CSV before confirming ingestion
**so that** I can verify the data looks correct

### Acceptance Criteria

1. After validation passes, extract first 5-10 rows from CSV
2. Return preview data to frontend: `{columns: [...], preview_rows: [...], total_rows: N}`
3. Preview includes column names and sample values
4. Row count calculated and returned (e.g., "40,523 jobs found")
5. Frontend displays preview in table format
6. Frontend provides "Confirm Upload" and "Cancel" buttons
7. Cancel button discards uploaded file, no data stored
8. Confirm button triggers actual ingestion process

## Story 2.4: Batch Processing Engine

**As a** system
**I want** to process large CSV files in batches
**so that** memory usage stays within bounds and progress can be tracked

### Acceptance Criteria

1. CSV processing split into batches of 500-1000 records
2. Batch size configurable via `.env` variable `BATCH_SIZE` (default: 1000)
3. Each batch processed sequentially (not parallel to avoid DB contention)
4. Batch processing tracks: records_processed, records_failed, current_batch, total_batches
5. Failed records logged with row number and error message
6. Processing continues after batch failures (does not halt entire ingestion)
7. Ingestion status updated in PostgreSQL after each batch: `{records_processed, records_failed, status: "processing"}`
8. Final status set to "completed" or "completed_with_errors" based on failure count

## Story 2.5: Real-Time Progress Tracking

**As a** user
**I want** to see real-time progress while my CSV is being ingested
**so that** I know the system is working and how long it will take

### Acceptance Criteria

1. `/ingest/status/{job_id}` endpoint created (protected)
2. Endpoint returns JSON: `{status, records_processed, records_failed, total_records, estimated_time_remaining}`
3. Frontend polls `/ingest/status/{job_id}` every 2 seconds during ingestion
4. Progress bar displays percentage: `(records_processed / total_records) * 100`
5. Display stats: "Processing 15,234 / 40,523 records (5 failed)"
6. Estimated time remaining calculated based on average processing speed
7. Status values: "pending", "processing", "completed", "completed_with_errors", "failed"
8. When status = "completed", polling stops and success message shown

## Story 2.6: Error Handling & Logging

**As a** user
**I want** detailed error logs when ingestion fails
**so that** I can fix data issues and retry

### Acceptance Criteria

1. Failed records logged to PostgreSQL table: `ingestion_errors` (job_id, row_number, error_message, raw_data)
2. Common errors logged: missing required field, invalid data type, parsing error
3. Error log downloadable via `/ingest/errors/{job_id}` endpoint (returns CSV)
4. Error CSV format: `row_number,error_message,raw_data`
5. Frontend provides "Download Error Log" button when `records_failed > 0`
6. System-level errors (DB connection failures, API failures) return 500 with clear message
7. Partial ingestion success: Display "40,518 / 40,523 records ingested successfully (5 failed). Download error log to review failures."

## Story 2.7: Frontend CSV Upload UI

**As a** user
**I want** a simple drag-and-drop interface to upload CSV files
**so that** I can easily ingest data into the system

### Acceptance Criteria

1. CSV upload page created at `/upload` route (protected)
2. Two upload zones: "Upload Skills CSV" and "Upload Jobs CSV"
3. Drag-and-drop functionality for both zones
4. File picker fallback (click to select file)
5. Upload triggers validation → preview → user confirms → ingestion starts
6. During ingestion: Display progress bar, stats, estimated time
7. After completion: Show success message with summary stats
8. Failed ingestion: Show error count and "Download Error Log" button
9. Option to "Upload Another File" after completion
10. Clean, intuitive UI with clear labeling and status indicators

---
