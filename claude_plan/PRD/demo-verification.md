# Demo Verification

## 1. Neo4j Browser Queries

After implementation, these queries should work and show data:

```cypher
-- 1. Job-Skill graph with stored metrics
MATCH (j:Job)-[r:REQUIRES]->(s:Skill)
WHERE s.centrality IS NOT NULL
RETURN j, r, s LIMIT 50;

-- 2. Similar jobs (NEW relationship)
MATCH (j:Job {job_title:'UI Developer'})-[r:SIMILAR_JOB]-(j2:Job)
RETURN j, r, j2
ORDER BY r.jaccard_score DESC
LIMIT 15;

-- 3. Skill bridge path
MATCH (a:Skill {canonical_name:'react'}), (b:Skill {canonical_name:'go'})
CALL gds.shortestPath.dijkstra.stream({
  sourceNode: id(a),
  targetNode: id(b),
  relationshipWeightProperty: 'cost'
})
YIELD nodeIds, totalCost
RETURN [n IN nodeIds | gds.util.asNode(n).name] AS path, totalCost;

-- 4. Top skills by centrality (stored metrics)
MATCH (s:Skill)
WHERE s.centrality IS NOT NULL
RETURN s.name, s.centrality, s.demand_count
ORDER BY s.centrality DESC
LIMIT 20;

-- 5. Skills with demand counts
MATCH (s:Skill)
WHERE s.demand_count > 0
RETURN s.name, s.demand_count
ORDER BY s.demand_count DESC
LIMIT 20;
```

## 2. Sample Queries (Must Work Better)

| Query | Before | After |
|-------|--------|-------|
| "How do I transition from React developer to Go engineer?" | Generic career advice | Shows skill bridge: React → JavaScript → Backend → Go with closeness scores |
| "What are the most important skills for data science?" | List of skills | Centrality-ranked skills with market importance scores |
| "What jobs are similar to UI Developer?" | None or generic | List of 10 similar jobs with Jaccard scores |
| "I know Python and SQL, how close am I to Data Scientist?" | Generic match | 78% match with skill gap breakdown |

## 3. Ingestion Verification

After uploading a CSV:
1. Check `/api/ingest/status/{job_id}` returns:
   - `duplicates_skipped: N`
   - `co_occurrence_edges_created: M`
   - `similar_job_edges_created: K`
   - `enrichment_status: completed`

2. Query Neo4j:
```cypher
-- Verify new job has similarity edges
MATCH (j:Job {job_id: 'YOUR_NEW_JOB_ID'})-[r:SIMILAR_JOB]-(j2:Job)
RETURN count(r);

-- Verify skills have updated demand counts
MATCH (j:Job {job_id: 'YOUR_NEW_JOB_ID'})-[:REQUIRES]->(s:Skill)
RETURN s.name, s.demand_count;
```

---
