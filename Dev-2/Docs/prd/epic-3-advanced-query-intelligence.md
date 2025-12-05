# Epic 3: Advanced Query Intelligence

**Epic Goal:** Enhance LangGraph query pipeline with network metric integration, new query intent types, and transparent research methodology citations

**Integration Requirements:**
- Existing 5-node LangGraph workflow preserved (enhancements within nodes, not structural changes)
- Query response time <5s maintained (NFR1)
- Backward compatibility with v1.1 query types (skill requirement, career path, salary analysis)
- New metric citations displayed in chat responses

## Story 3.1: Query Understanding Node Enhancement - New Intent Types

**As a** LangGraph query pipeline,
**I want** to detect new query intent types related to skill transfer and network metrics,
**so that** I can route queries to appropriate graph algorithms and metric calculations.

### Acceptance Criteria

1. Enhanced intent classification in Query Understanding node:
   - **Existing v1.1 intents preserved**: skill_requirement, career_path, salary_analysis, skill_relationship, company_query
   - **New v2.0 intents added**:
     - `skill_transfer`: "Which of my skills transfer to UX design?"
     - `learning_path`: "What's the order to learn full-stack development?"
     - `high_leverage_skills`: "Which skills have highest impact on career options?"
     - `transition_difficulty`: "How hard is it to transition from UI dev to data scientist?"
     - `skill_bridge`: "What skills bridge Python to machine learning?"
2. Intent detection using LLM-based classification:
   - Prompt template includes example queries for each intent
   - Returns: Primary intent (string) + confidence score (float, 0-1)
3. Multi-intent handling: If query matches multiple intents (confidence >0.5 for 2+ intents), return ranked list
4. Default fallback: If no intent detected with confidence >0.4, use `general_query` intent (basic semantic search)

### Integration Verification

**IV1:** v1.1 intent detection unchanged - Test 20 v1.1 sample queries, verify same intent classification as before

**IV2:** New intent accuracy - Test 30 new query types, verify >80% correct intent classification

**IV3:** Multi-intent queries - Query "Which high-leverage skills transfer to UX design?" correctly detects both `high_leverage_skills` and `skill_transfer` intents

---

## Story 3.2: Graph Traversal Node Enhancement - Metric Integration

**As a** LangGraph query pipeline,
**I want** to inject centrality lookups and closeness calculations into graph traversal,
**so that** query responses include quantified metrics instead of just semantic matches.

### Acceptance Criteria

1. Graph Traversal node enhanced with metric functions:
   - For `high_leverage_skills` intent: Query top-N skills by centrality
   - For `skill_transfer` intent: Calculate closeness from user skills to target skills
   - For `learning_path` intent: Find shortest path through PREREQUISITE_OF relationships
   - For `transition_difficulty` intent: Compute TransitionIndex
2. Cypher query templates for new intents:
   - Learning path: `MATCH path = shortestPath((s1)-[:PREREQUISITE_OF*]-(s2)) WHERE s1.NAME = $skill_a AND s2.NAME = $skill_b RETURN path`
   - High-leverage: `MATCH (s:Skill) WHERE s.eigenvector_centrality > 0.5 RETURN s ORDER BY s.eigenvector_centrality DESC LIMIT 10`
3. Context construction includes metric values:
   - Centrality scores for mentioned skills
   - Closeness values for skill pairs
   - Shortest path node list
4. Performance: Graph traversal with metrics completes in <2s (fits within 5s total query time budget)

### Integration Verification

**IV1:** v1.1 graph traversal unchanged - Existing career path, salary analysis queries still use same Cypher patterns

**IV2:** Metric values present - Sample `skill_transfer` query response includes closeness scores in context JSON

**IV3:** Performance regression test - Graph traversal time increases by <1s compared to v1.1 baseline

---

## Story 3.3: Context Construction Node Enhancement - Research Citations

**As a** user,
**I want** to understand which research methodology and metrics were used to answer my query,
**so that** I can trust the AI's recommendations and learn about the underlying science.

### Acceptance Criteria

1. Context Construction node enhanced to include:
   - **Graph statistics**: Number of nodes traversed, relationships explored, path length
   - **Metric values**: Centrality scores (if used), closeness scores (if calculated), TransitionIndex components
   - **Research methodology**: Which formula applied (e.g., "Closeness calculated using shortest path distance from 'Ties that Bind' research")
   - **Validation status**: Mark each metric as "Research-validated" | "Heuristic" | "Experimental"
2. Context JSON structure:
   ```json
   {
     "retrieved_nodes": [...],
     "graph_stats": {"nodes_traversed": 35, "relationships_explored": 58, "path_length": 3},
     "metrics": {
       "centrality": {"Python": 0.92, "JavaScript": 0.85},
       "closeness": {"Python_to_Django": 0.78, "path": ["Python", "Web Framework", "Django"]},
       "transition_index": {"score": 0.65, "components": {...}}
     },
     "methodology": "Eigenvector centrality (Neo4j GDS), Shortest path closeness (Dijkstra)",
     "validation_status": {"centrality": "research-validated", "transition_index": "heuristic"}
   }
   ```
3. Research paper citation: Include link to "Ties that Bind: ICT Network" when closeness/centrality used

### Integration Verification

**IV1:** Context completeness - All new metric queries include graph_stats and methodology fields

**IV2:** Validation transparency - Heuristic metrics (TransitionIndex, TRANSITIONS_TO) clearly marked as "heuristic, not validated"

**IV3:** v1.1 context structure preserved - Existing queries still receive same context fields (backward compatible)

---

## Story 3.4: Response Generation Node Enhancement - Metric Explanation

**As a** user,
**I want** AI responses to explain metric values in plain language,
**so that** I understand what centrality scores and closeness metrics mean for my career decisions.

### Acceptance Criteria

1. LLM prompt template enhanced with metric explanation instructions:
   - "When mentioning centrality, explain: 'Centrality measures how connected a skill is to other important skills. Higher centrality (>0.7) indicates high-leverage skills that open many career paths.'"
   - "When mentioning closeness, explain: 'Closeness of 0.8 means these skills are closely related in the job market (often required together). Closeness <0.3 indicates distant skills requiring substantial learning.'"
   - "When mentioning TransitionIndex, include disclaimer: 'This is a heuristic score based on skill overlap and market data, not a validated probability. Use as directional guidance.'"
2. Response includes:
   - Metric values with units (e.g., "Python has centrality of 0.92 out of 1.0")
   - Plain language interpretation (e.g., "This is a high-leverage skill")
   - Actionable insights (e.g., "Learning Python opens paths to data science, backend dev, and automation roles")
3. Research citations in responses: "This calculation uses the shortest path closeness methodology from network analysis research (Ties that Bind: ICT Industries study)."
4. Tone: Conversational but precise (maintain v1.1 chat tone, add scientific rigor)

### Integration Verification

**IV1:** User comprehension test - 5 beta users read sample responses with metrics, can explain what centrality/closeness means in their own words

**IV2:** Citation presence - 100% of queries using centrality/closeness include research paper reference

**IV3:** Tone consistency - New responses match v1.1 conversational style (not overly academic)

---

## Story 3.5: Frontend Metric Display - Inline Citations

**As a** user,
**I want** to see metric values displayed in chat responses with visual indicators,
**so that** I can quickly identify high-leverage skills and understand transition difficulty.

### Acceptance Criteria

1. React `ChatMessage` component modified to parse and render metrics:
   - Detect metric values in response text (regex or structured JSON parsing)
   - Render `MetricBadge` component for centrality, closeness, TransitionIndex
2. `MetricBadge` component implementation:
   - Props: {type: "centrality" | "closeness" | "transition_index", value: number, label: string}
   - Visual: Chip/tag with color coding (green >0.7, yellow 0.4-0.7, red <0.4)
   - Hover tooltip: Detailed explanation ("Centrality 0.92: High-leverage skill connected to many career paths")
3. Skill path visualization (optional, expandable):
   - If closeness metric includes shortest path, render as node diagram
   - Use simple D3.js or Recharts line chart showing skill progression
   - Example: [Python] → [Web Framework] → [Django]
4. Copy-to-clipboard: Click metric badge to copy value (for sharing/reporting)

### Integration Verification

**IV1:** Visual regression test - Existing v1.1 chat messages without metrics still render correctly

**IV2:** Metric parsing accuracy - Test 10 responses with mixed text + metrics, verify all metrics rendered as badges

**IV3:** Accessibility - MetricBadge component WCAG 2.1 AA compliant (color contrast, keyboard navigation, screen reader support)

---

## Story 3.6: Query Performance Optimization

**As a** system,
**I want** to maintain <5s query response time even with network metric calculations,
**so that** user experience remains fast and engaging (NFR1 compliance).

### Acceptance Criteria

1. Performance profiling of enhanced query pipeline:
   - Log timestamps for each LangGraph node execution
   - Identify bottlenecks (centrality lookup, shortest path calculation, LLM generation)
2. Optimization techniques implemented:
   - **Cache centrality values**: Compute once on ingestion, read from Skill.eigenvector_centrality property (not recalculated per query)
   - **Batch closeness calculations**: If query requires multiple skill pairs, use batch mode function
   - **Query timeout**: Abort graph traversal if >4s elapsed, return partial results with warning
3. Performance benchmark results:
   - 90% of queries (new intents + v1.1 intents) complete in <5s
   - Median query time: 2-3s
   - Slowest query type: `learning_path` with 5+ prerequisite hops (acceptable if <5s)
4. Monitoring: Log query time per intent type for ongoing optimization

### Integration Verification

**IV1:** NFR1 validation - Run 100 random queries (mix of v1.1 and v2.0 intents), p95 response time <5s

**IV2:** Centrality cache hit rate - >95% of centrality lookups served from cache (not recalculated)

**IV3:** Graceful degradation - If query exceeds 5s, system returns partial results + "calculation timed out" message (not error)

---
