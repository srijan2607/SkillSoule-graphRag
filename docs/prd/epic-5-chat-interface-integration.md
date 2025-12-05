# Epic 5: Chat Interface & Integration

**Epic Goal**: Build the React chat interface and integrate all components into a complete, end-to-end conversational career intelligence system. By the end of this epic, users can login, upload CSV files, ask natural language questions in a chat interface, and receive intelligent responses backed by the knowledge graph.

## Story 5.1: Chat UI Components

**As a** user
**I want** a clean chat interface to interact with the system
**so that** I can ask questions naturally

### Acceptance Criteria

1. Chat page created at `/chat` route (protected)
2. Chat layout: Message list (scrollable) + Input field (bottom)
3. Message components: UserMessage (right-aligned) and AssistantMessage (left-aligned)
4. Input field with "Send" button and Enter key support
5. Typing indicator shown while waiting for LLM response
6. Auto-scroll to bottom when new messages appear
7. Message history persisted in React state (cleared on page refresh)
8. Clean, minimal UI with clear visual distinction between user and assistant messages
9. Timestamps displayed for each message (optional, can be hidden for MVP)
10. Empty state: "Ask me anything about careers, skills, or jobs!"

## Story 5.2: Chat Backend Integration

**As a** frontend developer
**I want** the chat UI to call the query API and display responses
**so that** users see answers to their questions

### Acceptance Criteria

1. When user sends message: Call `POST /query` with query text
2. Add user message to chat immediately (optimistic UI)
3. Show typing indicator while waiting for API response
4. On success: Add assistant message with LLM response
5. On error: Display error message in chat "Sorry, I couldn't process that. Please try again."
6. Include JWT token in Authorization header for authenticated requests
7. Handle API timeouts (>10 seconds): Display timeout message
8. Disable input field while query is processing (prevent multiple simultaneous queries)
9. Re-enable input field after response or error

## Story 5.3: Source Citations Display

**As a** user
**I want** to see which graph nodes were used to answer my question
**so that** I can verify the information source

### Acceptance Criteria

1. Parse `sources` array from `/query` response
2. Display sources as expandable section below assistant message
3. Source format: "Based on 5 jobs, 3 skills, and 2 companies"
4. Expandable view shows node details: Node type, key properties (name, title, etc.)
5. Sources grouped by node type: Jobs, Skills, Companies
6. Click to expand/collapse source details
7. Clean formatting with clear visual hierarchy
8. Optional: Link to Neo4j browser for power users (not required for MVP)

## Story 5.4: Conversation State Management

**As a** user
**I want** my conversation history maintained during my session
**so that** I can refer back to previous questions and answers

### Acceptance Criteria

1. Chat history stored in React state (array of messages)
2. Each message object: `{id, role: "user"|"assistant", content, timestamp, sources?}`
3. Message IDs generated (UUID or auto-increment)
4. Conversation persists during session (until page refresh or logout)
5. "Clear Chat" button to reset conversation
6. Optional: Store conversation in localStorage for persistence across page reloads
7. Optional: Save conversation to PostgreSQL for user history (deferred to post-MVP)

## Story 5.5: Navigation & Layout Integration

**As a** user
**I want** to easily navigate between chat, upload, and account pages
**so that** I can access all system features

### Acceptance Criteria

1. Navigation bar with links: "Chat", "Upload Data", "Logout"
2. Navigation always visible at top of page
3. Active route highlighted in navigation
4. Logout clears JWT token from localStorage and redirects to `/login`
5. Clicking "Upload Data" navigates to `/upload` page (from Epic 2)
6. Clicking "Chat" navigates to `/chat` page
7. Responsive navigation: Works on mobile and desktop
8. Clean, consistent styling across all pages

## Story 5.6: End-to-End Integration Testing

**As a** developer
**I want** to verify the complete user journey works end-to-end
**so that** I can confidently deliver the MVP

### Acceptance Criteria

1. **Test Scenario 1: New User Registration**
   - Register new account → Login → Redirect to chat → Success
2. **Test Scenario 2: CSV Upload**
   - Upload skills CSV → Validation passes → Preview shown → Confirm → Ingestion completes → Success message
   - Upload jobs CSV → Same flow → Success
3. **Test Scenario 3: Query Flow**
   - Ask "What skills are needed for Data Scientist jobs?" → Response generated with sources → Sources displayed
4. **Test Scenario 4: Multi-Turn Conversation**
   - Ask follow-up question → Response considers previous context (basic session memory)
5. **Test Scenario 5: Error Handling**
   - Invalid login → Error shown
   - Empty query → Error shown
   - API failure → Graceful error message
6. All scenarios documented in testing checklist
7. Manual testing performed and passed

## Story 5.7: Documentation & README

**As a** developer or user
**I want** comprehensive documentation to set up and use the system
**so that** I can run the application without assistance

### Acceptance Criteria

1. README.md updated with complete setup instructions:
   - Prerequisites (Python 3.10+, Node.js 18+)
   - Clone repository and install dependencies
   - Environment variable setup (copy `.env.example` to `.env`, fill in values)
   - Database setup (Prisma migrations, Neo4j connection test)
   - Run backend (uvicorn command)
   - Run frontend (npm start command)
2. `.env.example` includes all variables with descriptions
3. Troubleshooting section: Common issues and solutions
4. API documentation: List of endpoints with request/response examples
5. Architecture diagram: High-level system overview (optional, can be text description)
6. Usage guide: How to upload CSV, ask questions, interpret responses
7. Technology stack documented: React, FastAPI, Neo4j, PostgreSQL, LangGraph, OpenRouter

## Story 5.8: MVP Polish & Final QA

**As a** product owner
**I want** the MVP to be polished and bug-free
**so that** it provides a professional user experience

### Acceptance Criteria

1. All console errors and warnings resolved
2. Loading states implemented for all async operations
3. Error messages are user-friendly (not raw API errors)
4. Responsive design tested on desktop and mobile (basic responsiveness)
5. No broken links or 404 pages
6. All forms have proper validation feedback
7. Accessibility basics: Tab navigation works, labels on inputs
8. Performance: Page load <3 seconds, query response <5 seconds
9. Cross-browser testing: Chrome, Firefox, Safari (latest versions)
10. Final walkthrough with stakeholder → Approval for deployment

---
