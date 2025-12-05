# Career Intelligence AI System - Brownfield Enhancement PRD v2.0

**Document Version:** 2.0 (Research-Driven Skill-Centric Transformation)
**Date:** November 17, 2025
**Status:** Enhancement PRD - Network Analysis Integration
**Author:** John (PM Agent)
**Based on:** PROJECT-BRIEF-REVISED.md v2.1 + Existing PRD v1.1

---

## Table of Contents

- [Intro Project Analysis and Context](#intro-project-analysis-and-context)
  - [Existing Project Overview](#existing-project-overview)
  - [Available Documentation Analysis](#available-documentation-analysis)
  - [Enhancement Scope Definition](#enhancement-scope-definition)
  - [Goals and Background Context](#goals-and-background-context)
  - [Change Log](#change-log)
- [Requirements](#requirements)
  - [Functional Requirements](#functional-requirements)
  - [Non-Functional Requirements](#non-functional-requirements)
  - [Compatibility Requirements](#compatibility-requirements)
- [User Interface Enhancement Goals](#user-interface-enhancement-goals)
- [Technical Constraints and Integration Requirements](#technical-constraints-and-integration-requirements)
- [Epic and Story Structure](#epic-and-story-structure)
- [Epic 1: Skill-Centric Graph Restructuring](#epic-1-skill-centric-graph-restructuring)
- [Epic 2: Network Metrics Implementation](#epic-2-network-metrics-implementation)
- [Epic 3: Advanced Query Intelligence](#epic-3-advanced-query-intelligence)
- [Epic 4: Research Validation Framework](#epic-4-research-validation-framework)

---

## Intro Project Analysis and Context

### Existing Project Overview

#### Analysis Source
**IDE-based fresh analysis** - Working from:
- Existing PRD v1.1 at `/Users/srijan26/desktop/Dev/docs/prd/`
- PROJECT-BRIEF-REVISED.md v2.1 at `/Users/srijan26/desktop/Dev/Dev-2/`
- Research documentation in `/Users/srijan26/desktop/Dev/Dev-2/Docs/`

#### Current Project State

The **Graph RAG System for Skills & Jobs** (v1.1, October 2025) is a working MVP that provides conversational career intelligence through:

**Current Capabilities:**
- ✅ User authentication (FastAPI + JWT + PostgreSQL)
- ✅ CSV ingestion pipeline (Skills: 17 fields, Jobs: 30 fields)
- ✅ Neo4j knowledge graph with basic relationships:
  - Job -[REQUIRES]-> Skill
  - Job -[POSTED_BY]-> Company
  - Job -[LOCATED_IN]-> Location
  - Skill -[BELONGS_TO_CATEGORY]-> Category
  - Skill -[SIMILAR_TO]-> Skill (top 5 by cosine similarity >0.7)
- ✅ LangGraph query pipeline (5 nodes: Query Understanding → Vector Search → Graph Traversal → Context Construction → Response Generation)
- ✅ React chat interface with conversation state
- ✅ Hybrid search (vector embeddings + graph traversal)

**Current Limitations (What v2.0 Addresses):**
- ❌ **Job-centric model**: Skills are attributes of jobs, not primary nodes
- ❌ **No structural analysis**: Cannot answer "Which skills bridge my role to target role?"
- ❌ **No network metrics**: Missing centrality, closeness, skill importance scoring
- ❌ **No prerequisite modeling**: Cannot determine learning path order
- ❌ **Qualitative guidance only**: No quantified transition difficulty or skill distance
- ❌ **No research validation**: Basic similarity matching without validated methodology

**Technology Stack:**
- Backend: FastAPI (Python), Pydantic state management
- Graph DB: Neo4j (cloud instance, free tier)
- Relational DB: PostgreSQL + Prisma ORM
- Orchestration: LangGraph (5-node RAG pipeline)
- LLM: OpenRouter API (`meta-llama/llama-3.3-8b-instruct:free`)
- Embeddings: HuggingFace `all-MiniLM-L6-v2` (384-dim)
- Frontend: React + TypeScript

### Available Documentation Analysis

**Available Documentation:**
- ✅ **Existing PRD v1.1** (sharded in `/docs/prd/`) - Complete functional requirements and epic structure
- ✅ **Project Brief v2.1** (PROJECT-BRIEF-REVISED.md) - Comprehensive research methodology and mathematical definitions
- ✅ **Research Integration Docs** (Dev-2/Docs/) - Research findings, skill-centric transformation brief
- ⚠️ **Tech Stack Documentation** - Partial (embedded in PRD and brief)
- ⚠️ **Architecture Documentation** - Referenced but located in `/docs/architecture/` (needs verification)
- ❌ **Coding Standards** - Not yet created for v2.0 enhancements
- ❌ **API Documentation** - Exists for v1.1, needs update for v2.0
- ❌ **Technical Debt Documentation** - Not formally documented

**Documentation Strategy:**
This PRD focuses on **enhancement requirements** and assumes existing v1.1 documentation remains valid for baseline functionality. New documentation will be created during implementation for:
- Enhanced Neo4j schema (skill-centric model)
- Network algorithm APIs (centrality, closeness calculation)
- Updated LangGraph nodes (new query intents)

### Enhancement Scope Definition

#### Enhancement Type
- ✅ **Major Feature Modification** - Restructuring graph data model from job-centric to skill-centric
- ✅ **Integration with New Systems** - Neo4j GDS (Graph Data Science) for centrality algorithms
- ✅ **Performance/Scalability Improvements** - Optimized graph algorithms for <5s query response

#### Enhancement Description

**v2.0 transforms the existing Graph RAG system into a research-validated Career Intelligence platform** by:

1. **Restructuring the knowledge graph** to make skills primary nodes (not job attributes)
2. **Adding advanced relationship types**: PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO
3. **Implementing network metrics** from ICT innovation research: eigenvector centrality, shortest-path closeness
4. **Creating quantified scoring**: TransitionIndex, skill distance, closeness-based difficulty estimates
5. **Building validation framework**: Expert evaluation, baseline A/B testing, correlation checks

**Research Foundation:**
Adapts methodology from "Ties that Bind: ICT Network Approach to Assessing Knowledge Transfers from the ICT Industry" which demonstrated that network closeness predicts innovation outcomes (10.2% efficiency boost, p < 0.01).

**Working Hypothesis:** Analogous effects exist for careers—skill graph closeness predicts career transition feasibility.

#### Impact Assessment
- ✅ **Significant Impact (substantial existing code changes)**
  - Neo4j schema migration required (preserve data, add new node/relationship types)
  - LangGraph nodes need enhancement (new graph algorithms, query intents)
  - Frontend requires new UI components (centrality visualization, skill path diagrams)
  - Existing functionality must remain intact (authentication, CSV ingestion, chat)

### Goals and Background Context

#### Goals

1. **Enable Structural Career Queries** - Answer questions about skill transfer, prerequisite order, and high-leverage skills using graph algorithms (not just keyword matching)
2. **Implement Research-Validated Network Metrics** - Apply eigenvector centrality, shortest-path closeness, and recombinant innovation indices with transparent methodology
3. **Deliver Quantified Career Intelligence** - Provide TransitionIndex scores (0-1 range), closeness metrics, and data-driven difficulty estimates instead of qualitative guidance
4. **Transform to Skill-Centric Architecture** - Migrate from job-centric to skill-centric graph model where skills are primary infrastructure and jobs are skill combination clusters
5. **Validate Research Hypotheses** - Test whether skill closeness predicts career transition feasibility through expert evaluation (>80% agreement target) and user feedback
6. **Maintain Existing System Integrity** - Preserve all working functionality from v1.1 (authentication, CSV ingestion, chat, hybrid search) while adding research-driven capabilities
7. **Achieve Expert Validation Targets** - >80% agreement on skill transfer identification, >4.0/5 rating on learning path quality, >0.7 Pearson correlation on closeness metrics

#### Background Context

The existing Graph RAG System (v1.1) provides conversational career intelligence through basic skill-job relationships and keyword-based graph traversal. However, it **cannot answer structural questions** that require network analysis:

**Current Limitations (Real User Scenario):**
```
User: "I'm a UI developer. How do I become a UX designer?"

v1.1 System Response:
- Lists UX Designer jobs ✓
- Shows required skills: Figma, UX Research, User Psychology ✓

Missing (Critical Gaps):
✗ Which of my current skills (React, CSS, JavaScript) actually transfer?
✗ What's the prerequisite order (should I learn Design Systems before Figma)?
✗ Which skills are "high-leverage" (impact many roles vs niche)?
✗ Realistic timeline based on skill distance?
```

**Why Existing Solutions Fall Short:**
- **LinkedIn/Indeed:** Keyword-based job search without skill relationship graphs
- **Coursera/Udemy:** Course recommendations without job market integration
- **O*NET/ESCO:** Static skill taxonomies, no dynamic network analysis
- **v1.1 System:** Basic similarity matching without prerequisite/complement relationships

**v2.0 Differentiation:**
Neo4j skill-centric graph + vector similarity + research-inspired network metrics (centrality, closeness) + quantified transition scoring

**Research Integration:**
Adapts "Ties that Bind: ICT Network" methodology which demonstrated:
- **Eigenvector Centrality** (Page 15): Identifies important industries based on connections to other important industries → **Applied to identify high-leverage skills**
- **Shortest-Path Closeness** (Page 15-16): `Distance(A→B) = Σ(1/EdgeWeight_i)` → **Applied to calculate skill-to-skill distance for career transitions**
- **Recombinant Innovation Indices** (Appendix Table S1): Classify patents by novelty → **Applied to classify jobs as CUTTING_EDGE/EMERGING/ESTABLISHED**

**What We Extend (Modeling Assumptions to be Validated):**
1. Network metrics applicable to career domain (not just patent citations)
2. Skill closeness predicts career transition feasibility (requires longitudinal validation)
3. TRANSITIONS_TO approximated from static job-skill overlap (not observed user trajectories)
4. High-creation jobs (novel skill combos) correlate with salary premium (hypothesis to test)

### Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD creation | 2025-10-15 | 1.0 | Basic Graph RAG system with authentication, CSV ingestion, Neo4j graph, LangGraph pipeline, React chat | John (PM Agent) |
| Requirements refinement | 2025-10-15 | 1.1 | Added intent classification to FR14, similarity threshold to FR10, upsert behavior to FR11, retry strategy to NFR10 | John (PM Agent) |
| **Research-driven enhancement** | **2025-11-17** | **2.0** | **Skill-centric transformation, network metrics (centrality, closeness), research validation framework, quantified transition scoring** | **John (PM Agent)** |

---

## Requirements

### Functional Requirements

**Note:** Requirements FR1-FR28, NFR1-NFR10 from v1.1 remain valid and are preserved. Below are **additional/modified requirements** for v2.0 enhancement.

#### Enhanced Knowledge Graph (Extends FR9-FR12)

**FR29:** System shall restructure Neo4j graph to skill-centric model:
- **Primary nodes**: Skill (with eigenvector_centrality, market_demand, avg_salary_impact properties)
- **Derived clusters**: Jobs as combinations of required skills
- **Migration**: Preserve existing Job, Company, Location, Category, Subcategory nodes but reorient relationships

**FR30:** System shall create new relationship types:
- **PREREQUISITE_OF**: Foundational skill → Advanced skill (e.g., HTML -[PREREQUISITE_OF]-> React)
  - Properties: confidence_score (0-1), source (manual_curated | inferred)
- **COMPLEMENTS**: Co-occurring skills in jobs (e.g., Python -[COMPLEMENTS]-> PostgreSQL)
  - Properties: co_occurrence_rate (0-1), job_count (integer)
- **SUBSTITUTES**: Competing tools/frameworks (e.g., Django -[SUBSTITUTES]-> Flask)
  - Properties: substitution_score (0-1), context (string)
- **TRANSITIONS_TO**: Career path transitions (e.g., Python -[TRANSITIONS_TO]-> Django)
  - Properties: transition_likelihood (0-1), estimated_learning_time_hours (integer)

**FR31:** System shall compute and store eigenvector centrality for all skills using Neo4j GDS:
- Algorithm: `gds.eigenvector.stream()` on weighted skill graph
- Update frequency: After each CSV ingestion batch
- Storage: Skill.eigenvector_centrality property (float, 0-1 range)

**FR32:** System shall compute skill-to-skill shortest path distance using Dijkstra's algorithm:
- Graph: CO_OCCURS_WITH relationships (weighted by co-occurrence count)
- Edge distance: `d(s1, s2) = 1 / w(s1, s2)` where w = co-occurrence count
- Optionally include PREREQUISITE_OF edges in path calculation
- Return: Distance value and path (list of skill nodes)

**FR33:** System shall calculate closeness metric between skills:
- Formula: `Closeness(A, B) = 1 / (1 + Distance(A, B))`
- Range: [0, 1] where 1 = direct connection, 0 = very distant/no path
- Use case: Skill transfer analysis in career transitions

**FR34:** System shall compute user-to-job closeness:
- For each required skill in job: Find minimum distance to user's skill set
- Formula: `JobCloseness = (1/m) * Σ closeness_j` where m = number of required skills
- Optional enhancement: Weight core skills 2.0x in average

**FR35:** System shall calculate TransitionIndex for career transitions:
- Formula: `TransitionIndex = 0.50 * AvgCloseness + 0.30 * CoreSkillOverlap + 0.20 * MarketDemand`
- Range: [0, 1]
- Interpretation: >0.7 = High feasibility, 0.4-0.7 = Moderate, <0.4 = Major pivot
- **Disclaimer**: Heuristic score, not research-validated probability

**FR36:** System shall compute recombinant innovation indices for jobs:
- **Creation Index**: (Novel skill pairs) / (Total pairs in job) where novel = not seen in >5% of jobs
- **Reuse Index**: (Established skill pairs) / (Total pairs)
- Classification: CUTTING_EDGE (creation >50%), EMERGING (30-50%), ESTABLISHED (<30%)
- Storage: Job.creation_index, Job.reuse_index properties

**FR37:** System shall infer TRANSITIONS_TO relationships from static job-skill data:
- Factor 1: Skill co-occurrence in jobs (0.5 weight)
- Factor 2: Embedding cosine similarity (0.3 weight)
- Factor 3: Skill complexity delta penalty (0.2 weight)
- Threshold: Create relationship if combined score >0.3
- **Limitation Note**: Not based on observed user trajectories; refine when data available

#### Enhanced Query Pipeline (Extends FR13-FR22)

**FR38:** System shall add new query intent types to Query Understanding node:
- **Skill Transfer Query**: "Which of my skills transfer to X role?"
- **Learning Path Query**: "What's the order to learn Full-Stack Development?"
- **High-Leverage Skill Query**: "Which skills have highest centrality?"
- **Transition Difficulty Query**: "How hard is transitioning from X to Y?"
- **Skill Bridge Query**: "What skills bridge UI development to UX design?"

**FR39:** System shall implement structural graph queries for new intents:
- **Skill Transfer**: Calculate closeness from user skills to target job required skills
- **Learning Path**: Find shortest path through PREREQUISITE_OF relationships
- **High-Leverage**: Rank skills by eigenvector_centrality descending
- **Transition Difficulty**: Compute TransitionIndex between skill sets
- **Skill Bridge**: Find intermediate skills on shortest path between skill clusters

**FR40:** System shall enhance Context Construction node to include:
- Graph statistics: Number of nodes traversed, relationships explored, path length
- Centrality scores for mentioned skills
- Closeness metrics between skill pairs
- TransitionIndex with component breakdown (closeness, overlap, demand)
- Research methodology citations (specific formulas used)

**FR41:** System shall update Response Generation prompts to:
- Cite specific network metrics used (centrality values, closeness scores)
- Explain reasoning based on graph structure (not just semantic similarity)
- Highlight non-obvious connections discovered through graph traversal
- Include disclaimer for heuristic scores vs validated metrics

**FR42:** System shall log extended performance metrics:
- Centrality calculation time (Neo4j GDS)
- Shortest path computation time (Dijkstra)
- TransitionIndex calculation time
- Total graph algorithm overhead
- Target: Graph algorithm overhead <2s to maintain <5s total response time (NFR1)

#### Research Validation & Transparency (New)

**FR43:** System shall expose `/api/metrics/centrality` endpoint:
- Input: Optional skill_id or return top-N by centrality
- Output: JSON with skill name, centrality score, rank, market_demand
- Use case: Admin validation of centrality rankings

**FR44:** System shall expose `/api/metrics/closeness` endpoint:
- Input: skill_a, skill_b
- Output: JSON with distance, closeness score, shortest path (node list), path length
- Use case: Expert validation of closeness correlation

**FR45:** System shall log all graph algorithm decisions for audit:
- Which relationships used in path calculation (CO_OCCURS_WITH, PREREQUISITE_OF)
- Centrality algorithm parameters (iterations, convergence)
- TransitionIndex component weights (closeness 0.5, overlap 0.3, demand 0.2)
- Threshold values (similarity >0.7, transition likelihood >0.3)

**FR46:** System shall include research citations in responses:
- Reference "Ties that Bind: ICT Network" paper when using closeness/centrality
- Note which metrics are research-validated vs heuristic
- Provide GitHub/documentation links to algorithm implementations

#### Enhanced Embeddings (Modifies FR6)

**FR47:** System shall upgrade embedding model from `all-MiniLM-L6-v2` (384-dim) to `all-mpnet-base-v2` (768-dim):
- Rationale: Better semantic capture for career domain terminology
- Fallback: If performance issues, revert to 384-dim or use `BAAI/bge-large-en-v1.5` (1024-dim)
- Benchmark: Validate on 1000 skill pairs with expert ratings before production

### Non-Functional Requirements

**Note:** NFR1-NFR10 from v1.1 remain valid. Below are additional NFR for v2.0.

**NFR11:** Centrality calculation shall complete in <30 seconds for 5K-8K skill nodes using Neo4j GDS

**NFR12:** Shortest path queries shall return in <500ms for typical skill-to-skill distance calculations

**NFR13:** TransitionIndex calculation shall complete in <200ms for user-to-job transition scoring

**NFR14:** Graph schema migration shall preserve 100% of existing v1.1 data (zero data loss)

**NFR15:** System shall support free-tier Neo4j limits:
- 50,000 nodes maximum (Skills: 5K-8K, Jobs: 20K-40K, Companies/Locations/Categories: <5K)
- 175,000 relationships maximum
- If exceeded, provide graceful degradation (prioritize core skills, recent jobs)

**NFR16:** Environment configuration shall add new variables:
- `NEO4J_GDS_ENABLED` - Enable Graph Data Science algorithms (true/false)
- `EMBEDDING_MODEL_VERSION` - Embedding model (`all-MiniLM-L6-v2` | `all-mpnet-base-v2`)
- `CENTRALITY_UPDATE_FREQUENCY` - How often to recalculate centrality (`on_ingestion` | `daily` | `manual`)

**NFR17:** System shall maintain backward compatibility with v1.1 API endpoints:
- All existing `/auth/*`, `/ingest/*`, `/query`, `/health` endpoints unchanged
- New endpoints additive only (`/api/metrics/*`)

**NFR18:** Documentation shall include research methodology transparency:
- Mathematical formulas for all metrics
- Algorithm implementation details
- Validation status (validated | experimental | heuristic)
- Limitations and assumptions explicitly stated

### Compatibility Requirements

**CR1: Existing API Compatibility**
- All v1.1 FastAPI endpoints (`/auth/register`, `/auth/login`, `/ingest/skills`, `/ingest/jobs`, `/query`, `/health`) must remain functional with identical request/response schemas
- New v2.0 endpoints (`/api/metrics/centrality`, `/api/metrics/closeness`) are additive only

**CR2: Database Schema Compatibility**
- PostgreSQL schema (users table, JWT sessions) remains unchanged
- Neo4j graph migration must preserve all existing nodes (Job, Skill, Company, Location, Category, Subcategory) and relationships (REQUIRES, POSTED_BY, LOCATED_IN, BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, SIMILAR_TO)
- New node properties (eigenvector_centrality, creation_index, reuse_index) are additive
- New relationship types (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO) are additive

**CR3: UI/UX Consistency**
- Existing React chat interface remains default user experience
- New UI components (centrality visualization, skill path diagrams) are optional enhancements
- Chat responses maintain conversational tone with added metric citations

**CR4: Integration Compatibility**
- LangGraph pipeline structure (5 nodes) preserved, enhancements within existing nodes
- OpenRouter LLM integration unchanged (same model, same API)
- CSV ingestion format unchanged (Skills: 17 fields, Jobs: 30 fields)
- Embedding generation process enhanced but backward compatible (can upgrade embeddings incrementally)

---

## User Interface Enhancement Goals

### Integration with Existing UI

**Preserve v1.1 UI/UX:**
- Chat interface remains primary interaction paradigm
- Login/registration pages unchanged
- CSV upload interface unchanged
- Conversational tone and message history display unchanged

**Additive Enhancements:**
- **Inline metric citations**: Display centrality scores, closeness values in chat responses
- **Skill path visualization**: Optional expandable diagram showing shortest path between skills
- **TransitionIndex breakdown**: Show component scores (closeness 50%, overlap 30%, demand 20%)
- **Research methodology links**: "Learn more" tooltips explaining network metrics

### Modified/New Screens and Views

**Enhanced Query Results (Modification):**
- Existing chat message format + new metric badges
- Example: "Python has eigenvector centrality of 0.92 (high-leverage skill)"
- Expandable sections for graph statistics (35 nodes traversed, 58 relationships)

**New: Skill Explorer Dashboard (Optional Beta Feature)**
- Visualize skill network with centrality-based node sizing
- Interactive graph: Click skill → see connections (PREREQUISITE_OF, COMPLEMENTS)
- Filter by category, centrality threshold, co-occurrence frequency
- **Implementation**: Phase 5 stretch goal, not MVP blocking

**New: Career Transition Planner (Optional Beta Feature)**
- Input: Current skills, target role
- Output: TransitionIndex score, learning path (ordered skills), estimated timeline
- Visual roadmap with skill nodes and prerequisite arrows
- **Implementation**: Phase 5 stretch goal, not MVP blocking

### UI Consistency Requirements

**Visual Design:**
- Maintain existing color scheme, typography, component library (if any)
- New metric badges use consistent styling (chip/tag components)
- Graph visualizations use accessible colors (colorblind-friendly palette)

**Interaction Patterns:**
- Chat remains primary interface (no forced dashboard navigation)
- Metric details available on hover/click (progressive disclosure)
- Copy-to-clipboard for metric values (enable sharing/reporting)

**Accessibility:**
- All new UI components WCAG 2.1 AA compliant
- Metric values available as text (not just visual indicators)
- Graph visualizations include text alternatives (skill path lists)

---

## Technical Constraints and Integration Requirements

### Existing Technology Stack

**Languages:**
- Python 3.11+ (backend, graph algorithms, LangGraph)
- JavaScript/TypeScript (frontend React)

**Frameworks:**
- FastAPI (backend REST API)
- React 18+ with TypeScript (frontend)
- LangGraph (RAG orchestration)

**Databases:**
- Neo4j 5.x (cloud instance, free tier: 50K nodes, 175K relationships)
- PostgreSQL 15+ with Prisma ORM (user accounts, sessions)

**Infrastructure:**
- Local development (React dev server + FastAPI uvicorn)
- Cloud databases (Neo4j Aura free tier, Supabase/PostgreSQL free tier)
- No containerization required for MVP

**External Dependencies:**
- OpenRouter API (`meta-llama/llama-3.3-8b-instruct:free` model)
- HuggingFace Transformers (embedding generation)
- Neo4j Graph Data Science (GDS) library for centrality algorithms

**Constraints:**
- Free tier Neo4j GDS (limited algorithms: eigenvector centrality, shortest path available)
- No GPU (CPU-only inference for embeddings)
- No caching layer (direct database queries)
- Synchronous processing (no async job queue for MVP)

### Integration Approach

#### Database Integration Strategy

**Neo4j Graph Schema Migration:**
1. **Phase 1**: Add new node properties (eigenvector_centrality, creation_index) via Cypher `SET` commands
2. **Phase 2**: Create new relationship types (PREREQUISITE_OF, COMPLEMENTS) incrementally
3. **Phase 3**: Compute initial centrality values using Neo4j GDS `gds.eigenvector.write()`
4. **Rollback Plan**: Maintain v1.1 snapshot, use Cypher `REMOVE` to delete new properties if issues

**PostgreSQL Integration:**
- No schema changes required (users table unchanged)
- Optional: Add `user_skills` table for Phase 2 (personalized profiles)

**Data Migration Script:**
```cypher
// Add centrality property to existing skills
MATCH (s:Skill)
SET s.eigenvector_centrality = 0.0,
    s.market_demand = 0,
    s.avg_salary_impact = 0.0

// Compute initial centrality
CALL gds.graph.project('skill-graph', 'Skill', 'SIMILAR_TO')
CALL gds.eigenvector.write('skill-graph', {writeProperty: 'eigenvector_centrality'})
```

#### API Integration Strategy

**FastAPI Enhancements:**
- New router: `/api/metrics/*` for centrality, closeness endpoints
- Modify existing `/query` endpoint to accept `include_metrics=true` parameter
- Add background task for centrality recalculation (triggered post-ingestion)

**LangGraph Pipeline Modifications:**
- **Query Understanding Node**: Add skill transfer, learning path intent detection
- **Graph Traversal Node**: Inject Dijkstra shortest path calls, centrality lookups
- **Context Construction Node**: Include metric values in retrieval context
- No structural changes to pipeline (5 nodes remain, enhancements within nodes)

**Backward Compatibility:**
- v1.1 API contracts preserved (existing clients unaffected)
- New features opt-in via query parameters or separate endpoints

#### Frontend Integration Strategy

**React Component Enhancements:**
- Create `MetricBadge` component (reusable for centrality, closeness display)
- Create `SkillPathVisualization` component (D3.js or Recharts for graph rendering)
- Modify `ChatMessage` component to parse and render metric citations

**State Management:**
- Existing conversation state unchanged
- Add optional `metricsData` field to message objects
- Use React Context or local state (no Redux/Zustand needed for MVP)

**API Client Updates:**
- Modify query API call to request `include_metrics=true`
- Add new API calls for `/api/metrics/*` endpoints (optional, for dashboard features)

#### Testing Integration Strategy

**Unit Tests (New):**
- Centrality calculation accuracy (compare Neo4j GDS output to reference values)
- Shortest path correctness (validate Dijkstra results on known graphs)
- TransitionIndex formula (test edge cases: closeness=0, overlap=1)

**Integration Tests (Enhanced):**
- End-to-end query flow with metrics (submit query → verify metric values in response)
- Graph migration idempotence (run migration script 2x, verify no duplicates/errors)

**Regression Tests (Critical):**
- All v1.1 acceptance criteria must still pass after v2.0 deployment
- Specific focus: CSV ingestion (FR3-FR5), hybrid search (FR15), chat interface (FR26-FR27)

### Code Organization and Standards

#### File Structure Approach

**Backend (FastAPI):**
```
backend/
├── app/
│   ├── routers/
│   │   ├── auth.py (unchanged from v1.1)
│   │   ├── ingest.py (unchanged)
│   │   ├── query.py (enhanced: add metrics logic)
│   │   └── metrics.py (NEW: centrality, closeness endpoints)
│   ├── services/
│   │   ├── graph/
│   │   │   ├── centrality.py (NEW: Neo4j GDS wrapper)
│   │   │   ├── shortest_path.py (NEW: Dijkstra implementation)
│   │   │   └── schema_migration.py (NEW: v1.1 → v2.0 migration)
│   │   └── langgraph/
│   │       ├── nodes.py (enhanced: add metric calculation)
│   │       └── workflow.py (unchanged structure)
│   └── models/
│       └── metrics.py (NEW: TransitionIndex, Closeness Pydantic models)
```

**Frontend (React):**
```
frontend/
├── src/
│   ├── components/
│   │   ├── chat/ (existing, enhanced)
│   │   │   ├── ChatMessage.tsx (modify: render metrics)
│   │   │   └── MetricBadge.tsx (NEW)
│   │   └── metrics/ (NEW)
│   │       ├── SkillPathVisualization.tsx
│   │       └── TransitionIndexBreakdown.tsx
│   └── api/
│       └── metricsClient.ts (NEW)
```

#### Naming Conventions

**Follow Existing v1.1 Patterns:**
- Python: snake_case for functions/variables, PascalCase for classes
- TypeScript: camelCase for functions/variables, PascalCase for components
- Neo4j: UPPERCASE for relationship types, PascalCase for node labels

**New Conventions for v2.0:**
- Metric properties: `eigenvector_centrality` (snake_case, descriptive)
- Graph algorithm functions: `calculate_skill_centrality()`, `find_shortest_path()`
- API endpoints: `/api/metrics/centrality` (kebab-case, RESTful)

#### Coding Standards

**Python (Backend):**
- Type hints for all function signatures (enhanced from v1.1)
- Docstrings with mathematical formulas for metric functions
- Example:
  ```python
  def calculate_closeness(skill_a: str, skill_b: str) -> float:
      """
      Calculate closeness between two skills using shortest path distance.

      Formula: Closeness(A, B) = 1 / (1 + Distance(A, B))

      Args:
          skill_a: Source skill name
          skill_b: Target skill name

      Returns:
          Closeness score in range [0, 1]
      """
  ```

**TypeScript (Frontend):**
- Strict mode enabled (no `any` types)
- Interface definitions for all metric data structures
- Component prop validation with TypeScript interfaces

**Documentation Standards:**
- Inline comments for complex graph algorithms (explain Cypher queries)
- README updates for new environment variables (NFR16)
- API documentation using FastAPI auto-generated OpenAPI schema

### Deployment and Operations

#### Build Process Integration

**Backend:**
- No changes to existing FastAPI build process
- Add migration script to deployment checklist: `python scripts/migrate_graph_v2.py`
- Environment variable validation on startup (check `NEO4J_GDS_ENABLED`)

**Frontend:**
- Standard React build (`npm run build`)
- No additional dependencies for MVP (D3.js only if implementing optional dashboards)

#### Deployment Strategy

**Phased Rollout:**
1. **Phase 1 (Week 1)**: Deploy schema migration to staging Neo4j instance, validate data integrity
2. **Phase 2 (Week 2)**: Deploy backend enhancements, test new `/api/metrics/*` endpoints
3. **Phase 3 (Week 3)**: Deploy frontend enhancements, enable metric display in chat
4. **Phase 4 (Week 4)**: Production deployment with feature flag (`ENABLE_NETWORK_METRICS=true`)

**Rollback Plan:**
- Maintain v1.1 Docker image/codebase snapshot
- Neo4j Cypher script to remove new properties: `MATCH (s:Skill) REMOVE s.eigenvector_centrality`
- Toggle feature flag to disable metric display without full rollback

#### Monitoring and Logging

**Enhanced Logging (Extends v1.1):**
- Log graph algorithm execution time (centrality, shortest path)
- Log metric calculation failures with skill IDs
- Log Neo4j GDS errors separately from query errors

**Performance Monitoring:**
- Track p95 response time for queries with metrics vs without (target: <5s both)
- Monitor Neo4j GDS memory usage (free tier limit warnings)
- Alert if centrality calculation >30s (NFR11 violation)

#### Configuration Management

**New Environment Variables (NFR16):**
```env
# Existing v1.1 variables (unchanged)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxxxx
DATABASE_URL=postgresql://xxxxx
OPENROUTER_API_KEY=xxxxx
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free
EMBEDDING_MODEL=all-MiniLM-L6-v2
JWT_SECRET=xxxxx

# New v2.0 variables
NEO4J_GDS_ENABLED=true
EMBEDDING_MODEL_VERSION=all-mpnet-base-v2
CENTRALITY_UPDATE_FREQUENCY=on_ingestion
ENABLE_NETWORK_METRICS=true
```

**Configuration Validation:**
- Startup script checks `NEO4J_GDS_ENABLED` and verifies GDS library availability
- Fail fast if `EMBEDDING_MODEL_VERSION` not supported

### Risk Assessment and Mitigation

#### Technical Risks

**Risk 1: Neo4j GDS Performance on Free Tier**
- **Risk**: Centrality calculation exceeds 30s on 8K skill nodes (NFR11 violation)
- **Impact**: Query response time >5s, poor user experience
- **Mitigation**:
  - Benchmark centrality on 1K, 5K, 8K node datasets during Phase 1
  - If >30s, reduce graph size (top 5K skills only) or pre-compute centrality offline
  - Fallback: Use approximate centrality (PageRank instead of eigenvector)
- **Severity**: HIGH

**Risk 2: Embedding Model Insufficient for Career Domain**
- **Risk**: all-mpnet-base-v2 may not capture domain terminology (Kubernetes, GraphQL) well
- **Impact**: Poor semantic similarity, incorrect skill relationships
- **Mitigation**:
  - Validate on 1000 skill pairs with expert ratings (target: correlation >0.7)
  - Fallback: Use BAAI/bge-large-en-v1.5 (1024-dim) or fine-tune on job descriptions
  - A/B test: Compare all-MiniLM-L6-v2 vs all-mpnet-base-v2 on 50 sample queries
- **Severity**: MEDIUM-HIGH

**Risk 3: Graph Schema Migration Data Loss**
- **Risk**: Migration script corrupts existing v1.1 graph data
- **Impact**: Catastrophic (system unusable, requires full restore)
- **Mitigation**:
  - **CRITICAL**: Export full Neo4j snapshot before migration (`neo4j-admin dump`)
  - Test migration on staging database with v1.1 production data copy
  - Use idempotent Cypher queries (`MERGE` instead of `CREATE`)
  - Validation script: Count nodes/relationships before vs after migration (must match)
- **Severity**: CRITICAL

**Risk 4: Free Tier Neo4j Limits Exceeded**
- **Risk**: 50K nodes or 175K relationships exceeded with new relationship types
- **Impact**: Cannot ingest new data, feature degradation
- **Mitigation**:
  - Pre-calculate relationship counts (estimate: Skills 8K, Jobs 40K, new relationships ~80K = 128K total < 175K)
  - Implement data pruning: Archive jobs older than 1 year, keep top 5K skills only
  - Graceful degradation: Disable TRANSITIONS_TO relationships if approaching limit
- **Severity**: MEDIUM

#### Integration Risks

**Risk 5: LangGraph Pipeline Performance Degradation**
- **Risk**: Adding centrality/shortest path calculations increases query time >5s (NFR1 violation)
- **Impact**: User complaints about slow responses, poor adoption
- **Mitigation**:
  - Benchmark each graph algorithm separately (centrality lookup <100ms, shortest path <500ms)
  - Cache centrality values (recompute only on CSV ingestion, not per query)
  - Implement query timeout (abort if >4s, return partial results)
- **Severity**: MEDIUM-HIGH

**Risk 6: Backward Compatibility Breakage**
- **Risk**: v2.0 changes inadvertently break v1.1 API contracts
- **Impact**: Existing clients (if any) fail, regression in core features
- **Mitigation**:
  - **MANDATORY**: Run full v1.1 test suite after v2.0 deployment
  - API versioning: Create `/api/v2/query` if significant changes needed (keep `/query` for v1.1)
  - Automated regression tests in CI/CD pipeline
- **Severity**: HIGH

#### Deployment Risks

**Risk 7: Production Deployment During Active Users**
- **Risk**: Deploying schema migration while users querying system causes inconsistent results
- **Impact**: User sees errors, partial data, incorrect metric values
- **Mitigation**:
  - Schedule deployment during low-traffic window (announce downtime)
  - Use feature flag to disable new features during migration (`ENABLE_NETWORK_METRICS=false`)
  - Blue-green deployment: Migrate on staging, switch traffic after validation
- **Severity**: MEDIUM

---

## Epic and Story Structure

### Epic Approach

**Epic Structure Decision:** **Single comprehensive epic with 4 phases** for brownfield enhancement

**Rationale:**

**Why single epic:**
- All v2.0 enhancements are tightly coupled (centrality → closeness → TransitionIndex)
- Graph schema migration must be atomic (cannot partially deploy skill-centric model)
- Research validation requires complete metric implementation (cannot validate partial features)

**Why 4 phases (sub-epics):**
- **Phase 1 (Foundation)**: Graph restructuring without breaking existing system
- **Phase 2 (Metrics)**: Network algorithm implementation and validation
- **Phase 3 (Intelligence)**: Query pipeline enhancements and UI integration
- **Phase 4 (Validation)**: Research validation framework and expert evaluation

**Sequential dependencies:**
- Phase 2 depends on Phase 1 (need skill-centric graph to compute centrality)
- Phase 3 depends on Phase 2 (need centrality values to enhance queries)
- Phase 4 depends on Phase 3 (need working metric queries to validate)

**Alternative considered:**
- Separate epics for "Graph Migration", "Metrics", "UI", "Validation"
- **Rejected because**: Creates artificial boundaries; migration + metrics are inseparable

**Story Sequencing for Brownfield:**
- Stories ensure existing functionality remains intact (integration verification in each story)
- Each story includes rollback plan (Cypher scripts to remove changes)
- Stories sized for 1-3 day implementation (AI agent execution context)
- Mandatory validation checkpoints before proceeding to next phase

---

## Epic 1: Skill-Centric Graph Restructuring

**Epic Goal:** Transform Neo4j graph from job-centric to skill-centric model while preserving 100% of existing v1.1 data and functionality

**Integration Requirements:**
- All existing nodes (Job, Skill, Company, Location, Category, Subcategory) preserved
- All existing relationships (REQUIRES, POSTED_BY, LOCATED_IN, BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, SIMILAR_TO) preserved
- New properties additive only (eigenvector_centrality, market_demand, avg_salary_impact)
- Existing v1.1 test suite must pass after each story completion

### Story 1.1: Graph Schema Enhancement - Add Node Properties

**As a** system administrator,
**I want** to add new metric properties to Skill nodes,
**so that** we can store centrality, market demand, and salary impact data without breaking existing queries.

#### Acceptance Criteria

1. Cypher script adds properties to all Skill nodes:
   - `eigenvector_centrality` (float, default 0.0)
   - `market_demand` (integer, default 0)
   - `avg_salary_impact` (float, default 0.0)
2. Script is idempotent (safe to run multiple times)
3. Existing Skill node properties unchanged (ID, NAME, LEVEL, CATEGORY, DESCRIPTION, embeddings)
4. Validation: Query 100 random skills, verify new properties exist with default values
5. Rollback script tested: `REMOVE` properties and verify clean removal

#### Integration Verification

**IV1:** Run v1.1 query test suite - All skill-based queries return identical results (property additions don't affect query logic)

**IV2:** CSV ingestion test - Upload 100 skill records, verify new properties initialized correctly and existing properties unchanged

**IV3:** Vector search test - Run 10 sample semantic queries, verify similarity search performance unchanged (<500ms)

---

### Story 1.2: Relationship Type Addition - PREREQUISITE_OF

**As a** career advisor user,
**I want** the system to understand prerequisite relationships between skills,
**so that** learning paths can be ordered correctly (e.g., HTML before React).

#### Acceptance Criteria

1. Cypher relationship type `PREREQUISITE_OF` created with properties:
   - `confidence_score` (float, 0-1 range)
   - `source` (string: "manual_curated" | "inferred")
2. Initial curated prerequisite relationships loaded from CSV:
   - Example: HTML -[PREREQUISITE_OF {confidence_score: 1.0, source: "manual_curated"}]-> React
   - Minimum 50 curated relationships for common skill chains
3. Query to find all prerequisites for a skill: `MATCH (s1)-[:PREREQUISITE_OF]->(s2 {NAME: 'React'}) RETURN s1`
4. No impact on existing REQUIRES, SIMILAR_TO relationships

#### Integration Verification

**IV1:** Existing job-skill queries unchanged - REQUIRES relationships still return correct results

**IV2:** Graph visualization test - Open Neo4j Browser, verify PREREQUISITE_OF relationships visible alongside existing relationships

**IV3:** Relationship count validation - Total relationship count increases by ~50-100 (prerequisite additions only)

---

### Story 1.3: Relationship Type Addition - COMPLEMENTS

**As a** job seeker,
**I want** to discover complementary skills that often appear together,
**so that** I can learn skill combinations valued by employers.

#### Acceptance Criteria

1. Cypher relationship type `COMPLEMENTS` created with properties:
   - `co_occurrence_rate` (float, 0-1 range)
   - `job_count` (integer, number of jobs requiring both skills)
2. Algorithm computes COMPLEMENTS relationships:
   - For each skill pair in same job: Increment co-occurrence counter
   - Compute co_occurrence_rate = (jobs_with_both) / (jobs_with_either)
   - Create relationship if co_occurrence_rate >0.6 threshold
3. Query to find complementary skills: `MATCH (s1 {NAME: 'Python'})-[r:COMPLEMENTS]->(s2) RETURN s2, r.co_occurrence_rate ORDER BY r.co_occurrence_rate DESC LIMIT 10`
4. Estimated ~5K-10K COMPLEMENTS relationships created (within Neo4j free tier limit)

#### Integration Verification

**IV1:** Job requirement queries unchanged - REQUIRES relationships unaffected by COMPLEMENTS additions

**IV2:** Performance test - COMPLEMENTS computation completes in <5 minutes for 40K jobs, 8K skills

**IV3:** Relationship limit check - Total relationships <175K (free tier limit), graceful degradation if exceeded (keep top co-occurrence pairs only)

---

### Story 1.4: Relationship Type Addition - SUBSTITUTES

**As a** career transition planner,
**I want** to understand which skills are substitutable (e.g., Django vs Flask),
**so that** I can make strategic learning decisions based on job market flexibility.

#### Acceptance Criteria

1. Cypher relationship type `SUBSTITUTES` created with properties:
   - `substitution_score` (float, 0-1 range)
   - `context` (string, e.g., "web frameworks", "databases")
2. Initial SUBSTITUTES relationships loaded from manual curation:
   - Example: Django -[SUBSTITUTES {substitution_score: 0.8, context: "Python web frameworks"}]-> Flask
   - Minimum 30 curated substitution pairs for common tool categories
3. Bidirectional relationships: If Django substitutes Flask, create Flask substitutes Django
4. Query to find substitutes: `MATCH (s1 {NAME: 'Django'})-[r:SUBSTITUTES]-(s2) RETURN s2, r.context`

#### Integration Verification

**IV1:** Existing skill similarity queries (SIMILAR_TO) unchanged and distinct from SUBSTITUTES

**IV2:** Relationship validation - SUBSTITUTES count ~60-80 (30 pairs * 2 directions)

**IV3:** Context field populated - No null/empty context values, all have meaningful categories

---

### Story 1.5: Relationship Type Addition - TRANSITIONS_TO (Experimental)

**As a** career intelligence system,
**I want** to approximate career transition paths from job-skill data,
**so that** users receive transition likelihood estimates even without observed user trajectory data.

#### Acceptance Criteria

1. Cypher relationship type `TRANSITIONS_TO` created with properties:
   - `transition_likelihood` (float, 0-1 range, HEURISTIC SCORE)
   - `estimated_learning_time_hours` (integer)
2. Algorithm computes TRANSITIONS_TO relationships:
   - Factor 1 (50% weight): Skill co-occurrence in jobs
   - Factor 2 (30% weight): Embedding cosine similarity
   - Factor 3 (20% weight, penalty): Skill complexity delta
   - Create relationship if combined score >0.3 threshold
3. Disclaimer property: `is_validated = false` (experimental, not research-validated)
4. Query to find likely transitions: `MATCH (s1 {NAME: 'Python'})-[r:TRANSITIONS_TO]->(s2) WHERE r.transition_likelihood > 0.5 RETURN s2 ORDER BY r.transition_likelihood DESC`
5. Estimated ~2K-5K TRANSITIONS_TO relationships created

#### Integration Verification

**IV1:** Existing SIMILAR_TO relationships unchanged (different semantic meaning)

**IV2:** Experimental flag validation - All TRANSITIONS_TO relationships have `is_validated = false` property

**IV3:** Relationship limit check - Total relationships still <175K after additions

---

### Story 1.6: Graph Migration Validation & Rollback Testing

**As a** system administrator,
**I want** comprehensive validation of the graph migration,
**so that** I can confidently deploy v2.0 without data loss or corruption.

#### Acceptance Criteria

1. Automated validation script checks:
   - Node count unchanged from v1.1 (Job, Skill, Company, Location, Category, Subcategory counts match pre-migration snapshot)
   - All existing relationships preserved (REQUIRES, POSTED_BY, LOCATED_IN counts match)
   - New properties added to all Skill nodes (100% coverage)
   - New relationship types created (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO exist)
2. Rollback script tested on staging database:
   - Removes new properties: `MATCH (s:Skill) REMOVE s.eigenvector_centrality, s.market_demand, s.avg_salary_impact`
   - Removes new relationships: `MATCH ()-[r:PREREQUISITE_OF|COMPLEMENTS|SUBSTITUTES|TRANSITIONS_TO]->() DELETE r`
   - Validation: Post-rollback graph identical to v1.1 snapshot
3. Performance regression test:
   - Run v1.1 query benchmark suite (10 sample queries)
   - Query response time within ±10% of v1.1 baseline
4. Export full graph snapshot (neo4j-admin dump) for disaster recovery

#### Integration Verification

**IV1:** Zero data loss - Node/relationship counts before vs after migration match exactly (existing data)

**IV2:** v1.1 feature parity - All v1.1 acceptance criteria still pass (authentication, CSV ingestion, chat queries)

**IV3:** Rollback success - Rollback script executes without errors, graph restored to v1.1 state

---

## Epic 2: Network Metrics Implementation

**Epic Goal:** Implement and validate research-driven network metrics (eigenvector centrality, shortest path closeness, TransitionIndex) with performance optimization for <5s query response time

**Integration Requirements:**
- Neo4j GDS library enabled and functional
- Centrality calculation completes in <30s (NFR11)
- Shortest path queries return in <500ms (NFR12)
- All metrics logged for research validation framework

### Story 2.1: Eigenvector Centrality Calculation with Neo4j GDS

**As a** data scientist,
**I want** to compute eigenvector centrality for all skills using Neo4j Graph Data Science,
**so that** we can identify high-leverage skills based on network structure (not just frequency).

#### Acceptance Criteria

1. Neo4j GDS in-memory graph projection created:
   - Nodes: Skill (all 5K-8K skills)
   - Relationships: SIMILAR_TO, COMPLEMENTS (weighted by co_occurrence_rate)
   - Projection name: `skill-network`
2. Eigenvector centrality algorithm executed:
   - Algorithm: `gds.eigenvector.stream('skill-network')` or `gds.eigenvector.write()`
   - Write results to `Skill.eigenvector_centrality` property
   - Normalization: Centrality values in [0, 1] range
3. Top 10 skills by centrality logged and validated:
   - Manual review: Do high-centrality skills make sense? (e.g., Python, JavaScript, SQL expected)
4. Performance: Centrality calculation completes in <30s for 8K skills
5. Update frequency: Centrality recalculated after each CSV ingestion batch (configurable via `CENTRALITY_UPDATE_FREQUENCY` env var)

#### Integration Verification

**IV1:** Existing skill queries unchanged - Centrality property doesn't affect v1.1 semantic search

**IV2:** Centrality value sanity check - Top 10 skills have centrality >0.5, bottom 10% have centrality <0.1 (reasonable distribution)

**IV3:** Neo4j GDS memory usage - GDS projection fits within free tier limits, no out-of-memory errors

---

### Story 2.2: Shortest Path Distance Calculation (Dijkstra's Algorithm)

**As a** career advisor user,
**I want** to calculate the shortest path distance between any two skills,
**so that** I can quantify skill-to-skill transfer difficulty for career planning.

#### Acceptance Criteria

1. Python function `calculate_shortest_path(skill_a: str, skill_b: str)` implemented:
   - Uses Neo4j `shortestPath()` Cypher function or GDS Dijkstra algorithm
   - Relationships used: CO_OCCURS_WITH (primary), PREREQUISITE_OF (optional)
   - Edge weight: `w(s1, s2) = co_occurrence_count` from COMPLEMENTS relationship
   - Edge distance: `d(s1, s2) = 1 / w(s1, s2)` (inverse frequency)
2. Returns:
   - Distance value (float): Sum of edge distances along shortest path
   - Path (list of skill names): [skill_a, intermediate_1, ..., skill_b]
   - Path length (integer): Number of hops
3. Handles edge cases:
   - No path exists: Return distance = infinity, path = null
   - Direct connection: Return distance = 1 / w(a, b), path = [a, b]
4. Performance: Query completes in <500ms for typical skill pairs

#### Integration Verification

**IV1:** Path correctness validation - Test on 10 known skill pairs (e.g., HTML → React should path through CSS/JavaScript)

**IV2:** Performance benchmark - 100 random skill pair queries complete in <500ms average

**IV3:** No impact on existing graph traversal - v1.1 Cypher queries still execute at same speed

---

### Story 2.3: Closeness Metric Calculation

**As a** system,
**I want** to convert shortest path distance into normalized closeness scores,
**so that** metric values are intuitive (0-1 range, higher = more related).

#### Acceptance Criteria

1. Python function `calculate_closeness(skill_a: str, skill_b: str)` implemented:
   - Formula: `Closeness(A, B) = 1 / (1 + Distance(A, B))`
   - Range: [0, 1] where 1 = direct connection, 0 = very distant/no path
   - Uses `calculate_shortest_path()` function from Story 2.2
2. Returns:
   - Closeness score (float, 0-1)
   - Distance value (float, for transparency)
   - Shortest path (list of skills, for user explanation)
3. Edge cases:
   - No path (distance = infinity): Return closeness = 0.0
   - Same skill (distance = 0): Return closeness = 1.0
4. Batch mode: `calculate_closeness_batch(user_skills: list, target_skills: list)` for efficiency

#### Integration Verification

**IV1:** Formula correctness - Test cases: Direct connection (closeness ≈ 0.9-1.0), 2-hop path (closeness ≈ 0.5-0.7), no path (closeness = 0.0)

**IV2:** Batch performance - Calculate closeness for 10 user skills × 20 target skills (200 pairs) in <5s total

**IV3:** Result consistency - Running closeness calculation twice for same pair returns identical results (deterministic)

---

### Story 2.4: User-to-Job Closeness Scoring

**As a** job seeker,
**I want** the system to calculate how close my skill set is to a job's requirements,
**so that** I receive quantified match scores instead of just "qualified" or "not qualified".

#### Acceptance Criteria

1. Python function `calculate_job_closeness(user_skills: list, job_id: str)` implemented:
   - Fetch job required skills from Neo4j: `MATCH (j:Job {Job_ID: job_id})-[:REQUIRES]->(s:Skill) RETURN s.NAME`
   - For each required skill: Find minimum distance to any user skill
   - Formula: `JobCloseness = (1/m) * Σ closeness_j` where m = number of required skills
2. Optional enhancement: Core skill weighting
   - Identify core skills (top 3 by centrality or explicitly tagged)
   - Weight core skill closeness 2.0x in average
3. Returns:
   - Overall job closeness score (float, 0-1)
   - Per-skill breakdown (dict: {required_skill: closeness_to_nearest_user_skill})
   - Transferable skills (list: user skills with closeness >0.7 to any required skill)
4. Performance: Calculate closeness for user with 10 skills vs job with 15 required skills in <1s

#### Integration Verification

**IV1:** Score sanity check - User with exact skill match scores closeness ≈ 1.0, user with no matching skills scores <0.3

**IV2:** Core skill weighting test - Job requiring Python (core) vs obscure skill: Python mismatch penalizes score more

**IV3:** No regression in job search - Existing v1.1 job listing queries still work, closeness score additive

---

### Story 2.5: TransitionIndex Heuristic Implementation

**As a** career transition planner,
**I want** a quantified transition difficulty score between skill sets,
**so that** I can prioritize feasible career paths and set realistic timelines.

#### Acceptance Criteria

1. Python function `calculate_transition_index(user_skills: list, target_role: str)` implemented:
   - Fetch target role required skills from job title matching or skill category
   - Component 1 (50% weight): Average closeness from user skills to target skills
   - Component 2 (30% weight): Core skill overlap ratio
   - Component 3 (20% weight): Market demand (normalized log(job_count) for target skills)
   - Formula: `TransitionIndex = 0.50 * AvgCloseness + 0.30 * CoreOverlap + 0.20 * MarketDemand`
2. Returns:
   - TransitionIndex score (float, 0-1)
   - Component breakdown (dict: {closeness: 0.6, core_overlap: 0.4, market_demand: 0.8})
   - Interpretation (string): "High feasibility" (>0.7), "Moderate" (0.4-0.7), "Major pivot" (<0.4)
   - **Disclaimer flag**: `is_validated = false` (heuristic, not research-validated probability)
3. Edge cases:
   - User skills empty: Return TransitionIndex = 0.0 with warning
   - Target role unknown: Return error with suggested role names
4. Performance: Calculate TransitionIndex in <200ms (NFR13)

#### Integration Verification

**IV1:** Heuristic validation - Test on 10 known transitions (UI Dev → UX Designer should score 0.5-0.7, UI Dev → Data Scientist should score 0.2-0.4)

**IV2:** Component weight sensitivity - Manually adjust weights (0.6, 0.2, 0.2) and verify score changes make intuitive sense

**IV3:** Disclaimer enforcement - All API responses including TransitionIndex display "Heuristic score, not validated" warning

---

### Story 2.6: Recombinant Innovation Indices (Optional Beta)

**As a** researcher,
**I want** to classify jobs by skill combination novelty,
**so that** we can test the hypothesis that high-creation jobs correlate with salary premium.

#### Acceptance Criteria

1. Python function `calculate_creation_index(job_id: str)` implemented:
   - Fetch job required skills: `MATCH (j:Job {Job_ID: job_id})-[:REQUIRES]->(s:Skill) RETURN s`
   - Compute skill pair novelty:
     - Novel pair: Skill combination appears in <5% of all jobs
     - Established pair: Skill combination appears in >20% of jobs
   - Formula: `CreationIndex = (Novel pairs) / (Total pairs in job)`
2. Python function `calculate_reuse_index(job_id: str)` implemented:
   - Formula: `ReuseIndex = (Established pairs) / (Total pairs in job)`
3. Job classification based on CreationIndex:
   - CUTTING_EDGE: creation_index >0.5
   - EMERGING: creation_index 0.3-0.5
   - ESTABLISHED: creation_index <0.3
4. Store indices as Job node properties: `creation_index`, `reuse_index`, `innovation_class`
5. **Implementation note**: Backend-only for MVP, UI exposure deferred until validation

#### Integration Verification

**IV1:** Index calculation correctness - Jobs with all common skills (Python, SQL, Git) have low creation_index (<0.2)

**IV2:** Novel skill detection - Jobs requiring rare combos (Rust + WASM + WebGPU) have high creation_index (>0.7)

**IV3:** Performance - Calculate indices for 40K jobs in <10 minutes (batch processing)

---

### Story 2.7: Metrics API Endpoints

**As a** system administrator,
**I want** API endpoints to access centrality and closeness metrics programmatically,
**so that** we can validate research hypotheses and enable expert evaluation.

#### Acceptance Criteria

1. FastAPI endpoint `/api/metrics/centrality` (GET):
   - Query params: `skill_id` (optional), `top_n` (default 10)
   - Response: JSON array with [{skill_name, centrality_score, rank, market_demand}]
   - Example: `/api/metrics/centrality?top_n=20` returns top 20 skills by centrality
2. FastAPI endpoint `/api/metrics/closeness` (GET):
   - Query params: `skill_a` (required), `skill_b` (required)
   - Response: JSON with {distance, closeness_score, shortest_path: [skills], path_length}
   - Example: `/api/metrics/closeness?skill_a=Python&skill_b=Django`
3. FastAPI endpoint `/api/metrics/transition` (POST):
   - Request body: {user_skills: [list], target_role: string}
   - Response: JSON with {transition_index, components: {closeness, core_overlap, market_demand}, interpretation, disclaimer}
4. Authentication: Require JWT token (same as v1.1 endpoints)
5. Rate limiting: Max 100 requests/hour per user (prevent abuse)

#### Integration Verification

**IV1:** API contract validation - OpenAPI schema auto-generated by FastAPI, test with Swagger UI

**IV2:** Authentication enforcement - Unauthenticated requests return 401 Unauthorized

**IV3:** Response time - All metrics endpoints respond in <1s for typical queries

---

## Epic 3: Advanced Query Intelligence

**Epic Goal:** Enhance LangGraph query pipeline with network metric integration, new query intent types, and transparent research methodology citations

**Integration Requirements:**
- Existing 5-node LangGraph workflow preserved (enhancements within nodes, not structural changes)
- Query response time <5s maintained (NFR1)
- Backward compatibility with v1.1 query types (skill requirement, career path, salary analysis)
- New metric citations displayed in chat responses

### Story 3.1: Query Understanding Node Enhancement - New Intent Types

**As a** LangGraph query pipeline,
**I want** to detect new query intent types related to skill transfer and network metrics,
**so that** I can route queries to appropriate graph algorithms and metric calculations.

#### Acceptance Criteria

1. Enhanced intent classification in Query Understanding node:
   - **Existing v1.1 intents preserved**: skill_requirement, career_path, salary_analysis, skill_relationship, company_query
   - **New v2.0 intents added**:
     - `skill_transfer`: "Which of my skills transfer to UX design?"
     - `learning_path`: "What's the order to learn full-stack development?"
     - `high_leverage_skills`: "Which skills have highest impact on career options?"
     - `transition_difficulty`: "How hard is it to transition from UI dev to data scientist?"
     - `skill_bridge`: "What skills bridge Python to machine learning?"
2. Intent detection using LLM-based classification:
   - Prompt template includes example queries for each intent
   - Returns: Primary intent (string) + confidence score (float, 0-1)
3. Multi-intent handling: If query matches multiple intents (confidence >0.5 for 2+ intents), return ranked list
4. Default fallback: If no intent detected with confidence >0.4, use `general_query` intent (basic semantic search)

#### Integration Verification

**IV1:** v1.1 intent detection unchanged - Test 20 v1.1 sample queries, verify same intent classification as before

**IV2:** New intent accuracy - Test 30 new query types, verify >80% correct intent classification

**IV3:** Multi-intent queries - Query "Which high-leverage skills transfer to UX design?" correctly detects both `high_leverage_skills` and `skill_transfer` intents

---

### Story 3.2: Graph Traversal Node Enhancement - Metric Integration

**As a** LangGraph query pipeline,
**I want** to inject centrality lookups and closeness calculations into graph traversal,
**so that** query responses include quantified metrics instead of just semantic matches.

#### Acceptance Criteria

1. Graph Traversal node enhanced with metric functions:
   - For `high_leverage_skills` intent: Query top-N skills by centrality
   - For `skill_transfer` intent: Calculate closeness from user skills to target skills
   - For `learning_path` intent: Find shortest path through PREREQUISITE_OF relationships
   - For `transition_difficulty` intent: Compute TransitionIndex
2. Cypher query templates for new intents:
   - Learning path: `MATCH path = shortestPath((s1)-[:PREREQUISITE_OF*]-(s2)) WHERE s1.NAME = $skill_a AND s2.NAME = $skill_b RETURN path`
   - High-leverage: `MATCH (s:Skill) WHERE s.eigenvector_centrality > 0.5 RETURN s ORDER BY s.eigenvector_centrality DESC LIMIT 10`
3. Context construction includes metric values:
   - Centrality scores for mentioned skills
   - Closeness values for skill pairs
   - Shortest path node list
4. Performance: Graph traversal with metrics completes in <2s (fits within 5s total query time budget)

#### Integration Verification

**IV1:** v1.1 graph traversal unchanged - Existing career path, salary analysis queries still use same Cypher patterns

**IV2:** Metric values present - Sample `skill_transfer` query response includes closeness scores in context JSON

**IV3:** Performance regression test - Graph traversal time increases by <1s compared to v1.1 baseline

---

### Story 3.3: Context Construction Node Enhancement - Research Citations

**As a** user,
**I want** to understand which research methodology and metrics were used to answer my query,
**so that** I can trust the AI's recommendations and learn about the underlying science.

#### Acceptance Criteria

1. Context Construction node enhanced to include:
   - **Graph statistics**: Number of nodes traversed, relationships explored, path length
   - **Metric values**: Centrality scores (if used), closeness scores (if calculated), TransitionIndex components
   - **Research methodology**: Which formula applied (e.g., "Closeness calculated using shortest path distance from 'Ties that Bind' research")
   - **Validation status**: Mark each metric as "Research-validated" | "Heuristic" | "Experimental"
2. Context JSON structure:
   ```json
   {
     "retrieved_nodes": [...],
     "graph_stats": {"nodes_traversed": 35, "relationships_explored": 58, "path_length": 3},
     "metrics": {
       "centrality": {"Python": 0.92, "JavaScript": 0.85},
       "closeness": {"Python_to_Django": 0.78, "path": ["Python", "Web Framework", "Django"]},
       "transition_index": {"score": 0.65, "components": {...}}
     },
     "methodology": "Eigenvector centrality (Neo4j GDS), Shortest path closeness (Dijkstra)",
     "validation_status": {"centrality": "research-validated", "transition_index": "heuristic"}
   }
   ```
3. Research paper citation: Include link to "Ties that Bind: ICT Network" when closeness/centrality used

#### Integration Verification

**IV1:** Context completeness - All new metric queries include graph_stats and methodology fields

**IV2:** Validation transparency - Heuristic metrics (TransitionIndex, TRANSITIONS_TO) clearly marked as "heuristic, not validated"

**IV3:** v1.1 context structure preserved - Existing queries still receive same context fields (backward compatible)

---

### Story 3.4: Response Generation Node Enhancement - Metric Explanation

**As a** user,
**I want** AI responses to explain metric values in plain language,
**so that** I understand what centrality scores and closeness metrics mean for my career decisions.

#### Acceptance Criteria

1. LLM prompt template enhanced with metric explanation instructions:
   - "When mentioning centrality, explain: 'Centrality measures how connected a skill is to other important skills. Higher centrality (>0.7) indicates high-leverage skills that open many career paths.'"
   - "When mentioning closeness, explain: 'Closeness of 0.8 means these skills are closely related in the job market (often required together). Closeness <0.3 indicates distant skills requiring substantial learning.'"
   - "When mentioning TransitionIndex, include disclaimer: 'This is a heuristic score based on skill overlap and market data, not a validated probability. Use as directional guidance.'"
2. Response includes:
   - Metric values with units (e.g., "Python has centrality of 0.92 out of 1.0")
   - Plain language interpretation (e.g., "This is a high-leverage skill")
   - Actionable insights (e.g., "Learning Python opens paths to data science, backend dev, and automation roles")
3. Research citations in responses: "This calculation uses the shortest path closeness methodology from network analysis research (Ties that Bind: ICT Industries study)."
4. Tone: Conversational but precise (maintain v1.1 chat tone, add scientific rigor)

#### Integration Verification

**IV1:** User comprehension test - 5 beta users read sample responses with metrics, can explain what centrality/closeness means in their own words

**IV2:** Citation presence - 100% of queries using centrality/closeness include research paper reference

**IV3:** Tone consistency - New responses match v1.1 conversational style (not overly academic)

---

### Story 3.5: Frontend Metric Display - Inline Citations

**As a** user,
**I want** to see metric values displayed in chat responses with visual indicators,
**so that** I can quickly identify high-leverage skills and understand transition difficulty.

#### Acceptance Criteria

1. React `ChatMessage` component modified to parse and render metrics:
   - Detect metric values in response text (regex or structured JSON parsing)
   - Render `MetricBadge` component for centrality, closeness, TransitionIndex
2. `MetricBadge` component implementation:
   - Props: {type: "centrality" | "closeness" | "transition_index", value: number, label: string}
   - Visual: Chip/tag with color coding (green >0.7, yellow 0.4-0.7, red <0.4)
   - Hover tooltip: Detailed explanation ("Centrality 0.92: High-leverage skill connected to many career paths")
3. Skill path visualization (optional, expandable):
   - If closeness metric includes shortest path, render as node diagram
   - Use simple D3.js or Recharts line chart showing skill progression
   - Example: [Python] → [Web Framework] → [Django]
4. Copy-to-clipboard: Click metric badge to copy value (for sharing/reporting)

#### Integration Verification

**IV1:** Visual regression test - Existing v1.1 chat messages without metrics still render correctly

**IV2:** Metric parsing accuracy - Test 10 responses with mixed text + metrics, verify all metrics rendered as badges

**IV3:** Accessibility - MetricBadge component WCAG 2.1 AA compliant (color contrast, keyboard navigation, screen reader support)

---

### Story 3.6: Query Performance Optimization

**As a** system,
**I want** to maintain <5s query response time even with network metric calculations,
**so that** user experience remains fast and engaging (NFR1 compliance).

#### Acceptance Criteria

1. Performance profiling of enhanced query pipeline:
   - Log timestamps for each LangGraph node execution
   - Identify bottlenecks (centrality lookup, shortest path calculation, LLM generation)
2. Optimization techniques implemented:
   - **Cache centrality values**: Compute once on ingestion, read from Skill.eigenvector_centrality property (not recalculated per query)
   - **Batch closeness calculations**: If query requires multiple skill pairs, use batch mode function
   - **Query timeout**: Abort graph traversal if >4s elapsed, return partial results with warning
3. Performance benchmark results:
   - 90% of queries (new intents + v1.1 intents) complete in <5s
   - Median query time: 2-3s
   - Slowest query type: `learning_path` with 5+ prerequisite hops (acceptable if <5s)
4. Monitoring: Log query time per intent type for ongoing optimization

#### Integration Verification

**IV1:** NFR1 validation - Run 100 random queries (mix of v1.1 and v2.0 intents), p95 response time <5s

**IV2:** Centrality cache hit rate - >95% of centrality lookups served from cache (not recalculated)

**IV3:** Graceful degradation - If query exceeds 5s, system returns partial results + "calculation timed out" message (not error)

---

## Epic 4: Research Validation Framework

**Epic Goal:** Implement expert evaluation framework, baseline A/B testing, and correlation checks to validate research hypotheses and metric accuracy

**Integration Requirements:**
- Validation endpoints accessible to admin users only
- Evaluation data stored in PostgreSQL (separate schema from user data)
- Metrics logged for analysis (correlation coefficients, expert agreement rates)
- Results feed into research paper / methodology documentation

### Story 4.1: Expert Validation Interface - Skill Transfer Identification

**As a** career counselor (expert evaluator),
**I want** to validate whether the system correctly identifies transferable skills,
**so that** we can measure ground truth accuracy against research hypothesis.

#### Acceptance Criteria

1. Admin API endpoint `/api/validation/skill-transfer` (POST, admin-only):
   - Request body: {scenario_id, user_skills: [list], target_role: string, system_prediction: {transferable_skills: [list], closeness_scores: dict}}
   - Expert response: {transferable_skills_actual: [list], confidence: "high" | "medium" | "low", notes: string}
2. Validation dataset: 10 career transition scenarios (predefined):
   - Example: UI Developer → UX Designer (user skills: React, CSS, JavaScript, Figma)
   - System prediction: Figma (closeness 0.9), CSS (closeness 0.7) transferable; React (closeness 0.5) partial
3. Expert evaluation criteria:
   - Binary judgment: Does system correctly identify transferable skills? (Yes/No)
   - Rating: How logical is the transferable skill list? (1-5 scale)
4. Store evaluations in PostgreSQL `expert_validations` table
5. Target: >80% agreement between system prediction and expert judgment (per project brief)

#### Integration Verification

**IV1:** Data integrity - All 10 scenarios evaluated by 5 experts (50 total evaluations stored)

**IV2:** Agreement calculation - Automated script computes % agreement, flags discrepancies for review

**IV3:** No impact on production - Validation endpoints isolated from user-facing query API

---

### Story 4.2: Expert Validation Interface - Learning Path Quality

**As a** hiring manager (expert evaluator),
**I want** to rate the quality of recommended learning paths,
**so that** we can validate whether prerequisite ordering makes sense for real career transitions.

#### Acceptance Criteria

1. Admin API endpoint `/api/validation/learning-path` (POST, admin-only):
   - Request body: {scenario_id, source_skill: string, target_skill: string, system_path: [skills ordered list], estimated_time_hours: integer}
   - Expert response: {path_logical: boolean, rating: 1-5, suggested_changes: string, estimated_time_expert: integer}
2. Validation dataset: 10 learning path scenarios:
   - Example: HTML → Full-Stack Developer (path: [HTML, CSS, JavaScript, React, Node.js, Database])
3. Expert evaluation criteria:
   - Is path logically ordered? (Prerequisites before advanced skills)
   - Rating: Overall path quality (1-5 scale)
   - Time estimate: Does system's estimated learning time match expert judgment?
4. Target: Average expert rating >4.0/5 (per project brief)

#### Integration Verification

**IV1:** Rating distribution - Expert ratings span full 1-5 range (not all 5s, indicating critical evaluation)

**IV2:** Time estimate correlation - System time estimates within ±30% of expert estimates for >70% of scenarios

**IV3:** Feedback loop - Store expert suggested changes for future prerequisite relationship refinement

---

### Story 4.3: Closeness Correlation Check with Expert Judgment

**As a** researcher,
**I want** to measure correlation between system closeness scores and expert-rated skill relatedness,
**so that** we can validate whether our network metric captures human judgment of skill similarity.

#### Acceptance Criteria

1. Validation dataset: 100 skill pairs (50 highly related, 30 moderately related, 20 unrelated):
   - Examples: (Python, Django) = highly related, (Python, Photoshop) = unrelated
2. Expert evaluation: 5 domain experts rate each pair on 1-10 scale ("How related are these skills for career transitions?")
3. System calculation: Compute closeness score for all 100 pairs using `calculate_closeness()` function
4. Statistical analysis:
   - Compute Pearson correlation coefficient between expert average rating and system closeness score
   - Target: Correlation >0.7 (strong positive relationship, per project brief)
5. Results visualization: Scatter plot (x-axis: expert rating, y-axis: closeness score) with trend line
6. Store results in PostgreSQL `closeness_validation` table

#### Integration Verification

**IV1:** Dataset representativeness - 100 pairs cover diverse skill categories (technical, soft skills, tools, frameworks)

**IV2:** Expert agreement - Inter-rater reliability (Cronbach's alpha) >0.7 among 5 experts (ensures consistent judgments)

**IV3:** Correlation significance - p-value <0.05 for Pearson correlation (statistically significant result)

---

### Story 4.4: Baseline A/B Testing - Job-Centric vs Skill-Centric

**As a** product manager,
**I want** to compare user satisfaction with skill-centric search vs job-centric search,
**so that** we can validate whether graph restructuring improves query relevance.

#### Acceptance Criteria

1. A/B test setup:
   - **Group A (Baseline)**: v1.1 job-centric search (keyword matching + semantic similarity, no network metrics)
   - **Group B (Treatment)**: v2.0 skill-centric search (closeness metrics, centrality, TransitionIndex)
2. Metrics tracked:
   - Query relevance rating (user rates response 1-5 scale after each query)
   - Time to useful answer (user self-reports: <1min, 1-3min, >3min, or "not found")
   - Click-through rate (if recommendations include job links, track clicks)
3. Sample size: 50 beta users, 3+ queries each (minimum 150 total queries)
4. Target: Group B (skill-centric) outperforms Group A by >15% on relevance ratings (per project brief)
5. Statistical test: Two-sample t-test on mean relevance ratings, significance threshold p<0.05

#### Integration Verification

**IV1:** Random assignment - Users randomly assigned to Group A or B (no selection bias)

**IV2:** Data collection - All ratings and timing data stored in PostgreSQL `ab_test_results` table

**IV3:** Result interpretation - Clear summary report: "Skill-centric search achieved 4.2/5 avg rating vs 3.5/5 for job-centric (p=0.002, significant improvement)"

---

### Story 4.5: Research Methodology Documentation

**As a** future researcher or auditor,
**I want** comprehensive documentation of all algorithms, formulas, and validation results,
**so that** the system can be peer-reviewed and methods replicated.

#### Acceptance Criteria

1. Documentation includes:
   - **Mathematical formulas**: LaTeX-formatted equations for centrality, closeness, TransitionIndex
   - **Algorithm implementations**: Pseudocode + actual code (Python functions with docstrings)
   - **Validation results**: Expert agreement rates, correlation coefficients, A/B test outcomes
   - **Limitations section**: Explicitly state what is validated vs heuristic vs experimental
2. Research citations:
   - Full bibliography entry for "Ties that Bind: ICT Network" paper
   - Methodology comparison table: What we borrowed directly vs what we extended
3. Transparency markers:
   - **Research-validated**: Eigenvector centrality (Neo4j GDS standard algorithm)
   - **Heuristic**: TransitionIndex (weighted combination, not statistically validated)
   - **Experimental**: TRANSITIONS_TO relationships (approximated from static data)
4. Publication targets:
   - Internal documentation: `/docs/research-methodology.md`
   - Public-facing: Research section on project website/GitHub README

#### Integration Verification

**IV1:** Completeness check - All metrics (centrality, closeness, TransitionIndex, creation index) have documented formulas and implementations

**IV2:** Peer review - 2 external researchers review documentation, confirm reproducibility

**IV3:** Limitation disclosure - Every heuristic metric includes clear "not validated" disclaimer in docs and UI

---

### Story 4.6: Monitoring Dashboard for Research Metrics (Optional Stretch Goal)

**As a** system administrator,
**I want** a real-time dashboard showing metric calculation performance and validation stats,
**so that** I can monitor system health and identify metric accuracy issues.

#### Acceptance Criteria

1. Admin dashboard (`/admin/metrics-dashboard`, admin-only):
   - **Centrality health**: Last update timestamp, top 10 skills by centrality, calculation time
   - **Closeness performance**: Avg query time (p50, p95), failed path calculations (no path found %)
   - **TransitionIndex usage**: Number of queries using TransitionIndex, avg score distribution
   - **Validation metrics**: Expert agreement rate, closeness correlation, A/B test status
2. Real-time updates: Dashboard refreshes every 30 seconds (WebSocket or polling)
3. Alerts: Email/Slack notification if:
   - Centrality calculation fails or exceeds 30s (NFR11 violation)
   - Closeness query time >500ms for >10% of queries (NFR12 violation)
   - Expert agreement rate drops below 70% (quality issue)
4. **Implementation**: Optional Phase 5 feature, not MVP blocking

#### Integration Verification

**IV1:** Dashboard accessibility - Only users with `admin` role can access (JWT role check)

**IV2:** Performance impact - Dashboard queries do not affect user-facing query response time

**IV3:** Alert reliability - Test alerts by simulating performance degradation (e.g., disable Neo4j GDS), verify notifications sent

---

## Next Steps

### UX Expert Consultation (Post-MVP)

**Prompt:**
> We've built a research-driven Career Intelligence AI System with network metrics (centrality, closeness, TransitionIndex). The system displays metric values in chat responses with inline badges. As a UX expert, review our interface design and recommend improvements for:
> 1. Metric visualization clarity (are badges intuitive or overwhelming?)
> 2. User comprehension of research concepts (how to explain centrality without jargon?)
> 3. Mobile responsiveness (metric badges on small screens)
> 4. Optional dashboard features (skill graph visualization, career roadmap planner)

### Architect Review (Post-MVP)

**Prompt:**
> We've implemented a skill-centric Neo4j graph with GDS centrality algorithms and enhanced LangGraph pipeline. As a system architect, review our implementation and recommend optimizations for:
> 1. Neo4j free tier performance (approaching 50K nodes, 175K relationships limit)
> 2. Centrality calculation frequency (currently on every CSV ingestion - too aggressive?)
> 3. Caching strategy (should we cache closeness results or recalculate per query?)
> 4. Scalability path to paid tier (what breaks first at 100K skills, 500K jobs?)

### Research Validation Next Steps (Phase 2)

1. **Collect expert evaluations**: Recruit 10 career counselors + hiring managers for validation studies
2. **Run A/B test**: Onboard 50 beta users, split into job-centric vs skill-centric groups
3. **Analyze correlation**: Compute Pearson coefficient for closeness vs expert ratings
4. **Publish results**: Write research paper or blog post on validation outcomes
5. **Refine algorithms**: Use validation feedback to adjust TransitionIndex weights, centrality thresholds

---

**End of PRD v2.0**

---

## Document Control

**Version:** 2.0 (Research-Driven Skill-Centric Transformation)
**Approvals Required:**
- ✅ Technical Lead (Architecture review)
- ⏳ Research Advisor (Methodology validation)
- ⏳ Stakeholder Sign-Off (Scope and timeline approval)

**Implementation Timeline:** 4-6 weeks (4 epics, 35 stories)

**Dependencies:**
- Neo4j GDS library enabled on cloud instance (verify compatibility with free tier)
- Existing v1.1 PRD test suite passing (baseline for regression testing)
- PROJECT-BRIEF-REVISED.md assumptions validated (embedding model, free tier limits)

**Risks Acknowledged:**
- Schema migration complexity (mitigated by rollback plan)
- Free tier performance unknowns (mitigated by benchmarking)
- Research validation effort (requires expert recruitment, time investment)
