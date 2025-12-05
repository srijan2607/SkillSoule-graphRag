# Introduction

This document outlines the backend architecture for **Career Intelligence AI System v2.0**, a research-validated GraphRAG platform that provides quantified career guidance through network analysis. This architecture builds upon the existing v1.1 MVP, transforming it from a job-centric keyword-matching system into a skill-centric network intelligence platform.

## Relationship to Frontend Architecture

The project includes a React-based chat interface. This document focuses on backend systems (FastAPI, Neo4j, LangGraph orchestration, network metrics). Frontend enhancements (metric visualization, skill path diagrams) are documented separately and MUST be used in conjunction with this document.

**Core Technology Stack Choices:** All technology selections in the Tech Stack section below are definitive for the entire project, including frontend components.

## Starter Template or Existing Project

**Analysis:** This is a **brownfield enhancement project** built on existing v1.1 codebase.

**Existing Foundation:**
- ✅ FastAPI backend with JWT authentication
- ✅ Neo4j knowledge graph (job-centric schema)
- ✅ LangGraph RAG pipeline (5 nodes: Query Understanding → Vector Search → Graph Traversal → Context Construction → Response Generation)
- ✅ PostgreSQL + Prisma ORM for user management
- ✅ React + TypeScript frontend
- ✅ OpenRouter LLM integration (`meta-llama/llama-3.3-8b-instruct:free`)
- ✅ HuggingFace embeddings (`all-MiniLM-L6-v2`, 384-dim)

**v2.0 Enhancements:**
- 🔄 Graph schema migration (job-centric → skill-centric)
- ➕ Neo4j GDS integration (eigenvector centrality, shortest path algorithms)
- ➕ New relationship types (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO)
- ➕ Network metrics API (`/api/metrics/centrality`, `/api/metrics/closeness`)
- ➕ Enhanced LangGraph nodes (new query intents: skill transfer, learning path, transition difficulty)
- ➕ Research validation framework (expert evaluation, A/B testing)

**Constraints:**
- Must preserve all v1.1 functionality (backward compatibility requirement - CR1, CR2, CR3, CR4)
- Free-tier Neo4j limits (50K nodes, 175K relationships)
- No containerization for MVP
- CPU-only inference (no GPU)
- Synchronous processing (no async job queue for MVP)

**Decision:** Proceed with **incremental enhancement approach** - extend existing architecture rather than rebuild, ensuring zero regression in v1.1 features.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-15 | 1.0 | Initial Graph RAG system with authentication, CSV ingestion, Neo4j graph, LangGraph pipeline, React chat | John (PM Agent) |
| 2025-10-15 | 1.1 | Requirements refinement - added intent classification, similarity threshold, upsert behavior, retry strategy | John (PM Agent) |
| 2025-11-17 | 2.0 | Backend architecture for skill-centric transformation with network metrics (centrality, closeness), research validation framework, quantified transition scoring | Winston (Architect) |

---
