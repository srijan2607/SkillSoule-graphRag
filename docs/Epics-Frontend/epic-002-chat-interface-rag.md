# Epic 2: Chat Interface & RAG Integration - Brownfield Enhancement

**Epic ID**: EPIC-002  
**Created**: 2025-10-25  
**Status**: Ready for Development  
**Priority**: High (Core Feature)  
**Dependencies**: EPIC-001 (Authentication & Core Layout)

---

## Epic Goal

Deliver an intuitive conversational AI interface that enables users to ask natural language questions about careers, skills, and jobs, receiving intelligent answers powered by the Graph RAG pipeline with transparent source citations.

---

## Project Analysis

### Existing Project Context

- **Project**: Graph RAG System for Skills & Jobs Knowledge Graph
- **Current functionality**: Backend LangGraph RAG pipeline with POST `/query` endpoint, Neo4j knowledge graph populated with skills/jobs data
- **Technology stack**: React frontend, FastAPI backend with LangGraph, Neo4j graph database, LLM integration
- **Integration points**: 
  - POST `/query` - accepts natural language query, returns LLM-generated response with graph sources
  - Response format: `{answer: string, sources: [{type, id, name, metadata}]}`

### Enhancement Scope

- Implement conversational chat interface
- Integrate with backend RAG query endpoint
- Display source citations from graph traversal
- Handle loading states, errors, and timeouts
- Maintain conversation history

---

## Epic Description

### Existing System Context

- **Current relevant functionality**: Backend LangGraph RAG pipeline with POST `/query` endpoint, Neo4j knowledge graph populated with skills/jobs data
- **Technology stack**: React frontend, FastAPI backend with LangGraph, Neo4j graph database, LLM integration
- **Integration points**: 
  - POST `/query` - accepts natural language query, returns LLM-generated response with graph sources
  - Response format: `{answer: string, sources: [{type, id, name, metadata}]}`

### Enhancement Details

**What's being added:**

1. **Chat Interface Screen** - Full-screen conversational UI with message history
2. **Message Bubbles** - User messages (right-aligned) and assistant messages (left-aligned)
3. **Query Input** - Text input field with send button, Enter key support
4. **Source Citations** - Expandable sections showing graph nodes/relationships used in response
5. **Typing Indicator** - Animated dots while waiting for LLM response
6. **Clear Chat** - Button to reset conversation
7. **Auto-scroll** - Automatically scroll to bottom on new messages
8. **Error Handling** - Timeout handling (>10s), API error recovery, retry mechanism

**How it integrates:**

- Frontend sends user query to POST `/query` endpoint
- Backend processes with LangGraph RAG pipeline (query understanding → vector search → graph traversal → LLM generation)
- Response streamed back to frontend (or single response for MVP)
- Sources displayed as expandable cards below assistant message
- Conversation history maintained in React state (cleared on page refresh for MVP)

**Success criteria:**

- Users can type questions in natural language and receive answers
- Responses appear within 5 seconds for typical queries (<10s timeout)
- Source citations show which graph nodes informed the answer
- Typing indicator animates during LLM processing
- Messages scroll automatically to show latest response
- Clear chat button resets conversation
- Error messages display for timeouts, API failures, network issues
- Responsive design works on mobile, tablet, desktop

---

## Stories

### Story 1: Chat UI Foundation (Layout, Messages, Input)

**Description:**  
Implement chat screen layout with message bubbles and input field

**Scope:**
- Implement chat screen layout (message thread area + fixed input at bottom)
- Create message bubble components (user vs assistant styling)
- Build input field with send button and Enter key handler
- Implement message state management (add user message, add assistant response)
- Auto-scroll to bottom on new messages
- Empty state: "Ask me anything about careers, skills, and jobs!"
- Responsive design (mobile: full-screen, desktop: centered max-width)

**Estimated Effort**: 2-3 days

---

### Story 2: RAG Query Integration & Response Handling

**Description:**  
Integrate with backend RAG query endpoint and handle responses

**Scope:**
- API integration with POST `/query` endpoint
- Send user query on button click or Enter key
- Show typing indicator animation while waiting for response
- Parse response and display assistant message
- Handle timeout (>10s) with error message and retry option
- Handle API errors (400, 500) with user-friendly messages
- Disable input during processing to prevent multiple rapid queries
- Loading state management (disable send button, show spinner)

**Estimated Effort**: 2-3 days

---

### Story 3: Source Citations & Chat Management

**Description:**  
Implement source citations display and chat management features

**Scope:**
- Implement source citations expandable component
- Display source metadata (node type, name, count)
- Expandable/collapsible details on click
- "Based on 5 jobs, 3 skills, 2 companies" summary
- Clear chat button with confirmation dialog
- Clear conversation state on confirm
- Persist chat history in localStorage for session recovery (optional enhancement)
- Error state: "I don't have information about that" handling

**Estimated Effort**: 1-2 days

---

## Compatibility Requirements

- [x] **Existing APIs remain unchanged** - Uses existing POST `/query` endpoint
- [x] **Database schema changes are backward compatible** - No database changes
- [x] **UI changes follow existing patterns** - Follows UI/UX spec design system
- [x] **Performance impact is minimal** - Query response <5s target, client-side rendering optimized

---

## Risk Mitigation

### Primary Risk
LLM response times exceed 10 seconds, causing user frustration

### Mitigation
- Set explicit 10-second timeout on frontend
- Show clear timeout message with retry option
- Backend optimization: cache common queries (future)
- Consider streaming responses (Server-Sent Events) for perceived speed

### Rollback Plan
- Disable chat route in frontend navigation
- Users can still access upload functionality
- No backend changes required (API endpoint unchanged)

---

## Definition of Done

- [x] Users can send chat queries and receive AI-generated answers
- [x] Responses appear within 5-10 seconds
- [x] Source citations display with expandable details
- [x] Typing indicator shows during processing
- [x] Error handling covers timeouts and API failures
- [x] Clear chat functionality works
- [x] Auto-scroll keeps latest messages visible
- [x] Responsive design tested on mobile, tablet, desktop
- [x] No regression in backend RAG pipeline

---

## Validation Checklist

### Scope Validation
- [x] Epic can be completed in 3 stories maximum ✅
- [x] No architectural documentation is required ✅ (follows existing UI/UX spec)
- [x] Enhancement follows existing patterns ✅ (established by EPIC-001)
- [x] Integration complexity is manageable ✅ (single API endpoint)

### Risk Assessment
- [x] Risk to existing system is low ✅ (backend RAG pipeline unchanged)
- [x] Rollback plan is feasible ✅ (disable frontend route)
- [x] Testing approach covers existing functionality ✅ (backend tested independently)
- [x] Team has sufficient knowledge of integration points ✅ (REST API, JSON)

### Completeness Check
- [x] Epic goal is clear and achievable ✅
- [x] Stories are properly scoped ✅ (each story = 1-3 days work)
- [x] Success criteria are measurable ✅ (response time, error handling)
- [x] Dependencies are identified ✅ (backend /query endpoint, authentication)

---

## Story Manager Handoff

**Story Manager Instructions:**

Please develop detailed user stories for this brownfield epic. Key considerations:

- This is a **frontend implementation** integrating with existing LangGraph RAG pipeline
- **Technology stack**: React, TailwindCSS, Headless UI, React Router
- **Integration points**: 
  - POST `/query` (expects `{query: string}`, returns `{answer: string, sources: []}`)
  - JWT token in `Authorization: Bearer <token>` header required
- **Existing patterns to follow**: UI/UX specification at `docs/front-end-spec.md`
- **Critical compatibility requirements**: 
  - 5-second response time target, 10-second timeout
  - Source citation format from backend
  - Responsive design at breakpoints: 640px, 768px, 1024px, 1280px
- Each story must include:
  - Chat component implementation (message bubbles, input field)
  - API integration with timeout and error handling
  - Typing indicator and loading states
  - Source citation expandable UI
  - Accessibility: keyboard nav, screen reader support

The epic should deliver a production-ready conversational AI interface while maintaining performance and user experience standards.

---

## Dependencies

- EPIC-001 (Authentication & Core Layout) must be completed
- Backend POST `/query` endpoint must be deployed and tested
- Sample response format confirmed with backend team
- UI/UX specification finalized at `docs/front-end-spec.md`

---

## Success Metrics

- **Query Success Rate**: >95% of queries return valid responses
- **Response Time**: Average <5s, p95 <8s
- **User Engagement**: Average 5-10 queries per session
- **Error Recovery**: Users successfully retry after errors >80% of time
- **Source Citation Usage**: >30% of users expand source details

---

**Epic Status**: ✅ Ready for Story Breakdown and Development
