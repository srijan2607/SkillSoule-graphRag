# Story: Ingestion Progress Tracking & Completion

**Story ID**: EPIC-003-STORY-003  
**Epic**: Epic 3 - CSV Upload Workflow  
**Priority**: Medium  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-003-STORY-002 (CSV Preview & Upload)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** to see real-time progress of my CSV ingestion,  
**So that** I know how long it will take and when it's complete.

---

## Acceptance Criteria

### Functional Requirements

1. **Progress Screen Layout**
   - Page title: "Ingestion Progress - {type}" (Skills or Jobs)
   - Progress bar (0-100%)
   - Statistics: "Processed: 7,892 / 10,523 records"
   - Batch number: "Processing batch 8 of 11"
   - Estimated time remaining: "~45 seconds remaining"
   - Status message: "Processing..." or "Completed" or "Failed"

2. **Progress Polling**
   - Poll GET `/ingest/status/{job_id}` every 2 seconds
   - Include JWT token in Authorization header
   - Response: `{ processed: number, total: number, batchNumber: number, status: 'processing'|'completed'|'failed', errors: [] }`
   - Update UI with latest progress

3. **Progress Bar**
   - Calculate percentage: `(processed / total) * 100`
   - Animated fill (smooth transition, 300ms)
   - Color: Blue (#2563EB) for in-progress, Green (#10B981) for completed, Red (#EF4444) for failed
   - Width updates based on percentage

4. **Estimated Time Remaining**
   - Calculate from average processing speed
   - Formula: `(total - processed) / (processed / elapsedTime)`
   - Display as: "~45 seconds remaining" or "~2 minutes remaining"
   - Hide when status is completed or failed

5. **Completion States**
   - **Success**: All records ingested successfully
     - Status: "Completed ✓"
     - Message: "10,523 records successfully ingested"
     - Show "Return to Home" button
   - **Partial Success**: Some records failed
     - Status: "Completed with errors ⚠️"
     - Message: "10,518 / 10,523 records ingested. 5 records failed."
     - Show "Download Error Log" button + "Return to Home" button
   - **Total Failure**: Ingestion failed completely
     - Status: "Failed ✗"
     - Message: "Ingestion failed: {error message from backend}"
     - Show "Return to Home" button (no error log)

6. **Error Log Download**
   - If errors exist → show "Download Error Log" button
   - Click → download CSV file with failed rows
   - Error log format: Same as original CSV + "error_reason" column
   - Backend provides error log at GET `/ingest/errors/{job_id}` (confirm with backend)

7. **Polling Lifecycle**
   - Start polling when screen mounts
   - Poll every 2 seconds while `status === 'processing'`
   - Stop polling when `status === 'completed'` or `status === 'failed'`
   - Handle tab visibility: pause polling when tab hidden, resume when visible

### Integration Requirements

8. **API Integration - Status Polling**
   - Endpoint: GET `/ingest/status/{job_id}`
   - Headers: `{ 'Authorization': 'Bearer {token}' }`
   - Response: `{ processed: number, total: number, batchNumber: number, status: string, estimatedTimeRemaining: number, errors: [] }`

9. **API Integration - Error Log**
   - Endpoint: GET `/ingest/errors/{job_id}` (if errors exist)
   - Response: CSV file download
   - Trigger browser download

10. **Navigation**
    - "Return to Home" button → navigate to `/home`
    - Progress screen accessible at `/upload/progress/{job_id}`
    - job_id passed from previous screen (CSV preview)

### Quality Requirements

11. **User Experience**
    - Progress updates feel real-time (2-second polling acceptable)
    - No UI jank during updates (smooth transitions)
    - Clear completion states (success vs partial vs failure)
    - Error log download is instant

12. **Error Handling**
    - Handle network interruption during polling → show "Connection lost, retrying..."
    - Retry failed polling requests (3 attempts with exponential backoff)
    - Handle backend crash → show error after 3 failed retries

13. **Performance**
    - Polling doesn't cause memory leaks (cleanup on unmount)
    - Progress bar animates smoothly (60 FPS)
    - Component re-renders efficiently (no unnecessary renders)

---

## Technical Notes

### Polling Implementation (SWR)

```javascript
import useSWR from 'swr';

const ProgressScreen = ({ jobId, uploadType }) => {
  const { data, error } = useSWR(
    `/ingest/status/${jobId}`,
    (url) => apiClient(url, token),
    {
      refreshInterval: (data) => data?.status === 'processing' ? 2000 : 0, // Poll every 2s while processing
      revalidateOnFocus: false,
      revalidateOnReconnect: true
    }
  );
  
  const percentage = data ? (data.processed / data.total) * 100 : 0;
  const isComplete = data?.status === 'completed' || data?.status === 'failed';
  
  return (
    <div>
      <ProgressBar percentage={percentage} status={data?.status} />
      <p>Processed: {data?.processed} / {data?.total} records</p>
      {!isComplete && <p>~{data?.estimatedTimeRemaining}s remaining</p>}
      {isComplete && <CompletionState data={data} />}
    </div>
  );
};
```

### Error Log Download

```javascript
const downloadErrorLog = async (jobId, token) => {
  const response = await fetch(`${API_BASE_URL}/ingest/errors/${jobId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `error-log-${jobId}.csv`;
  a.click();
  window.URL.revokeObjectURL(url);
};
```

---

## Definition of Done

- [x] Progress screen displays progress bar, statistics, batch number
- [x] Poll `/ingest/status/{job_id}` every 2 seconds while processing
- [x] Progress bar updates smoothly with percentage
- [x] Estimated time remaining displays and updates
- [x] Success state shows completion message + "Return to Home" button
- [x] Partial success shows error count + "Download Error Log" button
- [x] Failure state shows error message
- [x] Error log downloads as CSV when button clicked
- [x] Polling stops when status is completed or failed
- [x] Polling pauses when tab hidden, resumes when visible
- [x] Network interruption handled with retry logic
- [x] "Return to Home" button navigates to `/home`

---

## Dependencies

- EPIC-003-STORY-002 (CSV Preview & Upload provides job_id)
- Backend GET `/ingest/status/{job_id}` endpoint deployed
- Backend GET `/ingest/errors/{job_id}` endpoint deployed (if errors)
- SWR library installed (`npm install swr`)

---

**Story Status**: ✅ Ready for Development
