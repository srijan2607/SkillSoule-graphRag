# User Stories - Graph RAG System Frontend

**Project**: Graph RAG System for Skills & Jobs Knowledge Graph  
**Phase**: Frontend Implementation  
**Created**: 2025-10-25  
**Total Stories**: 9 (across 3 epics)  
**Status**: ✅ All Stories Ready for Development

---

## Quick Navigation

### Epic 1: Authentication & Core Layout
- [EPIC-001-STORY-001: Authentication Screens](#epic-001-story-001-authentication-screens)
- [EPIC-001-STORY-002: Application Shell](#epic-001-story-002-application-shell)
- [EPIC-001-STORY-003: Route Protection](#epic-001-story-003-route-protection)

### Epic 2: Chat Interface & RAG Integration
- [EPIC-002-STORY-001: Chat UI Foundation](#epic-002-story-001-chat-ui-foundation)
- [EPIC-002-STORY-002: RAG Query Integration](#epic-002-story-002-rag-query-integration)
- [EPIC-002-STORY-003: Source Citations](#epic-002-story-003-source-citations)

### Epic 3: CSV Upload Workflow
- [EPIC-003-STORY-001: Upload UI & Validation](#epic-003-story-001-upload-ui--validation)
- [EPIC-003-STORY-002: CSV Preview](#epic-003-story-002-csv-preview)
- [EPIC-003-STORY-003: Progress Tracking](#epic-003-story-003-progress-tracking)

---

## Story Index

### Epic 1: Authentication & Core Layout

#### EPIC-001-STORY-001: Authentication Screens
**File**: `EPIC-001-STORY-001-authentication-screens.md`  
**Priority**: High  
**Effort**: 2-3 days  
**Dependencies**: None

**Summary**: Implement login and registration screens with form validation, API integration, JWT token storage, and responsive design.

**Key Acceptance Criteria**:
- Login screen with email/password form
- Registration screen with validation (email format, password ≥8 chars)
- API integration with `/auth/login` and `/auth/register`
- JWT token stored in localStorage
- Error handling for invalid credentials, network failures

**Technical Stack**: React, TailwindCSS, Headless UI, Fetch API

---

#### EPIC-001-STORY-002: Application Shell
**File**: `EPIC-001-STORY-002-application-shell.md`  
**Priority**: High  
**Effort**: 2-3 days  
**Dependencies**: EPIC-001-STORY-001

**Summary**: Create Home page dashboard, top navigation bar, mobile menu, routing infrastructure, and global authentication context.

**Key Acceptance Criteria**:
- Home dashboard with "Start Chatting" and "Upload Data" action cards
- Top navigation bar with logo, links, user menu dropdown
- Mobile hamburger menu (<768px)
- React Router with protected routes
- AuthContext for global auth state
- Logout functionality

**Technical Stack**: React, React Router v6, TailwindCSS, Headless UI

---

#### EPIC-001-STORY-003: Route Protection
**File**: `EPIC-001-STORY-003-route-protection.md`  
**Priority**: High  
**Effort**: 1-2 days  
**Dependencies**: EPIC-001-STORY-001, EPIC-001-STORY-002

**Summary**: Implement protected route wrapper, auto-redirect logic, session persistence, and token expiration handling.

**Key Acceptance Criteria**:
- ProtectedRoute component redirects unauthenticated users to `/login`
- After login, redirect to intended destination (or `/home`)
- Session persists across page refreshes (localStorage)
- Token expiration (401) triggers logout and redirect
- No "flicker" on page load (loading state during auth check)

**Technical Stack**: React Router v6, AuthContext

---

### Epic 2: Chat Interface & RAG Integration

#### EPIC-002-STORY-001: Chat UI Foundation
**File**: `EPIC-002-STORY-001-chat-ui-foundation.md`  
**Priority**: High  
**Effort**: 2-3 days  
**Dependencies**: EPIC-001 (Authentication & Core Layout)

**Summary**: Build chat screen layout with message bubbles, input field, auto-scroll, and empty state.

**Key Acceptance Criteria**:
- Chat screen with message thread area + fixed input at bottom
- User messages (right-aligned, blue) and assistant messages (left-aligned, gray)
- Textarea input with send button, Enter key sends message
- Auto-scroll to bottom on new messages
- Empty state: "Ask me anything about careers, skills, and jobs!"

**Technical Stack**: React, TailwindCSS

---

#### EPIC-002-STORY-002: RAG Query Integration
**File**: `EPIC-002-STORY-002-rag-query-integration.md`  
**Priority**: High  
**Effort**: 2-3 days  
**Dependencies**: EPIC-002-STORY-001

**Summary**: Integrate with backend RAG query endpoint, handle responses, implement typing indicator, and error handling with 10-second timeout.

**Key Acceptance Criteria**:
- POST query to `/query` endpoint with JWT token
- Typing indicator (animated dots) while waiting for response
- Display LLM response as assistant message
- 10-second timeout with retry option
- Error handling (400, 401, 500, network errors)
- Input disabled during processing

**Technical Stack**: Fetch API, React state management

---

#### EPIC-002-STORY-003: Source Citations
**File**: `EPIC-002-STORY-003-source-citations.md`  
**Priority**: Medium  
**Effort**: 1-2 days  
**Dependencies**: EPIC-002-STORY-002

**Summary**: Display expandable source citations below assistant messages and implement clear chat functionality.

**Key Acceptance Criteria**:
- Source citations expandable section below assistant messages
- Summary: "Based on 5 jobs, 3 skills, 2 companies"
- Expanded: List of sources with icon, type, name, metadata
- Clear chat button with confirmation dialog
- Limit sources to 10, show "...and X more" if needed

**Technical Stack**: React state, Headless UI (Dialog)

---

### Epic 3: CSV Upload Workflow

#### EPIC-003-STORY-001: Upload UI & Validation
**File**: `EPIC-003-STORY-001-upload-ui-validation.md`  
**Priority**: Medium  
**Effort**: 2-3 days  
**Dependencies**: EPIC-001 (Authentication & Core Layout)

**Summary**: Create upload type selection screen, drag-and-drop zone, file picker, and client-side validation (type, size, CSV headers).

**Key Acceptance Criteria**:
- Upload type selection: "Upload Skills CSV" vs "Upload Jobs CSV" cards
- Drag-and-drop zone (desktop ≥1024px)
- "Browse Files" button (all devices)
- File validation: type (.csv only), size (<100 MB), required columns
- Error messages for validation failures

**Technical Stack**: React, TailwindCSS, PapaParse (CSV parsing)

---

#### EPIC-003-STORY-002: CSV Preview
**File**: `EPIC-003-STORY-002-csv-preview.md`  
**Priority**: Medium  
**Effort**: 2-3 days  
**Dependencies**: EPIC-003-STORY-001

**Summary**: Display CSV preview modal showing first 10 rows, implement upload initiation to backend, and navigate to progress screen.

**Key Acceptance Criteria**:
- CSV preview modal with first 10 rows in table format
- Total record count displayed
- "Confirm Upload" button → POST to `/upload/skills` or `/upload/jobs`
- Receive job_id from backend
- Navigate to progress screen with job_id
- Error handling for upload failures

**Technical Stack**: PapaParse, Fetch API (multipart/form-data), Headless UI (Modal)

---

#### EPIC-003-STORY-003: Progress Tracking
**File**: `EPIC-003-STORY-003-progress-tracking.md`  
**Priority**: Medium  
**Effort**: 2-3 days  
**Dependencies**: EPIC-003-STORY-002

**Summary**: Implement real-time progress tracking with polling, display completion states, and enable error log download.

**Key Acceptance Criteria**:
- Progress screen with progress bar, statistics, batch number
- Poll GET `/ingest/status/{job_id}` every 2 seconds
- Display: processed/total, estimated time remaining
- Completion states: Success, Partial success (with error log), Failure
- "Download Error Log" button (if errors exist)
- "Return to Home" button

**Technical Stack**: SWR (polling), React, TailwindCSS

---

## Development Order

### Week 1-2: Foundation (Epic 1)
1. ✅ **EPIC-001-STORY-001** - Authentication Screens (2-3 days)
2. ✅ **EPIC-001-STORY-002** - Application Shell (2-3 days)
3. ✅ **EPIC-001-STORY-003** - Route Protection (1-2 days)

**Deliverable**: Users can register, login, navigate to Home dashboard

---

### Week 2-3: Chat Feature (Epic 2)
4. ✅ **EPIC-002-STORY-001** - Chat UI Foundation (2-3 days)
5. ✅ **EPIC-002-STORY-002** - RAG Query Integration (2-3 days)
6. ✅ **EPIC-002-STORY-003** - Source Citations (1-2 days)

**Deliverable**: Users can ask questions and receive AI-powered answers with source citations

---

### Week 3-4: Upload Feature (Epic 3)
7. ✅ **EPIC-003-STORY-001** - Upload UI & Validation (2-3 days)
8. ✅ **EPIC-003-STORY-002** - CSV Preview (2-3 days)
9. ✅ **EPIC-003-STORY-003** - Progress Tracking (2-3 days)

**Deliverable**: Users can upload Skills/Jobs CSV files with real-time progress tracking

---

### Week 4-5: Polish & Testing
- Responsive design verification
- Cross-browser testing (Chrome, Firefox, Safari, Edge)
- Accessibility testing (keyboard nav, screen readers)
- Performance optimization (code splitting, lazy loading)
- Bug fixes and refinements

---

## Technical Dependencies

### Required Libraries

```bash
npm install react react-dom react-router-dom
npm install @headlessui/react @heroicons/react
npm install tailwindcss postcss autoprefixer
npm install papaparse swr
```

### Environment Variables

```env
REACT_APP_API_BASE_URL=https://api.your-domain.com
```

### Backend API Endpoints

**Authentication:**
- POST `/auth/register` - User registration
- POST `/auth/login` - User login (returns JWT)

**Chat:**
- POST `/query` - RAG query endpoint (requires JWT)

**Upload:**
- POST `/upload/skills` - Upload skills CSV (multipart/form-data, returns job_id)
- POST `/upload/jobs` - Upload jobs CSV (multipart/form-data, returns job_id)
- GET `/ingest/status/{job_id}` - Poll ingestion progress
- GET `/ingest/errors/{job_id}` - Download error log (if errors exist)

---

## Quality Standards

### Performance Targets
- First Contentful Paint: <1.5s
- Largest Contentful Paint: <2.5s
- Time to Interactive: <3.5s
- Chat query response: <5s (average), <10s (timeout)

### Accessibility Requirements
- Keyboard navigation: All features accessible via keyboard
- Focus states: Visible focus rings on all interactive elements
- Color contrast: Minimum 4.5:1 for normal text
- Screen reader: Basic ARIA labels and semantic HTML

### Testing Requirements
- Unit tests: >80% code coverage
- Integration tests: API calls mocked
- E2E tests: Critical paths (login → chat, login → upload)
- Responsive design: Tested on mobile (375px), tablet (768px), desktop (1280px)
- Cross-browser: Chrome, Firefox, Safari, Edge

---

## Story Template

Each story follows this structure:

1. **User Story**: As a [user type], I want [action], So that [benefit]
2. **Acceptance Criteria**: Functional, Integration, Quality requirements
3. **Technical Notes**: Code examples, component structure, API integration
4. **Definition of Done**: Checklist of completion criteria
5. **Dependencies**: Required stories, endpoints, libraries
6. **Risk Assessment**: Primary risks and mitigation strategies

---

## Contributing

### Story Development Workflow

1. **Assign Story**: Pick story from backlog, move to "In Progress"
2. **Create Branch**: `git checkout -b feature/EPIC-XXX-STORY-XXX-description`
3. **Implement**: Follow acceptance criteria and technical notes
4. **Test**: Run unit tests, integration tests, manual testing
5. **Code Review**: Create PR, request review from team
6. **Merge**: After approval, merge to main branch
7. **Deploy**: Deploy to development environment
8. **Verify**: QA verification in dev environment
9. **Mark Complete**: Move story to "Done"

### Code Standards

- Use React functional components with hooks
- Follow ESLint and Prettier configuration
- Use TailwindCSS utility classes (no custom CSS)
- Write meaningful commit messages
- Add comments for complex logic
- Write tests for all new features

---

## Questions & Support

**Product Manager**: John 📋  
**Technical Lead**: (To be assigned)  
**Design Lead**: (To be assigned)

For questions about story requirements, acceptance criteria, or priorities, contact the Product Manager.

---

**Last Updated**: 2025-10-25  
**Status**: ✅ All 9 Stories Ready for Development
