# What Changes Where

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BEFORE (Current State)                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Query Flow:                                                             │
│   QueryUnderstanding → VectorSearch → GraphTraversal → Context → LLM    │
│                                         │                               │
│                              Uses REQUIRES, SIMILAR_TO only             │
│                              Network services NOT called                │
│                                                                         │
│ Ingestion Flow:                                                         │
│   Upload CSV → Validate → Create Nodes → Done                           │
│                              │                                          │
│                    No deduping, no normalization                        │
│                    No auto co-occurrence build                          │
│                    No stored metrics                                    │
│                                                                         │
│ Neo4j Graph:                                                            │
│   (:Job)-[:REQUIRES]->(:Skill)                                          │
│   (:Skill)-[:SIMILAR_TO]->(:Skill)  [semantic only]                     │
│   No JOB_SIMILAR, no stored centrality/demand                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         AFTER (Target State)                            │
├─────────────────────────────────────────────────────────────────────────┤
│ Query Flow:                                                             │
│   QueryUnderstanding → VectorSearch → GraphTraversal → NetworkEnrich    │
│         │                                    │              │           │
│   New intents:                      Hybrid retrieval    Calls network   │
│   CAREER_TRANSITION                 with scoring        services for:   │
│   SKILL_BRIDGE                                          - Skill paths   │
│   SKILL_IMPORTANCE                                      - Job closeness │
│   JOB_SIMILARITY                                        - Centrality    │
│                                                              │          │
│                                              Context → LLM with facts   │
│                                                                         │
│ Ingestion Flow:                                                         │
│   Upload CSV → Validate → Normalize → Dedupe → Create → AutoEnrich      │
│                   │           │          │                    │         │
│              Schema check  Skill name  Hash-based       Build edges:    │
│              + warnings    canonical   dedup            CO_OCCURS_WITH  │
│                                                         JOB_SIMILAR     │
│                                                         Store metrics   │
│                                                                         │
│ Neo4j Graph:                                                            │
│   (:Job {skill_count, updated_at})-[:REQUIRES]->(:Skill)                │
│   (:Skill {canonical_name, centrality, demand_count})                   │
│   (:Skill)-[:CO_OCCURS_WITH {weight, cost}]->(:Skill)                   │
│   (:Job)-[:SIMILAR_JOB {jaccard_score}]->(:Job)  [NEW]                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---
