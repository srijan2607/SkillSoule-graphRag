# Project Brief: Career Intelligence AI System with Skill-Centric Graph Architecture

**Document Version:** 2.1 (Revised)
**Date:** November 17, 2025
**Status:** Research Brief - Technical Implementation Focus
**Author:** Mary (Business Analyst) - Post-QC Review

---

## Executive Summary

The **Career Intelligence AI System** is a GraphRAG platform that provides career guidance through a **skill-centric knowledge graph**, inspired by network analysis methodologies from ICT innovation research.

**Core Innovation:** We adapt the "closeness to ICT industries" network structure from academic research to career planning. In the original study, industries closer to ICT in citation networks exhibited 10.2% higher innovation efficiency and 48.39% more recombinant reuse (p < 0.01). **Our working hypothesis** is that an analogous effect exists for careers: users with skill profiles structurally closer to high-demand core skills should experience better job matching and more career transition options.

**Primary Problem:** Current career platforms structure data around jobs (with skills as attributes), making it impossible to answer structural questions like: "Which skills bridge my current role to my target role?" or "What's the learning path from Python to Full-Stack Development?"

**Target Market:** Knowledge workers (25-45, tech/professional services) seeking career transitions. Secondary: HR/L&D professionals for workforce planning.

**Key Value Proposition:** Network-based career intelligence that uses graph centrality, closeness metrics, and skill relationship analysis—not just keyword matching or semantic similarity.

---

## Problem Statement

### Current State & Pain Points

**Problem 1: Job-Centric Data Model Fails Structural Queries**

```
Current Architecture:
User Query → Match Jobs → Extract Required Skills (as flat attributes)

Limitation: Cannot answer "Which of my current skills transfer to UX Design?"
```

**Real User Scenario:**

```
User: "I'm a UI developer. How do I become a UX designer?"

Current Platform Response:
- Lists UX Designer jobs
- Shows required skills: Figma, UX Research, User Psychology

Missing (Critical Gaps):
✗ Which of my current skills (React, CSS, JavaScript) actually transfer?
✗ What's the prerequisite order (should I learn Design Systems before Figma)?
✗ Which skills are "high-leverage" (impact many roles vs niche)?
✗ Realistic timeline based on skill distance?
```

**Problem 2: No Structural Relationship Understanding**

Existing solutions use:
- **Keyword matching** (LinkedIn, Indeed) - miss semantic relationships
- **Embedding similarity** (Coursera, chatbots) - capture meaning but ignore graph structure

**Missing:**
- Prerequisite relationships (HTML before React)
- Complementary skills (Python + PostgreSQL in backend)
- Transition frequencies (observed career paths)
- Substitution patterns (Django vs Flask)

**Problem 3: Lack of Quantification**

Career guidance is qualitative:
- "This transition is challenging" → **How challenging?** 6 months or 2 years?
- "Learn these skills" → **In what order?** What's the ROI per skill?
- "You're qualified" → **Based on what metric?** 40% skill overlap or 90%?

### Why Existing Solutions Fall Short

- **LinkedIn/Indeed:** Keyword-based job search without skill relationship graphs
- **Coursera/Udemy:** Course recommendations without job market integration
- **O*NET/ESCO:** Static skill taxonomies, no dynamic network analysis

**Our Differentiation:** Neo4j graph (skill relationships) + vector similarity (semantic search) + research-inspired network metrics (centrality, closeness)

---

## Proposed Solution

### Core Concept: Skill-Centric Graph Architecture

**Mental Model Shift:**

```
OLD: Jobs (primary) → Skills (attributes)
NEW: Skills (primary nodes) → Jobs (clusters that require skill combinations)

Analogy from Research:
ICT industries became central infrastructure that other industries depend on.
In our system, SKILLS become the infrastructure that careers are built upon.
```

**Graph Structure:**

```
Node: Skill "Python"
Properties:
  - embedding: [768 dimensions]
  - eigenvector_centrality: 0.92 (graph-derived importance)
  - market_demand: 8,542 jobs requiring this skill
  - avg_salary_impact: +₹3.2L (observed from data)

Relationships:
  - COMPLEMENTS → PostgreSQL (co-occur in 78% of backend jobs)
  - TRANSITIONS_TO → Django (estimated: 65% of Python devs learn Django)
  - PREREQUISITE_OF ← None (foundational skill)
  - SUBSTITUTES ↔ JavaScript (for web development context)

Connected Jobs:
  - Backend Developer (1,234 openings)
  - Data Scientist (890 openings)
  - ML Engineer (567 openings)
```

---

## Research-to-Model Mapping

**What We Borrow Directly from "Ties that Bind: ICT Network" Research:**

1. **Eigenvector Centrality** (Page 15)
   - Original: Identifies important industries based on connections to other important industries
   - Our Use: Identify high-leverage skills based on connections to other important skills
   - Implementation: Neo4j GDS eigenvector centrality on weighted skill graph

2. **Shortest-Path Closeness** (Page 15-16)
   - Original: `Distance(A→B) = Σ(1/EdgeWeight_i)` along shortest path between industries
   - Our Use: Calculate skill-to-skill distance for career transition planning
   - Implementation: Dijkstra's algorithm on skill CO_OCCURS_WITH graph

3. **Recombinant Innovation Indices** (Online Appendix Table S1)
   - Original: Classify patents by novelty of technology combinations
   - Our Use: Classify jobs by novelty of skill combinations (emerging vs established roles)
   - Implementation: Creation Index = (Novel Skill Pairs) / (Total Pairs in job)

**What Is Our Extension / Modeling Assumption:**

1. **Applying Network Metrics to Career Domain**
   - Research: ICT industries in patent citations
   - Our Assumption: Core skills in job-skill network exhibit analogous structural importance
   - **To be validated empirically** via user feedback and expert evaluation

2. **Mapping Closeness to Transition Difficulty**
   - Research: Industry closeness predicts innovation outcomes
   - Our Hypothesis: Skill closeness predicts career transition feasibility
   - **Requires longitudinal user data to validate**

3. **Approximating TRANSITIONS_TO from Static Data**
   - Ideal: Observe actual user career trajectories (UI Developer → UX Designer)
   - MVP Reality: Infer from skill overlap between job titles + semantic similarity
   - **Limitation:** Not based on observed transitions; will refine when user history available

4. **Salary Premium for High-Creation Jobs**
   - Research: No direct evidence linking recombinant creation to salaries
   - Our Hypothesis: Jobs requiring novel skill combinations pay premium
   - **To be tested** with labeled salary data

---

## Mathematical Definitions (Career Domain)

### 1. Skill-to-Skill Closeness

**Graph Setup:**
- Nodes: Skills (S)
- Edges: CO_OCCURS_WITH relationships (from job postings)
- Edge Weight: `w(s1, s2)` = count of jobs requiring both skills
- Edge Distance: `d(s1, s2) = 1 / w(s1, s2)`

**Distance Metric Rationale:**

We initially define edge distance as `1/weight`, where `weight = co-occurrence count`, as a simple inverse-frequency proxy. This makes frequently co-occurring skills "closer" in the graph, which aligns with our hypothesis that skills appearing together in many jobs are more transferable.

**Normalization Consideration:** If we observe distortion (e.g., a few hyper-common skills like "Communication" or "Excel" flattening distances), we will switch to a normalized or `-log(probability)` distance formulation. The core idea—shorter paths through densely co-occurring skills—is preserved under all these variants.

**Shortest Path Distance:**

```
D(skill_A, skill_B) = Σ d(edge_i) for all edges in shortest path from A to B

If no path exists: D(A, B) = ∞
```

**Closeness:**

```
Closeness(skill_A, skill_B) = 1 / (1 + D(A, B))

Range: [0, 1]
- Closeness = 1: Direct connection (same jobs)
- Closeness → 0: Very distant or no path
```

**Which Relationships Feed Into Distance Calculation:**

For path-based closeness in MVP, we use:
- **CO_OCCURS_WITH edges** (primary): Weighted by co-occurrence count, used for all shortest-path calculations
- **PREREQUISITE_OF edges** (optional): A small curated set of prerequisite relationships (e.g., HTML → React)

**Not used in pathfinding** (used for qualitative explanation and UI only):
- **COMPLEMENTS**: Co-occurring skills shown as "often learned together"
- **SUBSTITUTES**: Competing tools/frameworks (e.g., Django vs Flask)
- **TRANSITIONS_TO**: Experimental metadata, not incorporated into core distance algorithm until validated

This crystallizes scope and avoids confusion during implementation: only CO_OCCURS_WITH (and optionally PREREQUISITE_OF) edges participate in Dijkstra's shortest path algorithm.

### 2. User-to-Job Closeness

**User Skill Set:** `U = {skill_1, skill_2, ..., skill_n}`
**Job Required Skills:** `J = {req_1, req_2, ..., req_m}`

**For each required skill `req_j` in J:**

```
min_distance_to_user = min(D(req_j, u_i) for all u_i in U)
closeness_j = 1 / (1 + min_distance_to_user)
```

**Overall Job Closeness:**

```
JobCloseness(User, Job) = (1/m) * Σ closeness_j for all req_j in J

Where m = number of required skills in job
```

**Core Skills Weighting (Optional Enhancement):**

```
CoreJobCloseness = weighted average where core skills have weight = 2.0
```

### 3. Transition Index (Heuristic Score)

**NOT a research-validated probability**, but a heuristic inspired by ICT coefficients:

```
TransitionIndex(User, TargetCareer) =
    0.50 * AvgCloseness(user_skills, target_skills) +
    0.30 * CoreSkillOverlap(user, target) +
    0.20 * MarketDemand(target_skills)

Range: [0, 1]
Interpretation:
  > 0.7: High feasibility (strong skill transfer)
  0.4-0.7: Moderate feasibility (some reskilling needed)
  < 0.4: Major pivot (substantial learning required)
```

**Component Definitions:**

**CoreSkillOverlap:**
```
CoreSkillOverlap(User, Target) =
    (# of core skills in target career that user already has) /
    (# of core skills required for that career)

Range: [0, 1]
- 1.0 = User has all core skills
- 0.0 = User has none of the core skills
```

**MarketDemand:**
```
MarketDemand(target_skills) =
    normalized log(job_count_for_target_occupation)
    scaled to [0, 1] across all occupations in the dataset

Range: [0, 1]
- 1.0 = Highest job demand in dataset
- 0.0 = Lowest job demand
```

**Validation Plan:** Collect expert ratings on 50 known transitions, measure correlation between TransitionIndex and expert scores.

---

## Evaluation & Validation Plan

**How We Know If This Works:**

### 1. Baseline Comparison (A/B Test)

**Setup:**
- Baseline: Job-centric search (keyword matching + semantic similarity)
- Treatment: Skill-centric search (this system)

**Metrics:**
- Query relevance (user rating 1-5 scale)
- Time to useful answer (self-reported)
- Click-through rate on recommendations

**Target:** Skill-centric outperforms baseline by >15% on relevance ratings

### 2. Expert Validation (Ground Truth)

**Task:** 10 career transition scenarios (e.g., "UI Developer → UX Designer")

**Evaluators:** 5 career counselors + 5 hiring managers

**Questions:**
1. Does the system identify the correct transferable skills? (Binary: Yes/No)
2. Is the recommended learning path logical? (1-5 scale)
3. Is the difficulty estimate realistic? (1-5 scale)

**Target:** >80% agreement on transferable skills, avg rating >4.0 on path quality

### 3. Closeness Correlation Check

**Test:** Compare skill-to-skill closeness (our metric) vs human judgment

**Method:**
- Select 100 skill pairs
- Ask domain experts: "How related are these skills for career transitions?" (1-10 scale)
- Compute correlation between expert ratings and our closeness scores

**Target:** Pearson correlation >0.7 (strong positive relationship)

### 4. Skill Gap Accuracy

**Method:**
- Users self-report current skills + target role
- System predicts skill gap + learning time
- After 3 months, users report actual gaps encountered

**Target:** >70% of users report "accurate" or "very accurate" gap predictions

### 5. Recombinant Index → Salary Validation

**Hypothesis:** High-creation jobs (novel skill combinations) correlate with higher salaries

**Test:**
- Compute creation index for all jobs with salary data
- Measure correlation between creation index and salary percentile

**Expected:** Positive correlation (ρ > 0.3), but **to be empirically validated**

---

## MVP Scope

### Core Features (Must Have)

**1. Natural Language Query Interface**
- Chat-based interaction (React + WebSocket)
- LangGraph orchestration (5-node RAG pipeline)
- Example: "What skills bridge UI development to UX design?"

**2. Skill-Centric Knowledge Graph**
- **Nodes:** 5,000-8,000 skills (initial dataset)
- **Relationships:**
  - CO_OCCURS_WITH (from job postings, weighted) - **primary for MVP pathfinding**
  - PREREQUISITE_OF (manual curation for foundational skills) - **used in path calculations**
  - COMPLEMENTS (co-occurrence >60% threshold) - **used for explanation/UI only**
  - TRANSITIONS_TO (experimental; approximated from skill overlap - **used for explanation only in MVP, not core path computation**)
- **Embeddings:** 768-dim (sentence-transformers/all-mpnet-base-v2)

**3. Hybrid Search (Vector + Graph)**
- Vector: Semantic similarity for initial query understanding
- Graph: Cypher traversal for skill relationship exploration
- Combined: Context construction from both sources

**4. Eigenvector Centrality-Based Skill Ranking**
- Identify high-leverage skills (high centrality despite moderate frequency)
- Example: "System Design" (centrality: 0.85, frequency: 8K jobs) > "Legacy Framework" (centrality: 0.12, frequency: 15K jobs)

**5. Closeness-Based Transition Difficulty**
- Calculate user-to-job closeness using shortest path metric
- Output: TransitionIndex score + skill overlap % + estimated learning time
- **Disclaimer:** Index is heuristic; validate with user feedback

**6. Recombinant Job Classification (Optional Beta - Backend-Only)**
- Compute creation/reuse indices for jobs as backend fields
- Classify as: CUTTING_EDGE (>50% novel), EMERGING (30-50%), ESTABLISHED (<30%)
- **Implementation Note:** We will compute `creation_index` and `reuse_index` as backend metadata; UI exposure can wait until we see that it adds useful signal beyond core closeness and overlap
- **Hypothesis:** High-creation jobs pay premium (to be tested empirically)

**7. Source Citations & Transparency**
- Show graph statistics: "35 nodes, 58 relationships traversed"
- List skill paths explored
- Cite research paper methodology

### Out of Scope for MVP

- **User skill profiles** (PostgreSQL storage) → Phase 2
- **Resume parsing** (LLM-based extraction) → Phase 2
- **Learning resource recommendations** (course integrations) → Phase 2
- **Real-time skill trend tracking** → Phase 3
- **Monte Carlo career simulation** → Phase 3 (research project)
- **ERGM network validation** → Phase 3 (academic validation, not production)
- **Multi-language support** → Post-MVP
- **Mobile apps** → Post-MVP (web-responsive only)

### MVP Success Criteria

**Functional:**
- Query response time <3s (p95)
- 100% of 5 core intents return structured responses
- No critical bugs during 2-week beta

**Accuracy:**
- Expert validation >80% agreement on skill transfer identification
- User relevance rating >4.0/5 average
- Closeness correlation with expert judgment >0.7

**Adoption:**
- 50 beta users complete 3+ queries each
- 30%+ report time saved vs manual research

---

## Post-MVP Vision (Concise)

### Phase 2 (3-6 Months)
- User skill profiles with resume parsing
- Personalized learning resource recommendations
- Skill verification (quizzes, peer endorsements)

### Phase 3 (1-2 Years)
- Longitudinal skill trend analysis (quarterly centrality evolution)
- Career path simulation (Monte Carlo with uncertainty modeling)
- ERGM network validation (academic publication)

### Expansion Opportunities
- **B2B:** Workforce planning for enterprises, university career services
- **Geographic:** India (₹ salaries), Europe (GDPR), APAC
- **Verticals:** Healthcare (certifications), Finance (compliance), Manufacturing (operational tech)

---

## Technical Architecture (Summary)

**Full technical stack details:** See `/docs/architecture/tech-stack.md` and `/docs/architecture/components.md`

### Core Technologies

- **Frontend:** React + TypeScript, TailwindCSS
- **Backend:** FastAPI (Python), Pydantic state management
- **Graph Database:** Neo4j with vector indexes (HNSW)
- **Relational Database:** PostgreSQL
- **LLM:** OpenRouter API (Llama 3.3 8B)
- **Embeddings:** HuggingFace all-mpnet-base-v2 (768-dim)
- **Orchestration:** LangGraph for RAG workflow

### Key Architectural Decisions

- **Monolithic API** for MVP (no microservices complexity)
- **Stateless design** with JWT authentication
- **Direct database connections** (no caching layer initially)
- **Synchronous processing** (async can be added later)

---

## Constraints & Assumptions

### Constraints

**Budget:** $0/month infrastructure (free tiers: Neo4j Aura 50K nodes, Supabase 500MB, Vercel hosting)

**Timeline:** 2-3 weeks MVP development (single developer)

**Resources:** 1 full-stack developer, no GPU (CPU inference), no monitoring tools (basic logging only)

**Technical:**
- No concurrent CSV uploads (synchronous processing)
- No caching layer (direct DB queries)
- Free tier Neo4j limits (50K nodes, 175K relationships)

### Key Assumptions

1. **Data Quality:** Job postings with skill mentions are accessible (web scraping or CSV upload)
2. **Embedding Quality:** all-mpnet-base-v2 captures career domain semantics sufficiently
3. **Approximated Transitions:** TRANSITIONS_TO relationships inferred from skill overlap (not observed user trajectories)
   - **Disclosure:** "In MVP, career paths will primarily be computed using shortest paths in the CO_OCCURS_WITH skill graph. TRANSITIONS_TO edges are stored as experimental metadata and will be incorporated into the algorithm only after validation. Transition frequencies are estimated from job-skill overlap patterns, not longitudinal user data. Will refine when user histories available."
4. **LLM Performance:** llama-3.3-8b-instruct free tier provides adequate response quality
5. **User Trust:** Knowledge workers accept AI guidance if backed by research methodology and transparent citations

---

## Data Reality Check

### What We Have

- **Job postings:** 20K-40K (from Kaggle, web scraping, or manual CSV)
- **Skills:** 5K-8K (extracted from job descriptions via NLP)
- **Embeddings:** 768-dim vectors (all-mpnet-base-v2, local generation)

### What We Don't Have (Yet)

**1. Observed Career Transitions**

We do **not** have:
- User resume histories showing actual career paths
- Longitudinal data of "Person X went from UI Dev → UX Designer"

**Implication:** TRANSITIONS_TO relationships are **approximated** via:

```python
def approximate_transition_likelihood(skill_a, skill_b):
    """
    Estimate transition likelihood from static job data (not observed user paths)
    """
    # Factor 1: Skill co-occurrence in jobs
    co_occur_score = count_jobs_with_both(skill_a, skill_b) / count_jobs_with(skill_a)

    # Factor 2: Embedding similarity (semantic relatedness)
    semantic_sim = cosine_similarity(embedding_a, embedding_b)

    # Factor 3: Skill complexity delta (approximated from categories)
    complexity_gap = abs(complexity(skill_a) - complexity(skill_b))

    # Heuristic combination (not validated)
    transition_likelihood = 0.5 * co_occur_score + 0.3 * semantic_sim - 0.2 * complexity_gap

    return transition_likelihood
```

**Validation Plan:** When user trajectory data becomes available (Phase 2 profiles), compare approximated vs actual transitions and refine formula.

**2. Salary-to-Skill Correlation**

We claim: "High-creation jobs (novel skill combos) likely pay premium"

**Reality:** Hypothesis to be tested, not proven fact.

**Test:** When salary data is labeled:
```python
# Compute creation index for all jobs with salary
creation_indices = [compute_creation_index(job) for job in jobs_with_salary]
salaries = [job.salary for job in jobs_with_salary]

# Measure correlation
correlation = pearsonr(creation_indices, salaries)

# Expected: ρ > 0.3 (moderate positive), but currently unvalidated
```

---

## Risks & Mitigation

### High-Priority Risks

**1. Approximated Transitions May Be Inaccurate**
- **Risk:** TRANSITIONS_TO based on skill overlap, not observed career paths
- **Impact:** Bad career path recommendations
- **Mitigation:**
  - Validate top-100 transitions manually with career counselors
  - Add user feedback: "Was this path accurate?" (thumbs up/down)
  - Refine formula when user trajectory data available (Phase 2)
- **Severity:** HIGH

**2. Embedding Model Insufficient for Domain**
- **Risk:** all-mpnet-base-v2 may not capture career-specific terminology (Kubernetes, GraphQL)
- **Impact:** Poor semantic similarity results
- **Mitigation:**
  - Benchmark on 1000 skill pairs with expert ratings
  - Fallback to BAAI/bge-large-en-v1.5 (1024-dim) if quality insufficient
  - Consider fine-tuning on job descriptions (Phase 2)
- **Severity:** MEDIUM-HIGH

**3. Limited Data Coverage**
- **Risk:** Only 5K skills, 20K jobs (vs real job market: millions)
- **Impact:** Poor coverage for niche roles/skills
- **Mitigation:**
  - Start with tech roles (best data availability)
  - Supplement with O*NET/ESCO taxonomies
  - Add data sources iteratively (LinkedIn API, Indeed scraping)
- **Severity:** MEDIUM

**4. User Adoption / Trust**
- **Risk:** Users don't trust AI career guidance without personal validation
- **Impact:** Low engagement, high churn
- **Mitigation:**
  - Full transparency: show graph statistics, cite research paper
  - Expert testimonials (career counselors validate system)
  - User case studies: "How Priya transitioned from UI to UX in 8 months"
- **Severity:** MEDIUM

### Open Questions

**Technical:**
- Optimal threshold for TRANSITIONS_TO? (0.1, 0.2, 0.3 estimated likelihood?)
- How to handle skill name variations? (Python vs Python3, JS vs JavaScript)
- Should we implement ERGM validation for academic rigor? (R integration complexity)

**Product:**
- Minimum skill coverage for value? (1K, 5K, 10K skills?)
- Conversation history: stateful sessions or independent queries?
- Pricing model post-MVP? (Freemium, subscription, B2B only?)

**Business:**
- GTM strategy: Product Hunt, LinkedIn ads, content marketing?
- Partnerships with job boards (Indeed, LinkedIn) for fresh data?
- B2C or B2B focus? (Individual users vs enterprise workforce planning)

---

## Appendices

### A. Research Summary

**Primary Source:** "Ties that Bind: A Network Approach to Assessing Knowledge Transfers from the ICT Industry" (MainSub_Nov28.pdf)

**Key Findings (From Original ICT Study):**

1. **Closeness Metric** (Page 15-16)
   - Industries closer to ICT in patent citation network
   - Direct edge: Closeness = EdgeWeight
   - Indirect path: Closeness = 1 / (Σ 1/EdgeWeight_i along shortest path)

2. **Impact on Innovation** (Abstract, Table 3)
   - 1 σ increase in ICT-Closeness → **10.2% innovation efficiency boost** (p < 0.01)
   - 1 σ increase → **48.39% recombinant reuse increase** (p < 0.01)
   - 1 σ increase → **9.09% recombinant creation increase** (p < 0.01)

3. **Eigenvector Centrality** (Page 15)
   - ICT industries have high centrality (connected to other important industries)
   - Predicts influence in innovation network

4. **Recombinant Innovation** (Online Appendix Table S1)
   - Creation Index: Novel technology combinations
   - Reuse Index: Established combinations

**Statistical Validity:**
- Sample: 1.31M patents, 306 industries, 1976-2010
- Significance: p < 0.01 for all key coefficients
- Methods: Shortest path algorithms, eigenvector centrality, ERGM simulation

**Our Application:**
- Structure borrowed: Graph centrality, closeness formulas, recombinant indices
- Domain shifted: Industries → Skills, Patents → Jobs
- **Validation pending:** Need to test if career domain exhibits analogous patterns

### B. Stakeholder Feedback

**From Team Meeting Transcript:**

1. "Skills should be primary node, jobs orbit around skills" → ✅ Implemented skill-centric schema
2. "Need closeness formulation between skills and roles" → ✅ Applied shortest-path closeness
3. "Better embedder model (384-dim too small)" → ✅ Upgraded to 768-dim all-mpnet-base-v2
4. "Employee database for personalized profiles" → 📅 Scoped for Phase 2
5. "Need bridges between skills for career transitions" → ✅ TRANSITIONS_TO relationships (approximated)

### C. References

**Research:**
- "Ties that Bind: Network Closeness in ICT Industry" (MainSub_Nov28.pdf + Appendices)

**Architecture Docs:**
- `/docs/architecture/high-level-architecture.md`
- `/docs/architecture/tech-stack.md` (detailed versions/dependencies)
- `/docs/architecture/components.md`

**External Resources:**
- Neo4j GDS: https://neo4j.com/docs/graph-data-science/
- LangGraph: https://langchain-ai.github.io/langgraph/
- Sentence Transformers: https://www.sbert.net/

---

## Next Steps (Development Roadmap)

### 3-Phase Implementation Approach

**Phase 1: Graph Foundation (Week 1)**
- Data acquisition and schema finalization
- Neo4j graph construction with CO_OCCURS_WITH and PREREQUISITE_OF relationships
- Embedding generation (768-dim all-mpnet-base-v2)
- Vector index creation and validation
- **Deliverable:** Populated knowledge graph with validated relationships

**Phase 2: Core Algorithms & Interface (Weeks 2-3)**
- LangGraph RAG pipeline implementation (5 nodes: Query Understanding → Vector Search → Graph Traversal → Context Construction → Response Generation)
- Closeness calculations and TransitionIndex scoring
- FastAPI endpoints and React chat interface
- Intent-based query routing
- **Deliverable:** End-to-end query flow with natural language responses

**Phase 3: Evaluation & Refinement (Week 3+)**
- Expert validation (10 transition scenarios, 10 evaluators)
- Baseline A/B comparison (job-centric vs skill-centric)
- Closeness correlation check (100 skill pairs vs human judgment)
- Performance testing and optimization
- **Deliverable:** Validated system ready for beta launch

**Success Gate:** Each phase requires validation checkpoints before proceeding to next phase.

---

## PM Handoff

**To: Product Manager / Development Team**

This brief focuses on **technical implementation and research methodology** for the Career Intelligence AI System.

**Key Changes from v2.0:**
- ✅ **Research claims** clarified as hypotheses (not proven facts for career domain)
- ✅ **Statistical significance** (p < 0.01) attached to original ICT study only
- ✅ **Mathematical definitions** added (closeness, transition index formulas)
- ✅ **Evaluation plan** with 5 concrete validation tests
- ✅ **Data reality check** (TRANSITIONS_TO approximated, not observed)
- ✅ **Research-to-Model mapping** (what's borrowed vs what's our extension)
- ✅ **GTM/expansion content** reduced from 6 pages to 1 paragraph
- ✅ **Advanced research** (ERGM, Monte Carlo) moved to Phase 3 appendix

**Next Step:** Create **Engineering Spec** with:
1. Detailed Cypher queries for each relationship type
2. LangGraph node implementations (Python code)
3. API contracts (OpenAPI schemas)
4. Database migration scripts
5. Testing strategy (unit, integration, E2E)

**Questions?** Flag any ambiguities, missing details, or technical concerns.

**Timeline:** Target engineering spec completion within 1 week, development sprint kickoff immediately after.

---

**End of Revised Project Brief**

---

**Document Control:**
- **Version:** 2.1 (Revised - Post-QC)
- **Changes:** Research claims → hypotheses, added math definitions, evaluation plan, data reality check
- **Approvals Required:** Technical Lead, Research Advisor, Stakeholder Sign-Off
