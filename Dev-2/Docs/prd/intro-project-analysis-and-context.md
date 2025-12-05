# Intro Project Analysis and Context

## Existing Project Overview

### Analysis Source
**IDE-based fresh analysis** - Working from:
- Existing PRD v1.1 at `/Users/srijan26/desktop/Dev/docs/prd/`
- PROJECT-BRIEF-REVISED.md v2.1 at `/Users/srijan26/desktop/Dev/Dev-2/`
- Research documentation in `/Users/srijan26/desktop/Dev/Dev-2/Docs/`

### Current Project State

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

## Available Documentation Analysis

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

## Enhancement Scope Definition

### Enhancement Type
- ✅ **Major Feature Modification** - Restructuring graph data model from job-centric to skill-centric
- ✅ **Integration with New Systems** - Neo4j GDS (Graph Data Science) for centrality algorithms
- ✅ **Performance/Scalability Improvements** - Optimized graph algorithms for <5s query response

### Enhancement Description

**v2.0 transforms the existing Graph RAG system into a research-validated Career Intelligence platform** by:

1. **Restructuring the knowledge graph** to make skills primary nodes (not job attributes)
2. **Adding advanced relationship types**: PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO
3. **Implementing network metrics** from ICT innovation research: eigenvector centrality, shortest-path closeness
4. **Creating quantified scoring**: TransitionIndex, skill distance, closeness-based difficulty estimates
5. **Building validation framework**: Expert evaluation, baseline A/B testing, correlation checks

**Research Foundation:**
Adapts methodology from "Ties that Bind: ICT Network Approach to Assessing Knowledge Transfers from the ICT Industry" which demonstrated that network closeness predicts innovation outcomes (10.2% efficiency boost, p < 0.01).

**Working Hypothesis:** Analogous effects exist for careers—skill graph closeness predicts career transition feasibility.

### Impact Assessment
- ✅ **Significant Impact (substantial existing code changes)**
  - Neo4j schema migration required (preserve data, add new node/relationship types)
  - LangGraph nodes need enhancement (new graph algorithms, query intents)
  - Frontend requires new UI components (centrality visualization, skill path diagrams)
  - Existing functionality must remain intact (authentication, CSV ingestion, chat)

## Goals and Background Context

### Goals

1. **Enable Structural Career Queries** - Answer questions about skill transfer, prerequisite order, and high-leverage skills using graph algorithms (not just keyword matching)
2. **Implement Research-Validated Network Metrics** - Apply eigenvector centrality, shortest-path closeness, and recombinant innovation indices with transparent methodology
3. **Deliver Quantified Career Intelligence** - Provide TransitionIndex scores (0-1 range), closeness metrics, and data-driven difficulty estimates instead of qualitative guidance
4. **Transform to Skill-Centric Architecture** - Migrate from job-centric to skill-centric graph model where skills are primary infrastructure and jobs are skill combination clusters
5. **Validate Research Hypotheses** - Test whether skill closeness predicts career transition feasibility through expert evaluation (>80% agreement target) and user feedback
6. **Maintain Existing System Integrity** - Preserve all working functionality from v1.1 (authentication, CSV ingestion, chat, hybrid search) while adding research-driven capabilities
7. **Achieve Expert Validation Targets** - >80% agreement on skill transfer identification, >4.0/5 rating on learning path quality, >0.7 Pearson correlation on closeness metrics

### Background Context

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

## Change Log

| Change | Date | Version | Description | Author |
|--------|------|---------|-------------|--------|
| Initial PRD creation | 2025-10-15 | 1.0 | Basic Graph RAG system with authentication, CSV ingestion, Neo4j graph, LangGraph pipeline, React chat | John (PM Agent) |
| Requirements refinement | 2025-10-15 | 1.1 | Added intent classification to FR14, similarity threshold to FR10, upsert behavior to FR11, retry strategy to NFR10 | John (PM Agent) |
| **Research-driven enhancement** | **2025-11-17** | **2.0** | **Skill-centric transformation, network metrics (centrality, closeness), research validation framework, quantified transition scoring** | **John (PM Agent)** |

---
