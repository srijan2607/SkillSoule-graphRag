# Introduction

This document outlines the **backend architecture** for the **Graph RAG System for Skills & Jobs Knowledge Graph**, including API design, database schemas, LangGraph orchestration workflows, and system integration patterns. Its primary goal is to serve as the definitive technical blueprint for backend development, ensuring consistency and adherence to the chosen technology stack.

**Project Overview:**

The system enables conversational AI-powered career intelligence through a knowledge graph-based RAG (Retrieval-Augmented Generation) pipeline. Users upload CSV files containing skills and jobs taxonomies, which are processed into a Neo4j knowledge graph with semantic embeddings. Natural language queries are orchestrated through LangGraph agents that perform hybrid search (vector similarity + graph traversal) and generate intelligent responses via OpenRouter LLM.

**Relationship to Frontend Architecture:**

The frontend architecture is documented separately in `docs/front-end-spec.md`. This backend architecture document defines:
- RESTful API contracts that the React frontend consumes
- Data models and validation rules
- Authentication and authorization mechanisms
- Error response formats and status codes

The frontend spec defines UI/UX patterns, while this document defines the backend services that power those experiences.

**Core Technology Stack (Definitive):**
- **Backend Framework**: FastAPI (Python)
- **LLM Orchestration**: LangGraph for RAG workflows
- **Graph Database**: Neo4j (cloud-hosted)
- **Relational Database**: PostgreSQL (cloud-hosted) with Prisma ORM
- **LLM Provider**: OpenRouter API (`meta-llama/llama-3.3-8b-instruct:free`)
- **Embeddings**: Hugging Face Transformers (`all-MiniLM-L6-v2`)

All technology decisions documented in the "Tech Stack" section are the single source of truth for the entire project, including frontend dependencies.

## Starter Template or Existing Project

**Decision**: No starter template or boilerplate will be used.

**Rationale**:
- The project has specific requirements (LangGraph + Neo4j + FastAPI integration) that don't align well with generic templates
- Custom architecture allows optimization for Graph RAG workflows without template constraints
- Manual setup ensures full understanding of all components and dependencies
- Cleaner codebase without unnecessary boilerplate code

**Implication**: All tooling, configuration, and project structure will be set up manually following best practices for FastAPI, LangGraph, and Neo4j integration.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-22 | 1.0 | Initial backend architecture document creation | Winston (Architect) |

---
