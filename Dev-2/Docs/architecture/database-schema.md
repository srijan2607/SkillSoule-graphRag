# Database Schema

## Neo4j Graph Schema (v2.0 Skill-Centric Model)

```cypher
// ============================================
// NODE LABELS
// ============================================

// Primary Node: Skill (Skill-Centric Model)
CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_id IS UNIQUE;
CREATE INDEX skill_name_index IF NOT EXISTS FOR (s:Skill) ON (s.name);

// Skill properties:
// - skill_id: String (UUID)
// - name: String
// - description: String
// - category: String
// - subcategory: String (optional)
// - level: String (BEGINNER | INTERMEDIATE | ADVANCED | EXPERT)
// - embedding: List<Float> (768-dim vector)
// - eigenvector_centrality: Float (0-1) [NEW v2.0]
// - market_demand: Integer [NEW v2.0]
// - avg_salary_impact: Float [NEW v2.0]

// Derived Cluster: Job
CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE;

// Job properties:
// - job_id: String (UUID)
// - job_title: String
// - company_name: String
// - salary_min: Integer
// - salary_max: Integer
// - location: String
// - description: String
// - embedding: List<Float> (768-dim)
// - creation_index: Float (0-1) [NEW v2.0]
// - reuse_index: Float (0-1) [NEW v2.0]
// - classification: String (CUTTING_EDGE | EMERGING | ESTABLISHED) [NEW v2.0]

// Supporting Nodes
CREATE CONSTRAINT company_name_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_name IS UNIQUE;
CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.category_id IS UNIQUE;

// ============================================
// VECTOR INDEXES (for similarity search)
// ============================================

// Skill embeddings (768-dim, upgraded from 384-dim in v1.1)
CALL db.index.vector.createNodeIndex(
  'skill_embeddings',
  'Skill',
  'embedding',
  768,
  'cosine'
);

// Job embeddings (768-dim)
CALL db.index.vector.createNodeIndex(
  'job_embeddings',
  'Job',
  'embedding',
  768,
  'cosine'
);

// Company embeddings (768-dim)
CALL db.index.vector.createNodeIndex(
  'company_embeddings',
  'Company',
  'embedding',
  768,
  'cosine'
);

// ============================================
// RELATIONSHIPS (v1.1 Preserved + v2.0 NEW)
// ============================================

// v1.1 Relationships (Preserved)
// (Job)-[:REQUIRES]->(Skill) - Job skill requirements
// (Job)-[:POSTED_BY]->(Company) - Job posting company
// (Job)-[:LOCATED_IN]->(Location) - Job location
// (Skill)-[:SIMILAR_TO]->(Skill) - Semantic similarity (top-5, cosine >0.7)
// (Skill)-[:BELONGS_TO_CATEGORY]->(Category) - Skill categorization

// v2.0 NEW Relationships
// (Skill)-[:PREREQUISITE_OF]->(Skill)
//   Properties: confidence_score (0-1), source (manual_curated | inferred)
//   Example: HTML -[:PREREQUISITE_OF {confidence_score: 0.95}]-> React

// (Skill)-[:COMPLEMENTS]->(Skill)
//   Properties: co_occurrence_rate (0-1), job_count (integer)
//   Example: Python -[:COMPLEMENTS {co_occurrence_rate: 0.78, job_count: 1200}]-> PostgreSQL

// (Skill)-[:SUBSTITUTES]->(Skill)
//   Properties: substitution_score (0-1), context (string)
//   Example: Django -[:SUBSTITUTES {substitution_score: 0.82, context: "web frameworks"}]-> Flask

// (Skill)-[:TRANSITIONS_TO]->(Skill)
//   Properties: transition_likelihood (0-1), estimated_learning_time_hours (integer)
//   Example: Python -[:TRANSITIONS_TO {transition_likelihood: 0.65, estimated_learning_time_hours: 40}]-> Django

// ============================================
// GRAPH PROJECTION (for Neo4j GDS)
// ============================================

// Project skill graph for centrality calculation
CALL gds.graph.project(
  'skill-centrality-graph',
  'Skill',
  {
    SIMILAR_TO: {orientation: 'UNDIRECTED'},
    COMPLEMENTS: {orientation: 'UNDIRECTED', properties: 'co_occurrence_rate'},
    PREREQUISITE_OF: {orientation: 'DIRECTED'}
  }
);

// Compute eigenvector centrality and write to skill.eigenvector_centrality property
CALL gds.eigenvector.write(
  'skill-centrality-graph',
  {
    writeProperty: 'eigenvector_centrality',
    maxIterations: 100,
    tolerance: 0.0001
  }
);

// ============================================
// MIGRATION SCRIPT (v1.1 → v2.0)
// ============================================

// Phase 1: Add new properties to existing Skill nodes
MATCH (s:Skill)
SET s.eigenvector_centrality = COALESCE(s.eigenvector_centrality, 0.0),
    s.market_demand = COALESCE(s.market_demand, 0),
    s.avg_salary_impact = COALESCE(s.avg_salary_impact, 0.0);

// Phase 2: Add new properties to existing Job nodes
MATCH (j:Job)
SET j.creation_index = COALESCE(j.creation_index, 0.0),
    j.reuse_index = COALESCE(j.reuse_index, 0.0),
    j.classification = COALESCE(j.classification, 'ESTABLISHED');

// Phase 3: Create COMPLEMENTS relationships from job skill co-occurrence
MATCH (j:Job)-[:REQUIRES]->(s1:Skill)
MATCH (j)-[:REQUIRES]->(s2:Skill)
WHERE id(s1) < id(s2) // Avoid duplicates
WITH s1, s2, count(j) AS co_occurrence_count, count(j) * 1.0 / (SELECT count(*) FROM Job) AS co_occurrence_rate
WHERE co_occurrence_count >= 5 // Minimum 5 jobs
MERGE (s1)-[c:COMPLEMENTS]->(s2)
SET c.co_occurrence_rate = co_occurrence_rate,
    c.job_count = co_occurrence_count;

// Phase 4: Compute initial centrality (manual trigger, not in migration script)
// Run via Neo4j GDS as shown in Graph Projection section above

// ============================================
// ROLLBACK SCRIPT (if v2.0 issues)
// ============================================

// Remove new properties from Skill nodes
MATCH (s:Skill)
REMOVE s.eigenvector_centrality, s.market_demand, s.avg_salary_impact;

// Remove new properties from Job nodes
MATCH (j:Job)
REMOVE j.creation_index, j.reuse_index, j.classification;

// Remove new relationship types
MATCH ()-[r:PREREQUISITE_OF|COMPLEMENTS|SUBSTITUTES|TRANSITIONS_TO]->()
DELETE r;
```

## PostgreSQL Schema (v1.1 Preserved, No Changes in v2.0)

```sql
-- Users table (v1.1, unchanged)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Query history table (v1.1, metadata extended in v2.0)
CREATE TABLE query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    metadata JSONB NOT NULL, -- Extended in v2.0 to include metric values
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for query performance
CREATE INDEX idx_query_history_user_id ON query_history(user_id);
CREATE INDEX idx_query_history_session_id ON query_history(session_id);
CREATE INDEX idx_query_history_created_at ON query_history(created_at);

-- Example metadata structure (v2.0)
-- {
--   "intent": "skill_transfer",
--   "intent_confidence": 0.92,
--   "processing_time_ms": 1234,
--   "sources": [...],
--   "metrics": {
--     "transition_index": 0.68,
--     "skill_closeness_map": {"React": 0.72, "CSS": 0.85},
--     "centrality_values": {"Python": 0.92, "Django": 0.78}
--   }
-- }
```

---
