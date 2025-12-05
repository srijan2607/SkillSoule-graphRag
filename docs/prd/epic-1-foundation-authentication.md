# Epic 1: Foundation & Authentication

**Epic Goal**: Establish the foundational project structure, development environment, database connections, and user authentication system. By the end of this epic, developers can run the application locally, users can register and login, and the system successfully connects to both PostgreSQL and Neo4j cloud databases.

## Story 1.1: Project Setup & Repository Structure

**As a** developer
**I want** a properly structured monorepo with frontend and backend scaffolding
**so that** I can start building features with clear separation of concerns

### Acceptance Criteria

1. Repository created with folder structure: `frontend/`, `backend/`, `data/`, `.env.example`, `README.md`
2. Backend folder contains subfolders: `api/`, `agents/`, `services/`, `models/`
3. Frontend initialized with React (using Vite or Create React App)
4. Backend initialized with FastAPI project structure
5. `.gitignore` properly configured to exclude `.env`, `node_modules/`, `__pycache__/`, `.venv/`
6. `README.md` includes project overview and setup instructions placeholder
7. `.env.example` includes all required environment variables with descriptions

## Story 1.2: Environment Configuration & Dependencies

**As a** developer
**I want** environment variables properly configured and dependencies installed
**so that** the application can connect to external services

### Acceptance Criteria

1. `.env.example` file created with all required variables:
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
   - `DATABASE_URL` (PostgreSQL connection string)
   - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`
   - `EMBEDDING_MODEL`, `JWT_SECRET`
2. Backend `requirements.txt` or `pyproject.toml` includes: FastAPI, uvicorn, neo4j-driver, prisma, PyJWT, bcrypt, sentence-transformers, langgraph
3. Frontend `package.json` includes: React, Axios (or fetch), TailwindCSS or Material-UI, React Router
4. Developer can copy `.env.example` to `.env`, fill in credentials, and run the application
5. Documentation added to README explaining each environment variable

## Story 1.3: Database Connection Setup

**As a** developer
**I want** the backend to successfully connect to both PostgreSQL and Neo4j
**so that** I can verify database connectivity before implementing features

### Acceptance Criteria

1. Neo4j Python driver initialized with connection URI from `.env`
2. Neo4j connection verified with test query (e.g., `RETURN 1`)
3. Prisma schema file created with User model (id, email, password_hash, created_at)
4. Prisma migrations initialized and applied to PostgreSQL
5. PostgreSQL connection verified via Prisma client
6. `/health` endpoint created that checks Neo4j and PostgreSQL connectivity
7. `/health` endpoint returns JSON with status of each database (connected/disconnected)
8. Error handling implemented for database connection failures with clear error messages

## Story 1.4: User Registration API

**As a** new user
**I want** to register an account with email and password
**so that** I can access the system

### Acceptance Criteria

1. `POST /auth/register` endpoint created accepting `{email, password}`
2. Email validation: must be valid email format
3. Password validation: minimum 8 characters
4. Password hashed using bcrypt before storing in database
5. User record created in PostgreSQL via Prisma
6. Duplicate email registration returns 400 error with message "Email already exists"
7. Successful registration returns 201 with success message
8. Unit tests written for email validation, password hashing, duplicate detection

## Story 1.5: User Login & JWT Generation

**As a** registered user
**I want** to login with my credentials and receive a JWT token
**so that** I can authenticate subsequent requests

### Acceptance Criteria

1. `POST /auth/login` endpoint created accepting `{email, password}`
2. Email lookup in PostgreSQL via Prisma
3. Password verification using bcrypt compare
4. JWT token generated with payload: `{user_id, email, exp}` (expires in 24 hours)
5. Successful login returns 200 with `{token, user: {id, email}}`
6. Invalid credentials return 401 with message "Invalid email or password"
7. Non-existent email returns 401 (same message to prevent email enumeration)
8. JWT secret loaded from `.env` file
9. Unit tests written for login flow (success case, invalid password, non-existent user)

## Story 1.6: JWT Authentication Middleware

**As a** developer
**I want** protected endpoints to verify JWT tokens
**so that** only authenticated users can access restricted resources

### Acceptance Criteria

1. JWT verification middleware created for FastAPI
2. Middleware extracts token from `Authorization: Bearer <token>` header
3. Middleware verifies token signature and expiration
4. Valid token: request continues with user info attached to request context
5. Missing token: returns 401 with message "Authentication required"
6. Invalid token: returns 401 with message "Invalid token"
7. Expired token: returns 401 with message "Token expired"
8. `/health` endpoint remains public (no auth required)
9. Unit tests written for middleware (valid token, invalid token, expired token, missing token)

## Story 1.7: Basic Frontend Login & Registration UI

**As a** user
**I want** a simple login and registration interface
**so that** I can access the application

### Acceptance Criteria

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
