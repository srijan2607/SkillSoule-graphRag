# Epic List

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
