# Requirements

## Functional Requirements

### Authentication (FastAPI)
**FR1:** System shall provide user registration and login with email + password, storing user accounts in PostgreSQL via Prisma ORM and generating JWT tokens for session management

**FR2:** System shall expose FastAPI endpoint `/auth/register` for user registration and `/auth/login` for authentication

### Ingestion Pipeline (FastAPI)
**FR3:** System shall accept CSV file uploads via FastAPI endpoints `/ingest/skills` and `/ingest/jobs`:
- **Skills CSV (17 fields)**: ID, NAME, LEVEL, SUBCATEGORY, SUBCATEGORY_NAME, CATEGORY, CATEGORY_NAME, TYPE, IS_SOFTWARE, IS_LANGUAGE, WIKI_LINK, WIKI_EXTRACT, DESCRIPTION, DESCRIPTION_SOURCE, VERSION, LATEST_VERSION, embeddings
- **Jobs CSV (30 fields)**: Job Title, Company Name, Location, Via, Salary, Posted At, Schedule Type, Work From Home, Description, Apply Options, Job ID, District, Company Description, Job Description, Exact Matched Company, CIN, CompanyIndustrialClassification, NCO_Code_algo, NIC_Code_algo, Description Token Count, Company Description Token Count, Job Description Token Count, nic_code_2_2008, Minimum Salary, Maximum Salary, Mean Salary, Unit of Measure, skills, standardized_skills, similarity_scores

**FR4:** System shall validate CSV format and required columns before processing, returning validation errors if format is incorrect

**FR5:** System shall process CSV files in batches (500-1000 records per batch) with progress tracking

### Embedding Generation
**FR6:** System shall generate fresh embeddings during ingestion (ignoring pre-existing CSV embeddings) using Hugging Face `all-MiniLM-L6-v2` model (384-dimensional) for:
- Job fields: Job Description (primary), Description (fallback)
- Skill fields: DESCRIPTION (primary), WIKI_EXTRACT (secondary)
- Company fields: Company Description

**FR7:** System shall batch embedding generation (32-64 texts per API call) for efficiency

**FR8:** System shall store generated embeddings as node properties in Neo4j for vector search

### Knowledge Graph Construction (Neo4j)
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

### Query Pipeline (FastAPI + LangGraph)
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

### Frontend (React)
**FR23:** System shall provide React frontend with login/registration pages

**FR24:** System shall provide CSV upload interface with drag-and-drop for skills and jobs files

**FR25:** System shall display ingestion progress with records processed/failed counts

**FR26:** System shall provide chat interface for natural language queries

**FR27:** System shall display LLM responses in chat format with message history

### System Health
**FR28:** System shall expose `/health` endpoint for health checks

## Non-Functional Requirements

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
