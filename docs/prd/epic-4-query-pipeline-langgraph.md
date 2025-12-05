# Epic 4: Query Pipeline & LangGraph

**Epic Goal**: Implement the core RAG intelligence using LangGraph to orchestrate hybrid search (vector similarity + graph traversal) and generate LLM-powered responses. By the end of this epic, the system can accept natural language queries via API and return intelligent, context-aware answers backed by the knowledge graph.

## Story 4.1: LangGraph Workflow Setup

**As a** developer
**I want** a LangGraph state graph configured with all workflow nodes
**so that** I can orchestrate the query pipeline

### Acceptance Criteria

1. LangGraph installed and imported (`langgraph` package)
2. State graph created with 5 nodes: QueryUnderstanding, VectorSearch, GraphTraversal, ContextConstruction, ResponseGeneration
3. Graph state schema defined: `{user_query, query_embedding, query_intent, vector_results, graph_results, context, response}`
4. Node execution order: QueryUnderstanding → VectorSearch → GraphTraversal → ContextConstruction → ResponseGeneration
5. Each node implemented as async function accepting state and returning updated state
6. Graph compiled and ready for invocation
7. Basic end-to-end test: Pass dummy query through graph, verify all nodes execute

## Story 4.2: Query Understanding Node

**As a** system
**I want** to classify user query intent and generate query embedding
**so that** I can route to appropriate search strategies

### Acceptance Criteria

1. Node receives `user_query` from state
2. Generate query embedding using embedding service (same `all-MiniLM-L6-v2` model)
3. Classify query intent using simple keyword matching or LLM-based classification:
   - "skill requirement" - keywords: "what skills", "skills for", "skills needed"
   - "career path" - keywords: "transition", "career path", "how to become"
   - "salary analysis" - keywords: "salary", "pay", "compensation", "high-paying"
   - "skill relationship" - keywords: "similar to", "related skills", "alternatives"
   - "company query" - keywords: "companies", "employers", "who hires"
4. Default intent: "general" if no clear match
5. Update state: `{query_embedding: [...], query_intent: "skill_requirement"}`
6. Log query understanding results for debugging
7. Unit tests for each intent classification

## Story 4.3: Vector Search Node

**As a** system
**I want** to find semantically similar nodes using vector search
**so that** I retrieve relevant starting points for graph traversal

### Acceptance Criteria

1. Node receives `query_embedding` from state
2. Execute Neo4j vector search on Job.embedding, Skill.embedding, Company.embedding indexes
3. Use Cypher query: `CALL db.index.vector.queryNodes('skill_embedding_index', 15, $query_embedding) YIELD node, score`
4. Retrieve top 15 most similar nodes across all node types (configurable via param)
5. Filter results by similarity score > 0.5 (configurable threshold)
6. Return results with node properties and similarity scores
7. Update state: `{vector_results: [{node_type, node_id, properties, score}, ...]}`
8. Handle empty results gracefully (no similar nodes found)

## Story 4.4: Graph Traversal Node

**As a** system
**I want** to explore relationships from vector search results
**so that** I can retrieve rich contextual information

### Acceptance Criteria

1. Node receives `vector_results` and `query_intent` from state
2. Generate Cypher query based on intent:
   - **skill_requirement**: Start from Job nodes, traverse `Job -[REQUIRES]-> Skill`, include skill categories
   - **career_path**: Start from Skill nodes, traverse `Skill -[SIMILAR_TO]-> Skill` and `Skill <-[REQUIRES]- Job`
   - **salary_analysis**: Start from Job nodes, include salary properties, traverse to Skills and Companies
   - **skill_relationship**: Start from Skill nodes, traverse `Skill -[SIMILAR_TO]-> Skill` and categories
   - **company_query**: Start from Company or Job nodes, traverse `Job -[POSTED_BY]-> Company` and `Job -[REQUIRES]-> Skill`
3. Traversal depth: 2-3 hops from seed nodes (configurable)
4. Collect all traversed nodes and relationships
5. Return structured graph context: `{nodes: [...], relationships: [...]}`
6. Update state: `{graph_results: {nodes, relationships}}`
7. Limit total nodes returned to prevent context overflow (max 50 nodes)

## Story 4.5: Context Construction Node

**As a** system
**I want** to combine vector and graph results into structured LLM context
**so that** the LLM has all necessary information to answer the query

### Acceptance Criteria

1. Node receives `vector_results`, `graph_results`, `user_query` from state
2. Construct context string with sections:
   - **User Query**: Original question
   - **Top Matching Nodes**: Vector search results with scores
   - **Related Information**: Graph traversal results (nodes + relationships)
   - **Graph Structure**: Key relationships discovered (e.g., "Python is required by 1,234 jobs")
3. Format as structured text or JSON for LLM consumption
4. Token counting: Ensure context stays within 4000 tokens for free model
5. If context exceeds limit: Truncate graph results (keep highest-scoring nodes)
6. Include source citations: Node IDs and types for traceability
7. Update state: `{context: "...formatted context..."}`
8. Log context size and truncation events

## Story 4.6: Response Generation Node

**As a** system
**I want** to generate natural language responses using OpenRouter LLM
**so that** users receive intelligent, conversational answers

### Acceptance Criteria

1. Node receives `context` and `user_query` from state
2. Construct LLM prompt with instructions:
   - "Answer the user's question based on the knowledge graph context provided"
   - "Cite specific nodes and relationships from the graph in your answer"
   - "Explain reasoning based on graph structure"
   - "Highlight non-obvious connections discovered through graph traversal"
3. Call OpenRouter API with model `meta-llama/llama-3.3-8b-instruct:free`
4. Request parameters: `{temperature: 0.7, max_tokens: 500}`
5. Parse LLM response and extract answer text
6. Update state: `{response: "...LLM generated answer..."}`
7. Handle API failures: Retry with exponential backoff (max 3 retries: 1s, 2s, 4s)
8. If all retries fail: Return error message "Unable to generate response. Please try again."
9. Log LLM API calls (query, response, latency) for debugging

## Story 4.7: Query API Endpoint

**As a** user
**I want** to send natural language queries to the backend
**so that** I can get answers powered by the knowledge graph

### Acceptance Criteria

1. `POST /query` endpoint created (protected by JWT middleware)
2. Accepts JSON: `{query: "What skills do I need for Data Scientist roles?"}`
3. Invokes LangGraph workflow with user query
4. Returns JSON: `{query, response, sources: [{node_type, node_id, properties}], processing_time_ms}`
5. Processing time logged (total time from request to response)
6. Sources include all nodes/relationships cited in response
7. Error handling: Invalid query (empty string) returns 400
8. Error handling: LangGraph failures return 500 with error message
9. Query and response logged to PostgreSQL for analytics (user_id, query, response, timestamp)
10. Unit tests and integration tests for endpoint (valid query, empty query, malformed JSON)

## Story 4.8: Query Performance Metrics

**As a** developer
**I want** detailed performance metrics for each query
**so that** I can identify bottlenecks and optimize

### Acceptance Criteria

1. Instrument each LangGraph node with timing
2. Log metrics: `{query_understanding_time, vector_search_time, graph_traversal_time, context_construction_time, llm_generation_time, total_time}`
3. Metrics logged to application logs (JSON format for parsing)
4. Optional: Store metrics in PostgreSQL table `query_metrics` for analysis
5. `/query` endpoint returns `processing_time_ms` in response
6. Performance targets verified: Vector search <1s, Graph traversal <2s, Total <5s
7. Alert if query exceeds 5 second threshold (log warning)

---
