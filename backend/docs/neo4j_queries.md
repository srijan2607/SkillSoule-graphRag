# Neo4j Query Reference

## Vector Index Monitoring Queries

### Show All Vector Indexes

```cypher
SHOW INDEXES
YIELD name, type, state, populationPercent, entityType, labelsOrTypes, properties
WHERE type = "VECTOR"
RETURN
  name,
  state,
  populationPercent,
  entityType,
  labelsOrTypes,
  properties
ORDER BY name;
```

**Output Columns**:
- `name`: Index name (e.g., "skill_embedding_idx")
- `state`: Index state ("ONLINE", "POPULATING", "FAILED")
- `populationPercent`: Percentage of nodes indexed (0.0-100.0)
- `entityType`: "NODE"
- `labelsOrTypes`: Node label (e.g., ["Skill"])
- `properties`: Indexed properties (e.g., ["embedding"])

---

### Check Specific Vector Index

```cypher
SHOW INDEXES
YIELD name, type, state, populationPercent
WHERE name = "skill_embedding_idx" AND type = "VECTOR"
RETURN name, state, populationPercent;
```

---

### Count Nodes with Embeddings

```cypher
// Skills with embeddings
MATCH (s:Skill)
WHERE s.embedding IS NOT NULL
RETURN count(s) as skill_count;

// Jobs with embeddings
MATCH (j:Job)
WHERE j.embedding IS NOT NULL
RETURN count(j) as job_count;

// Companies with embeddings
MATCH (c:Company)
WHERE c.embedding IS NOT NULL
RETURN count(c) as company_count;

// All nodes with embeddings (combined)
MATCH (n)
WHERE n.embedding IS NOT NULL
RETURN labels(n) as node_type, count(n) as count
ORDER BY count DESC;
```

---

### Verify Embedding Dimensions

```cypher
// Check Skill embedding dimensions
MATCH (s:Skill)
WHERE s.embedding IS NOT NULL
WITH size(s.embedding) as dim
RETURN
  dim,
  count(*) as node_count
ORDER BY node_count DESC;

// Check all node types
MATCH (n)
WHERE n.embedding IS NOT NULL
WITH labels(n)[0] as node_type, size(n.embedding) as dim
RETURN
  node_type,
  dim,
  count(*) as node_count
ORDER BY node_type;
```

**Expected**: All embeddings should be 384 dimensions

---

### Index Health Summary

```cypher
SHOW INDEXES
YIELD name, type, state, populationPercent
WHERE type = "VECTOR"
WITH
  name,
  state,
  populationPercent,
  CASE
    WHEN state = "ONLINE" AND populationPercent = 100.0 THEN "healthy"
    WHEN state = "POPULATING" THEN "populating"
    ELSE "unhealthy"
  END as health_status
RETURN
  name,
  state,
  populationPercent,
  health_status
ORDER BY health_status, name;
```

---

## Vector Similarity Search Queries

### Find Similar Skills

```cypher
// By skill name
MATCH (s:Skill {name: 'Python'})
CALL db.index.vector.queryNodes('skill_embedding_idx', 10, s.embedding)
YIELD node, score
RETURN
  node.name as skill_name,
  node.description as description,
  score as similarity_score
ORDER BY score DESC;

// By skill ID
MATCH (s:Skill {id: 'python-001'})
CALL db.index.vector.queryNodes('skill_embedding_idx', 10, s.embedding)
YIELD node, score
WHERE node.id <> s.id  // Exclude the query skill itself
RETURN
  node.name as skill_name,
  node.type as skill_type,
  score as similarity_score
ORDER BY score DESC;
```

---

### Find Similar Jobs

```cypher
// By job ID
MATCH (j:Job {job_id: '12345'})
CALL db.index.vector.queryNodes('job_embedding_idx', 10, j.embedding)
YIELD node, score
WHERE node.job_id <> j.job_id
RETURN
  node.job_id as job_id,
  node.job_title as title,
  node.company_name as company,
  node.location as location,
  score as similarity_score
ORDER BY score DESC;

// By job title (case-insensitive search)
MATCH (j:Job)
WHERE toLower(j.job_title) CONTAINS toLower('Software Engineer')
WITH j
LIMIT 1
CALL db.index.vector.queryNodes('job_embedding_idx', 10, j.embedding)
YIELD node, score
WHERE node.job_id <> j.job_id
RETURN
  node.job_title as title,
  node.company_name as company,
  score as similarity_score
ORDER BY score DESC;
```

---

### Find Similar Companies

```cypher
// By company name
MATCH (c:Company {company_name: 'Google'})
CALL db.index.vector.queryNodes('company_embedding_idx', 10, c.embedding)
YIELD node, score
WHERE node.company_name <> c.company_name
RETURN
  node.company_name as company_name,
  score as similarity_score
ORDER BY score DESC;
```

---

### Cross-Type Similarity

```cypher
// Find jobs similar to a skill
MATCH (s:Skill {name: 'Python'})
CALL db.index.vector.queryNodes('job_embedding_idx', 10, s.embedding)
YIELD node, score
RETURN
  node.job_title as job_title,
  node.company_name as company,
  score as similarity_score
ORDER BY score DESC;

// Find skills similar to a job
MATCH (j:Job {job_id: '12345'})
CALL db.index.vector.queryNodes('skill_embedding_idx', 20, j.embedding)
YIELD node, score
RETURN
  node.name as skill_name,
  node.type as skill_type,
  score as similarity_score
ORDER BY score DESC;
```

---

## Performance Analysis Queries

### Index Usage Statistics

```cypher
// Show all indexes with usage stats (Neo4j 5.x+)
SHOW INDEXES
YIELD name, type, state, populationPercent, lastRead, readCount
WHERE type = "VECTOR"
RETURN
  name,
  state,
  populationPercent,
  lastRead,
  readCount
ORDER BY readCount DESC;
```

---

### Query Execution Plan

```cypher
// Check if vector index is being used
PROFILE
MATCH (s:Skill {name: 'Python'})
CALL db.index.vector.queryNodes('skill_embedding_idx', 5, s.embedding)
YIELD node, score
RETURN node.name, score
ORDER BY score DESC;
```

Look for "VectorIndexSeek" in the execution plan to confirm index usage.

---

## Maintenance Queries

### Rebuild All Vector Indexes

```cypher
// Drop all vector indexes
DROP INDEX skill_embedding_idx IF EXISTS;
DROP INDEX job_embedding_idx IF EXISTS;
DROP INDEX company_embedding_idx IF EXISTS;

// Wait 2-3 seconds, then recreate (see neo4j_vector_indexes.md)
```

---

### Find Nodes Without Embeddings

```cypher
// Skills without embeddings
MATCH (s:Skill)
WHERE s.embedding IS NULL
RETURN count(s) as skills_without_embedding;

// Jobs without embeddings
MATCH (j:Job)
WHERE j.embedding IS NULL
RETURN count(j) as jobs_without_embedding;

// Companies without embeddings
MATCH (c:Company)
WHERE c.embedding IS NULL
RETURN count(c) as companies_without_embedding;

// All nodes without embeddings
MATCH (n)
WHERE n.embedding IS NULL
RETURN labels(n) as node_type, count(n) as count
ORDER BY count DESC;
```

---

### Find Invalid Embeddings

```cypher
// Embeddings with wrong dimensions
MATCH (n)
WHERE n.embedding IS NOT NULL AND size(n.embedding) <> 384
RETURN
  labels(n) as node_type,
  id(n) as node_id,
  size(n.embedding) as actual_dimensions
LIMIT 100;

// Embeddings with non-numeric values
MATCH (s:Skill)
WHERE s.embedding IS NOT NULL
  AND any(val IN s.embedding WHERE val IS NULL OR NOT val = toFloat(val))
RETURN
  s.id as skill_id,
  s.name as skill_name,
  s.embedding as invalid_embedding
LIMIT 10;
```

---

## Database Statistics

### Node Counts by Type

```cypher
MATCH (n)
RETURN
  labels(n) as node_type,
  count(n) as total_count,
  count(n.embedding) as with_embedding,
  (toFloat(count(n.embedding)) / count(n) * 100) as embedding_coverage_percent
ORDER BY total_count DESC;
```

---

### Embedding Coverage Report

```cypher
// Comprehensive embedding coverage report
CALL {
  MATCH (s:Skill)
  RETURN
    "Skill" as type,
    count(s) as total,
    count(s.embedding) as with_embedding
}
UNION
CALL {
  MATCH (j:Job)
  RETURN
    "Job" as type,
    count(j) as total,
    count(j.embedding) as with_embedding
}
UNION
CALL {
  MATCH (c:Company)
  RETURN
    "Company" as type,
    count(c) as total,
    count(c.embedding) as with_embedding
}
RETURN
  type,
  total,
  with_embedding,
  (toFloat(with_embedding) / total * 100) as coverage_percent
ORDER BY type;
```

---

## Troubleshooting Queries

### Check Neo4j Version

```cypher
CALL dbms.components()
YIELD name, versions, edition
RETURN name, versions[0] as version, edition;
```

**Requirement**: Neo4j 5.11+ for vector indexes

---

### Check Available Memory

```cypher
CALL dbms.queryJmx("java.lang:type=Memory")
YIELD name, attributes
WITH attributes
UNWIND keys(attributes) as key
RETURN
  key,
  attributes[key] as value;
```

---

### List All Procedures

```cypher
// Find vector-related procedures
CALL dbms.procedures()
YIELD name, signature, description
WHERE name CONTAINS "vector"
RETURN name, signature, description;
```

---

## Quick Reference

### Most Common Queries

```cypher
-- Check index health
SHOW INDEXES WHERE type = "VECTOR";

-- Find similar items
MATCH (n:Skill {name: 'Python'})
CALL db.index.vector.queryNodes('skill_embedding_idx', 10, n.embedding)
YIELD node, score
RETURN node, score
ORDER BY score DESC;

-- Count nodes with embeddings
MATCH (n)
WHERE n.embedding IS NOT NULL
RETURN labels(n), count(n);

-- Verify embedding dimensions
MATCH (n:Skill)
WHERE n.embedding IS NOT NULL
RETURN size(n.embedding) as dims, count(*) as count;
```

---

**Last Updated**: 2025-10-24  
**Version**: 1.0
