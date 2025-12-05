# Story: Upload Type Selection & File Upload UI

**Story ID**: EPIC-003-STORY-001  
**Epic**: Epic 3 - CSV Upload Workflow  
**Priority**: Medium  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-001 (Authentication & Core Layout)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** to select whether I'm uploading Skills or Jobs data and validate my CSV file,  
**So that** I can ensure my file is correct before starting the ingestion process.

---

## Acceptance Criteria

### Functional Requirements

1. **Upload Type Selection Screen**
   - Two large cards: "Upload Skills CSV" and "Upload Jobs CSV"
   - Each card: Icon (document/table), Title, Description
   - Click card → navigate to respective upload screen (`/upload/skills` or `/upload/jobs`)
   - Breadcrumb: Home > Upload Data

2. **File Upload UI (Skills)**
   - Drag-and-drop zone (desktop only, ≥1024px)
   - Drop zone: Dashed border, upload icon, text "Drag and drop CSV file here"
   - "Browse Files" button as alternative (works on all devices)
   - Mobile (<1024px): Hide drag-drop, show only "Browse Files" button

3. **File Upload UI (Jobs)**
   - Same as Skills upload (separate route: `/upload/jobs`)
   - UI identical, backend endpoint different

4. **File Validation - Type & Size**
   - Accept only `.csv` files
   - Max size: 100 MB
   - If invalid type → show error: "Only CSV files are allowed"
   - If too large → show error: "File size exceeds 100 MB limit"
   - Validation happens immediately after file selection

5. **CSV Header Validation**
   - Parse CSV headers (first row)
   - Skills CSV expected columns: `skill_id`, `skill_name`, `category` (confirm with backend)
   - Jobs CSV expected columns: `job_id`, `job_title`, `company` (confirm with backend)
   - If missing required columns → show error: "Missing required columns: [list]"
   - Show expected columns in error message

6. **Error States**
   - Error messages display below upload zone
   - Red border around upload zone on error
   - "Try Again" button clears error and allows new selection
   - Errors clear when user selects new file

### Integration Requirements

7. **Client-Side CSV Parsing**
   - Use PapaParse library for CSV parsing
   - Parse headers only (don't load full file into memory)
   - Streaming parsing for large files (memory efficient)

8. **Drag-and-Drop Implementation**
   - `onDragOver` → highlight drop zone (solid border, background tint)
   - `onDrop` → validate file, show preview or error
   - `onDragLeave` → remove highlight

9. **File Picker Fallback**
   - `<input type="file" accept=".csv" />` hidden input
   - "Browse Files" button triggers file input click
   - Works on all devices (mobile, tablet, desktop)

### Quality Requirements

10. **Responsive Design**
    - Desktop (≥1024px): Large drag-drop zone (300px height min)
    - Tablet (768px-1023px): Medium-sized zone, "Browse Files" button
    - Mobile (<768px): Hide drag-drop, show only button (full-width)

11. **Accessibility**
    - File input has label (can be visually hidden)
    - Drag-drop zone has role="button" and aria-label
    - Keyboard accessible (Tab to button, Enter to open file picker)
    - Error messages associated with upload zone using aria-describedby

12. **User Experience**
    - Drag-over state clearly visible (instant feedback)
    - Validation errors clear and actionable
    - File selection confirmation (show file name after selection)

---

## Technical Notes

### Component Structure

```
src/
├── screens/
│   ├── UploadSelection.jsx    # Upload type selection
│   ├── UploadSkills.jsx        # Skills CSV upload
│   └── UploadJobs.jsx          # Jobs CSV upload
├── components/
│   ├── DragDropZone.jsx        # Drag-and-drop component
│   ├── FileValidator.jsx       # Client-side validation
│   └── UploadError.jsx         # Error message display
└── utils/
    └── csvValidation.js        # CSV parsing and validation
```

### CSV Validation Example

```javascript
import Papa from 'papaparse';

const validateSkillsCSV = (file) => {
  return new Promise((resolve, reject) => {
    const requiredColumns = ['skill_id', 'skill_name', 'category'];
    
    Papa.parse(file, {
      preview: 1, // Only parse first row (headers)
      complete: (results) => {
        const headers = results.data[0];
        const missing = requiredColumns.filter(col => !headers.includes(col));
        
        if (missing.length > 0) {
          reject({ message: `Missing required columns: ${missing.join(', ')}` });
        } else {
          resolve({ headers, valid: true });
        }
      },
      error: (err) => reject({ message: 'Failed to parse CSV file' })
    });
  });
};
```

### CSV Column Schemas

**Skills CSV Expected Columns** (confirm with backend):
- `skill_id` (required)
- `skill_name` (required)
- `category` (required)
- `subcategory` (optional)
- Additional columns as needed

**Jobs CSV Expected Columns** (confirm with backend):
- `job_id` (required)
- `job_title` (required)
- `company` (required)
- `skills_required` (optional)
- Additional columns as needed

---

## Definition of Done

- [x] Upload type selection screen displays two cards
- [x] Click card → navigates to respective upload screen
- [x] Drag-and-drop zone works on desktop
- [x] Browse Files button works on all devices
- [x] File type validation (only .csv accepted)
- [x] File size validation (max 100 MB)
- [x] CSV header validation (required columns checked)
- [x] Error messages display for validation failures
- [x] Responsive design tested (mobile, tablet, desktop)
- [x] Keyboard navigation works
- [x] Screen reader tested

---

## Dependencies

- EPIC-001-STORY-002 (Application Shell with Navigation)
- PapaParse library installed (`npm install papaparse`)
- Backend CSV column schemas confirmed

---

**Story Status**: ✅ Ready for Development
