# Epic 1: Skill-Centric Graph Restructuring

**Epic Goal:** Transform Neo4j graph from job-centric to skill-centric model while preserving 100% of existing v1.1 data and functionality

**Integration Requirements:**
- All existing nodes (Job, Skill, Company, Location, Category, Subcategory) preserved
- All existing relationships (REQUIRES, POSTED_BY, LOCATED_IN, BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, SIMILAR_TO) preserved
- New properties additive only (eigenvector_centrality, market_demand, avg_salary_impact)
- Existing v1.1 test suite must pass after each story completion

## Story 1.1: Graph Schema Enhancement - Add Node Properties

**As a** system administrator,
**I want** to add new metric properties to Skill nodes,
**so that** we can store centrality, market demand, and salary impact data without breaking existing queries.

### Acceptance Criteria

1. Cypher script adds properties to all Skill nodes:
   - `eigenvector_centrality` (float, default 0.0)
   - `market_demand` (integer, default 0)
   - `avg_salary_impact` (float, default 0.0)
2. Script is idempotent (safe to run multiple times)
3. Existing Skill node properties unchanged (ID, NAME, LEVEL, CATEGORY, DESCRIPTION, embeddings)
4. Validation: Query 100 random skills, verify new properties exist with default values
5. Rollback script tested: `REMOVE` properties and verify clean removal

### Integration Verification

**IV1:** Run v1.1 query test suite - All skill-based queries return identical results (property additions don't affect query logic)

**IV2:** CSV ingestion test - Upload 100 skill records, verify new properties initialized correctly and existing properties unchanged

**IV3:** Vector search test - Run 10 sample semantic queries, verify similarity search performance unchanged (<500ms)

---

## Story 1.2: Relationship Type Addition - PREREQUISITE_OF

**As a** career advisor user,
**I want** the system to understand prerequisite relationships between skills,
**so that** learning paths can be ordered correctly (e.g., HTML before React).

### Acceptance Criteria

1. Cypher relationship type `PREREQUISITE_OF` created with properties:
   - `confidence_score` (float, 0-1 range)
   - `source` (string: "manual_curated" | "inferred")
2. Initial curated prerequisite relationships loaded from CSV:
   - Example: HTML -[PREREQUISITE_OF {confidence_score: 1.0, source: "manual_curated"}]-> React
   - Minimum 50 curated relationships for common skill chains
3. Query to find all prerequisites for a skill: `MATCH (s1)-[:PREREQUISITE_OF]->(s2 {NAME: 'React'}) RETURN s1`
4. No impact on existing REQUIRES, SIMILAR_TO relationships

### Integration Verification

**IV1:** Existing job-skill queries unchanged - REQUIRES relationships still return correct results

**IV2:** Graph visualization test - Open Neo4j Browser, verify PREREQUISITE_OF relationships visible alongside existing relationships

**IV3:** Relationship count validation - Total relationship count increases by ~50-100 (prerequisite additions only)

---

## Story 1.3: Relationship Type Addition - COMPLEMENTS

**As a** job seeker,
**I want** to discover complementary skills that often appear together,
**so that** I can learn skill combinations valued by employers.

### Acceptance Criteria

1. Cypher relationship type `COMPLEMENTS` created with properties:
   - `co_occurrence_rate` (float, 0-1 range)
   - `job_count` (integer, number of jobs requiring both skills)
2. Algorithm computes COMPLEMENTS relationships:
   - For each skill pair in same job: Increment co-occurrence counter
   - Compute co_occurrence_rate = (jobs_with_both) / (jobs_with_either)
   - Create relationship if co_occurrence_rate >0.6 threshold
3. Query to find complementary skills: `MATCH (s1 {NAME: 'Python'})-[r:COMPLEMENTS]->(s2) RETURN s2, r.co_occurrence_rate ORDER BY r.co_occurrence_rate DESC LIMIT 10`
4. Estimated ~5K-10K COMPLEMENTS relationships created (within Neo4j free tier limit)

### Integration Verification

**IV1:** Job requirement queries unchanged - REQUIRES relationships unaffected by COMPLEMENTS additions

**IV2:** Performance test - COMPLEMENTS computation completes in <5 minutes for 40K jobs, 8K skills

**IV3:** Relationship limit check - Total relationships <175K (free tier limit), graceful degradation if exceeded (keep top co-occurrence pairs only)

---

## Story 1.4: Relationship Type Addition - SUBSTITUTES

**As a** career transition planner,
**I want** to understand which skills are substitutable (e.g., Django vs Flask),
**so that** I can make strategic learning decisions based on job market flexibility.

### Acceptance Criteria

1. Cypher relationship type `SUBSTITUTES` created with properties:
   - `substitution_score` (float, 0-1 range)
   - `context` (string, e.g., "web frameworks", "databases")
2. Initial SUBSTITUTES relationships loaded from manual curation:
   - Example: Django -[SUBSTITUTES {substitution_score: 0.8, context: "Python web frameworks"}]-> Flask
   - Minimum 30 curated substitution pairs for common tool categories
3. Bidirectional relationships: If Django substitutes Flask, create Flask substitutes Django
4. Query to find substitutes: `MATCH (s1 {NAME: 'Django'})-[r:SUBSTITUTES]-(s2) RETURN s2, r.context`

### Integration Verification

**IV1:** Existing skill similarity queries (SIMILAR_TO) unchanged and distinct from SUBSTITUTES

**IV2:** Relationship validation - SUBSTITUTES count ~60-80 (30 pairs * 2 directions)

**IV3:** Context field populated - No null/empty context values, all have meaningful categories

---

## Story 1.5: Relationship Type Addition - TRANSITIONS_TO (Experimental)

**As a** career intelligence system,
**I want** to approximate career transition paths from job-skill data,
**so that** users receive transition likelihood estimates even without observed user trajectory data.

### Acceptance Criteria

1. Cypher relationship type `TRANSITIONS_TO` created with properties:
   - `transition_likelihood` (float, 0-1 range, HEURISTIC SCORE)
   - `estimated_learning_time_hours` (integer)
2. Algorithm computes TRANSITIONS_TO relationships:
   - Factor 1 (50% weight): Skill co-occurrence in jobs
   - Factor 2 (30% weight): Embedding cosine similarity
   - Factor 3 (20% weight, penalty): Skill complexity delta
   - Create relationship if combined score >0.3 threshold
3. Disclaimer property: `is_validated = false` (experimental, not research-validated)
4. Query to find likely transitions: `MATCH (s1 {NAME: 'Python'})-[r:TRANSITIONS_TO]->(s2) WHERE r.transition_likelihood > 0.5 RETURN s2 ORDER BY r.transition_likelihood DESC`
5. Estimated ~2K-5K TRANSITIONS_TO relationships created

### Integration Verification

**IV1:** Existing SIMILAR_TO relationships unchanged (different semantic meaning)

**IV2:** Experimental flag validation - All TRANSITIONS_TO relationships have `is_validated = false` property

**IV3:** Relationship limit check - Total relationships still <175K after additions

---

## Story 1.6: Graph Migration Validation & Rollback Testing

**As a** system administrator,
**I want** comprehensive validation of the graph migration,
**so that** I can confidently deploy v2.0 without data loss or corruption.

### Acceptance Criteria

1. Automated validation script checks:
   - Node count unchanged from v1.1 (Job, Skill, Company, Location, Category, Subcategory counts match pre-migration snapshot)
   - All existing relationships preserved (REQUIRES, POSTED_BY, LOCATED_IN counts match)
   - New properties added to all Skill nodes (100% coverage)
   - New relationship types created (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO exist)
2. Rollback script tested on staging database:
   - Removes new properties: `MATCH (s:Skill) REMOVE s.eigenvector_centrality, s.market_demand, s.avg_salary_impact`
   - Removes new relationships: `MATCH ()-[r:PREREQUISITE_OF|COMPLEMENTS|SUBSTITUTES|TRANSITIONS_TO]->() DELETE r`
   - Validation: Post-rollback graph identical to v1.1 snapshot
3. Performance regression test:
   - Run v1.1 query benchmark suite (10 sample queries)
   - Query response time within ±10% of v1.1 baseline
4. Export full graph snapshot (neo4j-admin dump) for disaster recovery

### Integration Verification

**IV1:** Zero data loss - Node/relationship counts before vs after migration match exactly (existing data)

**IV2:** v1.1 feature parity - All v1.1 acceptance criteria still pass (authentication, CSV ingestion, chat queries)

**IV3:** Rollback success - Rollback script executes without errors, graph restored to v1.1 state

---
