# Epic 4: Research Validation Framework

**Epic Goal:** Implement expert evaluation framework, baseline A/B testing, and correlation checks to validate research hypotheses and metric accuracy

**Integration Requirements:**
- Validation endpoints accessible to admin users only
- Evaluation data stored in PostgreSQL (separate schema from user data)
- Metrics logged for analysis (correlation coefficients, expert agreement rates)
- Results feed into research paper / methodology documentation

## Story 4.1: Expert Validation Interface - Skill Transfer Identification

**As a** career counselor (expert evaluator),
**I want** to validate whether the system correctly identifies transferable skills,
**so that** we can measure ground truth accuracy against research hypothesis.

### Acceptance Criteria

1. Admin API endpoint `/api/validation/skill-transfer` (POST, admin-only):
   - Request body: {scenario_id, user_skills: [list], target_role: string, system_prediction: {transferable_skills: [list], closeness_scores: dict}}
   - Expert response: {transferable_skills_actual: [list], confidence: "high" | "medium" | "low", notes: string}
2. Validation dataset: 10 career transition scenarios (predefined):
   - Example: UI Developer → UX Designer (user skills: React, CSS, JavaScript, Figma)
   - System prediction: Figma (closeness 0.9), CSS (closeness 0.7) transferable; React (closeness 0.5) partial
3. Expert evaluation criteria:
   - Binary judgment: Does system correctly identify transferable skills? (Yes/No)
   - Rating: How logical is the transferable skill list? (1-5 scale)
4. Store evaluations in PostgreSQL `expert_validations` table
5. Target: >80% agreement between system prediction and expert judgment (per project brief)

### Integration Verification

**IV1:** Data integrity - All 10 scenarios evaluated by 5 experts (50 total evaluations stored)

**IV2:** Agreement calculation - Automated script computes % agreement, flags discrepancies for review

**IV3:** No impact on production - Validation endpoints isolated from user-facing query API

---

## Story 4.2: Expert Validation Interface - Learning Path Quality

**As a** hiring manager (expert evaluator),
**I want** to rate the quality of recommended learning paths,
**so that** we can validate whether prerequisite ordering makes sense for real career transitions.

### Acceptance Criteria

1. Admin API endpoint `/api/validation/learning-path` (POST, admin-only):
   - Request body: {scenario_id, source_skill: string, target_skill: string, system_path: [skills ordered list], estimated_time_hours: integer}
   - Expert response: {path_logical: boolean, rating: 1-5, suggested_changes: string, estimated_time_expert: integer}
2. Validation dataset: 10 learning path scenarios:
   - Example: HTML → Full-Stack Developer (path: [HTML, CSS, JavaScript, React, Node.js, Database])
3. Expert evaluation criteria:
   - Is path logically ordered? (Prerequisites before advanced skills)
   - Rating: Overall path quality (1-5 scale)
   - Time estimate: Does system's estimated learning time match expert judgment?
4. Target: Average expert rating >4.0/5 (per project brief)

### Integration Verification

**IV1:** Rating distribution - Expert ratings span full 1-5 range (not all 5s, indicating critical evaluation)

**IV2:** Time estimate correlation - System time estimates within ±30% of expert estimates for >70% of scenarios

**IV3:** Feedback loop - Store expert suggested changes for future prerequisite relationship refinement

---

## Story 4.3: Closeness Correlation Check with Expert Judgment

**As a** researcher,
**I want** to measure correlation between system closeness scores and expert-rated skill relatedness,
**so that** we can validate whether our network metric captures human judgment of skill similarity.

### Acceptance Criteria

1. Validation dataset: 100 skill pairs (50 highly related, 30 moderately related, 20 unrelated):
   - Examples: (Python, Django) = highly related, (Python, Photoshop) = unrelated
2. Expert evaluation: 5 domain experts rate each pair on 1-10 scale ("How related are these skills for career transitions?")
3. System calculation: Compute closeness score for all 100 pairs using `calculate_closeness()` function
4. Statistical analysis:
   - Compute Pearson correlation coefficient between expert average rating and system closeness score
   - Target: Correlation >0.7 (strong positive relationship, per project brief)
5. Results visualization: Scatter plot (x-axis: expert rating, y-axis: closeness score) with trend line
6. Store results in PostgreSQL `closeness_validation` table

### Integration Verification

**IV1:** Dataset representativeness - 100 pairs cover diverse skill categories (technical, soft skills, tools, frameworks)

**IV2:** Expert agreement - Inter-rater reliability (Cronbach's alpha) >0.7 among 5 experts (ensures consistent judgments)

**IV3:** Correlation significance - p-value <0.05 for Pearson correlation (statistically significant result)

---

## Story 4.4: Baseline A/B Testing - Job-Centric vs Skill-Centric

**As a** product manager,
**I want** to compare user satisfaction with skill-centric search vs job-centric search,
**so that** we can validate whether graph restructuring improves query relevance.

### Acceptance Criteria

1. A/B test setup:
   - **Group A (Baseline)**: v1.1 job-centric search (keyword matching + semantic similarity, no network metrics)
   - **Group B (Treatment)**: v2.0 skill-centric search (closeness metrics, centrality, TransitionIndex)
2. Metrics tracked:
   - Query relevance rating (user rates response 1-5 scale after each query)
   - Time to useful answer (user self-reports: <1min, 1-3min, >3min, or "not found")
   - Click-through rate (if recommendations include job links, track clicks)
3. Sample size: 50 beta users, 3+ queries each (minimum 150 total queries)
4. Target: Group B (skill-centric) outperforms Group A by >15% on relevance ratings (per project brief)
5. Statistical test: Two-sample t-test on mean relevance ratings, significance threshold p<0.05

### Integration Verification

**IV1:** Random assignment - Users randomly assigned to Group A or B (no selection bias)

**IV2:** Data collection - All ratings and timing data stored in PostgreSQL `ab_test_results` table

**IV3:** Result interpretation - Clear summary report: "Skill-centric search achieved 4.2/5 avg rating vs 3.5/5 for job-centric (p=0.002, significant improvement)"

---

## Story 4.5: Research Methodology Documentation

**As a** future researcher or auditor,
**I want** comprehensive documentation of all algorithms, formulas, and validation results,
**so that** the system can be peer-reviewed and methods replicated.

### Acceptance Criteria

1. Documentation includes:
   - **Mathematical formulas**: LaTeX-formatted equations for centrality, closeness, TransitionIndex
   - **Algorithm implementations**: Pseudocode + actual code (Python functions with docstrings)
   - **Validation results**: Expert agreement rates, correlation coefficients, A/B test outcomes
   - **Limitations section**: Explicitly state what is validated vs heuristic vs experimental
2. Research citations:
   - Full bibliography entry for "Ties that Bind: ICT Network" paper
   - Methodology comparison table: What we borrowed directly vs what we extended
3. Transparency markers:
   - **Research-validated**: Eigenvector centrality (Neo4j GDS standard algorithm)
   - **Heuristic**: TransitionIndex (weighted combination, not statistically validated)
   - **Experimental**: TRANSITIONS_TO relationships (approximated from static data)
4. Publication targets:
   - Internal documentation: `/docs/research-methodology.md`
   - Public-facing: Research section on project website/GitHub README

### Integration Verification

**IV1:** Completeness check - All metrics (centrality, closeness, TransitionIndex, creation index) have documented formulas and implementations

**IV2:** Peer review - 2 external researchers review documentation, confirm reproducibility

**IV3:** Limitation disclosure - Every heuristic metric includes clear "not validated" disclaimer in docs and UI

---

## Story 4.6: Monitoring Dashboard for Research Metrics (Optional Stretch Goal)

**As a** system administrator,
**I want** a real-time dashboard showing metric calculation performance and validation stats,
**so that** I can monitor system health and identify metric accuracy issues.

### Acceptance Criteria

1. Admin dashboard (`/admin/metrics-dashboard`, admin-only):
   - **Centrality health**: Last update timestamp, top 10 skills by centrality, calculation time
   - **Closeness performance**: Avg query time (p50, p95), failed path calculations (no path found %)
   - **TransitionIndex usage**: Number of queries using TransitionIndex, avg score distribution
   - **Validation metrics**: Expert agreement rate, closeness correlation, A/B test status
2. Real-time updates: Dashboard refreshes every 30 seconds (WebSocket or polling)
3. Alerts: Email/Slack notification if:
   - Centrality calculation fails or exceeds 30s (NFR11 violation)
   - Closeness query time >500ms for >10% of queries (NFR12 violation)
   - Expert agreement rate drops below 70% (quality issue)
4. **Implementation**: Optional Phase 5 feature, not MVP blocking

### Integration Verification

**IV1:** Dashboard accessibility - Only users with `admin` role can access (JWT role check)

**IV2:** Performance impact - Dashboard queries do not affect user-facing query response time

**IV3:** Alert reliability - Test alerts by simulating performance degradation (e.g., disable Neo4j GDS), verify notifications sent

---
