# Graph RAG System for Skills & Jobs Knowledge Graph Product Requirements Document (PRD)

## Goals and Background Context

### Goals

- Enable conversational, natural language access to career intelligence through graph-powered RAG
- Successfully ingest and structure 40-50K job records and 10K+ skill records into Neo4j knowledge graph
- Demonstrate that hybrid search (vector + graph traversal) provides superior career insights vs keyword search
- Create reusable LangGraph + Neo4j architecture patterns for knowledge graph RAG applications
- Validate technical feasibility of real-time query responses (<5 seconds) on complex relationship queries
- Deliver MVP foundation that enables users to discover non-obvious career paths and skill relationships

### Background Context

Career planning today suffers from fragmented, disconnected data sources where job seekers struggle to understand skill relationships, career progression paths, and market opportunities. Traditional job search platforms rely on keyword matching that misses semantic connections—searching for "Python" won't surface related opportunities in data analysis, API development, or automation that require similar skill combinations.

This Graph RAG System addresses these limitations by combining Neo4j knowledge graphs with semantic embeddings to power conversational AI-driven career intelligence. The system ingests comprehensive skills and jobs taxonomies (CSV format), creates rich relationship netwoxrks between skills, jobs, companies, and locations, and enables natural language queries backed by hybrid search that leverages both vector similarity and graph traversal. This MVP validates whether graph-based RAG can provide superior career insights compared to traditional approaches, while establishing foundational patterns for future knowledge graph applications.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-10-15 | 1.0 | Initial PRD creation from approved Project Brief | John (PM Agent) |
| 2025-10-15 | 1.1 | Requirements refinement: Added intent classification to FR14, similarity threshold to FR10, upsert behavior to FR11, retry strategy to NFR10, removed duplicate FR17 | John (PM Agent) |

---

## Requirements

### Functional Requirements

#### Authentication (FastAPI)
**FR1:** System shall provide user registration and login with email + password, storing user accounts in PostgreSQL via Prisma ORM and generating JWT tokens for session management

**FR2:** System shall expose FastAPI endpoint `/auth/register` for user registration and `/auth/login` for authentication

#### Ingestion Pipeline (FastAPI)
**FR3:** System shall accept CSV file uploads via FastAPI endpoints `/ingest/skills` and `/ingest/jobs`:
- **Skills CSV (17 fields)**: ID, NAME, LEVEL, SUBCATEGORY, SUBCATEGORY_NAME, CATEGORY, CATEGORY_NAME, TYPE, IS_SOFTWARE, IS_LANGUAGE, WIKI_LINK, WIKI_EXTRACT, DESCRIPTION, DESCRIPTION_SOURCE, VERSION, LATEST_VERSION, embeddings
- **Jobs CSV (30 fields)**: Job Title, Company Name, Location, Via, Salary, Posted At, Schedule Type, Work From Home, Description, Apply Options, Job ID, District, Company Description, Job Description, Exact Matched Company, CIN, CompanyIndustrialClassification, NCO_Code_algo, NIC_Code_algo, Description Token Count, Company Description Token Count, Job Description Token Count, nic_code_2_2008, Minimum Salary, Maximum Salary, Mean Salary, Unit of Measure, skills, standardized_skills, similarity_scores

**FR4:** System shall validate CSV format and required columns before processing, returning validation errors if format is incorrect

**FR5:** System shall process CSV files in batches (500-1000 records per batch) with progress tracking

#### Embedding Generation
**FR6:** System shall generate fresh embeddings during ingestion (ignoring pre-existing CSV embeddings) using Hugging Face `all-MiniLM-L6-v2` model (384-dimensional) for:
- Job fields: Job Description (primary), Description (fallback)
- Skill fields: DESCRIPTION (primary), WIKI_EXTRACT (secondary)
- Company fields: Company Description

**FR7:** System shall batch embedding generation (32-64 texts per API call) for efficiency

**FR8:** System shall store generated embeddings as node properties in Neo4j for vector search

#### Knowledge Graph Construction (Neo4j)
**FR9:** System shall create Neo4j knowledge graph with node types:
- Job (Job Title, Salary, Description, Location, etc.)
- Skill (ID, NAME, LEVEL, CATEGORY, DESCRIPTION)
- Company (Company Name, Description, CIN, NIC codes)
- Location (Location name, District)
- Category (CATEGORY_NAME)
- Subcategory (SUBCATEGORY_NAME)

**FR10:** System shall create relationships in Neo4j:
- Job -[REQUIRES]-> Skill (matched via standardized_skills → NAME with normalized string matching)
- Job -[POSTED_BY]-> Company
- Job -[LOCATED_IN]-> Location
- Skill -[BELONGS_TO_CATEGORY]-> Category
- Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory
- Skill -[SIMILAR_TO]-> Skill (compute top 5 most similar skills per skill using cosine similarity >0.7 threshold on embeddings)

**FR11:** System shall support upsert mode for incremental updates (match by Job ID or Skill ID), updating existing node properties and replacing all relationships (delete existing relationships, create new ones from updated CSV data)

**FR12:** System shall create Neo4j vector indexes on Job.embeddings, Skill.embeddings, and Company.embeddings for fast similarity search

#### Query Pipeline (FastAPI + LangGraph)
**FR13:** System shall expose FastAPI endpoint `/query` accepting natural language queries and returning AI-generated responses

**FR14:** System shall implement LangGraph workflow with nodes:
1. **Query Understanding** - Classify query intent (skill requirement, career path, salary analysis, skill relationship, company query) and generate query embedding
2. **Vector Search** - Find top-k similar nodes using Neo4j vector indexes (cosine similarity)
3. **Graph Traversal** - Explore relationships from vector results using Cypher queries (2-3 hops)
4. **Context Construction** - Combine vector results + graph context into structured prompt
5. **Response Generation** - Call OpenRouter LLM (`meta-llama/llama-3.3-8b-instruct:free`) with context

**FR15:** System shall perform hybrid search:
- Vector similarity search on embeddings (top 10-20 nodes)
- Graph traversal from matched nodes to explore relationships
- Combine results into retrieval context for LLM

**FR16:** System shall use Cypher queries for graph traversal based on query type (from FR14 intent classification):
- Skill requirements: Job -[REQUIRES]-> Skill relationships
- Career paths: Skill -[SIMILAR_TO]-> Skill, Job -[REQUIRES]-> Skill chains
- Salary analysis: Job salary properties + Skill relationships
- Company queries: Job -[POSTED_BY]-> Company + Skill relationships

**FR17:** System shall maintain basic conversation state within user session (chat history)

**FR18:** System shall extract key entities from user queries (skills, job titles, companies, locations, salary ranges) using LLM-based entity extraction to guide hybrid search

**FR19:** System shall support query types:
- Skill requirement queries ("What skills for X job?")
- Career path queries ("How to transition from X to Y?")
- Salary analysis queries ("High-paying jobs with X skills?")
- Skill relationship queries ("What skills are similar to X?")
- Company-based queries ("What companies hire for X skills?")

**FR20:** System shall implement retrieval context construction by combining matched nodes (Jobs, Skills, Companies), node properties (descriptions, salaries, levels), relationship types and properties, and graph structure context (skill categories, subcategories)

**FR21:** System shall pass structured retrieval context to OpenRouter LLM with prompt template instructing model to answer query, cite specific nodes/relationships used, explain reasoning based on graph structure, and highlight non-obvious connections discovered through graph traversal

**FR22:** System shall log query performance metrics (vector search time, graph traversal time, LLM generation time, total response time) for optimization analysis

#### Frontend (React)
**FR23:** System shall provide React frontend with login/registration pages

**FR24:** System shall provide CSV upload interface with drag-and-drop for skills and jobs files

**FR25:** System shall display ingestion progress with records processed/failed counts

**FR26:** System shall provide chat interface for natural language queries

**FR27:** System shall display LLM responses in chat format with message history

#### System Health
**FR28:** System shall expose `/health` endpoint for health checks

### Non-Functional Requirements

**NFR1:** Query response time shall be <5 seconds for typical natural language queries

**NFR2:** CSV ingestion processing time shall be ~5-10 minutes for 50K records

**NFR3:** System shall support 10+ concurrent users during MVP testing

**NFR4:** System shall use environment variable configuration via `.env` file for:
- `NEO4J_URI` - Cloud Neo4j connection string
- `NEO4J_USERNAME` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `DATABASE_URL` - PostgreSQL connection string for Prisma
- `OPENROUTER_API_KEY` - OpenRouter API key
- `OPENROUTER_MODEL` - LLM model (`meta-llama/llama-3.3-8b-instruct:free`)
- `EMBEDDING_MODEL` - Embedding model (`all-MiniLM-L6-v2`)
- `JWT_SECRET` - JWT token secret

**NFR5:** System shall be deployable locally with React frontend and FastAPI backend connecting to cloud databases (Neo4j + PostgreSQL)

**NFR6:** System shall support modern browsers (Chrome, Firefox, Safari, Edge)

**NFR7:** PostgreSQL schema shall be managed through Prisma migrations

**NFR8:** System shall use free-tier OpenRouter model to minimize costs

**NFR9:** System shall achieve 100% ingestion success rate for valid CSV records (properly formatted data)

**NFR10:** System shall handle embedding API failures gracefully with retry logic (max 3 retries with exponential backoff: 1s, 2s, 4s) and error reporting to prevent full ingestion pipeline failures

---

## User Interface Design Goals

### Overall UX Vision

The system shall provide a clean, minimal chat interface that prioritizes conversational interaction over complex UI elements. The primary user journey is: login → upload CSV data (one-time setup) → ask questions in natural language → receive intelligent responses. The interface should feel like talking to a knowledgeable career advisor rather than querying a database. Simplicity and clarity are paramount—users should be able to accomplish all tasks without training or documentation.

### Key Interaction Paradigms

**Conversational-First Design**: The chat interface is the primary interaction model. Users type questions in plain English and receive contextual responses with citations from the knowledge graph. The system should minimize UI chrome and maximize conversation space.

**Progressive Disclosure**: Advanced features (CSV upload, ingestion progress) are accessible but not prominent. The default view is the chat interface—data management is secondary.

**Instant Feedback**: All operations (login, file upload, query submission) provide immediate visual feedback. Ingestion shows real-time progress with records processed/failed counts. Chat messages show typing indicators during LLM response generation.

### Core Screens and Views

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

### Accessibility

**Level**: None (MVP does not require WCAG compliance)

For post-MVP, consider WCAG AA compliance for:
- Keyboard navigation support
- Screen reader compatibility for chat messages
- Color contrast requirements
- Focus indicators

### Branding

**Style**: Clean, minimal, professional interface with focus on readability and usability over visual flair.

**Design Approach**: Use TailwindCSS or Material-UI default components with minimal customization. Prioritize functional clarity over branding elements.

**Color Palette**: Standard neutral colors (grays for backgrounds, blue for primary actions, red for errors, green for success states). No custom brand colors required for MVP.

### Target Platforms

**Primary**: Web Responsive (desktop browsers: Chrome, Firefox, Safari, Edge)

**Secondary**: Mobile-friendly layout (responsive design, but not optimized for mobile-first interaction)

**Not Supported**: Native mobile apps, tablet-specific layouts, legacy browsers (IE11)

---

## Technical Assumptions

### Repository Structure

**Structure**: Monorepo

The project shall use a monolithic repository structure with clear separation of concerns:

```
/
├── frontend/          # React application
├── backend/           # FastAPI application
│   ├── api/          # API endpoints
│   ├── agents/       # LangGraph agents
│   ├── services/     # Business logic (ingestion, query)
│   └── models/       # Data models
├── data/             # Sample CSV files
├── docker-compose.yml
├── .env.example
└── README.md
```

**Rationale**: Monorepo simplifies development for single developer, enables shared configuration, and ensures version consistency between frontend and backend.

### Service Architecture

**Architecture**: Monolithic API (FastAPI) - No microservices for MVP

The system shall use a single FastAPI application handling all backend logic:
- CSV ingestion endpoints
- Authentication endpoints
- Query processing endpoints
- Direct Neo4j connection from backend (no ORM complexity)
- Stateless API design (JWT for auth, no session storage)

**Rationale**: Microservices add unnecessary complexity for MVP scope. Monolithic architecture is faster to develop, easier to debug, and sufficient for 10+ concurrent users.

### Testing Requirements

**Testing Level**: Unit testing for core business logic + Manual testing for UI/integration

The system shall include:
- Unit tests for CSV validation logic
- Unit tests for embedding generation
- Unit tests for graph construction logic
- Unit tests for LangGraph agent workflows
- Manual testing for frontend UI interactions
- Manual testing for end-to-end query workflows

**Not Required for MVP**:
- E2E automated testing
- Integration test automation
- Load testing
- Security testing

**Rationale**: Manual testing is acceptable for internal MVP with single developer. Automated testing infrastructure adds significant development overhead.

### Additional Technical Assumptions and Requests

**Frontend**:
- **Framework**: React with functional components and hooks
- **Styling**: TailwindCSS or Material-UI (simple, clean chat interface)
- **State Management**: React Context API or Zustand (lightweight, no Redux)
- **HTTP Client**: Axios or Fetch API for backend communication

**Backend**:
- **Framework**: FastAPI (Python)
- **LLM Orchestration**: LangGraph for agent workflows
- **LLM Provider**: OpenRouter API with `meta-llama/llama-3.3-8b-instruct:free` model
- **Embeddings**: Hugging Face `all-MiniLM-L6-v2` model (384-dimensional)
- **Authentication**: JWT tokens with PyJWT library
- **Database ORM**: Prisma for PostgreSQL (user management)
- **Neo4j Driver**: Official Neo4j Python driver

**Databases**:
- **Graph Database**: Neo4j (cloud-hosted via connection URI from .env)
- **Relational Database**: PostgreSQL (cloud-hosted for user accounts via Prisma)
- **Vector Storage**: Neo4j vector indexes (native support for embeddings, no separate vector DB)

**Infrastructure**:
- **Deployment**: Local development environment (React dev server + FastAPI uvicorn)
- **Neo4j**: Cloud-hosted (Aura or other cloud provider) via connection URI
- **PostgreSQL**: Cloud-hosted via connection URI
- **No Docker required**: All services accessed via cloud URIs
- **Environment Management**: `.env` files for configuration

**Integration Requirements**:
- OpenRouter API for LLM responses (unified gateway to multiple models)
- Hugging Face Transformers for embedding generation (can run locally or via API)
- Neo4j cloud connection via official driver
- PostgreSQL cloud connection via Prisma

**Security/Compliance**:
- Basic JWT authentication (not production-grade)
- Password hashing with bcrypt
- No encryption at rest (cloud provider responsibility)
- No HTTPS required for local development
- Environment variables for secrets (`.env` file, not committed to git)
- **Internal project only - minimal security hardening acceptable**

**Performance Optimization**:
- Batch embedding generation (32-64 texts per API call)
- Batch Neo4j transactions (commit every 500-1000 records)
- Neo4j vector indexes for fast similarity search
- Connection pooling for Neo4j and PostgreSQL
- No caching layer required for MVP

**Development Workflow**:
- Git for version control
- Feature branches for development
- `.env.example` file for configuration template
- Comprehensive README with setup instructions
- Inline code documentation for complex logic
- No CI/CD pipeline required for MVP

---

## Epic List

The following epics represent the sequential delivery of the Graph RAG System. Each epic delivers end-to-end, deployable functionality that builds upon previous work.

**Epic 1: Foundation & Authentication**
Establish project infrastructure, repository structure, environment configuration, and user authentication system. Delivers a working application with login/registration capability and database connectivity.

**Epic 2: CSV Ingestion Pipeline**
Build the data ingestion system that validates, processes, and stores CSV data. Delivers the ability to upload skills and jobs CSVs with validation, progress tracking, and error handling.

**Epic 3: Knowledge Graph Construction**
Create the Neo4j graph database schema, implement embedding generation, and construct the knowledge graph with all node types and relationships. Delivers a fully populated graph database ready for querying.

**Epic 4: Query Pipeline & LangGraph**
Implement the LangGraph-based query orchestration system with hybrid search (vector + graph traversal) and LLM response generation. Delivers the core RAG functionality.

**Epic 5: Chat Interface & Integration**
Build the React chat interface and integrate all components into a complete end-to-end system. Delivers the full MVP user experience with conversational career intelligence.

---

**Rationale:**

**Why this epic structure:**
- **Epic 1** establishes foundational infrastructure (database connections, auth) while delivering immediate user value (login works)
- **Epic 2** focuses on data ingestion without query complexity—enables testing graph construction independently
- **Epic 3** builds the graph database—can be validated visually in Neo4j browser before query implementation
- **Epic 4** implements the core RAG intelligence—can be tested via API before UI integration
- **Epic 5** completes the user experience—ties everything together into cohesive application

**Sequential dependencies:**
- Epic 2 depends on Epic 1 (need auth + DB setup)
- Epic 3 depends on Epic 2 (need ingested data to build graph)
- Epic 4 depends on Epic 3 (need populated graph to query)
- Epic 5 depends on Epic 4 (need working query API for chat interface)

**Alternative considered:** Could combine Epics 2+3 into single "Data Ingestion & Graph" epic, but separating allows for clearer testing boundaries—validate ingestion logic separately from graph construction logic.

---

## Epic 1: Foundation & Authentication

**Epic Goal**: Establish the foundational project structure, development environment, database connections, and user authentication system. By the end of this epic, developers can run the application locally, users can register and login, and the system successfully connects to both PostgreSQL and Neo4j cloud databases.

### Story 1.1: Project Setup & Repository Structure

**As a** developer
**I want** a properly structured monorepo with frontend and backend scaffolding
**so that** I can start building features with clear separation of concerns

#### Acceptance Criteria

1. Repository created with folder structure: `frontend/`, `backend/`, `data/`, `.env.example`, `README.md`
2. Backend folder contains subfolders: `api/`, `agents/`, `services/`, `models/`
3. Frontend initialized with React (using Vite or Create React App)
4. Backend initialized with FastAPI project structure
5. `.gitignore` properly configured to exclude `.env`, `node_modules/`, `__pycache__/`, `.venv/`
6. `README.md` includes project overview and setup instructions placeholder
7. `.env.example` includes all required environment variables with descriptions

### Story 1.2: Environment Configuration & Dependencies

**As a** developer
**I want** environment variables properly configured and dependencies installed
**so that** the application can connect to external services

#### Acceptance Criteria

1. `.env.example` file created with all required variables:
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
   - `DATABASE_URL` (PostgreSQL connection string)
   - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
   - `EMBEDDING_MODEL`, `JWT_SECRET`
2. Backend `requirements.txt` or `pyproject.toml` includes: FastAPI, uvicorn, neo4j-driver, prisma, PyJWT, bcrypt, sentence-transformers, langgraph
3. Frontend `package.json` includes: React, Axios (or fetch), TailwindCSS or Material-UI, React Router
4. Developer can copy `.env.example` to `.env`, fill in credentials, and run the application
5. Documentation added to README explaining each environment variable

### Story 1.3: Database Connection Setup

**As a** developer
**I want** the backend to successfully connect to both PostgreSQL and Neo4j
**so that** I can verify database connectivity before implementing features

#### Acceptance Criteria

1. Neo4j Python driver initialized with connection URI from `.env`
2. Neo4j connection verified with test query (e.g., `RETURN 1`)
3. Prisma schema file created with User model (id, email, password_hash, created_at)
4. Prisma migrations initialized and applied to PostgreSQL
5. PostgreSQL connection verified via Prisma client
6. `/health` endpoint created that checks Neo4j and PostgreSQL connectivity
7. `/health` endpoint returns JSON with status of each database (connected/disconnected)
8. Error handling implemented for database connection failures with clear error messages

### Story 1.4: User Registration API

**As a** new user
**I want** to register an account with email and password
**so that** I can access the system

#### Acceptance Criteria

1. `POST /auth/register` endpoint created accepting `{email, password}`
2. Email validation: must be valid email format
3. Password validation: minimum 8 characters
4. Password hashed using bcrypt before storing in database
5. User record created in PostgreSQL via Prisma
6. Duplicate email registration returns 400 error with message "Email already exists"
7. Successful registration returns 201 with success message
8. Unit tests written for email validation, password hashing, duplicate detection

### Story 1.5: User Login & JWT Generation

**As a** registered user
**I want** to login with my credentials and receive a JWT token
**so that** I can authenticate subsequent requests

#### Acceptance Criteria

1. `POST /auth/login` endpoint created accepting `{email, password}`
2. Email lookup in PostgreSQL via Prisma
3. Password verification using bcrypt compare
4. JWT token generated with payload: `{user_id, email, exp}` (expires in 24 hours)
5. Successful login returns 200 with `{token, user: {id, email}}`
6. Invalid credentials return 401 with message "Invalid email or password"
7. Non-existent email returns 401 (same message to prevent email enumeration)
8. JWT secret loaded from `.env` file
9. Unit tests written for login flow (success case, invalid password, non-existent user)

### Story 1.6: JWT Authentication Middleware

**As a** developer
**I want** protected endpoints to verify JWT tokens
**so that** only authenticated users can access restricted resources

#### Acceptance Criteria

1. JWT verification middleware created for FastAPI
2. Middleware extracts token from `Authorization: Bearer <token>` header
3. Middleware verifies token signature and expiration
4. Valid token: request continues with user info attached to request context
5. Missing token: returns 401 with message "Authentication required"
6. Invalid token: returns 401 with message "Invalid token"
7. Expired token: returns 401 with message "Token expired"
8. `/health` endpoint remains public (no auth required)
9. Unit tests written for middleware (valid token, invalid token, expired token, missing token)

### Story 1.7: Basic Frontend Login & Registration UI

**As a** user
**I want** a simple login and registration interface
**so that** I can access the application

#### Acceptance Criteria

1. React Router configured with routes: `/login`, `/register`, `/chat` (protected)
2. Login page created with email and password input fields
3. Registration page created with email and password input fields
4. Form validation on frontend (email format, password min length)
5. Login form calls `POST /auth/login` and stores JWT token in localStorage
6. Registration form calls `POST /auth/register` and redirects to login on success
7. Error messages displayed for invalid credentials or registration failures
8. Protected routes redirect to `/login` if no valid token in localStorage
9. Successful login redirects to `/chat` (placeholder page for now)
10. Clean, minimal UI using TailwindCSS or Material-UI components

---

## Epic 2: CSV Ingestion Pipeline

**Epic Goal**: Build a robust CSV ingestion system that accepts skills and jobs taxonomy files, validates their format and content, processes them in batches with real-time progress tracking, and stores the raw data ready for graph construction. By the end of this epic, users can upload CSV files through the UI and see them successfully validated and stored.

### Story 2.1: CSV Upload API Endpoints

**As a** developer
**I want** FastAPI endpoints for CSV file uploads
**so that** frontend can send CSV files to the backend

#### Acceptance Criteria

1. `POST /ingest/skills` endpoint created (protected by JWT middleware)
2. `POST /ingest/jobs` endpoint created (protected by JWT middleware)
3. Endpoints accept `multipart/form-data` with file field named `file`
4. File size limit enforced (e.g., 100MB max)
5. File type validation: only `.csv` files accepted
6. Invalid file type returns 400 with message "Only CSV files are allowed"
7. File too large returns 413 with message "File size exceeds 100MB limit"
8. Successful upload returns 202 (Accepted) with `{ingestion_job_id, status: "pending"}`
9. Ingestion job ID stored in PostgreSQL with user_id, filename, status, created_at

### Story 2.2: CSV Validation Logic

**As a** user
**I want** my CSV files validated before ingestion starts
**so that** I get immediate feedback on formatting issues

#### Acceptance Criteria

1. CSV parser validates file can be read (not corrupted)
2. Skills CSV validation: Check for required columns (ID, NAME, DESCRIPTION, CATEGORY, SUBCATEGORY)
3. Jobs CSV validation: Check for required columns (Job ID, Job Title, Company Name, Location, standardized_skills)
4. Column name matching is case-insensitive
5. Validation checks for minimum 1 data row (not just headers)
6. Missing required columns returns 400 with list of missing column names
7. Empty CSV (header only) returns 400 with message "CSV file contains no data rows"
8. Validation successful: proceed to row preview
9. Unit tests written for validation logic (valid CSV, missing columns, empty CSV, corrupted file)

### Story 2.3: CSV Preview & Confirmation

**As a** user
**I want** to preview the first few rows of my CSV before confirming ingestion
**so that** I can verify the data looks correct

#### Acceptance Criteria

1. After validation passes, extract first 5-10 rows from CSV
2. Return preview data to frontend: `{columns: [...], preview_rows: [...], total_rows: N}`
3. Preview includes column names and sample values
4. Row count calculated and returned (e.g., "40,523 jobs found")
5. Frontend displays preview in table format
6. Frontend provides "Confirm Upload" and "Cancel" buttons
7. Cancel button discards uploaded file, no data stored
8. Confirm button triggers actual ingestion process

### Story 2.4: Batch Processing Engine

**As a** system
**I want** to process large CSV files in batches
**so that** memory usage stays within bounds and progress can be tracked

#### Acceptance Criteria

1. CSV processing split into batches of 500-1000 records
2. Batch size configurable via `.env` variable `BATCH_SIZE` (default: 1000)
3. Each batch processed sequentially (not parallel to avoid DB contention)
4. Batch processing tracks: records_processed, records_failed, current_batch, total_batches
5. Failed records logged with row number and error message
6. Processing continues after batch failures (does not halt entire ingestion)
7. Ingestion status updated in PostgreSQL after each batch: `{records_processed, records_failed, status: "processing"}`
8. Final status set to "completed" or "completed_with_errors" based on failure count

### Story 2.5: Real-Time Progress Tracking

**As a** user
**I want** to see real-time progress while my CSV is being ingested
**so that** I know the system is working and how long it will take

#### Acceptance Criteria

1. `/ingest/status/{job_id}` endpoint created (protected)
2. Endpoint returns JSON: `{status, records_processed, records_failed, total_records, estimated_time_remaining}`
3. Frontend polls `/ingest/status/{job_id}` every 2 seconds during ingestion
4. Progress bar displays percentage: `(records_processed / total_records) * 100`
5. Display stats: "Processing 15,234 / 40,523 records (5 failed)"
6. Estimated time remaining calculated based on average processing speed
7. Status values: "pending", "processing", "completed", "completed_with_errors", "failed"
8. When status = "completed", polling stops and success message shown

### Story 2.6: Error Handling & Logging

**As a** user
**I want** detailed error logs when ingestion fails
**so that** I can fix data issues and retry

#### Acceptance Criteria

1. Failed records logged to PostgreSQL table: `ingestion_errors` (job_id, row_number, error_message, raw_data)
2. Common errors logged: missing required field, invalid data type, parsing error
3. Error log downloadable via `/ingest/errors/{job_id}` endpoint (returns CSV)
4. Error CSV format: `row_number,error_message,raw_data`
5. Frontend provides "Download Error Log" button when `records_failed > 0`
6. System-level errors (DB connection failures, API failures) return 500 with clear message
7. Partial ingestion success: Display "40,518 / 40,523 records ingested successfully (5 failed). Download error log to review failures."

### Story 2.7: Frontend CSV Upload UI

**As a** user
**I want** a simple drag-and-drop interface to upload CSV files
**so that** I can easily ingest data into the system

#### Acceptance Criteria

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

## Epic 3: Knowledge Graph Construction

**Epic Goal**: Transform ingested CSV data into a rich Neo4j knowledge graph with semantic embeddings, node relationships, and vector indexes. By the end of this epic, the system has a fully populated graph database with Job, Skill, Company, Location, Category, and Subcategory nodes, all relationships established, and vector indexes ready for similarity search.

### Story 3.1: Embedding Generation Service

**As a** system
**I want** to generate embeddings for text fields using Hugging Face model
**so that** I can perform semantic similarity search

#### Acceptance Criteria

1. Embedding service created using `sentence-transformers` library with `all-MiniLM-L6-v2` model
2. Service loads model once on startup (singleton pattern)
3. Method `generate_embeddings(texts: List[str]) -> List[List[float]]` created
4. Batch processing: accepts 32-64 texts per call
5. Returns 384-dimensional embeddings (one vector per text)
6. Empty or None texts return zero vector [0.0] * 384
7. Embedding generation retries on failure (max 3 retries, exponential backoff: 1s, 2s, 4s)
8. Unit tests written (single text, batch texts, empty text, retry logic)

### Story 3.2: Skills Graph Construction

**As a** system
**I want** to create Skill, Category, and Subcategory nodes in Neo4j from skills CSV
**so that** the skills taxonomy is represented in the graph

#### Acceptance Criteria

1. For each skill row: Generate embedding from DESCRIPTION field (primary) or WIKI_EXTRACT (secondary if DESCRIPTION empty)
2. Create `Skill` node with properties: ID, NAME, LEVEL, TYPE, IS_SOFTWARE, IS_LANGUAGE, DESCRIPTION, WIKI_LINK, WIKI_EXTRACT, embedding
3. Create `Category` node with properties: CATEGORY (ID), CATEGORY_NAME (upsert by CATEGORY ID)
4. Create `Subcategory` node with properties: SUBCATEGORY (ID), SUBCATEGORY_NAME (upsert by SUBCATEGORY ID)
5. Create relationship: `Skill -[BELONGS_TO_CATEGORY]-> Category`
6. Create relationship: `Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory`
7. Create relationship: `Category -[CONTAINS]-> Subcategory`
8. Use batch transactions (commit every 1000 nodes)
9. Node creation uses MERGE (upsert) to avoid duplicates on re-ingestion

### Story 3.3: Skill Similarity Relationships

**As a** system
**I want** to compute and store skill-to-skill similarity relationships
**so that** users can discover related skills

#### Acceptance Criteria

1. For each Skill node: compute cosine similarity with all other Skill embeddings
2. Keep top 5 most similar skills with similarity > 0.7 threshold
3. Create relationship: `Skill -[SIMILAR_TO {similarity_score}]-> Skill`
4. Similarity score stored as relationship property (float 0.0-1.0)
5. Similarity computation batched (process 100 skills at a time to avoid memory issues)
6. Skip self-similarity (Skill should not link to itself)
7. Bidirectional relationships: If Skill A similar to Skill B, create both A->B and B->A
8. Progress logged: "Computing similarities for skills 1000/10523"

### Story 3.4: Jobs Graph Construction

**As a** system
**I want** to create Job, Company, and Location nodes from jobs CSV
**so that** job market data is represented in the graph

#### Acceptance Criteria

1. For each job row: Generate embedding from Job Description field (primary) or Description (fallback if Job Description empty)
2. Create `Job` node with ALL 30 CSV fields as properties (Job Title, Salary, Posted At, Description, Job ID, CIN, NCO_Code_algo, Minimum Salary, Maximum Salary, Mean Salary, etc.)
3. Create `Company` node with properties: Company Name, CIN, CompanyIndustrialClassification, NIC codes, Company Description, company_embedding (upsert by Company Name)
4. Company embedding generated from Company Description field
5. Create `Location` node with properties: Location name, District (upsert by Location name)
6. Create relationship: `Job -[POSTED_BY]-> Company`
7. Create relationship: `Job -[LOCATED_IN]-> Location`
8. Use batch transactions (commit every 1000 nodes)
9. Handle missing fields gracefully (store as NULL in Neo4j)

### Story 3.5: Job-Skill Relationships

**As a** system
**I want** to link jobs to required skills using standardized_skills field
**so that** I can query which skills are needed for specific jobs

#### Acceptance Criteria

1. Parse `standardized_skills` field from jobs CSV (comma-separated list or JSON array)
2. For each skill name in list: normalize (lowercase, trim whitespace)
3. Match against existing Skill nodes using: `WHERE toLower(s.NAME) = normalized_skill_name`
4. Create relationship: `Job -[REQUIRES {similarity_score}]-> Skill`
5. If `similarity_scores` field exists in CSV and aligns with standardized_skills (same length/order), store as relationship property
6. Log unmatched skills: "Skill 'Machine Lerning' from Job 12345 not found in Skills taxonomy"
7. For unmatched skills: Create orphan Skill node with only NAME property (no metadata, no embedding)
8. Orphan skills logged to separate table for data quality review
9. Batch relationship creation (commit every 1000 relationships)

### Story 3.6: Neo4j Vector Indexes

**As a** system
**I want** vector indexes created on embedding properties
**so that** similarity search queries are fast

#### Acceptance Criteria

1. Create vector index on `Skill.embedding` with cosine similarity metric
2. Create vector index on `Job.embedding` with cosine similarity metric
3. Create vector index on `Company.embedding` with cosine similarity metric
4. Index creation query: `CREATE VECTOR INDEX skill_embedding_index FOR (s:Skill) ON (s.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}`
5. Indexes created during initial setup (before first ingestion) or on-demand if missing
6. Index status verification: Query `SHOW INDEXES` to confirm indexes exist
7. Document index names in README for reference

### Story 3.7: Incremental Update & Upsert Logic

**As a** system
**I want** to handle weekly CSV re-uploads without duplicating data
**so that** users can update the graph with new data

#### Acceptance Criteria

1. Node creation uses MERGE instead of CREATE (upsert by unique ID: Job ID, Skill ID, Company Name)
2. On match: Update all node properties with new CSV values
3. Relationship handling: Delete existing relationships for updated nodes, create new ones from CSV
4. Example: If Job 123 previously required [Python, Java], new CSV says [Python, React], result is [Python, React]
5. Orphan relationship cleanup: Relationships to deleted nodes are automatically removed
6. Ingestion mode flag: "full" (delete all, recreate) vs "incremental" (upsert only)
7. Default mode: incremental (safer for production)
8. Full mode requires explicit confirmation to prevent accidental data loss

---

## Epic 4: Query Pipeline & LangGraph

**Epic Goal**: Implement the core RAG intelligence using LangGraph to orchestrate hybrid search (vector similarity + graph traversal) and generate LLM-powered responses. By the end of this epic, the system can accept natural language queries via API and return intelligent, context-aware answers backed by the knowledge graph.

### Story 4.1: LangGraph Workflow Setup

**As a** developer
**I want** a LangGraph state graph configured with all workflow nodes
**so that** I can orchestrate the query pipeline

#### Acceptance Criteria

1. LangGraph installed and imported (`langgraph` package)
2. State graph created with 5 nodes: QueryUnderstanding, VectorSearch, GraphTraversal, ContextConstruction, ResponseGeneration
3. Graph state schema defined: `{user_query, query_embedding, query_intent, vector_results, graph_results, context, response}`
4. Node execution order: QueryUnderstanding → VectorSearch → GraphTraversal → ContextConstruction → ResponseGeneration
5. Each node implemented as async function accepting state and returning updated state
6. Graph compiled and ready for invocation
7. Basic end-to-end test: Pass dummy query through graph, verify all nodes execute

### Story 4.2: Query Understanding Node

**As a** system
**I want** to classify user query intent and generate query embedding
**so that** I can route to appropriate search strategies

#### Acceptance Criteria

1. Node receives `user_query` from state
2. Generate query embedding using embedding service (same `all-MiniLM-L6-v2` model)
3. Classify query intent using simple keyword matching or LLM-based classification:
   - "skill requirement" - keywords: "what skills", "skills for", "skills needed"
   - "career path" - keywords: "transition", "career path", "how to become"
   - "salary analysis" - keywords: "salary", "pay", "compensation", "high-paying"
   - "skill relationship" - keywords: "similar to", "related skills", "alternatives"
   - "company query" - keywords: "companies", "employers", "who hires"
4. Default intent: "general" if no clear match
5. Update state: `{query_embedding: [...], query_intent: "skill_requirement"}`
6. Log query understanding results for debugging
7. Unit tests for each intent classification

### Story 4.3: Vector Search Node

**As a** system
**I want** to find semantically similar nodes using vector search
**so that** I retrieve relevant starting points for graph traversal

#### Acceptance Criteria

1. Node receives `query_embedding` from state
2. Execute Neo4j vector search on Job.embedding, Skill.embedding, Company.embedding indexes
3. Use Cypher query: `CALL db.index.vector.queryNodes('skill_embedding_index', 15, $query_embedding) YIELD node, score`
4. Retrieve top 15 most similar nodes across all node types (configurable via param)
5. Filter results by similarity score > 0.5 (configurable threshold)
6. Return results with node properties and similarity scores
7. Update state: `{vector_results: [{node_type, node_id, properties, score}, ...]}`
8. Handle empty results gracefully (no similar nodes found)

### Story 4.4: Graph Traversal Node

**As a** system
**I want** to explore relationships from vector search results
**so that** I can retrieve rich contextual information

#### Acceptance Criteria

1. Node receives `vector_results` and `query_intent` from state
2. Generate Cypher query based on intent:
   - **skill_requirement**: Start from Job nodes, traverse `Job -[REQUIRES]-> Skill`, include skill categories
   - **career_path**: Start from Skill nodes, traverse `Skill -[SIMILAR_TO]-> Skill` and `Skill <-[REQUIRES]- Job`
   - **salary_analysis**: Start from Job nodes, include salary properties, traverse to Skills and Companies
   - **skill_relationship**: Start from Skill nodes, traverse `Skill -[SIMILAR_TO]-> Skill` and categories
   - **company_query**: Start from Company or Job nodes, traverse `Job -[POSTED_BY]-> Company` and `Job -[REQUIRES]-> Skill`
3. Traversal depth: 2-3 hops from seed nodes (configurable)
4. Collect all traversed nodes and relationships
5. Return structured graph context: `{nodes: [...], relationships: [...]}`
6. Update state: `{graph_results: {nodes, relationships}}`
7. Limit total nodes returned to prevent context overflow (max 50 nodes)

### Story 4.5: Context Construction Node

**As a** system
**I want** to combine vector and graph results into structured LLM context
**so that** the LLM has all necessary information to answer the query

#### Acceptance Criteria

1. Node receives `vector_results`, `graph_results`, `user_query` from state
2. Construct context string with sections:
   - **User Query**: Original question
   - **Top Matching Nodes**: Vector search results with scores
   - **Related Information**: Graph traversal results (nodes + relationships)
   - **Graph Structure**: Key relationships discovered (e.g., "Python is required by 1,234 jobs")
3. Format as structured text or JSON for LLM consumption
4. Token counting: Ensure context stays within 4000 tokens for free model
5. If context exceeds limit: Truncate graph results (keep highest-scoring nodes)
6. Include source citations: Node IDs and types for traceability
7. Update state: `{context: "...formatted context..."}`
8. Log context size and truncation events

### Story 4.6: Response Generation Node

**As a** system
**I want** to generate natural language responses using OpenRouter LLM
**so that** users receive intelligent, conversational answers

#### Acceptance Criteria

1. Node receives `context` and `user_query` from state
2. Construct LLM prompt with instructions:
   - "Answer the user's question based on the knowledge graph context provided"
   - "Cite specific nodes and relationships from the graph in your answer"
   - "Explain reasoning based on graph structure"
   - "Highlight non-obvious connections discovered through graph traversal"
3. Call OpenRouter API with model `meta-llama/llama-3.3-8b-instruct:free`
4. Request parameters: `{temperature: 0.7, max_tokens: 500}`
5. Parse LLM response and extract answer text
6. Update state: `{response: "...LLM generated answer..."}`
7. Handle API failures: Retry with exponential backoff (max 3 retries: 1s, 2s, 4s)
8. If all retries fail: Return error message "Unable to generate response. Please try again."
9. Log LLM API calls (query, response, latency) for debugging

### Story 4.7: Query API Endpoint

**As a** user
**I want** to send natural language queries to the backend
**so that** I can get answers powered by the knowledge graph

#### Acceptance Criteria

1. `POST /query` endpoint created (protected by JWT middleware)
2. Accepts JSON: `{query: "What skills do I need for Data Scientist roles?"}`
3. Invokes LangGraph workflow with user query
4. Returns JSON: `{query, response, sources: [{node_type, node_id, properties}], processing_time_ms}`
5. Processing time logged (total time from request to response)
6. Sources include all nodes/relationships cited in response
7. Error handling: Invalid query (empty string) returns 400
8. Error handling: LangGraph failures return 500 with error message
9. Query and response logged to PostgreSQL for analytics (user_id, query, response, timestamp)
10. Unit tests and integration tests for endpoint (valid query, empty query, malformed JSON)

### Story 4.8: Query Performance Metrics

**As a** developer
**I want** detailed performance metrics for each query
**so that** I can identify bottlenecks and optimize

#### Acceptance Criteria

1. Instrument each LangGraph node with timing
2. Log metrics: `{query_understanding_time, vector_search_time, graph_traversal_time, context_construction_time, llm_generation_time, total_time}`
3. Metrics logged to application logs (JSON format for parsing)
4. Optional: Store metrics in PostgreSQL table `query_metrics` for analysis
5. `/query` endpoint returns `processing_time_ms` in response
6. Performance targets verified: Vector search <1s, Graph traversal <2s, Total <5s
7. Alert if query exceeds 5 second threshold (log warning)

---

## Epic 5: Chat Interface & Integration

**Epic Goal**: Build the React chat interface and integrate all components into a complete, end-to-end conversational career intelligence system. By the end of this epic, users can login, upload CSV files, ask natural language questions in a chat interface, and receive intelligent responses backed by the knowledge graph.

### Story 5.1: Chat UI Components

**As a** user
**I want** a clean chat interface to interact with the system
**so that** I can ask questions naturally

#### Acceptance Criteria

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

### Story 5.2: Chat Backend Integration

**As a** frontend developer
**I want** the chat UI to call the query API and display responses
**so that** users see answers to their questions

#### Acceptance Criteria

1. When user sends message: Call `POST /query` with query text
2. Add user message to chat immediately (optimistic UI)
3. Show typing indicator while waiting for API response
4. On success: Add assistant message with LLM response
5. On error: Display error message in chat "Sorry, I couldn't process that. Please try again."
6. Include JWT token in Authorization header for authenticated requests
7. Handle API timeouts (>10 seconds): Display timeout message
8. Disable input field while query is processing (prevent multiple simultaneous queries)
9. Re-enable input field after response or error

### Story 5.3: Source Citations Display

**As a** user
**I want** to see which graph nodes were used to answer my question
**so that** I can verify the information source

#### Acceptance Criteria

1. Parse `sources` array from `/query` response
2. Display sources as expandable section below assistant message
3. Source format: "Based on 5 jobs, 3 skills, and 2 companies"
4. Expandable view shows node details: Node type, key properties (name, title, etc.)
5. Sources grouped by node type: Jobs, Skills, Companies
6. Click to expand/collapse source details
7. Clean formatting with clear visual hierarchy
8. Optional: Link to Neo4j browser for power users (not required for MVP)

### Story 5.4: Conversation State Management

**As a** user
**I want** my conversation history maintained during my session
**so that** I can refer back to previous questions and answers

#### Acceptance Criteria

1. Chat history stored in React state (array of messages)
2. Each message object: `{id, role: "user"|"assistant", content, timestamp, sources?}`
3. Message IDs generated (UUID or auto-increment)
4. Conversation persists during session (until page refresh or logout)
5. "Clear Chat" button to reset conversation
6. Optional: Store conversation in localStorage for persistence across page reloads
7. Optional: Save conversation to PostgreSQL for user history (deferred to post-MVP)

### Story 5.5: Navigation & Layout Integration

**As a** user
**I want** to easily navigate between chat, upload, and account pages
**so that** I can access all system features

#### Acceptance Criteria

1. Navigation bar with links: "Chat", "Upload Data", "Logout"
2. Navigation always visible at top of page
3. Active route highlighted in navigation
4. Logout clears JWT token from localStorage and redirects to `/login`
5. Clicking "Upload Data" navigates to `/upload` page (from Epic 2)
6. Clicking "Chat" navigates to `/chat` page
7. Responsive navigation: Works on mobile and desktop
8. Clean, consistent styling across all pages

### Story 5.6: End-to-End Integration Testing

**As a** developer
**I want** to verify the complete user journey works end-to-end
**so that** I can confidently deliver the MVP

#### Acceptance Criteria

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

### Story 5.7: Documentation & README

**As a** developer or user
**I want** comprehensive documentation to set up and use the system
**so that** I can run the application without assistance

#### Acceptance Criteria

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

### Story 5.8: MVP Polish & Final QA

**As a** product owner
**I want** the MVP to be polished and bug-free
**so that** it provides a professional user experience

#### Acceptance Criteria

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

## Next Steps

### UX Expert Prompt

The PRD for the **Graph RAG System for Skills & Jobs Knowledge Graph** is complete. Please review the **User Interface Design Goals** section and create detailed UI/UX specifications including:

1. **Wireframes** for all core screens (Login, Registration, CSV Upload, Chat Interface)
2. **Design system** components and styling guide (using TailwindCSS or Material-UI)
3. **User flow diagrams** for primary journeys (registration → upload → chat)
4. **Interaction patterns** for chat interface, file upload, progress tracking, and source citations
5. **Responsive design** considerations for desktop and mobile views
6. **Accessibility recommendations** for post-MVP WCAG AA compliance

Focus on creating a clean, minimal, conversational interface that prioritizes ease of use over visual complexity. The system should feel like talking to a knowledgeable career advisor, not querying a database.

### Architect Prompt

The PRD for the **Graph RAG System for Skills & Jobs Knowledge Graph** is complete. Please review the full document and create a comprehensive technical architecture document including:

1. **System Architecture Diagram** - High-level overview of frontend, backend, databases, and external services
2. **Data Flow Diagrams** - Ingestion pipeline and query pipeline workflows
3. **Database Schemas**:
   - PostgreSQL schema (Prisma models for User, IngestionJob, QueryHistory, etc.)
   - Neo4j graph schema (detailed node properties and relationship types with Cypher examples)
4. **API Specifications** - Detailed endpoint documentation (request/response schemas, status codes, error handling)
5. **LangGraph Workflow** - Detailed state graph diagram with node implementations and state transitions
6. **Deployment Architecture** - Local development setup and future cloud deployment strategy
7. **Technology Stack** - Complete dependency list with versions and justifications
8. **Code Structure** - Detailed folder/file organization for monorepo
9. **Implementation Plan** - Epic-by-epic breakdown with estimated effort and dependencies

Focus on creating a pragmatic, MVP-focused architecture that balances simplicity with extensibility. All technical decisions should support the goal of validating Graph RAG effectiveness for career intelligence.

**Key Priorities:**
- Monolithic architecture (no microservices)
- Cloud-hosted databases (Neo4j + PostgreSQL)
- Free-tier LLM model (`meta-llama/llama-3.3-8b-instruct:free`)
- Batch processing for CSV ingestion (40-50K records)
- Hybrid search (vector + graph traversal) with <5 second query response
- Minimal security (basic JWT auth, internal project)

---

**PRD Status**: ✅ Complete and Ready for Implementation

**Total Scope**:
- 5 Epics
- 38 User Stories
- 28 Functional Requirements
- 10 Non-Functional Requirements

**Estimated Implementation Timeline**: 6-8 weeks (single developer, full-time)

---

*PRD v1.1 - Created by John (PM Agent) - 2025-10-15*

