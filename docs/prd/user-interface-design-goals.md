# User Interface Design Goals

## Overall UX Vision

The system shall provide a clean, minimal chat interface that prioritizes conversational interaction over complex UI elements. The primary user journey is: login → upload CSV data (one-time setup) → ask questions in natural language → receive intelligent responses. The interface should feel like talking to a knowledgeable career advisor rather than querying a database. Simplicity and clarity are paramount—users should be able to accomplish all tasks without training or documentation.

## Key Interaction Paradigms

**Conversational-First Design**: The chat interface is the primary interaction model. Users type questions in plain English and receive contextual responses with citations from the knowledge graph. The system should minimize UI chrome and maximize conversation space.

**Progressive Disclosure**: Advanced features (CSV upload, ingestion progress) are accessible but not prominent. The default view is the chat interface—data management is secondary.

**Instant Feedback**: All operations (login, file upload, query submission) provide immediate visual feedback. Ingestion shows real-time progress with records processed/failed counts. Chat messages show typing indicators during LLM response generation.

## Core Screens and Views

**1. Login/Registration Screen**
- Simple email + password form
- Clear error messages for validation failures
- No email verification required (MVP simplicity)

**2. Chat Interface (Main Screen)**
- Full-screen chat layout with message history
- Input field for natural language queries
- LLM responses displayed with proper formatting
- Source citations shown inline or as expandable sections

**3. CSV Upload Screen**
- Drag-and-drop zones for skills.csv and jobs.csv
- File validation feedback (format, columns, size)
- Option to preview first 5-10 rows before confirming upload
- Real-time ingestion progress bar with detailed stats

**4. Ingestion Progress View**
- Records processed / failed / total counts
- Estimated time remaining
- Error log download for failed records
- Success confirmation with summary statistics

## Accessibility

**Level**: None (MVP does not require WCAG compliance)

For post-MVP, consider WCAG AA compliance for:
- Keyboard navigation support
- Screen reader compatibility for chat messages
- Color contrast requirements
- Focus indicators

## Branding

**Style**: Clean, minimal, professional interface with focus on readability and usability over visual flair.

**Design Approach**: Use TailwindCSS or Material-UI default components with minimal customization. Prioritize functional clarity over branding elements.

**Color Palette**: Standard neutral colors (grays for backgrounds, blue for primary actions, red for errors, green for success states). No custom brand colors required for MVP.

## Target Platforms

**Primary**: Web Responsive (desktop browsers: Chrome, Firefox, Safari, Edge)

**Secondary**: Mobile-friendly layout (responsive design, but not optimized for mobile-first interaction)

**Not Supported**: Native mobile apps, tablet-specific layouts, legacy browsers (IE11)

---
