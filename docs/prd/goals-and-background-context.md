# Goals and Background Context

## Goals

- Enable conversational, natural language access to career intelligence through graph-powered RAG
- Successfully ingest and structure 40-50K job records and 10K+ skill records into Neo4j knowledge graph
- Demonstrate that hybrid search (vector + graph traversal) provides superior career insights vs keyword search
- Create reusable LangGraph + Neo4j architecture patterns for knowledge graph RAG applications
- Validate technical feasibility of real-time query responses (<5 seconds) on complex relationship queries
- Deliver MVP foundation that enables users to discover non-obvious career paths and skill relationships

## Background Context

Career planning today suffers from fragmented, disconnected data sources where job seekers struggle to understand skill relationships, career progression paths, and market opportunities. Traditional job search platforms rely on keyword matching that misses semantic connections—searching for "Python" won't surface related opportunities in data analysis, API development, or automation that require similar skill combinations.

This Graph RAG System addresses these limitations by combining Neo4j knowledge graphs with semantic embeddings to power conversational AI-driven career intelligence. The system ingests comprehensive skills and jobs taxonomies (CSV format), creates rich relationship netwoxrks between skills, jobs, companies, and locations, and enables natural language queries backed by hybrid search that leverages both vector similarity and graph traversal. This MVP validates whether graph-based RAG can provide superior career insights compared to traditional approaches, while establishing foundational patterns for future knowledge graph applications.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-10-15 | 1.0 | Initial PRD creation from approved Project Brief | John (PM Agent) |
| 2025-10-15 | 1.1 | Requirements refinement: Added intent classification to FR14, similarity threshold to FR10, upsert behavior to FR11, retry strategy to NFR10, removed duplicate FR17 | John (PM Agent) |

---
