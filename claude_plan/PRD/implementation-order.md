# Implementation Order

> ⚠️ **CRITICAL ORDER**: This prevents the classic mistake: "build the math, but the data is dirty so math is meaningless."
>
> **Rule**: Clean data FIRST, then build features on clean data.

```
STEP 1: DATA FOUNDATION (Must complete before anything else!)
────────────────────────────────────────────────────────────
│
├── 1.1 Skill Normalization + Dedupe + Migration [BLOCKING]
│   ├── Implement SkillNormalizer (with import re, C# alias, display names)
│   ├── Run migration script (normalize → dedupe → constraint)
│   ├── Verify: No duplicate canonical_names in graph
│   └── CHECKPOINT: Query MATCH (s:Skill) RETURN s.canonical_name, count(*) - all should be 1
│
└── 1.2 Indexes (safe to do anytime)
    └── Create indexes on canonical_name, centrality, demand_count

STEP 2: VISIBLE WIN #1 - Job Similarity (Fast impact)
────────────────────────────────────────────────────────────
│
├── 2.1 SIMILAR_JOB via GDS nodeSimilarity
│   ├── Implement JobSimilarityBuilder with GDS
│   ├── Run build_all_gds() on clean data
│   └── CHECKPOINT: MATCH ()-[r:SIMILAR_JOB]->() RETURN count(r) - should be >0
│
└── 2.2 Verify in Neo4j Browser
    └── Query: MATCH (j:Job)-[r:SIMILAR_JOB]-(j2) RETURN j, r, j2 LIMIT 20

STEP 3: VISIBLE WIN #2 - Stored Metrics
────────────────────────────────────────────────────────────
│
├── 3.1 Update demand_count on Skills
│   ├── Run query to set demand_count from REQUIRES relationships
│   └── CHECKPOINT: MATCH (s:Skill) WHERE s.demand_count > 0 RETURN count(s)
│
└── 3.2 (Optional) Compute Eigenvector Centrality
    ├── If GDS available, compute and store centrality
    └── CHECKPOINT: MATCH (s:Skill) WHERE s.centrality IS NOT NULL RETURN count(s)

STEP 4: VISIBLE WIN #3 - Query Pipeline Integration
────────────────────────────────────────────────────────────
│
├── 4.1 Add network_enrichment_node to LangGraph workflow
│   ├── Add new intent patterns (skill_importance, job_similarity, etc.)
│   ├── Wire enrichment node after graph_traversal
│   └── CHECKPOINT: Query "What are the most important skills?" returns centrality data
│
├── 4.2 Update context_construction to include network facts
│   └── CHECKPOINT: LLM response mentions "Graph Insights" section
│
└── 4.3 Update QueryResponse model with network_insights field
    └── CHECKPOINT: API response includes network_insights JSON

STEP 5: VISIBLE WIN #4 - Frontend Panel
────────────────────────────────────────────────────────────
│
├── 5.1 Create NetworkInsightsPanel component
│   └── Skill paths, similar jobs, top skills, job closeness sections
│
└── 5.2 Integrate into ChatMessage component
    └── CHECKPOINT: UI shows collapsible network insights panels

STEP 6: ADVANCED FEATURES (Only after Steps 1-5 stable)
────────────────────────────────────────────────────────────
│
├── 6.1 CO_OCCURS_WITH edges
│   ├── Implement CoOccurrenceBuilder with stoplist
│   ├── Run build_all() on clean graph
│   └── Store both weight AND cost properties
│
├── 6.2 Dijkstra skill paths
│   ├── Use cost property for shortest path
│   └── Add BFS fallback for non-GDS environments
│
└── 6.3 Auto-enrichment on ingestion
    └── Wire post-ingestion enrichment hooks
```

## Implementation Checkpoints

| Step | Verification Query | Expected Result |
|------|-------------------|-----------------|
| 1.1 | `MATCH (s:Skill) WITH s.canonical_name as cn, count(*) as c WHERE c > 1 RETURN cn, c` | Empty result (no duplicates) |
| 2.1 | `MATCH ()-[r:SIMILAR_JOB]->() RETURN count(r)` | > 0 relationships |
| 3.1 | `MATCH (s:Skill) WHERE s.demand_count > 0 RETURN count(s)` | > 0 skills with demand |
| 4.1 | Query: "most important skills" | Response includes centrality data |
| 5.2 | UI test | Network panels visible |
| 6.1 | `MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r)` | > 0 edges |

## Why This Order?

1. **Step 1 is BLOCKING** - If data is dirty (duplicate skills), all downstream math is garbage
2. **Steps 2-5 are visible wins** - Each step produces user-visible improvement
3. **Step 6 is advanced** - CO_OCCURS_WITH and Dijkstra need clean, stable graph
4. **No time estimates** - Focus on completion, not calendar

---
