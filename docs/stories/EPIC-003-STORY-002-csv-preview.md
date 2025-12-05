# Story: CSV Preview & Upload Initiation

**Story ID**: EPIC-003-STORY-002  
**Epic**: Epic 3 - CSV Upload Workflow  
**Priority**: Medium  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-003-STORY-001 (Upload UI & Validation)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** to preview my CSV data before uploading,  
**So that** I can verify the file contents are correct before starting ingestion.

---

## Acceptance Criteria

### Functional Requirements

1. **CSV Preview Modal**
   - After file validation passes → show modal overlay
   - Modal title: "CSV Preview - {filename}"
   - Display first 10 rows of CSV in table format
   - Table headers: Column names from CSV
   - Table rows: First 10 data rows
   - Show record count: "Total records: 10,523"

2. **Modal Actions**
   - "Confirm Upload" primary button → start upload
   - "Cancel" secondary button → close modal, return to upload screen
   - X icon (top-right) → close modal (same as Cancel)
   - ESC key → close modal

3. **CSV Parsing for Preview**
   - Parse first 10 rows using PapaParse
   - Don't load entire file into memory (streaming)
   - Count total rows (without loading all into memory)
   - Handle large CSVs efficiently (100 MB files)

4. **Upload Initiation**
   - On "Confirm Upload" → POST to `/upload/skills` or `/upload/jobs`
   - Request type: multipart/form-data
   - Include JWT token in Authorization header
   - File sent as form data: `{ file: File }`

5. **Upload Response Handling**
   - Response: `{ job_id: string }`
   - Store `job_id` for progress polling (next story)
   - Navigate to progress screen: `/upload/progress/{job_id}`
   - Show loading spinner during upload POST

6. **Error Handling**
   - Handle 400 response: "Invalid file format"
   - Handle 401 response: Logout (handled by global interceptor)
   - Handle 500 response: "Upload failed. Please try again."
   - Handle network error: "Unable to connect. Please check your connection."
   - Show error in modal, allow user to retry or cancel

### Integration Requirements

7. **API Integration**
   - Endpoint: POST `/upload/skills` or POST `/upload/jobs`
   - Headers: `{ 'Authorization': 'Bearer {token}' }`
   - Body: FormData with file: `formData.append('file', file)`
   - Response: `{ job_id: '550e8400-e29b-41d4-a716-446655440000' }`

8. **Navigation**
   - After successful upload → navigate to `/upload/progress/{job_id}`
   - Pass job_id and upload type (skills/jobs) to progress screen
   - Progress screen can poll status using job_id

### Quality Requirements

9. **User Experience**
   - Preview loads quickly (<2 seconds for large files)
   - Table scrollable if >10 columns
   - Modal responsive (works on mobile, tablet, desktop)
   - Upload progress feedback (spinner in button during POST)

10. **Performance**
    - Streaming CSV parsing (memory efficient)
    - Row count calculated without loading full file
    - Modal renders smoothly (no lag)

11. **Accessibility**
    - Modal traps focus (Tab cycles within modal)
    - ESC key closes modal
    - Focus returns to upload zone when modal closes
    - Table has proper semantic HTML (<table>, <thead>, <tbody>)

---

## Technical Notes

### CSV Parsing for Preview

```javascript
import Papa from 'papaparse';

const parseCSVPreview = (file) => {
  return new Promise((resolve, reject) => {
    let rowCount = 0;
    let previewRows = [];
    
    Papa.parse(file, {
      header: true,
      step: (row) => {
        rowCount++;
        if (rowCount <= 11) { // Headers + 10 rows
          previewRows.push(row.data);
        }
      },
      complete: () => {
        resolve({
          headers: Object.keys(previewRows[0]),
          rows: previewRows.slice(0, 10),
          totalRows: rowCount - 1 // Exclude header row
        });
      },
      error: (err) => reject(err)
    });
  });
};
```

### Upload Service

```javascript
const uploadCSV = async (file, type, token) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const endpoint = type === 'skills' ? '/upload/skills' : '/upload/jobs';
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Upload failed');
  }
  
  return await response.json(); // { job_id }
};
```

---

## Definition of Done

- [x] CSV preview modal displays after validation
- [x] Modal shows first 10 rows in table format
- [x] Total record count displayed accurately
- [x] Confirm button uploads file to backend
- [x] Cancel/X/ESC closes modal without upload
- [x] Upload POST request uses multipart/form-data with JWT token
- [x] job_id received from backend after upload
- [x] Navigate to progress screen with job_id
- [x] Error handling for upload failures
- [x] Loading spinner during upload POST
- [x] Responsive modal (mobile, tablet, desktop)
- [x] Keyboard navigation and focus management work

---

## Dependencies

- EPIC-003-STORY-001 (Upload UI & Validation)
- Backend POST `/upload/skills` and POST `/upload/jobs` endpoints deployed
- PapaParse library installed

---

**Story Status**: ✅ Ready for Development
