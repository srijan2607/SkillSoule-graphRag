# Frontend Epics - Graph RAG System

**Project**: Graph RAG System for Skills & Jobs Knowledge Graph  
**Phase**: Frontend Implementation  
**Created**: 2025-10-25  
**Total Epics**: 3  
**Total Stories**: 9

---

## Overview

This directory contains the epic definitions for the frontend implementation of the Graph RAG System. The frontend is built with React, TailwindCSS, and integrates with an existing FastAPI backend and Neo4j knowledge graph.

---

## Epic Roadmap

### Phase 1: Foundation (Week 1-2)

#### [Epic 1: Authentication & Core Layout](./epic-001-authentication-core-layout.md)
**Status**: Ready for Development  
**Priority**: High (Foundation)  
**Stories**: 3  
**Estimated Effort**: 5-8 days

**Scope:**
- Login and Registration screens
- Home page dashboard
- Navigation bar (desktop + mobile)
- Protected routes
- JWT token management

**Key Deliverables:**
- Users can register and log in
- Protected route system redirects unauthenticated users
- Home dashboard provides navigation to Chat and Upload

**Dependencies:** None (foundation epic)

---

### Phase 2: Core Features (Week 2-4)

#### [Epic 2: Chat Interface & RAG Integration](./epic-002-chat-interface-rag.md)
**Status**: Ready for Development  
**Priority**: High (Core Feature)  
**Stories**: 3  
**Estimated Effort**: 5-8 days

**Scope:**
- Conversational AI chat interface
- Integration with backend RAG query endpoint
- Source citations from graph traversal
- Typing indicators and error handling
- Message history management

**Key Deliverables:**
- Users can ask natural language questions
- Responses appear within 5-10 seconds
- Source citations show graph nodes used in answers
- Error handling for timeouts and API failures

**Dependencies:** Epic 1 (Authentication & Core Layout)

---

#### [Epic 3: CSV Upload Workflow](./epic-003-csv-upload-workflow.md)
**Status**: Ready for Development  
**Priority**: Medium (Data Management)  
**Stories**: 3  
**Estimated Effort**: 6-9 days

**Scope:**
- Upload type selection (Skills vs Jobs CSV)
- Drag-and-drop file upload with validation
- CSV preview modal
- Real-time ingestion progress tracking
- Completion summary and error reporting

**Key Deliverables:**
- Users can upload Skills and Jobs CSV files
- Client-side validation prevents invalid uploads
- Progress updates every 2 seconds during ingestion
- Success/error states with actionable feedback

**Dependencies:** Epic 1 (Authentication & Core Layout)

---

## Development Timeline

```
Week 1-2: Epic 1 (Authentication & Core Layout)
  ├─ Story 1: Authentication Screens (2-3 days)
  ├─ Story 2: Application Shell (2-3 days)
  └─ Story 3: Route Protection (1-2 days)

Week 2-3: Epic 2 (Chat Interface & RAG Integration)
  ├─ Story 1: Chat UI Foundation (2-3 days)
  ├─ Story 2: RAG Query Integration (2-3 days)
  └─ Story 3: Source Citations (1-2 days)

Week 3-4: Epic 3 (CSV Upload Workflow)
  ├─ Story 1: Upload UI & Validation (2-3 days)
  ├─ Story 2: CSV Preview (2-3 days)
  └─ Story 3: Progress Tracking (2-3 days)

Week 4-5: Polish & Testing
  ├─ Responsive design testing
  ├─ Cross-browser compatibility
  ├─ Performance optimization
  ├─ Accessibility testing
  └─ Bug fixes and refinements
```

**Total Estimated Duration**: 4-5 weeks

---

## Technology Stack

### Frontend
- **Framework**: React (functional components, hooks)
- **Styling**: TailwindCSS (utility-first CSS)
- **UI Components**: Headless UI (accessible, unstyled components)
- **Routing**: React Router v6
- **State Management**: React Context API
- **Icons**: Heroicons
- **CSV Parsing**: PapaParse
- **Data Fetching**: SWR or React Query

### Backend Integration
- **API**: FastAPI REST endpoints
- **Authentication**: JWT tokens (stored in localStorage)
- **File Upload**: multipart/form-data
- **Polling**: Long-polling for progress updates

### Design System
- **Color Palette**: Blue primary (#2563EB), semantic colors for states
- **Typography**: System font stack (no custom fonts)
- **Spacing**: 4px grid system (TailwindCSS default)
- **Breakpoints**: 640px (tablet), 768px (small laptop), 1024px (desktop)

---

## API Integration Points

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User authentication (returns JWT)

### Chat
- `POST /query` - RAG query endpoint (requires JWT auth)
  - Request: `{query: string}`
  - Response: `{answer: string, sources: [{type, id, name, metadata}]}`

### Upload
- `POST /upload/skills` - Upload skills CSV (multipart/form-data, returns `{job_id}`)
- `POST /upload/jobs` - Upload jobs CSV (multipart/form-data, returns `{job_id}`)
- `GET /ingest/status/{job_id}` - Poll ingestion progress
  - Response: `{processed: number, total: number, status: string, errors: []}`

---

## Success Criteria

### Epic 1: Authentication & Core Layout
- [x] Users can register and log in successfully
- [x] Protected routes redirect unauthenticated users
- [x] Navigation works on desktop and mobile
- [x] Responsive design at all breakpoints

### Epic 2: Chat Interface & RAG Integration
- [x] Users can send queries and receive answers within 5-10s
- [x] Source citations display with expandable details
- [x] Error handling covers timeouts and API failures
- [x] Typing indicators provide clear feedback

### Epic 3: CSV Upload Workflow
- [x] File validation prevents invalid uploads
- [x] CSV preview displays first 10 rows accurately
- [x] Progress updates every 2 seconds during ingestion
- [x] Error states provide actionable feedback

---

## Quality Standards

### Performance
- **First Contentful Paint**: <1.5s
- **Largest Contentful Paint**: <2.5s
- **Time to Interactive**: <3.5s
- **Chat Query Response**: <5s (average), <10s (timeout)

### Accessibility
- **Keyboard Navigation**: All features accessible via keyboard
- **Focus States**: Visible focus rings on all interactive elements
- **Color Contrast**: Minimum 4.5:1 for normal text
- **Screen Reader**: Basic ARIA labels and semantic HTML

### Code Quality
- **TypeScript**: Optional but recommended
- **Testing**: >80% code coverage (unit + integration tests)
- **Linting**: ESLint + Prettier configured
- **Code Review**: All PRs require review and approval

---

## Risk Management

### Epic 1 Risks
- **Risk**: Token storage in localStorage vulnerable to XSS
- **Mitigation**: Use httpOnly cookies post-MVP, implement CSP headers

### Epic 2 Risks
- **Risk**: LLM response times exceed 10 seconds
- **Mitigation**: Set explicit timeout, show retry option, consider streaming responses

### Epic 3 Risks
- **Risk**: Large CSV files cause browser memory issues
- **Mitigation**: Stream parsing, only load first 10 rows for preview

---

## Next Steps

### For Development Team
1. **Environment Setup** (Week 0)
   - Initialize React project (Vite recommended)
   - Install dependencies (TailwindCSS, Headless UI, React Router)
   - Configure ESLint, Prettier, TypeScript
   - Set up Git repository and branching strategy

2. **Epic 1 Implementation** (Week 1-2)
   - Break down stories into tasks
   - Implement authentication screens
   - Build application shell
   - Set up protected routes

3. **Epic 2 & 3 Implementation** (Week 2-4)
   - Implement chat interface
   - Integrate with RAG endpoint
   - Build CSV upload workflow
   - Implement progress tracking

4. **Polish & Testing** (Week 4-5)
   - Responsive design verification
   - Cross-browser testing
   - Performance optimization
   - Accessibility audit

### For Story Manager
- Break down each epic into detailed user stories with acceptance criteria
- Estimate story points based on complexity
- Create JIRA/Linear tickets for tracking
- Assign stories to sprint backlog

### For Backend Team
- Confirm API endpoint contracts
- Provide sample request/response formats
- Deploy endpoints to development environment
- Document authentication flow and JWT format

---

## Documentation

- **UI/UX Specification**: `/Users/srijan26/desktop/Dev/docs/front-end-spec.md`
- **Architecture Document**: (To be created)
- **API Documentation**: (Provided by backend team)
- **Component Library**: (To be created in Storybook)

---

## Questions & Support

**Epic Owner**: Product Manager (John) 📋  
**Technical Lead**: (To be assigned)  
**Design Lead**: (To be assigned)

**Contact**: For questions about epic scope, priorities, or clarifications, reach out to the Product Manager.

---

**Last Updated**: 2025-10-25  
**Version**: 1.0  
**Status**: ✅ All Epics Ready for Development
