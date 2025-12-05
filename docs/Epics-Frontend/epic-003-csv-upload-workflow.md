# Epic 3: CSV Upload Workflow - Brownfield Enhancement

**Epic ID**: EPIC-003  
**Created**: 2025-10-25  
**Status**: Ready for Development  
**Priority**: Medium (Data Management)  
**Dependencies**: EPIC-001 (Authentication & Core Layout)

---

## Epic Goal

Enable users to populate the knowledge graph with skills and jobs data through a streamlined CSV upload workflow, providing clear validation feedback, real-time progress tracking, and comprehensive error reporting.

---

## Project Analysis

### Existing Project Context

- **Project**: Graph RAG System for Skills & Jobs Knowledge Graph
- **Current functionality**: Backend CSV ingestion pipeline with POST `/upload/skills`, POST `/upload/jobs`, GET `/ingest/status/{job_id}` endpoints
- **Technology stack**: React frontend, FastAPI backend, Neo4j batch ingestion (1000 records/batch)
- **Integration points**:
  - POST `/upload/skills` - uploads skills CSV, returns `{job_id}`
  - POST `/upload/jobs` - uploads jobs CSV, returns `{job_id}`
  - GET `/ingest/status/{job_id}` - returns `{processed, total, status, errors[]}`

### Enhancement Scope

- Implement CSV upload interface with drag-and-drop
- Client-side validation and preview
- Real-time progress tracking with polling
- Error handling and reporting
- Success/failure state management

---

## Epic Description

### Existing System Context

- **Current relevant functionality**: Backend CSV ingestion pipeline with POST `/upload/skills`, POST `/upload/jobs`, GET `/ingest/status/{job_id}` endpoints
- **Technology stack**: React frontend, FastAPI backend, Neo4j batch ingestion (1000 records/batch)
- **Integration points**:
  - POST `/upload/skills` - uploads skills CSV, returns `{job_id}`
  - POST `/upload/jobs` - uploads jobs CSV, returns `{job_id}`
  - GET `/ingest/status/{job_id}` - returns `{processed, total, status, errors[]}`

### Enhancement Details

**What's being added:**

1. **Upload Type Selection** - Screen to choose between Skills CSV or Jobs CSV
2. **Drag-and-Drop Zone** - Visual file upload area (desktop) with file picker fallback (mobile)
3. **File Validation** - Client-side checks (file type, size <100MB, required columns)
4. **CSV Preview Modal** - Display first 5-10 rows with record count before upload
5. **Ingestion Progress Screen** - Real-time progress bar with batch tracking
6. **Progress Polling** - Poll `/ingest/status/{job_id}` every 2 seconds
7. **Completion Summary** - Success message with record counts or error log download
8. **Error Handling** - Validation errors, ingestion failures, partial success states

**How it integrates:**

- User selects upload type (Skills or Jobs)
- Drag-and-drop file or use file picker
- Client validates file (type, size, headers)
- Preview modal shows first 10 rows
- On confirm, POST to `/upload/skills` or `/upload/jobs`
- Backend returns `job_id`, frontend polls `/ingest/status/{job_id}` every 2s
- Progress updates: `{processed: 7892, total: 10523, batchNumber: 8, estimatedTime: 45s}`
- On completion: Show summary or error log download

**Success criteria:**

- Users can select Skills CSV or Jobs CSV upload type
- Drag-and-drop works on desktop, file picker works on mobile
- File validation catches invalid files before upload (wrong type, too large, missing columns)
- CSV preview shows first 10 rows with accurate record count
- Upload starts after user confirms preview
- Progress bar updates every 2 seconds with percentage and counts
- Estimated time remaining displayed during ingestion
- Completion shows success (all records) or partial success (X/Y records, download error log)
- Users can return to Home after completion
- Responsive design works on all devices

---

## Stories

### Story 1: Upload Type Selection & File Upload UI

**Description:**  
Create upload type selection screen and file upload interface with validation

**Scope:**
- Create upload type selection screen (Skills CSV vs Jobs CSV cards)
- Build drag-and-drop zone component with hover states
- Implement file picker fallback for mobile
- File validation: type check (.csv only), size check (<100MB)
- Column header validation (check required columns match expected schema)
- Error states: invalid file type, size exceeded, missing columns
- Responsive design (mobile: hide drag-drop, show button only)

**Estimated Effort**: 2-3 days

---

### Story 2: CSV Preview & Upload Initiation

**Description:**  
Implement CSV preview modal and upload initiation workflow

**Scope:**
- Implement CSV preview modal (overlay with backdrop)
- Parse first 10 rows client-side for preview
- Display record count summary
- Confirm/Cancel buttons
- POST to `/upload/skills` or `/upload/jobs` on confirm
- Handle upload errors (network failure, backend rejection)
- Close modal and navigate to progress screen on success
- Loading spinner during upload POST request

**Estimated Effort**: 2-3 days

---

### Story 3: Ingestion Progress Tracking & Completion

**Description:**  
Implement real-time progress tracking and completion states

**Scope:**
- Create progress screen with progress bar (0-100%)
- Implement polling: GET `/ingest/status/{job_id}` every 2 seconds
- Update progress bar and statistics (processed/total, batch number)
- Calculate and display estimated time remaining
- Handle completion: success (all records) or partial (X/Y records, errors)
- Show "Return to Home" button on completion
- Error log download button if errors occurred
- Cancel ingestion button (optional, stops polling)
- Handle edge cases: network interruption, backend crash, user navigates away

**Estimated Effort**: 2-3 days

---

## Compatibility Requirements

- [x] **Existing APIs remain unchanged** - Uses existing upload and status endpoints
- [x] **Database schema changes are backward compatible** - Backend handles Neo4j ingestion
- [x] **UI changes follow existing patterns** - Follows UI/UX spec design system
- [x] **Performance impact is minimal** - Client-side validation fast, polling lightweight (2s intervals)

---

## Risk Mitigation

### Primary Risk
Large CSV files (50K+ rows) cause browser memory issues or slow preview rendering

### Mitigation
- Only parse first 10 rows for preview (don't load entire file in memory)
- Use streaming CSV parser (e.g., PapaParse with streaming)
- Show record count without rendering all rows
- Backend handles actual ingestion (frontend just uploads file)

### Rollback Plan
- Disable upload navigation in frontend
- Users can still use chat functionality
- Backend ingestion pipeline unchanged (can run manually via API)

---

## Definition of Done

- [x] Users can select Skills CSV or Jobs CSV upload type
- [x] File upload works via drag-and-drop (desktop) and file picker (mobile)
- [x] File validation prevents invalid uploads (wrong type, too large, bad headers)
- [x] CSV preview displays first 10 rows accurately
- [x] Ingestion progress updates every 2 seconds
- [x] Progress bar, statistics, and time estimate display correctly
- [x] Completion summary shows success or partial success with error log
- [x] Error handling covers validation failures, network issues, backend errors
- [x] Responsive design tested on mobile, tablet, desktop
- [x] No regression in backend ingestion pipeline

---

## Validation Checklist

### Scope Validation
- [x] Epic can be completed in 3 stories maximum ✅
- [x] No architectural documentation is required ✅ (follows existing UI/UX spec)
- [x] Enhancement follows existing patterns ✅ (established by EPIC-001)
- [x] Integration complexity is manageable ✅ (file upload + polling)

### Risk Assessment
- [x] Risk to existing system is low ✅ (backend ingestion unchanged)
- [x] Rollback plan is feasible ✅ (disable frontend route)
- [x] Testing approach covers existing functionality ✅ (backend tested independently)
- [x] Team has sufficient knowledge of integration points ✅ (REST API, file upload, polling)

### Completeness Check
- [x] Epic goal is clear and achievable ✅
- [x] Stories are properly scoped ✅ (each story = 2-3 days work)
- [x] Success criteria are measurable ✅ (validation, progress, completion)
- [x] Dependencies are identified ✅ (backend upload/status endpoints, authentication)

---

## Story Manager Handoff

**Story Manager Instructions:**

Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a **frontend implementation** integrating with existing CSV ingestion pipeline
- **Technology stack**: React, TailwindCSS, Headless UI, React Router, PapaParse (CSV parsing)
- **Integration points**: 
  - POST `/upload/skills` (multipart/form-data, returns `{job_id}`)
  - POST `/upload/jobs` (multipart/form-data, returns `{job_id}`)
  - GET `/ingest/status/{job_id}` (returns `{processed, total, status, errors[]}`)
  - JWT token in `Authorization: Bearer <token>` header required
- **Existing patterns to follow**: UI/UX specification at `docs/front-end-spec.md`
- **Critical compatibility requirements**: 
  - File size limit: 100MB max
  - Polling interval: 2 seconds
  - CSV format validation (required columns)
  - Responsive design at breakpoints: 640px, 768px, 1024px, 1280px
- Each story must include:
  - Upload UI components (drag-drop zone, file picker, modals)
  - File validation logic (client-side)
  - Progress tracking with polling
  - Error handling (validation, network, backend failures)
  - Accessibility: keyboard nav, screen reader support

The epic should deliver a robust CSV upload workflow with excellent user feedback and error recovery.

---

## Dependencies

- EPIC-001 (Authentication & Core Layout) must be completed
- Backend POST `/upload/skills` and POST `/upload/jobs` endpoints deployed
- Backend GET `/ingest/status/{job_id}` endpoint deployed
- Sample CSV formats and schemas confirmed with backend team
- UI/UX specification finalized at `docs/front-end-spec.md`

---

## Success Metrics

- **Upload Success Rate**: >95% of valid CSV files upload successfully
- **Validation Accuracy**: 100% of invalid files caught before upload
- **Progress Accuracy**: Progress bar reflects actual ingestion status within ±5%
- **Error Recovery**: Users successfully retry after errors >80% of time
- **Completion Time**: Typical 10K row CSV completes within 30-60 seconds

---

## Technical Notes

### CSV Validation Rules

**Skills CSV Expected Columns:**
- `skill_id`, `skill_name`, `category`, `subcategory`, etc.
- (Confirm exact schema with backend team)

**Jobs CSV Expected Columns:**
- `job_id`, `job_title`, `company`, `skills_required`, etc.
- (Confirm exact schema with backend team)

### Polling Strategy
- Poll every 2 seconds while status is "processing"
- Stop polling when status is "completed" or "failed"
- Handle backend unavailability (retry 3 times, then show error)
- Continue polling even if user navigates away (background job)

---

**Epic Status**: ✅ Ready for Story Breakdown and Development
