# Career Intelligence AI System - Technical Architecture

**Purpose**: This document provides a comprehensive technical overview of the Career Intelligence AI System for Claude to understand the project architecture, query mechanism, and context builder.

**Last Updated**: 2025-10-28
**Version**: 2.0.0

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Query Processing Pipeline](#query-processing-pipeline)
4. [Context Builder Mechanism](#context-builder-mechanism)
5. [LangGraph Workflow](#langgraph-workflow)
6. [Database Architecture](#database-architecture)
7. [Key Services](#key-services)
8. [API Structure](#api-structure)
9. [Data Flow](#data-flow)
10. [Monitoring and Observability](#monitoring-and-observability)

---

## System Overview

### What is This System?

A **GraphRAG (Graph-based Retrieval Augmented Generation)** system that provides career guidance by combining:
- **Knowledge Graph** (Neo4j) - Skills, Jobs, Companies with relationships
- **Vector Search** - Semantic similarity for query matching
- **LangGraph** - Multi-step RAG workflow orchestration
- **LLM** - Natural language response generation via OpenRouter

### Core Capabilities

1. **Natural Language Query Processing**: "What skills do I need for Data Scientist roles?"
2. **Multi-Intent Understanding**: Handles complex queries with multiple intents
3. **Graph-Based Context**: Traverses relationships to build rich context
4. **Conversation History**: Maintains session context for follow-up questions
5. **Real-time Monitoring**: Tracks query processing through WebSocket events

---

## Architecture Diagram

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI[React Frontend<br/>Port 5173]
    end

    subgraph "API Layer"
        API[FastAPI Backend<br/>Port 8000]
        AUTH[JWT Auth Middleware]
        RATE[Rate Limiter]
    end

    subgraph "LangGraph RAG Pipeline"
        LGS[LangGraph Service]
        N1[1. Query Understanding]
        N2[2. Vector Search]
        N3[3. Graph Traversal]
        N4[4. Context Construction]
        N5[5. Response Generation]

        N1 --> N2
        N2 --> N3
        N3 --> N4
        N4 --> N5
    end

    subgraph "Data Layer"
        NEO4J[(Neo4j<br/>Knowledge Graph)]
        POSTGRES[(PostgreSQL<br/>User Data)]
    end

    subgraph "External Services"
        OPENROUTER[OpenRouter LLM API]
        HF[HuggingFace Embeddings]
    end

    UI -->|HTTP + JWT| API
    API --> AUTH
    AUTH --> RATE
    RATE --> LGS
    LGS --> N1
    N1 --> HF
    N2 --> NEO4J
    N3 --> NEO4J
    N5 --> OPENROUTER
    API --> POSTGRES

    style N1 fill:#FFE5B4
    style N2 fill:#B4E5FF
    style N3 fill:#B4FFB4
    style N4 fill:#FFB4FF
    style N5 fill:#FFB4B4
```

---

## Query Processing Pipeline

### 1. Entry Point: `/api/query/ask`

**File**: `backend/app/api/query.py`

**Responsibilities**:
- Receives user query via POST request
- Validates JWT token and rate limits
- Retrieves conversation history for session
- Executes LangGraph workflow
- Logs query to PostgreSQL
- Returns structured response

**Key Flow**:
```python
# 1. Validate query
if not query_data.query.strip():
    raise HTTPException(400, "Query cannot be empty")

# 2. Generate/retrieve session_id
session_id = query_data.session_id or str(uuid.uuid4())

# 3. Retrieve conversation history (last 5 messages)
conversation_history = await query_history_repo.get_conversation_history(
    session_id=session_id,
    limit=5
)

# 4. Execute LangGraph workflow
result = await langgraph_service.execute_query(
    query=query_data.query,
    user_id=current_user_id,
    session_id=session_id,
    conversation_history=conversation_history
)

# 5. Log to database
await query_history_repo.create_query_history(...)

# 6. Return response
return QueryResponse(
    query=query_data.query,
    response=result["response"],
    sources=result["sources"],
    processing_time_ms=result["processing_time_ms"],
    metadata=result["metadata"]
)
```

### 2. LangGraph Service: Workflow Orchestration

**File**: `backend/app/services/langgraph_service.py`

**Responsibilities**:
- Compiles and executes LangGraph workflow
- Manages state transitions between nodes
- Collects metrics and timing data
- Handles timeouts (200s for reasoning models)
- Extracts and deduplicates sources

**Key Flow**:
```python
# 1. Format conversation history
history_context = "\n".join([
    f"User: {msg['query']}\nAssistant: {msg['response'][:200]}..."
    for msg in conversation_history
])

# 2. Create initial state
initial_state = GraphRAGState(
    user_query=query,
    user_id=user_id,
    metadata={
        "metrics": QueryMetrics(...),
        "session_id": session_id,
        "conversation_history": conversation_history,
        "history_context": history_context
    }
)

# 3. Execute workflow with timeout
result = await asyncio.wait_for(
    self.workflow.ainvoke(initial_state),
    timeout=200.0
)

# 4. Extract response and sources
response_text = result.get("final_response", "")
sources = self._extract_sources(result)
```

---

## LangGraph Workflow

### Workflow State Schema

**File**: `backend/app/agents/graph.py`

```python
class GraphRAGState(BaseModel):
    # Required fields
    user_query: str                           # Original query
    user_id: str                              # User ID

    # Populated by nodes
    query_embedding: Optional[List[float]]    # 384-dim vector
    intent: Optional[str]                     # Primary intent (backward compat)
    intents: Optional[List[str]]              # All detected intents
    entities: Optional[List[Dict]]            # Extracted entities
    vector_results: Optional[List[Dict]]      # Vector search results
    graph_context: Optional[List[Dict]]       # Graph traversal results
    constructed_context: Optional[str]        # Formatted context for LLM
    final_response: Optional[str]             # Generated response
    metadata: Optional[Dict[str, Any]]        # Execution metadata
```

### Node 1: Query Understanding

**File**: `backend/app/agents/nodes/query_understanding.py`

**Purpose**: Analyze user query using multi-layer intent analysis

**Process**:
```
1. EMBEDDING GENERATION
   └─ Generate 384-dim vector using sentence-transformers/all-MiniLM-L6-v2

2. ENTITY EXTRACTION (Graph-Informed)
   ├─ Use DeepEntityExtractor with semantic matching
   ├─ Match entities against Neo4j graph nodes
   ├─ Extract: skills, jobs, companies, locations
   └─ Fallback to regex patterns if graph fails

3. INTENT CLASSIFICATION (Multi-Layer)
   ├─ Layer 1: Syntactic (regex patterns)
   ├─ Layer 2: Semantic (embedding similarity)
   ├─ Layer 3: Entity-informed (graph context)
   └─ Layer 4: Query decomposition (execution planning)

4. OUTPUT
   ├─ query_embedding: [384 floats]
   ├─ intent: "skill_requirement" (primary)
   ├─ intents: ["skill_requirement", "salary_analysis"]
   └─ entities: [{type, value, confidence, source, graph_node_id}]
```

**Intent Types**:
- `skill_requirement` - "What skills are needed for X?"
- `career_path` - "How do I become a Y?"
- `salary_analysis` - "What's the salary for Z?"
- `skill_relationship` - "Skills similar to A?"
- `company_query` - "Which companies hire for B?"
- `general` - Catch-all for other queries

**Example**:
```
Query: "What frameworks are needed for backend development and what's the typical salary?"

Output:
  intents: ["skill_requirement", "salary_analysis"]
  entities: [
    {type: "role", value: "backend developer", confidence: 0.7},
    {type: "skill", value: "frameworks", confidence: 0.6}
  ]
  query_embedding: [0.234, -0.567, ..., 0.123]  # 384 dimensions
```

### Node 2: Vector Search

**File**: `backend/app/agents/nodes/vector_search.py`

**Purpose**: Find semantically similar nodes using vector similarity

**Process**:
```
1. PARALLEL VECTOR SEARCHES
   ├─ Search Skills index (top-k=15)
   ├─ Search Jobs index (top-k=15)
   └─ Search Companies index (top-k=15)

2. COMBINE AND RANK
   ├─ Merge all results
   ├─ Sort by similarity score (descending)
   ├─ Filter by threshold (default: 0.5)
   └─ Return top-k (default: 15)

3. OUTPUT
   └─ vector_results: [{
        node_type: "Skill",
        id: "skill_123",
        name: "Python",
        score: 0.92,
        properties: {...}
      }]
```

**Vector Search Query** (Cypher):
```cypher
CALL db.index.vector.queryNodes(
  'skill_embeddings',        // Index name
  15,                        // Top-k
  $query_embedding           // 384-dim vector
)
YIELD node, score
WHERE score >= 0.5          // Threshold
RETURN node, score
```

**Performance**: ~45-100ms for parallel search across 3 indexes

### Node 3: Graph Traversal

**File**: `backend/app/agents/nodes/graph_traversal.py`

**Purpose**: Discover related nodes and relationships through graph traversal

**Process**:
```
1. EXTRACT SEED NODES
   ├─ Take top-10 vector results as starting points
   └─ seed_ids: ["skill_1", "skill_2", ..., "skill_10"]

2. GENERATE INTENT-SPECIFIC CYPHER
   ├─ For each detected intent:
   │   ├─ skill_requirement → Find REQUIRES relationships
   │   ├─ career_path → Traverse SIMILAR_TO chains
   │   ├─ salary_analysis → Join with POSTED_BY companies
   │   └─ company_query → Find jobs and skills
   └─ Use variable-length patterns [*1..depth]

3. EXECUTE QUERIES (Multi-Intent)
   ├─ Run separate query for EACH intent
   ├─ Merge all results
   └─ Deduplicate nodes and relationships

4. FORMAT RESULTS
   └─ graph_context: [
       {node_type: "Skill", node_id: "...", properties: {...}},
       {type: "REQUIRES", properties: {...}}
     ]
```

**Example Cypher** (skill_requirement):
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

**Output Statistics**:
- Nodes discovered: 20-50 typical
- Relationships traversed: 30-100 typical
- Relationship types: REQUIRES, SIMILAR_TO, POSTED_BY, BELONGS_TO_CATEGORY

### Node 4: Context Construction

**File**: `backend/app/agents/nodes/context_construction.py`

**Purpose**: Format vector + graph data into structured LLM context

**Process**:
```
1. BUILD CONTEXT SECTIONS
   ├─ Section 0: Graph Statistics Header (CRITICAL)
   │   └─ "🔍 KNOWLEDGE GRAPH ANALYSIS RESULTS"
   │       "Vector Search: 15 matches"
   │       "Graph Traversal: 35 nodes, 58 relationships"
   │
   ├─ Section 1: User Query + Intents + Entities
   │   └─ "User's Question: ..."
   │       "Focus Areas: skill requirements, salary analysis"
   │       "Skills Mentioned: Python, Django"
   │
   ├─ Section 2: Top Matching Nodes (from vector search)
   │   └─ Grouped by type (Jobs, Skills, Companies)
   │       Formatted naturally with details
   │
   ├─ Section 3: Related Information (from graph traversal)
   │   └─ "Skills from Graph (8 found):"
   │       "Jobs from Graph (5 positions):"
   │       "Graph Connections Found:"
   │
   ├─ Section 4: Skill Gap Analysis (if career_path + skill_requirement)
   │   └─ "Your Foundation: Python, JavaScript"
   │       "Skills to Develop: Django, PostgreSQL, AWS"
   │
   └─ Section 5: Market Summary
       └─ Job counts, salary ranges, company insights

2. TOKEN MANAGEMENT
   ├─ Count tokens (tiktoken for GPT models)
   ├─ Check against limit (4000 tokens)
   ├─ Truncate if needed (preserve query + top results)
   └─ Add truncation notice

3. OUTPUT
   └─ constructed_context: "=== GRAPH STATISTICS ===\n\n## User Query\n..."
```

**Context Format Example**:
```
======================================================================
🔍 KNOWLEDGE GRAPH ANALYSIS RESULTS
======================================================================

**Vector Search:** 15 initial matches found
**Graph Traversal:** Explored 35 nodes and 58 relationships

**Relationship Types Discovered:**
  • 24× Requires
  • 18× Similar To
  • 12× Posted By
  • 4× Belongs To Category

⚠️  IMPORTANT: You MUST reference these graph statistics in your response.
======================================================================

## User's Question
What skills do I need to become a backend developer?

**Focus Area:** Exploring skill requirements

## Relevant Opportunities & Information

**Job Opportunities:**
• Backend Developer at Google (₹12.0-18.0 LPA)
• Python Developer at Amazon (₹10.0-15.0 LPA)
• Django Engineer at Microsoft (₹15.0-22.0 LPA)

**Relevant Skills:**
• Python (Programming Language)
  → Popular server-side language with extensive frameworks
• Django (Web Framework)
  → High-level Python web framework for rapid development
• PostgreSQL (Database)
  → Advanced open-source relational database

## Graph Relationships & Insights

**Skills from Graph (8 found):**
- Python
- Django
- Flask
- PostgreSQL
- Redis
- Docker
- AWS
- REST APIs

**Jobs from Graph (5 positions):**
- Backend Developer
- Python Developer
- Django Engineer
- API Developer
- Full Stack Developer

**Graph Connections Found:**
- 24 Skills Required relationships
- 18 Similar Skills relationships
- 4 Skill Categories relationships

*Graph traversal discovered 35 nodes and 58 relationships across the knowledge graph.*

## Market Summary

• Found **5 job opportunities** matching your interests
• Typical salary range: **₹10.0-18.0 LPA** (based on 5 positions)
• Identified **8 relevant skills** in high demand
```

**Token Budget**:
- Target: 2000-3000 tokens
- Limit: 4000 tokens (hard limit)
- Truncation: Preserve query + top vector results, reduce graph context

### Node 5: Response Generation

**File**: `backend/app/agents/nodes/response_generation.py`

**Purpose**: Generate natural language response using LLM

**Process**:
```
1. CHECK PIPELINE ERRORS
   ├─ If any previous node failed → Return error message
   └─ Include debug instructions for user

2. BUILD PROMPTS
   ├─ System Prompt: Career advisor persona + instructions
   │   └─ "You are a helpful career advisor..."
   │       "ALWAYS mention graph statistics..."
   │       "Response structure: Direct Answer, Key Insights, Graph Insights..."
   │
   └─ User Prompt: Context + Query + Conversation History
       └─ "CONVERSATION HISTORY: ..."
           "CURRENT CONTEXT: ..."
           "User's Question: ..."

3. CALL LLM (OpenRouter)
   ├─ Model: meta-llama/llama-3.3-8b-instruct:free (or configured)
   ├─ Temperature: 0.3 (low for factual precision)
   ├─ Max Tokens: 1200 (comprehensive responses)
   ├─ Retry: 3 attempts with exponential backoff
   └─ Circuit Breaker: Fail fast after 3 consecutive failures

4. OUTPUT
   └─ final_response: "Based on the job market data..."
```

**System Prompt Structure**:
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

**Response Example**:
```markdown
Based on the job market data, **backend development roles typically require 5-7 core skills**. Our graph analysis explored **35 nodes and 58 relationships** across the knowledge graph to give you this comprehensive view.

**Essential Skills:**
- Python is required by 95% of positions
- Django or Flask (web frameworks)
- PostgreSQL for data management
- REST API development

**Graph Insights:**
Graph analysis revealed 35 nodes across 58 relationships, including:
- Found 24 skill-requirement connections
- Discovered 18 similar skill relationships showing career progression paths
- Traversed relationships linking 5 job positions to 8 key skills

**Salary Expectations:**
Entry-level positions typically offer ₹10-15 LPA, while experienced developers can expect ₹18-30 LPA.

**Next Steps:**
Start with Python and a web framework. Build portfolio projects with REST APIs and databases.

<details>
<summary>📊 Technical Details</summary>

- Query type: skill_requirement
- Graph traversal: 35 nodes, 58 relationships
- Results found: 5 jobs, 8 skills
- Confidence: 92%
</details>
```

---

## Context Builder Mechanism

### Overview

The context builder is a **multi-stage pipeline** that transforms user queries into structured LLM context:

```
User Query → Vector Results + Graph Results → Formatted Context → LLM Response
```

### Stage 1: Vector Search Results

**Input**: Query embedding (384-dim)
**Process**: Semantic similarity search
**Output**: Top-k most similar nodes

```python
vector_results = [
    {
        "node_type": "Skill",
        "id": "skill_python",
        "name": "Python",
        "score": 0.92,
        "properties": {
            "description": "High-level programming language",
            "category": "Programming Language"
        }
    },
    # ... more results
]
```

### Stage 2: Graph Traversal Results

**Input**: Seed node IDs from vector results
**Process**: Intent-specific Cypher queries
**Output**: Related nodes + relationships

```python
graph_context = [
    # Nodes
    {
        "node_type": "Job",
        "node_id": "job_123",
        "name": "Backend Developer",
        "properties": {
            "company_name": "Google",
            "salary_min": 1200000,
            "salary_max": 1800000
        }
    },
    # Relationships
    {
        "type": "REQUIRES",
        "properties": {
            "importance": "critical"
        }
    }
]
```

### Stage 3: Context Formatting

**Input**: vector_results + graph_context + intents + entities
**Process**: Format into structured sections
**Output**: Natural language context

**Formatting Strategy**:

1. **Prioritization**:
   - Always include: User query, graph statistics, top vector results
   - Conditional: Skill gap analysis (if career_path + skill_requirement)
   - Optional: Market summary, salary insights

2. **Grouping**:
   - Group by node type (Skills, Jobs, Companies)
   - Group relationships by type (REQUIRES, SIMILAR_TO, etc.)

3. **Natural Language**:
   - Replace technical terms ("REQUIRES" → "Skills Required")
   - Format salaries (1200000 → "₹12.0 LPA")
   - Add contextual descriptions

4. **Token Management**:
   - Count tokens using tiktoken
   - Progressive truncation (reduce graph context first)
   - Add truncation notice if needed

### Stage 4: LLM Integration

**Input**: Constructed context + conversation history
**Process**: Prompt engineering
**Output**: Natural language response

**Prompt Structure**:
```
SYSTEM: <Career advisor persona + instructions>

USER:
  CONVERSATION HISTORY (if exists):
    User: Previous question
    Assistant: Previous answer

  CURRENT CONTEXT:
    <Formatted context from Stage 3>

  User's Current Question: <query>

  Instructions:
    - Consider conversation history for follow-ups
    - Reference specific data from context
    - Include graph statistics
```

---

## Database Architecture

### Neo4j Knowledge Graph

**Purpose**: Store skills, jobs, companies, and relationships

**Node Types**:

1. **Skill**:
   ```cypher
   (:Skill {
     id: "skill_python",
     name: "Python",
     description: "High-level programming language",
     category: "Programming Language",
     embedding: [384-dim vector]
   })
   ```

2. **Job**:
   ```cypher
   (:Job {
     job_id: "job_123",
     job_title: "Backend Developer",
     company_name: "Google",
     salary_min: 1200000,
     salary_max: 1800000,
     embedding: [384-dim vector]
   })
   ```

3. **Company**:
   ```cypher
   (:Company {
     company_name: "Google",
     industry: "Technology",
     embedding: [384-dim vector]
   })
   ```

4. **Category**:
   ```cypher
   (:Category {
     category_id: "cat_prog",
     name: "Programming Languages"
   })
   ```

**Relationships**:

- `(:Job)-[:REQUIRES]->(:Skill)` - Job skill requirements
- `(:Skill)-[:SIMILAR_TO]->(:Skill)` - Similar skills
- `(:Job)-[:POSTED_BY]->(:Company)` - Job postings
- `(:Skill)-[:BELONGS_TO_CATEGORY]->(:Category)` - Skill categorization

**Vector Indexes**:
```cypher
// HNSW indexes for fast similarity search
CREATE VECTOR INDEX skill_embeddings FOR (n:Skill) ON (n.embedding)
CREATE VECTOR INDEX job_embeddings FOR (n:Job) ON (n.embedding)
CREATE VECTOR INDEX company_embeddings FOR (n:Company) ON (n.embedding)
```

### PostgreSQL Relational Database

**Purpose**: Store user data, query history, sessions

**Schema** (`backend/prisma/schema.prisma`):

```prisma
model User {
  id            String   @id @default(uuid())
  email         String   @unique
  password_hash String
  full_name     String
  created_at    DateTime @default(now())

  query_history QueryHistory[]
}

model QueryHistory {
  id            String   @id @default(uuid())
  user_id       String
  session_id    String   // For conversation tracking
  query_text    String
  response_text String
  metadata      Json     // Intent, sources, metrics
  created_at    DateTime @default(now())

  user User @relation(fields: [user_id], references: [id])

  @@index([user_id, session_id])
  @@index([created_at])
}
```

**Queries**:

1. **Create Query History**:
   ```python
   await query_history_repo.create_query_history(
       user_id=user_id,
       session_id=session_id,
       query_text=query,
       response_text=response,
       metadata=json.dumps({
           "intent": "skill_requirement",
           "sources": [...],
           "processing_time_ms": 1234
       })
   )
   ```

2. **Get Conversation History**:
   ```python
   # Retrieve last 5 messages for session
   history = await query_history_repo.get_conversation_history(
       session_id=session_id,
       limit=5
   )
   # Returns: [{query, response, timestamp}, ...]
   ```

---

## Key Services

### 1. EmbeddingService

**File**: `backend/app/services/embedding_service.py`

**Purpose**: Generate vector embeddings using HuggingFace

**Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)

**Usage**:
```python
service = EmbeddingService()
result = await service.generate_embedding("Python programming")

# Output:
{
    "embedding": [0.234, -0.567, ..., 0.123],  # 384 floats
    "model_version": "all-MiniLM-L6-v2",
    "dimensions": 384
}
```

### 2. OpenRouterService

**File**: `backend/app/services/openrouter_service.py`

**Purpose**: Call LLM APIs with retry logic and circuit breaker

**Features**:
- Retry logic (3 attempts, exponential backoff)
- Circuit breaker (fail fast after failures)
- Token counting and usage tracking
- Latency monitoring

**Usage**:
```python
service = OpenRouterService()
result = await service.generate_completion(
    system_prompt="You are a career advisor...",
    user_prompt="Context: ...\nQuestion: ...",
    max_tokens=1200,
    temperature=0.3,
    max_retries=3
)

# Output:
{
    "text": "Based on the job market data...",
    "model": "meta-llama/llama-3.3-8b-instruct:free",
    "usage": {
        "prompt_tokens": 856,
        "completion_tokens": 234,
        "total_tokens": 1090
    },
    "latency_ms": 1234,
    "retry_count": 0
}
```

### 3. DeepIntentAnalyzer

**File**: `backend/app/services/intent_analysis_service.py`

**Purpose**: Multi-layer intent classification

**Layers**:
1. **Syntactic**: Regex pattern matching
2. **Semantic**: Embedding similarity to intent archetypes
3. **Entity-Informed**: Refine based on extracted entities
4. **Query Decomposition**: Break complex queries into steps

**Usage**:
```python
analyzer = DeepIntentAnalyzer(embedding_service)
result = await analyzer.analyze_intent(
    query="What skills are needed for backend development?",
    query_embedding=[...],
    entities=[Entity(type="role", value="backend developer")]
)

# Output:
{
    "primary_intent": "skill_requirement",
    "primary_confidence": 0.92,
    "all_intents": ["skill_requirement"],
    "reasoning_trail": [
        {
            "layer": "syntactic",
            "decision": "Matched pattern: 'skills needed'",
            "confidence": 0.85
        },
        {
            "layer": "semantic",
            "decision": "High similarity to skill_requirement archetype",
            "confidence": 0.90
        }
    ],
    "query_plan": {
        "steps": ["Find skills", "Check requirements", "Provide learning path"],
        "complexity_score": 0.6,
        "requires_multi_hop": True
    }
}
```

### 4. DeepEntityExtractor

**File**: `backend/app/services/entity_extraction_service.py`

**Purpose**: Extract entities with graph-informed matching

**Features**:
- Semantic matching against Neo4j nodes
- Entity linking to graph IDs
- Confidence scoring
- Fallback to regex patterns

**Usage**:
```python
extractor = DeepEntityExtractor(embedding_service, neo4j_repo)
entities = await extractor.extract_entities(
    query="I want to learn Python and Django",
    query_embedding=[...],
    user_id="user_123"
)

# Output:
[
    Entity(
        type="skill",
        value="Python",
        confidence=0.95,
        source="graph_match",
        graph_node_id="skill_python"
    ),
    Entity(
        type="skill",
        value="Django",
        confidence=0.92,
        source="graph_match",
        graph_node_id="skill_django"
    )
]
```

### 5. PipelineMonitoringService

**File**: `backend/app/services/pipeline_monitoring_service.py`

**Purpose**: Real-time query pipeline monitoring via WebSockets

**Events**:
- `query_understanding`: Intent classification complete
- `vector_search`: Vector similarity results
- `graph_traversal`: Graph exploration complete
- `context_construction`: Context formatted
- `response_generation`: LLM response ready

**Usage**:
```python
monitor = get_pipeline_monitoring_service()

# Emit stage completion
await monitor.emit_vector_search(
    session_id=session_id,
    user_id=user_id,
    query=query,
    status=StageStatus.COMPLETED,
    duration_ms=45.2,
    skills_found=8,
    jobs_found=5,
    companies_found=2
)
```

---

## API Structure

### Authentication Endpoints

**Base**: `/api/auth`

1. **Register**: `POST /api/auth/register`
   ```json
   Request: {
     "email": "user@example.com",
     "password": "secure_password",
     "full_name": "John Doe"
   }

   Response: {
     "access_token": "eyJhbGc...",
     "user_id": "uuid"
   }
   ```

2. **Login**: `POST /api/auth/login`
   ```json
   Request: {
     "email": "user@example.com",
     "password": "secure_password"
   }

   Response: {
     "access_token": "eyJhbGc...",
     "token_type": "bearer"
   }
   ```

### Query Endpoint

**Base**: `/api/query`

**Execute Query**: `POST /api/query/ask`

```json
Request: {
  "query": "What skills do I need for backend development?",
  "session_id": "uuid"  // Optional, for follow-ups
}

Response: {
  "query": "What skills do I need for backend development?",
  "response": "Based on the job market data...",
  "sources": [
    {
      "node_type": "Skill",
      "node_id": "skill_python",
      "properties": {
        "name": "Python",
        "description": "..."
      }
    }
  ],
  "processing_time_ms": 1234,
  "metadata": {
    "intent": "skill_requirement",
    "intent_confidence": 0.92,
    "vector_results_count": 15,
    "graph_nodes_count": 35,
    "graph_relationships_count": 58
  }
}
```

---

## Data Flow

### Complete Query Flow Diagram

```
User Query
    ↓
[1] API Endpoint (/api/query/ask)
    ├─ JWT Authentication
    ├─ Rate Limiting (10/min)
    ├─ Retrieve conversation history
    └─ Generate/retrieve session_id
    ↓
[2] LangGraph Service
    ├─ Create initial state
    ├─ Format conversation history
    └─ Execute workflow (200s timeout)
    ↓
[3] Node 1: Query Understanding
    ├─ Generate embedding (HuggingFace)
    ├─ Extract entities (graph-informed)
    ├─ Classify intent (4 layers)
    └─ Output: embedding, intents, entities
    ↓
[4] Node 2: Vector Search
    ├─ Parallel search (Skills, Jobs, Companies)
    ├─ Combine and rank by score
    └─ Output: Top-15 similar nodes
    ↓
[5] Node 3: Graph Traversal
    ├─ Extract seed nodes (top-10 from vector)
    ├─ Generate intent-specific Cypher
    ├─ Execute multi-intent queries
    └─ Output: Related nodes + relationships
    ↓
[6] Node 4: Context Construction
    ├─ Format 5 sections (stats, query, results, insights, summary)
    ├─ Token counting (target: 3000, limit: 4000)
    ├─ Truncate if needed
    └─ Output: Formatted context string
    ↓
[7] Node 5: Response Generation
    ├─ Check pipeline errors
    ├─ Build prompts (system + user)
    ├─ Call LLM (OpenRouter, temp=0.3, max_tokens=1200)
    ├─ Retry 3x on failure
    └─ Output: Natural language response
    ↓
[8] LangGraph Service (return)
    ├─ Extract response
    ├─ Extract sources (deduplicated)
    ├─ Collect metrics
    └─ Return result dict
    ↓
[9] API Endpoint (return)
    ├─ Log to PostgreSQL (query history)
    ├─ Format QueryResponse
    └─ Return to frontend
    ↓
User receives response + sources + metadata
```

### State Transitions

```python
# State after Node 1 (Query Understanding)
{
    "user_query": "What skills...",
    "user_id": "user_123",
    "query_embedding": [384 floats],
    "intent": "skill_requirement",
    "intents": ["skill_requirement"],
    "entities": [{type, value, confidence}],
    "metadata": {
        "query_understanding_completed": True,
        "intent_confidence": 0.92
    }
}

# State after Node 2 (Vector Search)
{
    ...,
    "vector_results": [
        {node_type, id, name, score, properties}
    ],
    "metadata": {
        ...,
        "vector_search_completed": True,
        "vector_results_count": 15
    }
}

# State after Node 3 (Graph Traversal)
{
    ...,
    "graph_context": [
        {node_type, node_id, properties},
        {type: "REQUIRES", properties}
    ],
    "metadata": {
        ...,
        "graph_traversal_completed": True,
        "graph_nodes_count": 35,
        "graph_relationships_count": 58
    }
}

# State after Node 4 (Context Construction)
{
    ...,
    "constructed_context": "=== GRAPH STATS ===\n...",
    "metadata": {
        ...,
        "context_construction_completed": True,
        "context_token_count": 2856
    }
}

# State after Node 5 (Response Generation)
{
    ...,
    "final_response": "Based on the job market data...",
    "metadata": {
        ...,
        "response_generation_completed": True,
        "llm_tokens_used": 1090
    }
}
```

---

## Monitoring and Observability

### Metrics Collection

**File**: `backend/app/utils/metrics.py`

**QueryMetrics Class**:
```python
metrics = QueryMetrics(
    query_id="uuid",
    user_id="user_123",
    query_text="What skills..."
)

# Track stage timing
metrics.start_timer("query_understanding")
# ... processing ...
duration = metrics.end_timer("query_understanding")  # Returns ms

# Get total time
total_ms = metrics.get_total_time()

# Export for logging
metrics_dict = metrics.to_dict()
# {
#   "query_id": "uuid",
#   "timings": {
#     "query_understanding": 45.2,
#     "vector_search": 78.3,
#     ...
#   },
#   "total_time_ms": 1234
# }
```

### Logging Strategy

**Format**: JSON structured logging

**Levels**:
- `INFO`: Stage completion, metrics
- `WARNING`: Fallbacks, empty results
- `ERROR`: Failures, exceptions

**Example Log**:
```json
{
  "timestamp": "2025-10-28T10:30:45.123Z",
  "level": "INFO",
  "logger": "QueryUnderstanding",
  "message": "Deep analysis complete",
  "context": {
    "session_id": "abc123",
    "user_id": "user_456",
    "primary_intent": "skill_requirement",
    "confidence": 0.92,
    "duration_ms": 45.2
  }
}
```

### Pipeline Monitoring

**WebSocket Events**:

Frontend can subscribe to real-time pipeline events:

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/monitoring");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Event types:
  // - query_understanding_complete
  // - vector_search_complete
  // - graph_traversal_complete
  // - context_construction_complete
  // - response_generation_complete

  console.log(`Stage ${data.stage}: ${data.status}`);
  console.log(`Duration: ${data.duration_ms}ms`);
};
```

---

## Performance Benchmarks

### Typical Query Performance

```
Total Query Time: 1000-2000ms

Breakdown:
├─ Query Understanding: 40-80ms
│  ├─ Embedding generation: 20-40ms
│  ├─ Entity extraction: 10-20ms
│  └─ Intent classification: 10-20ms
│
├─ Vector Search: 40-100ms
│  ├─ Skills search: 15-30ms
│  ├─ Jobs search: 15-30ms
│  └─ Companies search: 10-40ms
│
├─ Graph Traversal: 80-200ms
│  ├─ Cypher query execution: 60-150ms
│  └─ Result formatting: 20-50ms
│
├─ Context Construction: 20-50ms
│  ├─ Formatting: 10-30ms
│  └─ Token counting: 10-20ms
│
└─ Response Generation: 800-1500ms
   ├─ Prompt building: 5-10ms
   └─ LLM API call: 795-1490ms
```

### Optimization Targets

- **Vector Search**: <100ms (HNSW index optimization)
- **Graph Traversal**: <150ms (Cypher query optimization)
- **Context Construction**: <50ms (Template caching)
- **LLM Response**: <1500ms (Model selection, streaming)

---

## Error Handling

### Pipeline Error Detection

Each node can fail independently. The system tracks errors in `state.metadata`:

```python
# Check for errors before LLM generation
pipeline_errors = []
if state.metadata.get("vector_search_error"):
    pipeline_errors.append("Vector Search failed")
if state.metadata.get("graph_traversal_error"):
    pipeline_errors.append("Graph Traversal failed")

if pipeline_errors:
    # Return diagnostic error message
    return {
        "final_response": "⚠️ PIPELINE ERROR\n\nStages failed:\n..." + debug_instructions
    }
```

### Error Response Format

```json
{
  "query": "What skills...",
  "response": "⚠️ PIPELINE ERROR DETECTED\n\nStages failed:\n- Vector Search: Connection timeout\n\n🔧 DEBUG INSTRUCTIONS:\n1. Check server logs\n2. Verify Neo4j connection...",
  "sources": [],
  "processing_time_ms": 234,
  "metadata": {
    "response_generation_skipped": true,
    "pipeline_errors_detected": ["Vector Search: Connection timeout"]
  }
}
```

---

## Conversation History

### Session Management

**Session ID**: UUID generated on first query, reused for follow-ups

**Flow**:
```
Query 1 (New Session):
  └─ No session_id provided
  └─ Generate new UUID
  └─ conversation_history = []
  └─ Return session_id in response

Query 2 (Follow-up):
  └─ session_id provided
  └─ Retrieve history from PostgreSQL
  └─ conversation_history = [
       {query: "...", response: "...", timestamp: "..."},
       ...
     ]
  └─ Include in LLM context
```

### History Context Format

```python
# Format for LLM context
history_context = "\n".join([
    f"User: {msg['query']}\nAssistant: {msg['response'][:200]}..."
    for msg in conversation_history[-5:]  # Last 5 messages
])

# Example output:
"""
User: What skills are needed for backend development?
Assistant: Based on the job market data, backend development roles typically require 5-7 core skills. Essential skills include Python (95% of positions), SQL...

User: What about salaries?
Assistant: Entry-level backend developer positions typically offer ₹10-15 LPA in India. Experienced developers can expect ₹18-30 LPA depending on skills...
"""
```

### Follow-up Query Handling

**Prompt Modification**:
```python
if history_context:
    prompt = f"""CONVERSATION HISTORY:
{history_context}

---

CURRENT CONTEXT (Knowledge Graph Data):
{context}

---

User's Current Question: {query}

IMPORTANT: This is a follow-up question. Consider the conversation history when responding.
If the user asks "what about salaries?" or "tell me more", refer back to the previous discussion.
"""
```

---

## Configuration

### Environment Variables

**Required**:
```bash
# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/db

# LLM
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=meta-llama/llama-3.3-8b-instruct:free

# Embedding
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

**Optional**:
```bash
# Performance tuning
VECTOR_SEARCH_K=15
VECTOR_SEARCH_THRESHOLD=0.5
GRAPH_TRAVERSAL_DEPTH=2
CONTEXT_TOKEN_LIMIT=4000
LLM_MAX_TOKENS=1200
LLM_TEMPERATURE=0.3
```

---

## Development Guidelines

### Adding New Intent Types

1. **Update `detect_intents()` in `query_understanding.py`**:
   ```python
   intent_patterns.append((
       r"pattern for new intent",
       "new_intent_type"
   ))
   ```

2. **Update `GraphRAGState` validators in `graph.py`**:
   ```python
   allowed_intents = [
       ...,
       "new_intent_type"
   ]
   ```

3. **Add Cypher query in `graph_traversal.py`**:
   ```python
   queries["new_intent_type"] = """
       MATCH (n:NodeType) WHERE n.id IN $seed_ids
       ...
       RETURN ...
   """
   ```

4. **Update context formatting in `context_construction.py`**:
   ```python
   if "new_intent_type" in intents:
       # Add special formatting logic
   ```

### Testing Query Pipeline

```bash
# Run backend tests
cd backend
pytest tests/test_agents/test_query_understanding.py
pytest tests/test_agents/test_vector_search.py
pytest tests/test_agents/test_graph_traversal.py

# Test end-to-end flow
pytest tests/test_integration/test_query_flow.py -v

# Test with sample query
curl -X POST http://localhost:8000/api/query/ask \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What skills are needed for backend development?"}'
```

---

## Future Enhancements

### Planned Features

1. **Query Caching**:
   - Cache vector search results
   - Cache graph traversal results
   - TTL: 1 hour

2. **Streaming Responses**:
   - Stream LLM responses token-by-token
   - WebSocket-based streaming
   - Progress indicators for long queries

3. **Multi-Modal Queries**:
   - Support image inputs (resumes, skill diagrams)
   - OCR + entity extraction
   - Visual skill relationship graphs

4. **Advanced Analytics**:
   - Query pattern analysis
   - User journey tracking
   - Skill demand forecasting

5. **Personalization**:
   - User skill profiles
   - Personalized recommendations
   - Career path suggestions

---

## Troubleshooting

### Common Issues

**1. Empty Vector Search Results**:
```
Issue: vector_results = []
Cause: Threshold too high or no embeddings in Neo4j
Solution: Lower threshold to 0.3 or re-index embeddings
```

**2. Graph Traversal Timeout**:
```
Issue: Cypher query takes >10 seconds
Cause: Missing indexes or complex pattern
Solution: Add indexes on frequently queried properties
```

**3. Context Token Overflow**:
```
Issue: Context exceeds 4000 tokens
Cause: Too many graph results
Solution: Reduce graph traversal depth or top-k
```

**4. LLM Generation Failure**:
```
Issue: OpenRouter API returns 429 (rate limit)
Cause: Too many requests
Solution: Implement request queuing or use paid tier
```

---

## References

### Key Files

**API**:
- `backend/app/api/query.py` - Query endpoint
- `backend/app/middleware/auth.py` - JWT authentication

**Services**:
- `backend/app/services/langgraph_service.py` - Workflow orchestration
- `backend/app/services/embedding_service.py` - Vector embeddings
- `backend/app/services/openrouter_service.py` - LLM API
- `backend/app/services/intent_analysis_service.py` - Intent classification
- `backend/app/services/entity_extraction_service.py` - Entity extraction

**Agents/Nodes**:
- `backend/app/agents/graph.py` - Workflow definition
- `backend/app/agents/nodes/query_understanding.py` - Intent + entities
- `backend/app/agents/nodes/vector_search.py` - Semantic search
- `backend/app/agents/nodes/graph_traversal.py` - Graph exploration
- `backend/app/agents/nodes/context_construction.py` - Context formatting
- `backend/app/agents/nodes/response_generation.py` - LLM response

**Repositories**:
- `backend/app/repositories/neo4j_repository.py` - Neo4j operations
- `backend/app/repositories/query_history_repository.py` - Query logging

**Utils**:
- `backend/app/utils/metrics.py` - Performance tracking
- `backend/app/utils/logger.py` - Structured logging
- `backend/app/utils/token_counter.py` - Token counting

### External Documentation

- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Neo4j**: https://neo4j.com/docs/
- **FastAPI**: https://fastapi.tiangolo.com/
- **OpenRouter**: https://openrouter.ai/docs

---

**End of Technical Architecture Document**
