# Career Intelligence AI System - Comprehensive Architecture Documentation

**Document Version:** 2.0  
**Last Updated:** 2025-10-29  
**Status:** Production Implementation  
**Project Type:** GraphRAG System

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Component Architecture](#component-architecture)
4. [LangGraph RAG Pipeline](#langgraph-rag-pipeline)
5. [API Architecture](#api-architecture)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [Database Architecture](#database-architecture)
8. [Service Orchestration](#service-orchestration)
9. [Deployment Architecture](#deployment-architecture)
10. [Monitoring & Observability](#monitoring--observability)
11. [Security Architecture](#security-architecture)
12. [Performance Characteristics](#performance-characteristics)

---

## Executive Summary

### System Overview

The Career Intelligence AI System is a **GraphRAG (Graph-based Retrieval Augmented Generation)** application that provides natural language access to career intelligence through knowledge graph-powered conversational AI. The system combines Neo4j graph database, vector similarity search, and LLM-based response generation to answer complex queries about skills, jobs, and career paths.

### Key Architectural Characteristics

| Aspect | Implementation |
|--------|----------------|
| **Architecture Style** | Monolithic API (FastAPI) + SPA Frontend (React) |
| **Data Layer** | Hybrid: Neo4j (Knowledge Graph + Vector Search) + PostgreSQL (Relational) |
| **AI Orchestration** | LangGraph 5-node workflow |
| **LLM Provider** | OpenRouter (meta-llama/llama-3.3-8b-instruct:free) |
| **Embeddings** | HuggingFace (sentence-transformers/all-MiniLM-L6-v2, 384-dim) |
| **Authentication** | JWT-based stateless auth |
| **Deployment** | Local development (cloud-hosted databases) |

### Core Capabilities

1. **CSV Ingestion Pipeline** - Batch processing of 40-50K job records and 10K+ skill records with real-time progress tracking
2. **Knowledge Graph Construction** - Automated creation of nodes (Job, Skill, Company, Location, Category) and relationships (REQUIRES, SIMILAR_TO, POSTED_BY, BELONGS_TO_CATEGORY)
3. **Hybrid Search** - Vector similarity search (HNSW indexes) combined with graph traversal (Cypher queries)
4. **Multi-Intent Query Processing** - Handles complex queries with multiple intents (skill_requirement + salary_analysis)
5. **Conversational AI** - Session-based conversation history with 24-hour expiration
6. **Real-Time Monitoring** - WebSocket-based pipeline monitoring and Neo4j query logging

---

## System Architecture Overview

### High-Level System Diagram

```mermaid
graph TB
    subgraph "Frontend Layer - React SPA"
        UI[React Application<br/>Vite Dev Server<br/>Port 5173]
        
        subgraph "UI Components"
            LOGIN[Login/Register Pages]
            UPLOAD[CSV Upload Interface]
            CHAT[Chat Interface]
            MONITOR[Monitoring Dashboard]
        end
        
        UI --> LOGIN
        UI --> UPLOAD
        UI --> CHAT
        UI --> MONITOR
    end
    
    subgraph "API Layer - FastAPI"
        FASTAPI[FastAPI Application<br/>Uvicorn Server<br/>Port 8000]
        
        subgraph "Middleware Stack"
            CORS[CORS Middleware<br/>localhost:5173, 3000]
            RATELIMIT[SlowAPI Rate Limiter<br/>10 requests/minute]
            JWTAUTH[JWT Auth Middleware]
            ERRORHANDLER[Error Handlers]
        end
        
        subgraph "API Routers"
            AUTHAPI["/api/auth/*<br/>Login, Register"]
            INGESTAPI["/api/ingest/*<br/>CSV Upload, Status"]
            QUERYAPI["/api/query/*<br/>NL Query Processing"]
            ADMINAPI["/api/admin/*<br/>Admin Operations"]
            MONITORAPI["/api/monitor/*<br/>WebSocket Monitoring"]
        end
        
        FASTAPI --> CORS
        CORS --> RATELIMIT
        RATELIMIT --> JWTAUTH
        JWTAUTH --> ERRORHANDLER
        ERRORHANDLER --> AUTHAPI
        ERRORHANDLER --> INGESTAPI
        ERRORHANDLER --> QUERYAPI
        ERRORHANDLER --> ADMINAPI
        ERRORHANDLER --> MONITORAPI
    end
    
    subgraph "Service Layer"
        subgraph "Core Services"
            LANGGRAPH[LangGraph Service<br/>Workflow Orchestration]
            INGEST_SVC[Ingestion Service<br/>Batch Processing]
            AUTH_SVC[Auth Service<br/>JWT + bcrypt]
        end
        
        subgraph "AI Services"
            EMBEDDING[Embedding Service<br/>all-MiniLM-L6-v2<br/>384 dimensions]
            OPENROUTER[OpenRouter Service<br/>LLM API Client<br/>Circuit Breaker]
            INTENT[Intent Analysis<br/>Multi-layer Classification]
            ENTITY[Entity Extraction<br/>Graph-informed Matching]
        end
        
        subgraph "Graph Services"
            SKILL_GRAPH[Skill Graph Service<br/>Node + Relationship Creation]
            JOB_GRAPH[Job Graph Service<br/>Node + Relationship Creation]
            VECTOR_IDX[Vector Index Service<br/>HNSW Index Management]
            SIMILARITY[Skill Similarity Service<br/>Cosine Similarity Top-K]
        end
    end
    
    subgraph "Repository Layer"
        NEO4J_REPO[Neo4j Repository<br/>Cypher Queries]
        USER_REPO[User Repository<br/>Prisma Queries]
        QUERY_REPO[Query History Repository]
        INGEST_REPO[Ingestion Repository]
    end
    
    subgraph "Data Layer"
        subgraph "Neo4j Knowledge Graph"
            NEO4J[(Neo4j Cloud<br/>Knowledge Graph<br/>+ Vector Indexes)]
            
            NODES[Nodes:<br/>Job, Skill, Company<br/>Location, Category]
            RELS[Relationships:<br/>REQUIRES, SIMILAR_TO<br/>POSTED_BY, BELONGS_TO]
            VIDX[Vector Indexes:<br/>skill_embedding_idx<br/>job_embedding_idx<br/>company_embedding_idx]
            
            NEO4J --> NODES
            NEO4J --> RELS
            NEO4J --> VIDX
        end
        
        subgraph "PostgreSQL Database"
            POSTGRES[(PostgreSQL Cloud<br/>Relational Data)]
            
            TABLES[Tables:<br/>users, ingestion_jobs<br/>query_history, orphan_skill_logs<br/>neo4j_query_logs]
            
            POSTGRES --> TABLES
        end
    end
    
    subgraph "External Services"
        OPENROUTER_API[OpenRouter API<br/>meta-llama/llama-3.3-8b]
        HF_API[HuggingFace API<br/>Embedding Model]
    end
    
    subgraph "Background Jobs"
        SCHEDULER[APScheduler<br/>File Cleanup<br/>Every 15 minutes]
    end
    
    %% Frontend to API connections
    UI -->|HTTP + JWT| FASTAPI
    
    %% API to Services
    QUERYAPI --> LANGGRAPH
    INGESTAPI --> INGEST_SVC
    AUTHAPI --> AUTH_SVC
    
    %% Service to Service connections
    LANGGRAPH --> EMBEDDING
    LANGGRAPH --> OPENROUTER
    LANGGRAPH --> INTENT
    LANGGRAPH --> ENTITY
    
    INGEST_SVC --> EMBEDDING
    INGEST_SVC --> SKILL_GRAPH
    INGEST_SVC --> JOB_GRAPH
    INGEST_SVC --> VECTOR_IDX
    INGEST_SVC --> SIMILARITY
    
    %% Services to Repositories
    LANGGRAPH --> NEO4J_REPO
    LANGGRAPH --> QUERY_REPO
    INGEST_SVC --> NEO4J_REPO
    INGEST_SVC --> INGEST_REPO
    AUTH_SVC --> USER_REPO
    
    %% Repositories to Databases
    NEO4J_REPO --> NEO4J
    USER_REPO --> POSTGRES
    QUERY_REPO --> POSTGRES
    INGEST_REPO --> POSTGRES
    
    %% External API connections
    OPENROUTER --> OPENROUTER_API
    EMBEDDING --> HF_API
    
    %% Background Jobs
    SCHEDULER -.->|Cleanup| FASTAPI
    
    style FASTAPI fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style NEO4J fill:#00A86B,stroke:#006B45,stroke-width:3px,color:#fff
    style POSTGRES fill:#336791,stroke:#1E3A5F,stroke-width:3px,color:#fff
    style LANGGRAPH fill:#FF6B6B,stroke:#C23B3B,stroke-width:3px,color:#fff
    style OPENROUTER fill:#9B59B6,stroke:#6C3483,stroke-width:3px,color:#fff
```

### Technology Stack

#### Frontend
- **Framework:** React 18 with functional components and hooks
- **Build Tool:** Vite (fast HMR, ES modules)
- **Styling:** TailwindCSS (utility-first CSS)
- **State Management:** React Context API + Zustand (lightweight)
- **HTTP Client:** Axios
- **Routing:** React Router v6
- **Testing:** Vitest + React Testing Library + Playwright (E2E)

#### Backend
- **Framework:** FastAPI 0.109+ (Python 3.10+)
- **ASGI Server:** Uvicorn with auto-reload
- **AI Orchestration:** LangGraph 0.2+
- **ORM:** Prisma Client Python (asyncio interface)
- **Database Drivers:**
  - `neo4j` (official Python driver for Neo4j)
  - `prisma` (PostgreSQL via Prisma)
- **Authentication:** PyJWT + bcrypt
- **Rate Limiting:** SlowAPI
- **Scheduling:** APScheduler (async mode)
- **Embeddings:** sentence-transformers (`all-MiniLM-L6-v2`)
- **LLM Client:** OpenRouter API (unified gateway)

#### Databases
- **Graph Database:** Neo4j 5.x (Cloud Aura)
  - Vector indexes with HNSW algorithm
  - Cosine similarity search
  - Cypher query language
- **Relational Database:** PostgreSQL 14+ (Cloud)
  - Managed via Prisma migrations
  - UUID primary keys
  - JSONB for metadata storage

#### Infrastructure
- **Development:** Local (React dev server + FastAPI uvicorn)
- **Databases:** Cloud-hosted (Neo4j Aura + managed PostgreSQL)
- **Environment:** `.env` file configuration
- **Version Control:** Git

---

## Component Architecture

### Component Interaction Diagram

```mermaid
sequenceDiagram
    participant User
    participant React as React Frontend
    participant FastAPI as FastAPI Server
    participant Auth as Auth Middleware
    participant LangGraph as LangGraph Service
    participant Neo4j as Neo4j Graph DB
    participant PostgreSQL as PostgreSQL DB
    participant OpenRouter as OpenRouter LLM API
    participant HF as HuggingFace API
    
    Note over User,HF: User Query Flow (Natural Language Question)
    
    User->>React: Types query: "What skills for backend dev?"
    React->>FastAPI: POST /api/query/ask<br/>{query, session_id}<br/>Authorization: Bearer {JWT}
    FastAPI->>Auth: Validate JWT token
    Auth->>PostgreSQL: Verify user exists
    PostgreSQL-->>Auth: User valid
    Auth-->>FastAPI: user_id extracted
    
    FastAPI->>PostgreSQL: Get conversation history<br/>(last 5 messages, 24h max)
    PostgreSQL-->>FastAPI: [{query, response, timestamp}]
    
    FastAPI->>LangGraph: execute_query(query, user_id, session_id, history)
    
    Note over LangGraph: Node 1: Query Understanding
    LangGraph->>HF: Generate embedding for query
    HF-->>LangGraph: 384-dim vector
    LangGraph->>LangGraph: Extract entities (skills, jobs, companies)
    LangGraph->>LangGraph: Classify intent (multi-layer analysis)<br/>Result: ["skill_requirement"]
    
    Note over LangGraph: Node 2: Vector Search
    LangGraph->>Neo4j: Vector similarity search<br/>db.index.vector.queryNodes()<br/>top-k=15, threshold=0.5
    Neo4j-->>LangGraph: Top 15 similar nodes<br/>(Jobs, Skills, Companies)
    
    Note over LangGraph: Node 3: Graph Traversal
    LangGraph->>Neo4j: Cypher query based on intent<br/>MATCH (j:Job)-[REQUIRES]->(s:Skill)<br/>2-3 hop traversal
    Neo4j-->>LangGraph: 35 nodes, 58 relationships
    
    Note over LangGraph: Node 4: Context Construction
    LangGraph->>LangGraph: Format context string<br/>• Graph statistics<br/>• Vector results<br/>• Graph relationships<br/>• Token counting (tiktoken)
    LangGraph->>LangGraph: Truncate if >4000 tokens
    
    Note over LangGraph: Node 5: Response Generation
    LangGraph->>OpenRouter: Generate completion<br/>model: meta-llama/llama-3.3-8b<br/>temp: 0.3, max_tokens: 1200<br/>context + query + history
    OpenRouter-->>LangGraph: Natural language response
    
    LangGraph-->>FastAPI: {response, sources, metrics,<br/>constructed_context, context_stats}
    
    FastAPI->>PostgreSQL: Log query to query_history<br/>(user_id, session_id, query, response, metadata)
    PostgreSQL-->>FastAPI: Logged
    
    FastAPI-->>React: QueryResponse {<br/>query, response, sources,<br/>processing_time_ms, metadata<br/>}
    React-->>User: Display response + sources
```

### Component Responsibility Matrix

| Component | Responsibilities | Technologies | Dependencies |
|-----------|-----------------|--------------|--------------|
| **React Frontend** | UI rendering, user input, state management, HTTP requests | React, Vite, TailwindCSS, Axios | FastAPI endpoints |
| **FastAPI Server** | HTTP routing, middleware orchestration, request validation, response formatting | FastAPI, Pydantic, SlowAPI | Prisma, Neo4j driver |
| **Auth Middleware** | JWT validation, token expiration checks, user identity extraction | PyJWT | PostgreSQL (user verification) |
| **LangGraph Service** | Workflow orchestration, state management, node execution, timeout handling | LangGraph, Pydantic | All node implementations |
| **Query Understanding Node** | Embedding generation, entity extraction, intent classification | sentence-transformers, custom NLP logic | HuggingFace API, Neo4j (entity matching) |
| **Vector Search Node** | Semantic similarity search across 3 node types (Jobs, Skills, Companies) | Neo4j vector indexes (HNSW) | Neo4j database |
| **Graph Traversal Node** | Intent-specific Cypher query generation, relationship exploration | Cypher query language | Neo4j database |
| **Context Construction Node** | Formatting vector + graph results, token counting, truncation | tiktoken, custom formatting logic | None (pure transformation) |
| **Response Generation Node** | LLM prompt construction, API call with retry logic, response parsing | OpenRouter client, circuit breaker | OpenRouter API |
| **Ingestion Service** | CSV parsing, batch processing, node/relationship creation, progress tracking | Pandas, custom batch logic | Embedding service, graph services |
| **Neo4j Repository** | Cypher query execution, connection pooling, transaction management | neo4j Python driver | Neo4j database |
| **Prisma Client** | SQL query generation, type-safe database access, migration management | Prisma Client Python | PostgreSQL database |

---

## LangGraph RAG Pipeline

### Workflow State Machine

```mermaid
stateDiagram-v2
    [*] --> QueryUnderstanding: Initial State<br/>{user_query, user_id}
    
    state QueryUnderstanding {
        [*] --> GenerateEmbedding
        GenerateEmbedding --> ExtractEntities: 384-dim vector
        ExtractEntities --> ClassifyIntent: Entities extracted
        ClassifyIntent --> [*]: intent, intents, entities
    }
    
    QueryUnderstanding --> VectorSearch: State updated
    
    state VectorSearch {
        [*] --> SearchSkills
        SearchSkills --> SearchJobs: Top-k skills
        SearchJobs --> SearchCompanies: Top-k jobs
        SearchCompanies --> RankAndFilter: Top-k companies
        RankAndFilter --> [*]: vector_results (top-15)
    }
    
    VectorSearch --> GraphTraversal: State updated
    
    state GraphTraversal {
        [*] --> ExtractSeeds
        ExtractSeeds --> GenerateCypher: Top-10 node IDs
        GenerateCypher --> ExecuteQueries: Intent-specific queries
        ExecuteQueries --> FormatResults: Graph data retrieved
        FormatResults --> [*]: graph_context
    }
    
    GraphTraversal --> ContextConstruction: State updated
    
    state ContextConstruction {
        [*] --> BuildSections
        BuildSections --> CountTokens: Formatted context
        CountTokens --> CheckLimit: Token count
        CheckLimit --> Truncate: If >4000 tokens
        CheckLimit --> [*]: If <=4000 tokens
        Truncate --> [*]: constructed_context
    }
    
    ContextConstruction --> ResponseGeneration: State updated
    
    state ResponseGeneration {
        [*] --> CheckErrors
        CheckErrors --> BuildPrompt: No errors
        CheckErrors --> ErrorResponse: Errors found
        BuildPrompt --> CallLLM: System + user prompts
        CallLLM --> Retry: API failure
        Retry --> CallLLM: Attempt < 3
        CallLLM --> ParseResponse: Success
        ParseResponse --> [*]: final_response
        ErrorResponse --> [*]: Error message
        Retry --> [*]: Max retries exceeded
    }
    
    ResponseGeneration --> [*]: Workflow complete
```

### State Schema Evolution

```mermaid
graph LR
    subgraph "Initial State"
        S0["GraphRAGState {<br/>user_query: str<br/>user_id: str<br/>metadata: {<br/>  metrics: QueryMetrics<br/>  session_id: str<br/>  conversation_history: []<br/>  history_context: str<br/>}<br/>}"]
    end
    
    subgraph "After Query Understanding"
        S1["GraphRAGState {<br/>...<br/>query_embedding: [384 floats]<br/>intent: 'skill_requirement'<br/>intents: ['skill_requirement']<br/>entities: [{<br/>  type: 'skill'<br/>  value: 'Python'<br/>  confidence: 0.95<br/>  source: 'graph_match'<br/>  graph_node_id: 'skill_123'<br/>}]<br/>metadata: {<br/>  query_understanding_completed: true<br/>  intent_confidence: 0.92<br/>}<br/>}"]
    end
    
    subgraph "After Vector Search"
        S2["GraphRAGState {<br/>...<br/>vector_results: [{<br/>  node_type: 'Skill'<br/>  id: 'skill_python'<br/>  name: 'Python'<br/>  score: 0.92<br/>  properties: {...}<br/>}, ...]<br/>metadata: {<br/>  vector_search_completed: true<br/>  vector_results_count: 15<br/>}<br/>}"]
    end
    
    subgraph "After Graph Traversal"
        S3["GraphRAGState {<br/>...<br/>graph_context: [{<br/>  node_type: 'Job'<br/>  node_id: 'job_123'<br/>  properties: {...}<br/>}, {<br/>  type: 'REQUIRES'<br/>  properties: {...}<br/>}, ...]<br/>metadata: {<br/>  graph_traversal_completed: true<br/>  graph_nodes_count: 35<br/>  graph_relationships_count: 58<br/>}<br/>}"]
    end
    
    subgraph "After Context Construction"
        S4["GraphRAGState {<br/>...<br/>constructed_context: '=== GRAPH STATS ===<br/>Vector Search: 15 matches<br/>Graph Traversal: 35 nodes...'<br/>metadata: {<br/>  context_construction_completed: true<br/>  context_token_count: 2856<br/>  context_char_count: 12459<br/>  context_truncated: false<br/>}<br/>}"]
    end
    
    subgraph "After Response Generation"
        S5["GraphRAGState {<br/>...<br/>final_response: 'Based on the job market...'<br/>metadata: {<br/>  response_generation_completed: true<br/>  llm_tokens_used: 1090<br/>  llm_latency_ms: 1234<br/>}<br/>}"]
    end
    
    S0 --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    
    style S0 fill:#E8F4F8,stroke:#4A90E2,stroke-width:2px
    style S1 fill:#FFF4E6,stroke:#FF9800,stroke-width:2px
    style S2 fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style S3 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style S4 fill:#FFF3E0,stroke:#FF6F00,stroke-width:2px
    style S5 fill:#E3F2FD,stroke:#2196F3,stroke-width:2px
```

### Node Implementation Details

#### Node 1: Query Understanding

**Purpose:** Analyze user query using multi-layer intent analysis and extract entities

**Processing Steps:**
1. **Embedding Generation** - Generate 384-dim vector using `sentence-transformers/all-MiniLM-L6-v2`
2. **Entity Extraction** - Use `DeepEntityExtractor` with graph-informed semantic matching
3. **Intent Classification** - Multi-layer analysis:
   - Layer 1: Syntactic (regex patterns)
   - Layer 2: Semantic (embedding similarity to intent archetypes)
   - Layer 3: Entity-informed (refine based on extracted entities)
   - Layer 4: Query decomposition (execution planning)

**Outputs:**
- `query_embedding`: List[float] (384 dimensions)
- `intent`: str (primary intent for backward compatibility)
- `intents`: List[str] (all detected intents for multi-intent queries)
- `entities`: List[Dict] with fields: `{type, value, confidence, source, graph_node_id}`

**Intent Types:**
- `skill_requirement` - "What skills are needed for X?"
- `career_path` - "How do I become a Y?"
- `salary_analysis` - "What's the salary for Z?"
- `skill_relationship` - "Skills similar to A?"
- `company_query` - "Which companies hire for B?"
- `general` - Catch-all
- `unknown` - Cannot classify

**Performance:** Typically 40-80ms

#### Node 2: Vector Search

**Purpose:** Find semantically similar nodes using HNSW vector indexes

**Processing Steps:**
1. **Parallel Vector Searches:**
   - Search `skill_embedding_idx` (top-k=15)
   - Search `job_embedding_idx` (top-k=15)
   - Search `company_embedding_idx` (top-k=15)
2. **Combine and Rank:**
   - Merge all results
   - Sort by similarity score (descending)
   - Filter by threshold (default: 0.5)
   - Return top-k (default: 15)

**Cypher Query Example:**
```cypher
CALL db.index.vector.queryNodes(
  'skill_embedding_idx',    // Index name
  15,                        // Top-k
  $query_embedding           // 384-dim vector
)
YIELD node, score
WHERE score >= 0.5          // Threshold
RETURN node, score
```

**Outputs:**
- `vector_results`: List[Dict] with fields: `{node_type, id, name, score, properties}`

**Performance:** Typically 40-100ms (parallel execution)

#### Node 3: Graph Traversal

**Purpose:** Discover related nodes and relationships through intent-specific graph exploration

**Processing Steps:**
1. **Extract Seed Nodes** - Take top-10 vector results as starting points
2. **Generate Intent-Specific Cypher:**
   - `skill_requirement`: `(Job)-[REQUIRES]->(Skill)`
   - `career_path`: `(Skill)-[SIMILAR_TO*1..2]->(Skill)`
   - `salary_analysis`: `(Job)-[POSTED_BY]->(Company)` + salary properties
   - `skill_relationship`: `(Skill)-[SIMILAR_TO]->(Skill)` + categories
   - `company_query`: `(Job)-[POSTED_BY]->(Company)` + `(Job)-[REQUIRES]->(Skill)`
3. **Execute Multi-Intent Queries** - Run separate query for EACH intent, merge results
4. **Format Results** - Return nodes + relationships as structured dictionaries

**Cypher Query Example (skill_requirement):**
```cypher
MATCH (j:Job) WHERE j.job_id IN $seed_ids
MATCH path = (j)-[req:REQUIRES*1..2]->(s:Skill)
OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
WITH DISTINCT j, req, s, cat
RETURN
    j AS job_node,
    req AS requires_rel,
    s AS skill_node,
    cat AS category_node
LIMIT 50
```

**Outputs:**
- `graph_context`: List[Dict] with node and relationship objects

**Typical Results:** 20-50 nodes, 30-100 relationships

**Performance:** Typically 80-200ms

#### Node 4: Context Construction

**Purpose:** Format vector + graph data into structured LLM context with token management

**Context Structure:**
```
Section 0: Graph Statistics Header (CRITICAL)
  🔍 KNOWLEDGE GRAPH ANALYSIS RESULTS
  Vector Search: 15 matches
  Graph Traversal: 35 nodes, 58 relationships
  Relationship Types: 24× Requires, 18× Similar To, 12× Posted By, 4× Belongs To

Section 1: User Query + Intents + Entities
  User's Question: ...
  Focus Areas: skill requirements, salary analysis
  Skills Mentioned: Python, Django

Section 2: Top Matching Nodes (from vector search)
  Grouped by type (Jobs, Skills, Companies)
  Formatted naturally with details

Section 3: Related Information (from graph traversal)
  Skills from Graph (8 found):
  Jobs from Graph (5 positions):
  Graph Connections Found:

Section 4: Skill Gap Analysis (if career_path + skill_requirement)
  Your Foundation: Python, JavaScript
  Skills to Develop: Django, PostgreSQL, AWS

Section 5: Market Summary
  Job counts, salary ranges, company insights
```

**Token Management:**
- **Target:** 2000-3000 tokens
- **Limit:** 4000 tokens (hard limit for free models)
- **Counting:** tiktoken library (GPT-compatible)
- **Truncation:** Progressive reduction (preserve query + top vector results, reduce graph context)

**Outputs:**
- `constructed_context`: str (formatted context)
- `metadata.context_token_count`: int
- `metadata.context_char_count`: int
- `metadata.context_truncated`: bool

**Performance:** Typically 20-50ms

#### Node 5: Response Generation

**Purpose:** Generate natural language response using OpenRouter LLM API

**System Prompt Structure:**
```
YOU ARE: Helpful career advisor with graph analysis expertise

CRITICAL REQUIREMENTS:
- ALWAYS mention graph statistics (nodes, relationships)
- Reference specific data from context
- Include Graph Insights section

RESPONSE STRUCTURE:
1. Direct Answer (2-4 sentences)
2. Key Insights (3-5 bullet points)
3. Graph Insights (REQUIRED if graph data present)
4. Supporting Data (with numbers)
5. Next Steps (optional)
6. Technical Details (collapsible)

STYLE:
✅ Friendly, conversational
✅ Specific numbers and data
✅ Natural language
❌ Not overly technical
❌ No raw queries
```

**User Prompt:**
```
CONVERSATION HISTORY (if exists):
  User: Previous question
  Assistant: Previous answer

CURRENT CONTEXT:
  <Formatted context from Node 4>

User's Current Question: <query>

Instructions:
  - Consider conversation history for follow-ups
  - Reference specific data from context
  - Include graph statistics
```

**API Configuration:**
- **Model:** `meta-llama/llama-3.3-8b-instruct:free`
- **Temperature:** 0.3 (low for factual precision)
- **Max Tokens:** 1200 (comprehensive responses)
- **Retry:** 3 attempts with exponential backoff (1s, 2s, 4s)
- **Timeout:** 200 seconds (reasoning models)
- **Circuit Breaker:** Fail fast after 3 consecutive failures

**Outputs:**
- `final_response`: str (natural language answer)
- `metadata.llm_tokens_used`: int
- `metadata.llm_latency_ms`: float

**Performance:** Typically 800-1500ms

---

## API Architecture

### API Endpoint Structure

```mermaid
graph TB
    subgraph "Public Endpoints (No Auth)"
        ROOT[GET /<br/>Welcome message + API info]
        HEALTH[GET /health<br/>Database connectivity check]
        STATS[GET /stats<br/>Graph statistics]
    end
    
    subgraph "Authentication Endpoints (/api/auth)"
        REGISTER["POST /api/auth/register<br/>Create new user account<br/>Body: (email, password, full_name)"]
        LOGIN["POST /api/auth/login<br/>Login with credentials<br/>Body: (email, password)<br/>Returns: (access_token, user)"]
    end
    
    subgraph "Query Endpoints (/api/query) - Protected"
        ASK["POST /api/query/ask<br/>Execute NL query<br/>Rate limit: 10/min<br/>Body: (query, session_id?)<br/>Returns: QueryResponse"]
        CONTEXT["GET /api/query/history/(query_id)/context<br/>Retrieve constructed context<br/>For debugging"]
    end
    
    subgraph "Ingestion Endpoints (/api/ingest) - Protected"
        UPLOAD_SKILLS["POST /api/ingest/skills<br/>Upload skills CSV<br/>Multipart/form-data<br/>Max 500MB"]
        UPLOAD_JOBS["POST /api/ingest/jobs<br/>Upload jobs CSV<br/>Multipart/form-data<br/>Max 500MB"]
        STATUS["GET /api/ingest/status/(job_id)<br/>Check ingestion progress<br/>Returns: (status, records_processed, ETA)"]
        ERRORS["GET /api/ingest/errors/(job_id)<br/>Download error log CSV<br/>Returns: CSV file"]
    end
    
    subgraph "Admin Endpoints (/api/admin) - Protected"
        DELETE_GRAPH[DELETE /api/admin/graph<br/>Delete all graph data<br/>Requires confirmation]
        REBUILD_IDX[POST /api/admin/indexes/rebuild<br/>Rebuild vector indexes]
    end
    
    subgraph "Monitoring Endpoints (/api/monitor)"
        WS_MONITOR[WebSocket /api/monitor/ws<br/>Real-time pipeline events]
        QUERY_METRICS[GET /api/monitor/queries<br/>Query performance metrics]
    end
    
    style ROOT fill:#E8F4F8,stroke:#4A90E2,stroke-width:2px
    style HEALTH fill:#E8F4F8,stroke:#4A90E2,stroke-width:2px
    style STATS fill:#E8F4F8,stroke:#4A90E2,stroke-width:2px
    
    style REGISTER fill:#FFF4E6,stroke:#FF9800,stroke-width:2px
    style LOGIN fill:#FFF4E6,stroke:#FF9800,stroke-width:2px
    
    style ASK fill:#FFEBEE,stroke:#F44336,stroke-width:3px
    style CONTEXT fill:#FCE4EC,stroke:#E91E63,stroke-width:2px
    
    style UPLOAD_SKILLS fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style UPLOAD_JOBS fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style STATUS fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style ERRORS fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    
    style DELETE_GRAPH fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px
    style REBUILD_IDX fill:#FFCDD2,stroke:#D32F2F,stroke-width:2px
    
    style WS_MONITOR fill:#E0F2F1,stroke:#009688,stroke-width:2px
    style QUERY_METRICS fill:#E0F2F1,stroke:#009688,stroke-width:2px
```

### Middleware Processing Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI as FastAPI Application
    participant CORS as CORS Middleware
    participant RateLimit as SlowAPI Rate Limiter
    participant JWTAuth as JWT Auth Middleware
    participant ErrorHandler as Error Handler
    participant Router as API Router
    
    Client->>FastAPI: HTTP Request
    FastAPI->>CORS: Process request
    
    alt Preflight OPTIONS request
        CORS-->>Client: 200 OK + CORS headers
    else Regular request
        CORS->>CORS: Validate origin<br/>(localhost:5173, localhost:3000)
        CORS->>CORS: Add CORS headers
        CORS->>RateLimit: Forward request
        
        RateLimit->>RateLimit: Check rate limit<br/>(10 requests/minute per IP)
        
        alt Rate limit exceeded
            RateLimit-->>Client: 429 Too Many Requests<br/>{detail: "Rate limit exceeded"}
        else Rate limit OK
            RateLimit->>JWTAuth: Forward request
            
            alt Protected endpoint
                JWTAuth->>JWTAuth: Extract Bearer token<br/>from Authorization header
                
                alt Token missing
                    JWTAuth-->>Client: 401 Unauthorized<br/>{detail: "Authentication required"}
                else Token present
                    JWTAuth->>JWTAuth: Verify token signature<br/>using JWT_SECRET
                    
                    alt Token invalid
                        JWTAuth-->>Client: 401 Unauthorized<br/>{detail: "Invalid token"}
                    else Token expired
                        JWTAuth-->>Client: 401 Unauthorized<br/>{detail: "Token expired"}
                    else Token valid
                        JWTAuth->>JWTAuth: Extract user_id from payload
                        JWTAuth->>Router: Forward with user_id
                    end
                end
            else Public endpoint
                RateLimit->>Router: Forward request
            end
        end
    end
    
    Router->>Router: Execute endpoint handler
    
    alt Success
        Router-->>ErrorHandler: Response data
        ErrorHandler-->>Client: 200 OK + data
    else Validation error
        Router-->>ErrorHandler: RequestValidationError
        ErrorHandler-->>Client: 422 Unprocessable Entity<br/>{detail: [...]}
    else Business logic error
        Router-->>ErrorHandler: HTTPException
        ErrorHandler-->>Client: Status code from exception<br/>{detail: "..."}
    else Database error
        Router-->>ErrorHandler: PrismaError / Neo4jServiceUnavailable
        ErrorHandler-->>Client: 503 Service Unavailable<br/>{detail: "Database connection failed"}
    else Unexpected error
        Router-->>ErrorHandler: Exception
        ErrorHandler-->>Client: 500 Internal Server Error<br/>{detail: "Internal server error"}
    end
```

### Request/Response Examples

#### 1. User Registration

**Request:**
```http
POST /api/auth/register HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password_123",
  "full_name": "John Doe"
}
```

**Response (Success):**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

**Response (Error - Email Exists):**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "Email already registered"
}
```

#### 2. Natural Language Query

**Request:**
```http
POST /api/query/ask HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

{
  "query": "What skills are needed for backend development?",
  "session_id": "abc123-session-uuid"
}
```

**Response (Success):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "query": "What skills are needed for backend development?",
  "response": "Based on the job market data, **backend development roles typically require 5-7 core skills**. Our graph analysis explored **35 nodes and 58 relationships** across the knowledge graph to give you this comprehensive view.\n\n**Essential Skills:**\n- Python is required by 95% of positions\n- Django or Flask (web frameworks)\n- PostgreSQL for data management\n- REST API development\n\n**Graph Insights:**\nGraph analysis revealed 35 nodes across 58 relationships, including:\n- Found 24 skill-requirement connections\n- Discovered 18 similar skill relationships showing career progression paths\n- Traversed relationships linking 5 job positions to 8 key skills\n\n**Salary Expectations:**\nEntry-level positions typically offer ₹10-15 LPA, while experienced developers can expect ₹18-30 LPA.",
  "sources": [
    {
      "node_type": "Skill",
      "node_id": "skill_python",
      "properties": {
        "name": "Python",
        "description": "High-level programming language",
        "category": "Programming Language"
      }
    },
    {
      "node_type": "Job",
      "node_id": "job_backend_dev_1",
      "properties": {
        "job_title": "Backend Developer",
        "company_name": "Google",
        "salary_min": 1200000,
        "salary_max": 1800000
      }
    }
  ],
  "processing_time_ms": 1234.56,
  "metadata": {
    "intent": "skill_requirement",
    "intent_confidence": 0.92,
    "vector_results_count": 15,
    "graph_nodes_count": 35,
    "graph_relationships_count": 58,
    "metrics": {
      "query_understanding": 45.2,
      "vector_search": 78.3,
      "graph_traversal": 156.7,
      "context_construction": 34.1,
      "response_generation": 920.2,
      "total": 1234.5
    }
  },
  "constructed_context": "=== GRAPH STATISTICS ===\n\n...",
  "context_stats": {
    "token_count": 2856,
    "char_count": 12459,
    "truncated": false,
    "vector_results_count": 15,
    "graph_nodes_count": 35
  }
}
```

#### 3. CSV Ingestion Status

**Request:**
```http
GET /api/ingest/status/job-123-uuid HTTP/1.1
Host: localhost:8000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (In Progress):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "job_id": "job-123-uuid",
  "file_type": "skills",
  "file_name": "skills_taxonomy.csv",
  "status": "processing",
  "total_records": 10523,
  "processed_records": 5234,
  "failed_records": 12,
  "batch_number": 5,
  "processing_speed": 234.5,
  "estimated_completion_time": "2025-10-29T15:45:30Z",
  "progress_percentage": 49.7,
  "created_at": "2025-10-29T15:40:00Z",
  "started_at": "2025-10-29T15:40:05Z"
}
```

---

## Data Flow Diagrams

### CSV Ingestion Data Flow

```mermaid
flowchart TD
    START([User uploads CSV file]) --> UPLOAD[Frontend: FileUploadZone<br/>Drag & drop or file picker]
    UPLOAD --> API_UPLOAD[POST /api/ingest/skills or /jobs<br/>multipart/form-data]
    
    API_UPLOAD --> VALIDATE{File validation<br/>• Format: CSV<br/>• Size: <500MB<br/>• Required columns}
    
    VALIDATE -->|Invalid| ERROR_RESPONSE[400 Bad Request<br/>Validation error message]
    VALIDATE -->|Valid| CACHE[Store in temporary cache<br/>backend/app/utils/file_cache.py<br/>hash-based deduplication]
    
    CACHE --> PARSE[CSV Parser<br/>pandas.read_csv<br/>Extract first 5-10 rows]
    PARSE --> PREVIEW[Return preview data<br/>{columns, preview_rows, total_rows}]
    
    PREVIEW --> FRONTEND_PREVIEW[Frontend: CSVPreviewModal<br/>Display table + confirm button]
    FRONTEND_PREVIEW --> USER_CONFIRM{User confirms<br/>upload?}
    
    USER_CONFIRM -->|Cancel| CLEANUP[Delete cached file]
    USER_CONFIRM -->|Confirm| CREATE_JOB[Create IngestionJob record<br/>PostgreSQL via Prisma<br/>status: 'pending']
    
    CREATE_JOB --> BATCH_PROCESS[Ingestion Service<br/>Batch processing loop<br/>batch_size: 1000 records]
    
    BATCH_PROCESS --> BATCH_LOOP{For each batch}
    
    BATCH_LOOP --> GENERATE_EMBEDDINGS[Generate embeddings<br/>HuggingFace API<br/>batch_size: 32 texts<br/>all-MiniLM-L6-v2]
    
    GENERATE_EMBEDDINGS --> FILE_TYPE{File type?}
    
    FILE_TYPE -->|Skills CSV| SKILL_GRAPH[Skill Graph Service<br/>• Create Skill nodes<br/>• Create Category nodes<br/>• Create Subcategory nodes<br/>• BELONGS_TO relationships]
    
    FILE_TYPE -->|Jobs CSV| JOB_GRAPH[Job Graph Service<br/>• Create Job nodes<br/>• Create Company nodes<br/>• Create Location nodes<br/>• POSTED_BY, LOCATED_IN relationships]
    
    SKILL_GRAPH --> UPDATE_STATUS[Update IngestionJob<br/>processed_records += batch_size<br/>processing_speed = records/sec<br/>estimated_completion_time]
    
    JOB_GRAPH --> UPDATE_STATUS
    
    UPDATE_STATUS --> MORE_BATCHES{More batches?}
    
    MORE_BATCHES -->|Yes| BATCH_LOOP
    MORE_BATCHES -->|No| RELATIONSHIPS[Create relationships<br/>• Skill SIMILAR_TO Skill<br/>• Job REQUIRES Skill]
    
    RELATIONSHIPS --> VECTOR_IDX[Verify vector indexes<br/>• skill_embedding_idx<br/>• job_embedding_idx<br/>• company_embedding_idx]
    
    VECTOR_IDX --> COMPLETE[Update IngestionJob<br/>status: 'completed'<br/>completed_at: now()]
    
    COMPLETE --> NOTIFY[Frontend polling detects completion<br/>Display success message]
    
    ERROR_RESPONSE --> END([End])
    CLEANUP --> END
    NOTIFY --> END
    
    style START fill:#E8F4F8,stroke:#4A90E2,stroke-width:3px
    style BATCH_PROCESS fill:#FFEBEE,stroke:#F44336,stroke-width:2px
    style GENERATE_EMBEDDINGS fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style SKILL_GRAPH fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style JOB_GRAPH fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style VECTOR_IDX fill:#FFF3E0,stroke:#FF6F00,stroke-width:2px
    style COMPLETE fill:#C8E6C9,stroke:#388E3C,stroke-width:3px
    style END fill:#E0E0E0,stroke:#616161,stroke-width:2px
```

### Query Processing Data Flow

```mermaid
flowchart TD
    START([User types query]) --> CHAT_INPUT[ChatInput component<br/>Input validation]
    CHAT_INPUT --> ADD_USER_MSG[Add user message to chat<br/>Optimistic UI update]
    ADD_USER_MSG --> API_CALL[POST /api/query/ask<br/>{query, session_id, JWT token}]
    
    API_CALL --> AUTH_CHECK{JWT valid?}
    AUTH_CHECK -->|No| AUTH_ERROR[401 Unauthorized]
    AUTH_CHECK -->|Yes| RATE_CHECK{Rate limit OK?<br/>10/min}
    
    RATE_CHECK -->|No| RATE_ERROR[429 Too Many Requests]
    RATE_CHECK -->|Yes| QUERY_VALIDATE{Query valid?<br/>• Length: 3-500 chars<br/>• Not empty}
    
    QUERY_VALIDATE -->|No| VALIDATE_ERROR[400 Bad Request]
    QUERY_VALIDATE -->|Yes| GET_HISTORY[Get conversation history<br/>PostgreSQL query_history<br/>session_id, last 5 messages, 24h max]
    
    GET_HISTORY --> SESSION_CHECK{Session<br/>expired?}
    SESSION_CHECK -->|Yes| NEW_SESSION[Generate new session_id]
    SESSION_CHECK -->|No| USE_SESSION[Use existing session_id<br/>Include conversation history]
    
    NEW_SESSION --> LANGGRAPH_EXEC
    USE_SESSION --> LANGGRAPH_EXEC[Execute LangGraph workflow<br/>timeout: 200 seconds]
    
    LANGGRAPH_EXEC --> NODE1[Node 1: Query Understanding<br/>• Generate embedding<br/>• Extract entities<br/>• Classify intent]
    
    NODE1 --> NODE2[Node 2: Vector Search<br/>• Parallel search 3 indexes<br/>• Top-15 similar nodes<br/>• Score threshold: 0.5]
    
    NODE2 --> NODE3[Node 3: Graph Traversal<br/>• Intent-specific Cypher<br/>• 2-3 hop traversal<br/>• Multi-intent support]
    
    NODE3 --> NODE4[Node 4: Context Construction<br/>• Format 5 sections<br/>• Token counting<br/>• Truncate if >4000 tokens]
    
    NODE4 --> NODE5[Node 5: Response Generation<br/>• OpenRouter API call<br/>• Retry logic: 3 attempts<br/>• Timeout: 200s]
    
    NODE5 --> EXTRACT_SOURCES[Extract sources<br/>Deduplicate by node_id]
    
    EXTRACT_SOURCES --> LOG_QUERY[Log to PostgreSQL<br/>query_history table<br/>user_id, session_id, metadata]
    
    LOG_QUERY --> RESPONSE[Return QueryResponse<br/>{query, response, sources,<br/>processing_time_ms, metadata}]
    
    RESPONSE --> FRONTEND_DISPLAY[Frontend: Display response<br/>AssistantMessage component<br/>SourceCitations component]
    
    AUTH_ERROR --> ERROR_DISPLAY[Display error in chat]
    RATE_ERROR --> ERROR_DISPLAY
    VALIDATE_ERROR --> ERROR_DISPLAY
    
    FRONTEND_DISPLAY --> END([End])
    ERROR_DISPLAY --> END
    
    style START fill:#E8F4F8,stroke:#4A90E2,stroke-width:3px
    style NODE1 fill:#FFF4E6,stroke:#FF9800,stroke-width:2px
    style NODE2 fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style NODE3 fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style NODE4 fill:#FFF3E0,stroke:#FF6F00,stroke-width:2px
    style NODE5 fill:#FFEBEE,stroke:#F44336,stroke-width:2px
    style RESPONSE fill:#C8E6C9,stroke:#388E3C,stroke-width:3px
    style END fill:#E0E0E0,stroke:#616161,stroke-width:2px
```

---

## Database Architecture

### PostgreSQL Schema (Prisma)

```mermaid
erDiagram
    User ||--o{ QueryHistory : creates
    User ||--o{ IngestionJob : initiates
    IngestionJob ||--o{ IngestionError : contains
    
    User {
        uuid id PK "Primary key"
        string email UK "Unique, indexed"
        string password_hash "bcrypt hashed"
        datetime created_at "Auto timestamp"
        datetime updated_at "Auto updated"
    }
    
    QueryHistory {
        uuid id PK "Primary key"
        uuid user_id FK "FK to User"
        string session_id "Session identifier, indexed"
        text query_text "Original user query"
        text response_text "LLM generated response"
        text metadata "JSON: intent, sources, metrics"
        datetime created_at "Query timestamp, indexed"
    }
    
    IngestionJob {
        uuid id PK "Primary key"
        uuid user_id FK "FK to User"
        string file_type "skills or jobs, indexed"
        string file_name "Original filename"
        float file_size_mb "File size"
        string status "pending/processing/completed/failed, indexed"
        int total_records "Total CSV records"
        int processed_records "Successfully processed"
        int failed_records "Failed to process"
        int batch_number "Current batch number"
        float processing_speed "Records per second"
        datetime estimated_completion_time "ETA"
        text error_log "Error summary"
        datetime started_at "Processing start time"
        datetime completed_at "Processing end time"
        datetime created_at "Job creation time"
        datetime updated_at "Last update time"
    }
    
    IngestionError {
        uuid id PK "Primary key"
        uuid job_id FK "FK to IngestionJob"
        int row_number "1-indexed CSV row"
        text error_message "Error description"
        text raw_data "JSON of failed row"
        datetime created_at "Error timestamp, indexed"
    }
    
    OrphanSkillLog {
        uuid id PK "Primary key"
        string skill_id "Neo4j Skill node ID"
        string skill_name "Skill name"
        string job_id "Job that referenced skill"
        string orphan_reason "no_match/ambiguous_fuzzy_match/too_short"
        json fuzzy_candidates "Potential matches"
        string status "pending_review/approved/merged, indexed"
        datetime created_at "Log timestamp, indexed"
        datetime reviewed_at "Review timestamp"
        string reviewed_by "Reviewer ID"
    }
    
    Neo4jQueryLog {
        uuid id PK "Primary key"
        text query_text "Full Cypher query"
        json parameters "Query parameters"
        string operation_type "READ/WRITE/VECTOR_SEARCH/GRAPH_TRAVERSAL, indexed"
        float execution_time_ms "Query duration, indexed"
        int result_count "Records returned"
        string status "success/error, indexed"
        text error_message "Error details"
        string user_id "User context, indexed"
        string session_id "Session identifier, indexed"
        string source "ingestion/query_pipeline/vector_search, indexed"
        json metadata "Additional context"
        datetime created_at "Query timestamp, indexed"
    }
```

### Neo4j Graph Schema

```mermaid
graph TB
    subgraph "Node Types"
        Job[Job Node<br/>Properties:<br/>• job_id PK<br/>• job_title<br/>• company_name<br/>• location<br/>• salary_min, salary_max, mean_salary<br/>• description, job_description<br/>• posted_at<br/>• schedule_type, work_from_home<br/>• embedding 384-dim vector<br/>• CIN, NCO_Code_algo, NIC_Code_algo<br/>• ... 30 fields total]
        
        Skill[Skill Node<br/>Properties:<br/>• id PK<br/>• name<br/>• level BEGINNER, INTERMEDIATE, ADVANCED<br/>• category, category_name<br/>• subcategory, subcategory_name<br/>• type<br/>• is_software, is_language<br/>• description<br/>• wiki_link, wiki_extract<br/>• version, latest_version<br/>• embedding 384-dim vector]
        
        Company[Company Node<br/>Properties:<br/>• company_name PK<br/>• cin<br/>• company_industrial_classification<br/>• nic_code_2_2008<br/>• company_description<br/>• embedding 384-dim vector]
        
        Location[Location Node<br/>Properties:<br/>• location_name PK<br/>• district]
        
        Category[Category Node<br/>Properties:<br/>• category_id PK<br/>• category_name]
        
        Subcategory[Subcategory Node<br/>Properties:<br/>• subcategory_id PK<br/>• subcategory_name]
    end
    
    subgraph "Relationships"
        Job -->|REQUIRES| Skill
        Job -->|POSTED_BY| Company
        Job -->|LOCATED_IN| Location
        Skill -->|SIMILAR_TO| Skill
        Skill -->|BELONGS_TO_CATEGORY| Category
        Skill -->|BELONGS_TO_SUBCATEGORY| Subcategory
    end
    
    subgraph "REQUIRES Relationship"
        REQ_REL[REQUIRES<br/>Properties:<br/>• importance: critical/optional<br/>• similarity_score: 0.0-1.0]
    end
    
    subgraph "SIMILAR_TO Relationship"
        SIM_REL[SIMILAR_TO<br/>Properties:<br/>• similarity_score: 0.7-1.0<br/>• computed via cosine similarity<br/>• top-5 per skill]
    end
    
    subgraph "Vector Indexes HNSW"
        SKILL_IDX[skill_embedding_idx<br/>• Index: Skill.embedding<br/>• Dimensions: 384<br/>• Similarity: cosine<br/>• Algorithm: HNSW]
        
        JOB_IDX[job_embedding_idx<br/>• Index: Job.embedding<br/>• Dimensions: 384<br/>• Similarity: cosine<br/>• Algorithm: HNSW]
        
        COMPANY_IDX[company_embedding_idx<br/>• Index: Company.embedding<br/>• Dimensions: 384<br/>• Similarity: cosine<br/>• Algorithm: HNSW]
    end
    
    style Job fill:#E3F2FD,stroke:#2196F3,stroke-width:2px
    style Skill fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
    style Company fill:#FFF3E0,stroke:#FF6F00,stroke-width:2px
    style Location fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
    style Category fill:#FFF4E6,stroke:#FF9800,stroke-width:2px
    style Subcategory fill:#FCE4EC,stroke:#E91E63,stroke-width:2px
```

### Data Volume & Performance Characteristics

| Metric | Development | Production Estimate |
|--------|-------------|---------------------|
| **Users** | ~10 | 100-1000 |
| **Job Nodes** | 40,000-50,000 | 100,000+ |
| **Skill Nodes** | 10,000+ | 20,000+ |
| **Company Nodes** | 5,000-10,000 | 20,000+ |
| **REQUIRES Relationships** | 200,000+ | 500,000+ |
| **SIMILAR_TO Relationships** | 50,000 (5 per skill) | 100,000+ |
| **Query History Records** | Growing | Unlimited (with cleanup) |
| **Neo4j Database Size** | ~1-2 GB | 5-10 GB |
| **PostgreSQL Database Size** | ~50 MB | 200-500 MB |

---

## Service Orchestration

### Service Dependency Graph

```mermaid
graph TB
    subgraph "Core Application Services"
        FASTAPI_APP[FastAPI Application<br/>app.main:app]
        LIFESPAN[Lifespan Manager<br/>Startup/Shutdown Hooks]
        SCHEDULER[APScheduler<br/>Background Jobs]
    end
    
    subgraph "Database Clients Global Instances"
        PRISMA[Prisma Client<br/>prisma_client]
        NEO4J_DRIVER[Neo4j Driver<br/>neo4j_driver]
    end
    
    subgraph "Middleware Layer"
        CORS_MW[CORS Middleware]
        RATE_MW[Rate Limit Middleware]
        JWT_MW[JWT Auth Middleware]
        ERROR_MW[Error Handler Middleware]
    end
    
    subgraph "Repository Layer"
        USER_REPO[User Repository]
        QUERY_REPO[Query History Repository]
        INGEST_REPO[Ingestion Repository]
        NEO4J_REPO[Neo4j Repository<br/>MonitoredNeo4jRepository]
    end
    
    subgraph "AI/ML Services"
        LANGGRAPH_SVC[LangGraph Service<br/>Workflow orchestration]
        EMBEDDING_SVC[Embedding Service<br/>HuggingFace all-MiniLM-L6-v2]
        OPENROUTER_SVC[OpenRouter Service<br/>LLM API + Circuit Breaker]
        INTENT_SVC[Intent Analysis Service<br/>Multi-layer classification]
        ENTITY_SVC[Entity Extraction Service<br/>Graph-informed matching]
    end
    
    subgraph "Graph Services"
        SKILL_GRAPH_SVC[Skill Graph Service]
        JOB_GRAPH_SVC[Job Graph Service]
        VECTOR_IDX_SVC[Vector Index Service]
        SIMILARITY_SVC[Skill Similarity Service]
    end
    
    subgraph "Business Logic Services"
        INGEST_SVC[Ingestion Service<br/>Batch processing coordinator]
        AUTH_SVC[Auth Service<br/>JWT + bcrypt]
        MONITORING_SVC[Pipeline Monitoring Service<br/>WebSocket events]
        NEO4J_MONITORING[Neo4j Monitoring Service<br/>Query logging]
    end
    
    %% Application dependencies
    FASTAPI_APP --> LIFESPAN
    LIFESPAN --> PRISMA
    LIFESPAN --> NEO4J_DRIVER
    LIFESPAN --> SCHEDULER
    
    %% Middleware dependencies
    FASTAPI_APP --> CORS_MW
    CORS_MW --> RATE_MW
    RATE_MW --> JWT_MW
    JWT_MW --> ERROR_MW
    
    %% Repository dependencies
    USER_REPO --> PRISMA
    QUERY_REPO --> PRISMA
    INGEST_REPO --> PRISMA
    NEO4J_REPO --> NEO4J_DRIVER
    NEO4J_REPO --> NEO4J_MONITORING
    
    %% LangGraph Service dependencies
    LANGGRAPH_SVC --> EMBEDDING_SVC
    LANGGRAPH_SVC --> OPENROUTER_SVC
    LANGGRAPH_SVC --> INTENT_SVC
    LANGGRAPH_SVC --> ENTITY_SVC
    LANGGRAPH_SVC --> NEO4J_REPO
    LANGGRAPH_SVC --> MONITORING_SVC
    
    %% Ingestion Service dependencies
    INGEST_SVC --> EMBEDDING_SVC
    INGEST_SVC --> SKILL_GRAPH_SVC
    INGEST_SVC --> JOB_GRAPH_SVC
    INGEST_SVC --> VECTOR_IDX_SVC
    INGEST_SVC --> SIMILARITY_SVC
    INGEST_SVC --> INGEST_REPO
    
    %% Graph Services dependencies
    SKILL_GRAPH_SVC --> NEO4J_REPO
    JOB_GRAPH_SVC --> NEO4J_REPO
    VECTOR_IDX_SVC --> NEO4J_REPO
    SIMILARITY_SVC --> NEO4J_REPO
    
    %% Auth Service dependencies
    AUTH_SVC --> USER_REPO
    
    %% Intent/Entity services dependencies
    INTENT_SVC --> EMBEDDING_SVC
    ENTITY_SVC --> EMBEDDING_SVC
    ENTITY_SVC --> NEO4J_REPO
    
    style FASTAPI_APP fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style PRISMA fill:#336791,stroke:#1E3A5F,stroke-width:3px,color:#fff
    style NEO4J_DRIVER fill:#00A86B,stroke:#006B45,stroke-width:3px,color:#fff
    style LANGGRAPH_SVC fill:#FF6B6B,stroke:#C23B3B,stroke-width:3px,color:#fff
    style OPENROUTER_SVC fill:#9B59B6,stroke:#6C3483,stroke-width:3px,color:#fff
```

### Dependency Injection Pattern

The application uses FastAPI's dependency injection system for service management:

```python
# backend/app/dependencies.py

from functools import lru_cache
from app.services.langgraph_service import LangGraphService
from app.services.embedding_service import EmbeddingService
# ... other imports

@lru_cache()
def get_langgraph_service() -> LangGraphService:
    """Get cached LangGraph service instance (singleton)."""
    return LangGraphService()

@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get cached Embedding service instance (singleton)."""
    return EmbeddingService()

# Repositories use dependency injection with global database clients
async def get_neo4j_repository() -> Neo4jRepository:
    """Get Neo4j repository with global driver."""
    from app.main import neo4j_driver
    return Neo4jRepository(neo4j_driver)

async def get_user_repository() -> UserRepository:
    """Get User repository with global Prisma client."""
    from app.main import prisma_client
    return UserRepository(prisma_client)
```

**Usage in API endpoints:**
```python
@router.post("/query/ask")
async def ask_question(
    query_data: QueryRequest,
    current_user_id: str = Depends(get_current_user),  # JWT middleware
    langgraph_service: LangGraphService = Depends(get_langgraph_service),  # Singleton
    query_repo: QueryHistoryRepository = Depends(get_query_history_repository)  # Per-request
) -> QueryResponse:
    # Endpoint logic
    pass
```

---

## Deployment Architecture

### Current Deployment (Local Development)

```mermaid
graph TB
    subgraph "Developer Machine Localhost"
        subgraph "Frontend Dev Server"
            VITE[Vite Dev Server<br/>Port 5173<br/>Hot Module Replacement]
            REACT_APP[React Application<br/>Components + Services]
            VITE --> REACT_APP
        end
        
        subgraph "Backend API Server"
            UVICORN[Uvicorn ASGI Server<br/>Port 8000<br/>Auto-reload enabled]
            FASTAPI_APP[FastAPI Application<br/>Routers + Middleware + Services]
            UVICORN --> FASTAPI_APP
        end
        
        subgraph "Environment Configuration"
            ENV_FILE[.env File<br/>Local secrets]
        end
        
        REACT_APP -->|HTTP requests<br/>localhost:8000| FASTAPI_APP
        FASTAPI_APP -.->|Load config| ENV_FILE
    end
    
    subgraph "Cloud Services"
        subgraph "Neo4j Aura Cloud"
            NEO4J_CLOUD[Neo4j Database<br/>Knowledge Graph + Vector Indexes<br/>Connection: neo4j+s://]
        end
        
        subgraph "Managed PostgreSQL"
            POSTGRES_CLOUD[PostgreSQL Database<br/>User data + Query history<br/>Connection: postgresql://]
        end
        
        subgraph "External APIs"
            OPENROUTER_CLOUD[OpenRouter API<br/>LLM Gateway<br/>https://openrouter.ai]
            HF_CLOUD[HuggingFace API<br/>Embedding Model<br/>https://huggingface.co]
        end
    end
    
    FASTAPI_APP -->|Cypher queries<br/>SSL/TLS| NEO4J_CLOUD
    FASTAPI_APP -->|SQL queries<br/>SSL/TLS| POSTGRES_CLOUD
    FASTAPI_APP -->|LLM requests<br/>HTTPS| OPENROUTER_CLOUD
    FASTAPI_APP -->|Embedding requests<br/>HTTPS| HF_CLOUD
    
    style VITE fill:#646CFF,stroke:#4347B8,stroke-width:2px,color:#fff
    style UVICORN fill:#009688,stroke:#00695C,stroke-width:2px,color:#fff
    style NEO4J_CLOUD fill:#00A86B,stroke:#006B45,stroke-width:3px,color:#fff
    style POSTGRES_CLOUD fill:#336791,stroke:#1E3A5F,stroke-width:3px,color:#fff
    style OPENROUTER_CLOUD fill:#9B59B6,stroke:#6C3483,stroke-width:2px,color:#fff
    style HF_CLOUD fill:#FFD21E,stroke:#FFA000,stroke-width:2px,color:#000
```

### Environment Variables

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# Database - PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Database - Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=xxxxx

# Security
JWT_SECRET=your-secret-key-min-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embedding Configuration
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
EMBEDDING_BATCH_SIZE=32
EMBEDDING_RETRY_MAX=3

# CSV Processing
MAX_FILE_SIZE_MB=500
BATCH_SIZE=1000

# Skill Similarity
SIMILARITY_THRESHOLD=0.7
SIMILARITY_TOP_K=5

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Startup Sequence

1. **Environment Validation** (`backend/app/config.py`)
   - Load and validate all environment variables
   - Check format requirements (Neo4j URI, OpenRouter key, JWT secret length)
   - Exit with error code 1 if validation fails

2. **FastAPI Application Initialization** (`backend/app/main.py`)
   - Create FastAPI app instance
   - Register CORS middleware (must be first)
   - Register rate limiter
   - Register error handlers
   - Register API routers (auth, ingest, query, admin, monitor)

3. **Lifespan Startup** (`@asynccontextmanager lifespan`)
   - Connect to PostgreSQL via Prisma (`await prisma_client.connect()`)
   - Initialize Neo4j driver (`AsyncGraphDatabase.driver(...)`)
   - **CRITICAL:** Validate vector indexes (`await validate_neo4j_indexes()`)
     - Check for `skill_embedding_idx`, `job_embedding_idx`, `company_embedding_idx`
     - Verify all indexes are `ONLINE`
     - Fail fast if indexes missing or offline
   - Start APScheduler for file cleanup (every 15 minutes)

4. **Service Initialization** (on first request via dependency injection)
   - LangGraph Service: Compile workflow graph
   - Embedding Service: Load sentence-transformers model
   - OpenRouter Service: Initialize circuit breaker
   - Other services: Initialize as needed

5. **Ready to Serve**
   - Frontend: `npm run dev` (Vite dev server on port 5173)
   - Backend: `uvicorn app.main:app --reload --port 8000`

---

## Monitoring & Observability

### Real-Time Pipeline Monitoring

```mermaid
sequenceDiagram
    participant Frontend
    participant WebSocket as WebSocket Endpoint
    participant Monitor as Pipeline Monitoring Service
    participant LangGraph as LangGraph Workflow
    participant Neo4j as Neo4j Monitoring
    
    Frontend->>WebSocket: Connect WebSocket<br/>ws://localhost:8000/api/monitor/ws
    WebSocket-->>Frontend: Connection established
    
    Note over Frontend,Neo4j: User submits query
    
    Frontend->>LangGraph: POST /api/query/ask
    
    LangGraph->>Monitor: emit_query_understanding({<br/>  status: STARTED,<br/>  session_id, user_id, query<br/>})
    Monitor->>WebSocket: Broadcast event
    WebSocket-->>Frontend: {stage: "query_understanding", status: "started"}
    
    LangGraph->>LangGraph: Execute query_understanding_node
    
    LangGraph->>Monitor: emit_query_understanding({<br/>  status: COMPLETED,<br/>  duration_ms: 45.2,<br/>  intent: "skill_requirement"<br/>})
    Monitor->>WebSocket: Broadcast event
    WebSocket-->>Frontend: {stage: "query_understanding", status: "completed", duration_ms: 45.2}
    
    LangGraph->>Monitor: emit_vector_search({<br/>  status: STARTED<br/>})
    Monitor->>WebSocket: Broadcast event
    WebSocket-->>Frontend: {stage: "vector_search", status: "started"}
    
    LangGraph->>Neo4j: Vector similarity search
    Neo4j->>Neo4j: Log query to neo4j_query_logs<br/>operation_type: VECTOR_SEARCH
    
    LangGraph->>Monitor: emit_vector_search({<br/>  status: COMPLETED,<br/>  duration_ms: 78.3,<br/>  skills_found: 8,<br/>  jobs_found: 5,<br/>  companies_found: 2<br/>})
    Monitor->>WebSocket: Broadcast event
    WebSocket-->>Frontend: {stage: "vector_search", status: "completed", results: {...}}
    
    Note over LangGraph,Neo4j: Similar events for graph_traversal, context_construction, response_generation
    
    LangGraph-->>Frontend: Final QueryResponse
    Frontend->>Frontend: Display response + timeline
```

### Metrics Collection

**Query Metrics** (`backend/app/utils/metrics.py`):
```python
class QueryMetrics:
    def __init__(self, query_id: str, user_id: str, query_text: str):
        self.query_id = query_id
        self.user_id = user_id
        self.query_text = query_text
        self.timings = {}  # {stage_name: duration_ms}
        self.start_times = {}  # {stage_name: start_timestamp}
    
    def start_timer(self, stage: str):
        self.start_times[stage] = time.time()
    
    def end_timer(self, stage: str) -> float:
        duration_ms = (time.time() - self.start_times[stage]) * 1000
        self.timings[stage] = duration_ms
        return duration_ms
    
    def get_total_time(self) -> float:
        return sum(self.timings.values())
    
    def to_dict(self) -> dict:
        return {
            "query_id": self.query_id,
            "user_id": self.user_id,
            "timings": self.timings,
            "total_time_ms": self.get_total_time()
        }
```

**Neo4j Query Logging** (`backend/app/models/neo4j_query_logs` table):
- Logs every Cypher query executed
- Captures execution time, result count, status
- Tracks operation type: `READ`, `WRITE`, `VECTOR_SEARCH`, `GRAPH_TRAVERSAL`
- Enables performance analysis and slow query detection

---

## Security Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API as /api/auth/login
    participant AuthService
    participant UserRepo
    participant PostgreSQL
    
    User->>Frontend: Enter email + password
    Frontend->>API: POST /api/auth/login<br/>{email, password}
    
    API->>AuthService: authenticate_user(email, password)
    AuthService->>UserRepo: find_by_email(email)
    UserRepo->>PostgreSQL: SELECT * FROM users WHERE email = ?
    PostgreSQL-->>UserRepo: User record (with password_hash)
    UserRepo-->>AuthService: User object
    
    AuthService->>AuthService: bcrypt.checkpw(<br/>  password.encode(),<br/>  user.password_hash.encode()<br/>)
    
    alt Password valid
        AuthService->>AuthService: Generate JWT token<br/>jwt.encode({<br/>  user_id: user.id,<br/>  email: user.email,<br/>  exp: now + 24h<br/>}, JWT_SECRET, HS256)
        
        AuthService-->>API: {access_token, user}
        API-->>Frontend: 200 OK<br/>{access_token, token_type: "bearer", user}
        Frontend->>Frontend: Store token in localStorage
        Frontend-->>User: Redirect to /chat
    else Password invalid
        AuthService-->>API: None
        API-->>Frontend: 401 Unauthorized<br/>{detail: "Invalid email or password"}
        Frontend-->>User: Show error message
    end
```

### JWT Token Structure

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "exp": 1730304000
  },
  "signature": "HMACSHA256(base64UrlEncode(header) + \".\" + base64UrlEncode(payload), JWT_SECRET)"
}
```

### Security Measures

| Layer | Security Control | Implementation |
|-------|-----------------|----------------|
| **Transport** | HTTPS (Production) | SSL/TLS for all external connections |
| **Authentication** | JWT tokens | HS256 algorithm, 24-hour expiration |
| **Password Storage** | bcrypt hashing | Salted hashes, minimum 8 characters |
| **Rate Limiting** | SlowAPI | 10 requests/minute per IP for `/api/query/ask` |
| **CORS** | Origin whitelist | Only `localhost:5173` and `localhost:3000` allowed |
| **Input Validation** | Pydantic models | Strict type checking and validation |
| **SQL Injection** | Prisma ORM | Parameterized queries, type-safe |
| **NoSQL Injection** | Neo4j driver | Parameterized Cypher queries |
| **Error Handling** | Custom middleware | Sanitized error messages (no stack traces to client) |
| **Secret Management** | Environment variables | `.env` file (gitignored), validated on startup |
| **Session Security** | Stateless JWT | No server-side session storage |
| **Access Control** | User-based isolation | Users can only access their own queries/history |

---

## Performance Characteristics

### Query Processing Breakdown

| Stage | Typical Duration | Description |
|-------|-----------------|-------------|
| **Query Understanding** | 40-80ms | Embedding generation + entity extraction + intent classification |
| **Vector Search** | 40-100ms | Parallel HNSW index search across 3 node types |
| **Graph Traversal** | 80-200ms | Cypher query execution with 2-3 hop traversal |
| **Context Construction** | 20-50ms | Formatting + token counting |
| **Response Generation** | 800-1500ms | OpenRouter LLM API call (network + inference) |
| **Total** | **1000-2000ms** | End-to-end query processing |

### System Performance Targets

| Metric | Target | Current Performance |
|--------|--------|---------------------|
| **Query Response Time** | <5 seconds | 1-2 seconds (typical) |
| **CSV Ingestion (50K records)** | 5-10 minutes | ~8 minutes |
| **Concurrent Users** | 10+ | Tested with 10 |
| **Vector Search** | <100ms | 40-100ms |
| **Graph Traversal** | <200ms | 80-200ms |
| **Database Connections** | Connection pooling | Active |
| **API Throughput** | 10 requests/min/user | Rate limited |

### Optimization Strategies

1. **Embedding Generation:**
   - Batch API calls (32-64 texts per request)
   - Cache frequently used embeddings

2. **Neo4j Queries:**
   - HNSW vector indexes for O(log n) search
   - Connection pooling for reuse
   - Optimized Cypher queries with LIMIT clauses

3. **LLM API:**
   - Circuit breaker pattern (fail fast after 3 failures)
   - Retry logic with exponential backoff
   - Timeout: 200 seconds for reasoning models

4. **Context Construction:**
   - Token counting to avoid exceeding limits
   - Progressive truncation strategy
   - Template-based formatting (no redundant computations)

5. **Frontend:**
   - Optimistic UI updates
   - WebSocket for real-time monitoring
   - Debounced input handling

---

## Technical Debt & Known Issues

### Current Limitations

1. **No Streaming Responses:**
   - LLM responses are returned in full after completion
   - **Impact:** Users wait ~1-2 seconds without feedback during LLM generation
   - **Mitigation:** WebSocket monitoring shows pipeline progress

2. **Session Expiration:**
   - Conversations expire after 24 hours of inactivity
   - **Impact:** Long-lived sessions may lose context
   - **Mitigation:** Clear documentation, user notification on expiration

3. **Single-Threaded CSV Processing:**
   - Batch processing is sequential (not parallel)
   - **Impact:** Large datasets (100K+ records) take 15-20 minutes
   - **Mitigation:** Batch size optimization, progress tracking

4. **No Caching Layer:**
   - Frequently asked questions re-execute full RAG pipeline
   - **Impact:** Increased latency and API costs for repeated queries
   - **Mitigation:** Future Redis cache for query results

5. **Limited Error Recovery:**
   - LangGraph workflow fails entirely if any node fails
   - **Impact:** Single node failure aborts entire query
   - **Mitigation:** Retry logic in OpenRouter service, error state detection in response generation node

### Future Enhancements

1. **Query Result Caching** - Redis cache for frequently asked questions
2. **Streaming LLM Responses** - Server-Sent Events (SSE) or WebSocket streaming
3. **Parallel CSV Ingestion** - Multi-process batch processing
4. **Advanced Intent Routing** - Conditional edges in LangGraph based on query complexity
5. **User Skill Profiles** - Store user's current skills for personalized recommendations
6. **Career Path Visualization** - Graph visualization UI for skill progression
7. **Salary Prediction Model** - ML model for salary estimation based on skills + experience

---

## Appendix: Key File Locations

### Backend

| Component | File Path |
|-----------|-----------|
| **Main Application** | `backend/app/main.py` |
| **Configuration** | `backend/app/config.py` |
| **LangGraph Workflow** | `backend/app/agents/graph.py` |
| **Query Understanding Node** | `backend/app/agents/nodes/query_understanding.py` |
| **Vector Search Node** | `backend/app/agents/nodes/vector_search.py` |
| **Graph Traversal Node** | `backend/app/agents/nodes/graph_traversal.py` |
| **Context Construction Node** | `backend/app/agents/nodes/context_construction.py` |
| **Response Generation Node** | `backend/app/agents/nodes/response_generation.py` |
| **Query API** | `backend/app/api/query.py` |
| **Ingestion API** | `backend/app/api/ingest.py` |
| **Auth API** | `backend/app/api/auth.py` |
| **LangGraph Service** | `backend/app/services/langgraph_service.py` |
| **Embedding Service** | `backend/app/services/embedding_service.py` |
| **OpenRouter Service** | `backend/app/services/openrouter_service.py` |
| **Neo4j Repository** | `backend/app/repositories/neo4j_repository.py` |
| **Prisma Schema** | `backend/prisma/schema.prisma` |
| **Dependencies** | `backend/app/dependencies.py` |
| **Metrics** | `backend/app/utils/metrics.py` |

### Frontend

| Component | File Path |
|-----------|-----------|
| **Main Application** | `frontend/src/App.jsx` |
| **Chat Page** | `frontend/src/pages/Chat.jsx` |
| **Upload Page** | `frontend/src/pages/UploadPage.jsx` |
| **Login Page** | `frontend/src/pages/Login.jsx` |
| **Chat Input** | `frontend/src/components/Chat/ChatInput.jsx` |
| **Assistant Message** | `frontend/src/components/Chat/AssistantMessage.jsx` |
| **Source Citations** | `frontend/src/components/Chat/SourceCitations.jsx` |
| **File Upload Zone** | `frontend/src/components/FileUploadZone.jsx` |
| **Ingestion Progress** | `frontend/src/components/IngestionProgress.jsx` |
| **useChat Hook** | `frontend/src/hooks/useChat.ts` |
| **API Service** | `frontend/src/services/api.js` |
| **API Constants** | `frontend/src/constants/api.ts` |

---

## Document Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-10-29 | 2.0 | Complete architecture documentation with comprehensive Mermaid diagrams | Winston (Architect Agent) |
| 2025-10-15 | 1.0 | Initial architecture document in PRD | John (PM Agent) |

---

**End of Comprehensive Architecture Documentation**

---

