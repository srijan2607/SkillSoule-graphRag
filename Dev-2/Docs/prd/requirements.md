# Requirements

## Functional Requirements

**Note:** Requirements FR1-FR28, NFR1-NFR10 from v1.1 remain valid and are preserved. Below are **additional/modified requirements** for v2.0 enhancement.

### Enhanced Knowledge Graph (Extends FR9-FR12)

**FR29:** System shall restructure Neo4j graph to skill-centric model:
- **Primary nodes**: Skill (with eigenvector_centrality, market_demand, avg_salary_impact properties)
- **Derived clusters**: Jobs as combinations of required skills
- **Migration**: Preserve existing Job, Company, Location, Category, Subcategory nodes but reorient relationships

**FR30:** System shall create new relationship types:
- **PREREQUISITE_OF**: Foundational skill → Advanced skill (e.g., HTML -[PREREQUISITE_OF]-> React)
  - Properties: confidence_score (0-1), source (manual_curated | inferred)
- **COMPLEMENTS**: Co-occurring skills in jobs (e.g., Python -[COMPLEMENTS]-> PostgreSQL)
  - Properties: co_occurrence_rate (0-1), job_count (integer)
- **SUBSTITUTES**: Competing tools/frameworks (e.g., Django -[SUBSTITUTES]-> Flask)
  - Properties: substitution_score (0-1), context (string)
- **TRANSITIONS_TO**: Career path transitions (e.g., Python -[TRANSITIONS_TO]-> Django)
  - Properties: transition_likelihood (0-1), estimated_learning_time_hours (integer)

**FR31:** System shall compute and store eigenvector centrality for all skills using Neo4j GDS:
- Algorithm: `gds.eigenvector.stream()` on weighted skill graph
- Update frequency: After each CSV ingestion batch
- Storage: Skill.eigenvector_centrality property (float, 0-1 range)

**FR32:** System shall compute skill-to-skill shortest path distance using Dijkstra's algorithm:
- Graph: CO_OCCURS_WITH relationships (weighted by co-occurrence count)
- Edge distance: `d(s1, s2) = 1 / w(s1, s2)` where w = co-occurrence count
- Optionally include PREREQUISITE_OF edges in path calculation
- Return: Distance value and path (list of skill nodes)

**FR33:** System shall calculate closeness metric between skills:
- Formula: `Closeness(A, B) = 1 / (1 + Distance(A, B))`
- Range: [0, 1] where 1 = direct connection, 0 = very distant/no path
- Use case: Skill transfer analysis in career transitions

**FR34:** System shall compute user-to-job closeness:
- For each required skill in job: Find minimum distance to user's skill set
- Formula: `JobCloseness = (1/m) * Σ closeness_j` where m = number of required skills
- Optional enhancement: Weight core skills 2.0x in average

**FR35:** System shall calculate TransitionIndex for career transitions:
- Formula: `TransitionIndex = 0.50 * AvgCloseness + 0.30 * CoreSkillOverlap + 0.20 * MarketDemand`
- Range: [0, 1]
- Interpretation: >0.7 = High feasibility, 0.4-0.7 = Moderate, <0.4 = Major pivot
- **Disclaimer**: Heuristic score, not research-validated probability

**FR36:** System shall compute recombinant innovation indices for jobs:
- **Creation Index**: (Novel skill pairs) / (Total pairs in job) where novel = not seen in >5% of jobs
- **Reuse Index**: (Established skill pairs) / (Total pairs)
- Classification: CUTTING_EDGE (creation >50%), EMERGING (30-50%), ESTABLISHED (<30%)
- Storage: Job.creation_index, Job.reuse_index properties

**FR37:** System shall infer TRANSITIONS_TO relationships from static job-skill data:
- Factor 1: Skill co-occurrence in jobs (0.5 weight)
- Factor 2: Embedding cosine similarity (0.3 weight)
- Factor 3: Skill complexity delta penalty (0.2 weight)
- Threshold: Create relationship if combined score >0.3
- **Limitation Note**: Not based on observed user trajectories; refine when data available

### Enhanced Query Pipeline (Extends FR13-FR22)

**FR38:** System shall add new query intent types to Query Understanding node:
- **Skill Transfer Query**: "Which of my skills transfer to X role?"
- **Learning Path Query**: "What's the order to learn Full-Stack Development?"
- **High-Leverage Skill Query**: "Which skills have highest centrality?"
- **Transition Difficulty Query**: "How hard is transitioning from X to Y?"
- **Skill Bridge Query**: "What skills bridge UI development to UX design?"

**FR39:** System shall implement structural graph queries for new intents:
- **Skill Transfer**: Calculate closeness from user skills to target job required skills
- **Learning Path**: Find shortest path through PREREQUISITE_OF relationships
- **High-Leverage**: Rank skills by eigenvector_centrality descending
- **Transition Difficulty**: Compute TransitionIndex between skill sets
- **Skill Bridge**: Find intermediate skills on shortest path between skill clusters

**FR40:** System shall enhance Context Construction node to include:
- Graph statistics: Number of nodes traversed, relationships explored, path length
- Centrality scores for mentioned skills
- Closeness metrics between skill pairs
- TransitionIndex with component breakdown (closeness, overlap, demand)
- Research methodology citations (specific formulas used)

**FR41:** System shall update Response Generation prompts to:
- Cite specific network metrics used (centrality values, closeness scores)
- Explain reasoning based on graph structure (not just semantic similarity)
- Highlight non-obvious connections discovered through graph traversal
- Include disclaimer for heuristic scores vs validated metrics

**FR42:** System shall log extended performance metrics:
- Centrality calculation time (Neo4j GDS)
- Shortest path computation time (Dijkstra)
- TransitionIndex calculation time
- Total graph algorithm overhead
- Target: Graph algorithm overhead <2s to maintain <5s total response time (NFR1)

### Research Validation & Transparency (New)

**FR43:** System shall expose `/api/metrics/centrality` endpoint:
- Input: Optional skill_id or return top-N by centrality
- Output: JSON with skill name, centrality score, rank, market_demand
- Use case: Admin validation of centrality rankings

**FR44:** System shall expose `/api/metrics/closeness` endpoint:
- Input: skill_a, skill_b
- Output: JSON with distance, closeness score, shortest path (node list), path length
- Use case: Expert validation of closeness correlation

**FR45:** System shall log all graph algorithm decisions for audit:
- Which relationships used in path calculation (CO_OCCURS_WITH, PREREQUISITE_OF)
- Centrality algorithm parameters (iterations, convergence)
- TransitionIndex component weights (closeness 0.5, overlap 0.3, demand 0.2)
- Threshold values (similarity >0.7, transition likelihood >0.3)

**FR46:** System shall include research citations in responses:
- Reference "Ties that Bind: ICT Network" paper when using closeness/centrality
- Note which metrics are research-validated vs heuristic
- Provide GitHub/documentation links to algorithm implementations

### Enhanced Embeddings (Modifies FR6)

**FR47:** System shall upgrade embedding model from `all-MiniLM-L6-v2` (384-dim) to `all-mpnet-base-v2` (768-dim):
- Rationale: Better semantic capture for career domain terminology
- Fallback: If performance issues, revert to 384-dim or use `BAAI/bge-large-en-v1.5` (1024-dim)
- Benchmark: Validate on 1000 skill pairs with expert ratings before production

## Non-Functional Requirements

**Note:** NFR1-NFR10 from v1.1 remain valid. Below are additional NFR for v2.0.

**NFR11:** Centrality calculation shall complete in <30 seconds for 5K-8K skill nodes using Neo4j GDS

**NFR12:** Shortest path queries shall return in <500ms for typical skill-to-skill distance calculations

**NFR13:** TransitionIndex calculation shall complete in <200ms for user-to-job transition scoring

**NFR14:** Graph schema migration shall preserve 100% of existing v1.1 data (zero data loss)

**NFR15:** System shall support free-tier Neo4j limits:
- 50,000 nodes maximum (Skills: 5K-8K, Jobs: 20K-40K, Companies/Locations/Categories: <5K)
- 175,000 relationships maximum
- If exceeded, provide graceful degradation (prioritize core skills, recent jobs)

**NFR16:** Environment configuration shall add new variables:
- `NEO4J_GDS_ENABLED` - Enable Graph Data Science algorithms (true/false)
- `EMBEDDING_MODEL_VERSION` - Embedding model (`all-MiniLM-L6-v2` | `all-mpnet-base-v2`)
- `CENTRALITY_UPDATE_FREQUENCY` - How often to recalculate centrality (`on_ingestion` | `daily` | `manual`)

**NFR17:** System shall maintain backward compatibility with v1.1 API endpoints:
- All existing `/auth/*`, `/ingest/*`, `/query`, `/health` endpoints unchanged
- New endpoints additive only (`/api/metrics/*`)

**NFR18:** Documentation shall include research methodology transparency:
- Mathematical formulas for all metrics
- Algorithm implementation details
- Validation status (validated | experimental | heuristic)
- Limitations and assumptions explicitly stated

## Compatibility Requirements

**CR1: Existing API Compatibility**
- All v1.1 FastAPI endpoints (`/auth/register`, `/auth/login`, `/ingest/skills`, `/ingest/jobs`, `/query`, `/health`) must remain functional with identical request/response schemas
- New v2.0 endpoints (`/api/metrics/centrality`, `/api/metrics/closeness`) are additive only

**CR2: Database Schema Compatibility**
- PostgreSQL schema (users table, JWT sessions) remains unchanged
- Neo4j graph migration must preserve all existing nodes (Job, Skill, Company, Location, Category, Subcategory) and relationships (REQUIRES, POSTED_BY, LOCATED_IN, BELONGS_TO_CATEGORY, BELONGS_TO_SUBCATEGORY, SIMILAR_TO)
- New node properties (eigenvector_centrality, creation_index, reuse_index) are additive
- New relationship types (PREREQUISITE_OF, COMPLEMENTS, SUBSTITUTES, TRANSITIONS_TO) are additive

**CR3: UI/UX Consistency**
- Existing React chat interface remains default user experience
- New UI components (centrality visualization, skill path diagrams) are optional enhancements
- Chat responses maintain conversational tone with added metric citations

**CR4: Integration Compatibility**
- LangGraph pipeline structure (5 nodes) preserved, enhancements within existing nodes
- OpenRouter LLM integration unchanged (same model, same API)
- CSV ingestion format unchanged (Skills: 17 fields, Jobs: 30 fields)
- Embedding generation process enhanced but backward compatible (can upgrade embeddings incrementally)

---
