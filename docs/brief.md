# Project Brief: Graph RAG System for Skills & Jobs Knowledge Graph

## Executive Summary

**Graph RAG System for Skills & Jobs Knowledge Graph**

A knowledge graph-powered RAG (Retrieval-Augmented Generation) system that ingests skills and job market data from CSV files, creates semantic relationships in a Neo4j graph database, and provides conversational AI-powered insights through a chat interface. The system enables users to explore career paths, understand skill requirements, and discover job opportunities through natural language queries backed by hybrid vector and graph search.

**Primary Problem:** Job seekers and career planners lack an intelligent, conversational way to understand the relationships between skills, job requirements, and career progression paths using real market data.

**Target Market:** Individual users seeking career guidance, skill development planning, and job market insights.

**Key Value Proposition:** Natural language access to rich, relationship-aware job and skills data that goes beyond simple keyword matching, providing context-aware career intelligence through AI-powered conversations.

---

## Problem Statement

**Current State & Pain Points:**

Career planning and skill development today rely on fragmented, disconnected data sources. Job seekers face several critical challenges:

1. **Disconnected Information** - Job postings list required skills, but there's no easy way to understand how skills relate to each other, which skills are foundational vs. specialized, or what learning paths exist between skill sets.

2. **Static Search Limitations** - Traditional job search platforms use keyword matching that misses semantic relationships. Searching for "Python" won't surface related opportunities requiring similar skills like data analysis, API development, or automation.

3. **Hidden Career Paths** - Understanding career progression requires manual research across multiple sources. There's no systematic way to ask "What jobs can I get with my current skills?" or "What skills do I need to transition from X to Y role?"

4. **Salary & Market Intelligence Gaps** - Compensation data exists in isolation from skill requirements and job relationships, making it hard to understand the market value of specific skill combinations.

5. **No Conversational Access** - Users must navigate complex filters and forms rather than simply asking questions in natural language like "What are high-paying jobs in my city that use .NET?"

**Impact of the Problem:**

- Career decisions made with incomplete information lead to suboptimal skill investment
- Job seekers miss opportunities that don't match exact keyword searches
- Time wasted manually connecting dots between skills, jobs, companies, and locations
- Difficulty quantifying ROI of learning new skills

**Why Existing Solutions Fall Short:**

- **Job boards (LinkedIn, Indeed)** - Focus on job matching, not skill relationships or career intelligence
- **Skill platforms (Coursera, Udemy)** - Provide learning paths but lack real job market data integration
- **Career counseling** - Human-intensive, expensive, not data-driven or scalable
- **Simple chatbots** - Use basic keyword matching without understanding semantic relationships in a knowledge graph

**Urgency & Importance:**

The rapid evolution of the job market (AI disruption, remote work, skill shifts) makes career adaptability critical. Workers need intelligent, data-driven tools to navigate career decisions quickly. This is an internal MVP to validate whether graph-based RAG can provide superior career intelligence compared to traditional search and filtering approaches.

---

## Proposed Solution

**Core Concept:**

A LangGraph-based RAG system that combines knowledge graph relationships with semantic embeddings to answer natural language career questions. The solution consists of two main pipelines:

1. **Ingestion Pipeline** - CSV data → embedding → Neo4j knowledge graph construction
2. **Query Pipeline** - User question → embedding → hybrid search (vector + graph traversal) → LLM response generation

**Key Differentiators:**

- **Relationship-Aware Intelligence** - Unlike keyword search, the system understands semantic connections between skills, jobs, companies, and locations through the knowledge graph
- **Hybrid Search** - Combines vector similarity (semantic understanding) with graph traversal (relationship exploration) for richer context retrieval
- **Conversational Interface** - Natural language queries eliminate the learning curve of complex filter interfaces
- **Real Market Data** - Grounded in actual job postings and comprehensive skill taxonomies, not synthetic or outdated information

**Why This Will Succeed:**

- **Graph structure captures domain reality** - Skills and jobs naturally form a relationship network, making graph representation more powerful than flat databases
- **LangGraph orchestration** - Enables complex multi-step reasoning workflows (query understanding → graph traversal → answer synthesis)
- **Proven tech stack** - Neo4j, FastAPI, React, and OpenRouter API are battle-tested, reducing technical risk
- **Simple MVP scope** - Focused on core ingestion + query functionality without overengineering

**High-Level Product Vision:**

Users log in to a clean chat interface, ask questions about careers/skills/jobs in plain English, and receive intelligent answers backed by knowledge graph exploration. Behind the scenes, LangGraph agents orchestrate hybrid search and response generation, surfacing insights that would require hours of manual research.

---

## Target Users

### Primary User Segment: Career Planners & Job Seekers

**Demographic Profile:**
- Working professionals (25-45 years old) exploring career transitions or skill development
- Students/recent graduates planning career entry strategies
- Technical and non-technical backgrounds (system handles diverse job taxonomies)
- Self-directed learners comfortable with digital tools

**Current Behaviors & Workflows:**
- Manually browse job boards to understand market demand
- Google searches for "skills needed for X job"
- Ask friends/colleagues about career paths
- Read blog posts and LinkedIn articles about skill development
- Struggle to synthesize information from multiple disconnected sources

**Specific Needs & Pain Points:**
- Need to understand skill adjacencies ("What else should I learn if I know Python?")
- Want salary insights for specific skill combinations
- Seek efficient way to explore "what if" career scenarios
- Frustrated by information overload and fragmented data sources

**Goals They're Trying to Achieve:**
- Make informed decisions about skill investment (courses, certifications)
- Identify realistic career transition paths from current skills
- Understand market value of different skill combinations
- Discover job opportunities they wouldn't find through keyword search

---

## Goals & Success Metrics

### Business Objectives

- **Validate Graph RAG Approach** - Demonstrate that graph + vector hybrid search provides superior career insights vs. traditional keyword search (qualitative user feedback)
- **Technical Feasibility** - Prove LangGraph + Neo4j + embeddings architecture can handle ingestion and query workflows within reasonable performance bounds (<5 sec query response)
- **Foundation for Future Work** - Create reusable patterns for knowledge graph RAG that can extend to other domains

### User Success Metrics

- **Query Satisfaction** - Users find answers helpful and actionable (subjective feedback during testing)
- **Conversational Quality** - System handles diverse natural language queries without requiring specific syntax
- **Insight Discovery** - Users discover non-obvious connections (skills, jobs, companies) they wouldn't find through manual search

### Key Performance Indicators (KPIs)

- **Ingestion Success Rate**: 100% of CSV records successfully embedded and stored in Neo4j
- **Query Response Time**: <5 seconds for typical natural language queries (95th percentile)
- **System Uptime**: >95% availability during testing period
- **Graph Query Coverage**: System can answer queries across all relationship types (Job-Skill, Skill-Company, Location-Salary, etc.)

---

## MVP Scope

### Core Features (Must Have)

- **CSV Ingestion Pipeline:**
  - Upload skills taxonomy CSV (ID, NAME, LEVEL, CATEGORY, SUBCATEGORY, TYPE, IS_SOFTWARE, IS_LANGUAGE, WIKI_LINK, WIKI_EXTRACT, DESCRIPTION, embeddings)
  - Upload jobs taxonomy CSV (Job Title, Company Name, Location, Salary, Description, Skills, Standardized_Skills, etc.)
  - **CSV Validation** (pre-ingestion checks):
    - Validate CSV format, required columns, data types
    - Show validation errors before starting ingestion
    - Preview first 5-10 rows for user confirmation
  - **Chunking/Batching Strategy** (for large datasets ~40-50K records):
    - Process CSV in batches (adaptive batch size based on data volume and performance)
    - Real-time progress UI with stats (records processed, failed, estimated time remaining)
    - Batch embeddings generation (send multiple texts to embedding model at once)
    - Use Neo4j batch transactions (commit every N records to avoid memory issues)
    - Error handling: If chunk fails, log errors and continue (retry option for failed chunks)
  - **Embedding Generation** (always generate fresh embeddings during ingestion):
    - Ignore any pre-existing embeddings in CSV (not reliable/consistent format)
    - Embed job fields: `Job Description` (primary), `Description` (fallback if Job Description empty)
    - Embed skill fields: `DESCRIPTION` (primary), `WIKI_EXTRACT` (secondary for enhanced context)
    - Embed company fields: `Company Description` (for company-based queries)
    - Use `all-MiniLM-L6-v2` from Hugging Face (384-dimensional embeddings)
    - Batch processing: 32-64 texts per embedding API call for efficiency
  - **Skill Matching Logic**:
    - Skills taxonomy: Create `Skill` nodes from `NAME` field with normalization (lowercase, trim)
    - Jobs taxonomy: Parse `standardized_skills` list, match against existing `Skill` nodes using normalized string matching
    - Example: Job's `standardized_skills: ["Python", ".NET"]` → matches Skills taxonomy `NAME: "Python"` and `NAME: ".NET"`
    - **Handle unmatched skills**: Create orphan `Skill` nodes with only NAME property (no metadata), log for review
  - Create knowledge graph in Neo4j with relationships:
    - Job -[REQUIRES]-> Skill (via standardized_skills matching)
    - Job -[POSTED_BY]-> Company
    - Job -[LOCATED_IN]-> Location
    - Skill -[SIMILAR_TO]-> Skill (based on embeddings/taxonomy)
    - Skill -[BELONGS_TO_CATEGORY]-> Category
    - Skill -[BELONGS_TO_SUBCATEGORY]-> Subcategory
  - **Incremental Updates Strategy**:
    - Upsert mode: Update existing nodes (match by Job ID or Skill ID) + insert new records
    - Duplicate detection: Match by unique identifiers (Job ID for jobs, Skill ID for skills)
    - Update behavior: Overwrite existing properties with new data from CSV
    - Relationship handling: Replace existing relationships for updated nodes

- **Query Pipeline with LangGraph:**
  - Natural language query understanding
  - Hybrid search: Vector similarity search on embeddings + graph traversal for relationships
  - LLM (OpenRouter API) response generation with retrieved context
  - Basic conversational memory (maintain context within session)

- **Chat-Based Frontend (React):**
  - Simple login with JWT authentication (email + password)
  - **CSV Upload Interface**:
    - Drag-and-drop or file picker for CSV upload
    - Pre-ingestion validation with error display
    - Preview first 5-10 rows before confirming ingestion
    - Real-time progress bar with detailed stats (processed/failed/total, estimated time)
    - Error log download for failed records
    - Ingestion status tracking per file
  - Chat interface for conversational queries (human-like interaction)
  - Display responses in readable format (no graph visualization for MVP)
  - Show sources/citations from knowledge graph in responses

- **Backend API (FastAPI):**
  - `/auth/login` - JWT-based authentication
  - `/ingest/skills` - Upload and process skills CSV (frontend + API endpoint)
  - `/ingest/jobs` - Upload and process jobs CSV (frontend + API endpoint)
  - `/query` - Natural language query endpoint
  - `/health` - System health check

- **Environment Configuration:**
  - `.env` file with:
    - `NEO4J_URI` - Neo4j connection string (Aura cloud or local)
    - `NEO4J_USERNAME` - Database username
    - `NEO4J_PASSWORD` - Database password
    - `OPENROUTER_API_KEY` - OpenRouter API key for LLM access
    - `EMBEDDING_MODEL` - Hugging Face model name (default: `all-MiniLM-L6-v2`)
    - `JWT_SECRET` - Secret key for JWT token generation
    - `BATCH_SIZE` - Optional: CSV processing batch size (default: adaptive)
  - Simple deployment instructions (local development focus)

### Out of Scope for MVP

- User profile creation or resume upload
- Graph visualization UI
- Advanced analytics or trend analysis
- Multi-user collaboration features
- Role-based access control (beyond basic auth)
- Mobile app or responsive design optimization
- Integration with external job boards or APIs
- Skill recommendation engine
- Career path visualization
- Automated alerts or notifications
- Export functionality (reports, PDFs)
- Admin dashboard for data management
- Advanced caching or performance optimization
- Production-grade security hardening
- Multi-language support
- Accessibility compliance (WCAG)

### MVP Success Criteria

**The MVP is successful if:**

1. Users can ingest both CSV files via frontend UI and confirm data appears correctly in Neo4j
2. Users can ask natural language questions and receive relevant, context-aware answers
3. The system demonstrates full value of graph relationships:
   - Example query: "What skills do I need to learn for Data Scientist roles?"
   - Returns: Connected skills (not just keyword matches), skill relationships, relevant companies hiring, salary insights, and full career potential analysis
   - Leverages skill adjacency, company metadata, compensation data, and multi-dimensional graph traversal
4. The technical architecture is solid enough to extend post-MVP

---

## Post-MVP Vision

### Phase 2 Features

- **Resume Upload & Profile Matching** - Users upload resumes/CVs, system extracts skills and suggests career paths
- **Graph Visualization** - Interactive visualization of skill/job relationships
- **Advanced Analytics** - Salary trends by skill, demand forecasting, skill gap analysis
- **Skill Recommendations** - Proactive suggestions for adjacent skills to learn based on current profile
- **Career Path Explorer** - Visual representation of possible career transitions with skill requirements
- **Source Diversity** - Ingest data from multiple job boards (LinkedIn, Indeed) via APIs

### Long-term Vision (1-2 years)

Transform into a comprehensive career intelligence platform that:
- Provides personalized, proactive career guidance using AI agents
- Integrates learning resources (courses, certifications) matched to skill gaps
- Offers workforce analytics for enterprise clients (talent planning, skill forecasting)
- Becomes the "career GPS" - continually updated with market data, guiding users through dynamic career landscapes

### Expansion Opportunities

- **Enterprise SaaS** - Workforce planning and talent analytics for HR teams
- **Educational Institutions** - Career services platform for universities
- **Government/Policy** - Labor market analysis and workforce development insights
- **API Marketplace** - Offer career intelligence API to third-party developers

---

## Technical Considerations

### Platform Requirements

- **Target Platforms:** Web application (desktop browsers primary, mobile-friendly secondary)
- **Browser Support:** Modern browsers (Chrome, Firefox, Safari, Edge - last 2 versions)
- **Performance Requirements:**
  - Query response time: Acceptable for conversational flow (varies by query complexity)
  - Support concurrent users (10+ for MVP testing)
  - **CSV ingestion processing time**: ~5-10 minutes for 50K records (batch processing with progress tracking)
  - **Chunk size**: 500-1000 records per batch
  - **Embedding throughput**: Batch embedding generation to optimize API calls

### Technology Preferences

**Frontend:**
- **Framework:** React (functional components, hooks)
- **Styling:** TailwindCSS or Material-UI (simple, clean chat interface)
- **State Management:** React Context API or Zustand (lightweight)
- **HTTP Client:** Axios or Fetch API

**Backend:**
- **Framework:** FastAPI (Python)
- **LLM Orchestration:** LangGraph for agent workflows
- **LLM Provider:** OpenRouter API (access to multiple models: GPT-4, Claude, Llama, etc.)
- **Embeddings:** Hugging Face `all-MiniLM-L6-v2` model
- **Authentication:** JWT with PyJWT

**Database:**
- **Graph Database:** Neo4j Aura (cloud-hosted) or Neo4j via connection URI
- **Vector Storage:** Neo4j vector indexes (native support for embeddings)
- **Connection:** Via Neo4j URI from `.env` file (supports Aura, self-hosted, or Docker)

**Infrastructure:**
- **Deployment:** Local development environment (Docker Compose for backend services)
- **Neo4j:** Cloud (Aura) or containerized via Docker
- **Hosting:** Not required for MVP (local frontend + backend)
- **Environment Management:** `.env` files for configuration (Neo4j URI, OpenRouter key, JWT secret)

### Architecture Considerations

**Repository Structure:**
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

**Service Architecture:**
- Monolithic API (FastAPI) - no microservices for MVP
- Direct Neo4j connection from backend (no ORM complexity)
- Stateless API design (JWT for auth, no session storage)

**Integration Requirements:**
- OpenRouter API for LLM responses (unified gateway to multiple LLM providers)
- Hugging Face for embedding model (can run locally or via API)
- Neo4j database connection

**Security/Compliance:**
- Basic JWT authentication (not production-grade)
- No encryption at rest (local development)
- No HTTPS required (local only)
- Environment variables for secrets (`.env` file)
- **Internal project only - minimal security hardening**

---

## Constraints & Assumptions

### Constraints

**Budget:**
- API costs only (OpenRouter usage ~$10-50 for testing)
- No paid infrastructure or hosting

**Timeline:**
- MVP development timeframe: Not specified (flexible internal project)
- Focus on functionality over polish

**Resources:**
- Single developer
- No dedicated QA or design resources
- Self-managed infrastructure (local)

**Technical:**
- Python/JavaScript/TypeScript tech stack only
- OpenRouter API dependency (unified LLM gateway - no local LLM for MVP)
- Neo4j required (no alternative graph databases)
- CSV input format fixed (structured data sources)

### Key Assumptions

- OpenRouter API costs remain reasonable for MVP testing volume
- CSV data quality is sufficient (minimal cleaning/validation needed)
- **`standardized_skills` in jobs CSV already normalized to match `NAME` field in skills CSV** (pre-processed alignment)
- Skill and job taxonomies have enough relationship richness for valuable graph traversal
- Users have basic technical literacy (can use chat interfaces and file upload)
- Neo4j Community Edition has sufficient performance for MVP data volumes
- Local development environment is sufficient (no cloud deployment needed)
- Single-user testing is adequate for initial validation
- LangGraph provides sufficient flexibility for RAG workflow orchestration

---

## Risks & Open Questions

### Key Risks

- **Data Quality Risk:** CSV data may have inconsistencies, missing values, or poor skill-job mappings → Could result in weak graph relationships and poor query results
- **Embedding Quality Risk:** `all-MiniLM-L6-v2` may not capture domain-specific semantics well → Queries might miss relevant results due to poor semantic matching
- **LLM Hallucination Risk:** OpenRouter LLMs may generate plausible but incorrect career advice when context is insufficient → Users could receive misleading guidance
- **Performance Risk:** Graph traversal + vector search + LLM generation could impact response times → User experience variability depending on query complexity
- **Scope Creep Risk:** "Simple MVP" could expand with feature requests → Delays completion and increases complexity
- **API Cost Risk:** OpenRouter usage could become expensive with extensive testing → Budget overrun or need to optimize model selection

### Open Questions

- **Data volumes confirmed**: ~40-50K job records, ~10K+ skill records
- **CSV update frequency**: Weekly updates (manual re-upload via UI)
- **Query optimization**: General conversational interface (no specific query type prioritization)
- Should the system support multi-turn conversations with complex follow-ups? (Assumed: Yes, basic session context)
- What level of explainability is needed? (Assumed: Show source nodes/relationships used in response)
- Should we track query analytics (what users ask, success rates)? (Deferred to post-MVP)

### Areas Needing Further Research

- **Hybrid Search Strategy:** Optimal balance between vector similarity and graph traversal - what ratio/weighting?
- **Graph Schema Design:** Best practices for modeling skills/jobs/companies in Neo4j for this use case
- **LangGraph Patterns:** Effective agent design patterns for RAG workflows (planning → retrieval → synthesis)
- **Embedding Fine-tuning:** Whether domain-specific fine-tuning of embedding model would significantly improve results
- **Query Optimization:** Neo4j query patterns and indexing strategies for fast graph traversal
- **Context Window Management:** How much graph context to include in LLM prompts without exceeding token limits

---

## Appendices

### A. Data Schema & Structure

#### Job CSV Schema (30 fields)

| Field Name | Type | Description | Graph Usage |
|------------|------|-------------|-------------|
| Job Title | String | Job position name | Job node property |
| Company Name | String | Employer name | Create Company node |
| Location | String | Job location | Create Location node |
| Via | String | Job posting source | Job node property |
| Salary | String | Salary range text | Job node property |
| Posted At | DateTime | Job posting date | Job node property |
| Schedule Type | String | Full-time/Part-time | Job node property |
| Work From Home | Boolean | Remote work flag (0/1) | Job node property |
| Description | Text | Full job description | Job node property + embedding |
| Apply Options | String | Application link/method | Job node property |
| Job ID | String | Unique job identifier | Job node ID (primary key) |
| District | String | Geographic district | Location metadata |
| Company Description | Text | Company overview | Company node property + embedding |
| Job Description | Text | Detailed job description | Job node property + embedding |
| Exact Matched Company | String | Validated company name | Company matching |
| CIN | String | Corporate Identification Number | Company node property |
| CompanyIndustrialClassification | String | Industry classification | Company node property |
| NCO_Code_algo | String | National Classification of Occupations | Job node property |
| NIC_Code_algo | String | National Industrial Classification | Company node property |
| Description Token Count | Integer | Token count for description | Metadata |
| Company Description Token Count | Integer | Token count for company desc | Metadata |
| Job Description Token Count | Integer | Token count for job desc | Metadata |
| nic_code_2_2008 | String | NIC 2008 classification code | Company node property |
| Minimum Salary | Float | Minimum salary value | Job node property |
| Maximum Salary | Float | Maximum salary value | Job node property |
| Mean Salary | Float | Average salary | Job node property |
| Unit of Measure | String | Salary unit (annual/monthly) | Job node property |
| skills | List[String] | Raw skill mentions | Reference only |
| **standardized_skills** | **List[String]** | **Normalized skill names** | **PRIMARY JOIN KEY** |
| similarity_scores | List[Float] | Pre-computed skill match scores (purpose unclear - will be stored as metadata on REQUIRES relationship if available) | Optional relationship property |

#### Skill CSV Schema (17 fields)

| Field Name | Type | Description | Graph Usage |
|------------|------|-------------|-------------|
| ID | String | Unique skill identifier | Skill node ID (primary key) |
| **NAME** | **String** | **Canonical skill name** | **PRIMARY JOIN KEY** |
| LEVEL | Integer | Skill complexity level (1-5) | Skill node property |
| SUBCATEGORY | String | Subcategory ID | Create Subcategory node |
| SUBCATEGORY_NAME | String | Subcategory name | Subcategory node property |
| CATEGORY | String | Category ID | Create Category node |
| CATEGORY_NAME | String | Category name | Category node property |
| TYPE | String | Skill type classification | Skill node property |
| IS_SOFTWARE | Boolean | Software skill flag | Skill node property |
| IS_LANGUAGE | Boolean | Programming language flag | Skill node property |
| WIKI_LINK | String | Wikipedia reference URL | Skill node property |
| WIKI_EXTRACT | Text | Wikipedia summary | Skill node property + embedding |
| DESCRIPTION | Text | Skill description | Skill node property + embedding |
| DESCRIPTION_SOURCE | String | Description origin | Metadata |
| VERSION | String | Taxonomy version | Metadata |
| LATEST_VERSION | Boolean | Is latest version flag | Metadata |
| embeddings | Vector | Pre-computed embeddings | Vector index for similarity search |

#### Primary Join Relationship

```
Job CSV: standardized_skills = ["Python", "FastAPI", "Neo4j"]
                ↓ (normalize & match)
Skill CSV: NAME = "Python", "FastAPI", "Neo4j"
                ↓
Neo4j: Job -[REQUIRES {similarity_score: 0.95}]-> Skill
```

**Matching Logic:**
1. Parse `standardized_skills` list from job CSV (array of skill names)
2. For each skill name, normalize: `skill.lower().strip()`
3. Match against Skill nodes: `WHERE toLower(s.NAME) = normalized_name`
4. Create `REQUIRES` relationship
   - If `similarity_scores` list exists and aligns with `standardized_skills` (same length/order), store as relationship property
   - Similarity scores appear to be pre-computed confidence scores for skill matches (0.0-1.0 range likely)
5. Log unmatched skills for data quality review

#### Neo4j Graph Schema

**Node Types:**

1. **Job** (from Job CSV)
   - Properties: Job Title, Salary, Posted At, Description, Job ID, NCO_Code_algo, etc.
   - Relationships: -[REQUIRES]-> Skill, -[POSTED_BY]-> Company, -[LOCATED_IN]-> Location

2. **Skill** (from Skill CSV)
   - Properties: ID, NAME, LEVEL, TYPE, IS_SOFTWARE, IS_LANGUAGE, DESCRIPTION, embeddings
   - Relationships: -[BELONGS_TO_CATEGORY]-> Category, -[BELONGS_TO_SUBCATEGORY]-> Subcategory, -[SIMILAR_TO]-> Skill

3. **Company** (from Job CSV: Company Name, CIN, CompanyIndustrialClassification)
   - Properties: Company Name, CIN, NIC codes, Company Description
   - Relationships: -[EMPLOYS]-> Job, -[IN_INDUSTRY]-> Industry

4. **Location** (from Job CSV: Location, District)
   - Properties: Location name, District
   - Relationships: -[HAS_JOB]-> Job

5. **Category** (from Skill CSV: CATEGORY, CATEGORY_NAME)
   - Properties: CATEGORY (ID), CATEGORY_NAME
   - Relationships: -[CONTAINS]-> Subcategory

6. **Subcategory** (from Skill CSV: SUBCATEGORY, SUBCATEGORY_NAME)
   - Properties: SUBCATEGORY (ID), SUBCATEGORY_NAME
   - Relationships: -[CONTAINS]-> Skill

**Relationship Types:**

| Relationship | Source | Target | Properties | Description |
|--------------|--------|--------|------------|-------------|
| REQUIRES | Job | Skill | similarity_score | Job requires specific skill |
| POSTED_BY | Job | Company | - | Company posted the job |
| LOCATED_IN | Job | Location | - | Job is in specific location |
| BELONGS_TO_CATEGORY | Skill | Category | - | Skill belongs to category |
| BELONGS_TO_SUBCATEGORY | Skill | Subcategory | - | Skill belongs to subcategory |
| SIMILAR_TO | Skill | Skill | similarity_score | Skills are semantically similar |
| CONTAINS | Category | Subcategory | - | Category contains subcategory |
| CONTAINS | Subcategory | Skill | - | Subcategory contains skill |

**Key Insights:**
- **Primary Join**: `standardized_skills` (Jobs) ↔ `NAME` (Skills) with normalized string matching
- **Embeddings**: Both Job Description and Skill Description have embeddings for vector search
- **Hierarchical Structure**: Category → Subcategory → Skill taxonomy enables multi-level queries
- **Salary Data**: Min/Max/Mean salary enables compensation analysis
- **Company Metadata**: CIN and NIC codes enable company-level insights
- **Multi-dimensional Queries**: Can traverse Job → Skill → Category, Job → Company, Job → Location simultaneously

### B. Stakeholder Input

**User (Project Owner) Requirements:**
- Emphasis on simplicity - "don't make it complicated", "keep it MVP level"
- Preference for conversational interface over complex UIs
- Internal project - security is not a primary concern
- Incremental ingestion capability for weekly CSV updates
- No resume upload or user profile features for MVP
- Environment-based configuration (.env file approach)
- **Critical requirement**: Fully code-driven implementation with comprehensive documentation (user has minimal technical background)

### C. References

**Technologies:**
- LangGraph: https://langchain-ai.github.io/langgraph/
- Neo4j: https://neo4j.com/docs/
- FastAPI: https://fastapi.tiangulo.com/
- Hugging Face all-MiniLM-L6-v2: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- OpenRouter API: https://openrouter.ai/docs

**Related Concepts:**
- Graph RAG: Combining knowledge graphs with retrieval-augmented generation
- Hybrid Search: Vector similarity + graph traversal for enhanced retrieval
- Skills Taxonomy: Hierarchical classification of professional skills

---

## Next Steps

### Immediate Actions

1. **Review and approve this Project Brief** ✅ - Ensure alignment on scope, approach, and constraints
2. **Generate comprehensive PRD** - Create detailed Product Requirements Document with:
   - Complete API specifications
   - Frontend component breakdown
   - Database schema with Cypher queries
   - Step-by-step setup instructions
   - Code structure and file organization
3. **Create initial repository structure** - Frontend, backend, data directories with detailed README
4. **Write setup documentation** - Complete guide for:
   - Environment setup (.env configuration)
   - Neo4j Aura account creation and connection
   - OpenRouter API key setup
   - Local development workflow
5. **Implement ingestion pipeline** - CSV → validation → embedding → Neo4j with progress tracking
6. **Implement query pipeline** - LangGraph agent for hybrid search + OpenRouter LLM response
7. **Build React frontend** - Login, CSV upload UI, chat interface
8. **Create deployment guide** - Step-by-step instructions for running the complete system

### PM Handoff

This Project Brief provides the full context for **Graph RAG System for Skills & Jobs Knowledge Graph**. Please start in 'PRD Generation Mode', review the brief thoroughly to work with the user to create the PRD section by section as the template indicates, asking for any necessary clarification or suggesting improvements.

---

*Project Brief v1.0 - Created by Mary, Business Analyst*
