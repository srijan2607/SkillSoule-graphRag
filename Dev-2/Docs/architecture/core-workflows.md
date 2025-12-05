# Core Workflows

## Workflow 1: Skill Transfer Query (NEW v2.0)

**Use Case:** User asks "Which of my skills transfer to UX Designer roles?"

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LG as LangGraph
    participant GM as Graph Metrics
    participant NEO as Neo4j + GDS
    participant LLM

    User->>API: "Which skills transfer to UX Designer?"
    API->>LG: Execute pipeline

    Note over LG: Node 1: Query Understanding
    LG->>LG: Classify intent → skill_transfer
    LG->>LG: Extract entities → job: "UX Designer"

    Note over LG: Node 2: Vector Search
    LG->>NEO: Find UX Designer jobs
    NEO-->>LG: Top-10 UX Designer job nodes

    Note over LG: Node 3: Graph Traversal + Metrics
    LG->>NEO: Get required skills for UX Designer jobs
    NEO-->>LG: Required skills: [Figma, UX Research, User Psychology, ...]

    LG->>GM: Calculate closeness(user_skills, required_skills)
    GM->>NEO: Shortest path queries (React → Figma, CSS → Design Systems)
    NEO-->>GM: Paths + distances
    GM->>GM: Calculate closeness scores
    GM-->>LG: Closeness values

    LG->>GM: Calculate TransitionIndex
    GM->>GM: 0.5*AvgCloseness + 0.3*Overlap + 0.2*Demand
    GM-->>LG: TransitionIndex = 0.68 (Moderate feasibility)

    Note over LG: Node 4: Context Construction
    LG->>LG: Format context with closeness scores, paths

    Note over LG: Node 5: Response Generation
    LG->>LLM: Generate response with metric citations
    LLM-->>LG: "Your React, CSS, JavaScript skills transfer well (closeness 0.72)..."

    LG-->>API: Response + metrics
    API-->>User: JSON {response, TransitionIndex, skill_closeness_map}
```

## Workflow 2: Learning Path Query (NEW v2.0)

**Use Case:** User asks "What's the prerequisite order to learn Full-Stack Development?"

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LG as LangGraph
    participant NEO as Neo4j + GDS
    participant LLM

    User->>API: "Prerequisite order for Full-Stack?"
    API->>LG: Execute pipeline

    Note over LG: Node 1: Query Understanding
    LG->>LG: Classify intent → learning_path
    LG->>LG: Extract entities → skill_cluster: "Full-Stack Development"

    Note over LG: Node 2: Vector Search
    LG->>NEO: Find Full-Stack Developer jobs
    NEO-->>LG: Top-10 Full-Stack job nodes

    Note over LG: Node 3: Graph Traversal (PREREQUISITE_OF)
    LG->>NEO: Get required skills for Full-Stack
    NEO-->>LG: [HTML, CSS, JavaScript, React, Node.js, SQL, ...]

    LG->>NEO: Traverse PREREQUISITE_OF relationships
    NEO-->>NEO: HTML -[:PREREQUISITE_OF]-> CSS
    NEO-->>NEO: JavaScript -[:PREREQUISITE_OF]-> React
    NEO-->>NEO: SQL -[:PREREQUISITE_OF]-> Database Design
    NEO-->>LG: Prerequisite chains (DAG)

    LG->>LG: Topological sort of prerequisite graph
    LG->>LG: Ordered learning path

    Note over LG: Node 4: Context Construction
    LG->>LG: Format path with dependencies

    Note over LG: Node 5: Response Generation
    LG->>LLM: Generate response with ordered path
    LLM-->>LG: "Start with: HTML, CSS → Then: JavaScript → Next: React, Node.js..."

    LG-->>API: Response + ordered_path
    API-->>User: JSON {response, learning_path: [Layer1: [...], Layer2: [...]]}
```

## Workflow 3: CSV Ingestion with Centrality Recalculation (v2.0 Enhanced)

**Use Case:** Admin uploads skills CSV, triggering centrality update

```mermaid
sequenceDiagram
    participant Admin
    participant API as Ingest Router
    participant EMB as Embedding Service
    participant NEO as Neo4j Repository
    participant GM as Graph Metrics Service
    participant GDS as Neo4j GDS

    Admin->>API: POST /ingest/skills {csv_file}
    API->>API: Parse CSV (17 fields)

    loop For each skill row
        API->>EMB: Generate embedding (skill description)
        EMB-->>API: 768-dim vector
        API->>NEO: MERGE skill node (upsert)
        NEO-->>API: Confirmation
    end

    API->>NEO: Create SIMILAR_TO relationships (top-5, cosine >0.7)
    NEO-->>API: Relationships created

    Note over API: Trigger centrality recalculation (background task)
    API->>GM: Recalculate centrality (async)

    GM->>GDS: Project skill graph
    GDS-->>GM: Graph projected

    GM->>GDS: gds.eigenvector.write(writeProperty: 'eigenvector_centrality')
    GDS-->>GDS: Compute centrality (iterative algorithm)
    GDS-->>GM: Centrality written to nodes

    GM->>NEO: Verify centrality values
    NEO-->>GM: Sample centrality: Python=0.92, Django=0.78
    GM-->>API: Recalculation complete (30s elapsed)

    API-->>Admin: Ingestion successful (1000 skills processed)
```

**Performance Note:** Centrality recalculation runs asynchronously in background to avoid blocking API response (NFR11: <30s for 5K-8K skills).

---
