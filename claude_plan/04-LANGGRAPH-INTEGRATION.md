# Phase 4: LangGraph Integration

# Status: ✅ QA Approved | Ready for Phase 5


## Overview

This phase integrates network math capabilities into the existing LangGraph RAG pipeline. This includes adding a new TRANSITION_PATH intent, updating graph traversal queries, and enhancing context construction to include network metrics.

---

## 1. New Intent: TRANSITION_PATH

### Update Intent Patterns

**File**: `backend/app/services/intent_analysis_service.py`

Add to `INTENT_PATTERNS`:

```python
INTENT_PATTERNS = {
    # ... existing patterns ...

    "transition_path": [
        r"transition from",
        r"switch from .* to",
        r"move from .* to",
        r"how (do i|can i|to) (become|transition|switch|move)",
        r"career path from",
        r"gap between .* and",
        r"skills gap",
        r"what skills .* need .* to become",
        r"bridge .* to",
        r"from .* to .*",
        r"skills to learn (for|to)",
        r"learning path",
        r"upskill from",
    ],
}
```

### Add Intent Archetype

Add to `_initialize_archetypes()`:

```python
self.INTENT_ARCHETYPES["transition_path"] = IntentArchetype(
    intent_type="transition_path",
    canonical_queries=[
        "How do I transition from backend developer to ML engineer?",
        "What skills do I need to switch from Python to Go?",
        "Career path from data analyst to data scientist",
        "Skills gap between frontend developer and full stack",
        "Learning path to become a DevOps engineer from developer",
    ],
    keywords=["transition", "switch", "from", "to", "become", "gap", "path"],
    confidence_threshold=0.65,
)
```

### Update Intent Model

**File**: `backend/app/models/intent.py`

```python
# Add to allowed intent types
INTENT_TYPES = [
    "skill_requirement",
    "career_path",
    "skill_relationship",
    "salary_analysis",
    "company_query",
    "transition_path",  # NEW
    "general",
]
```

---

## 2. Update Graph Traversal

### New Traversal Query

**File**: `backend/app/agents/nodes/graph_traversal.py`

Add to `generate_traversal_query()`:

```python
def generate_traversal_query(
    intent: str, seed_node_ids: List[str], node_type: str, depth: int = None
) -> Optional[str]:
    # ... existing code ...

    queries = {
        # ... existing queries ...

        "transition_path": f"""
            // Find source and target skills from seed nodes
            MATCH (source:Skill) WHERE source.id IN $seed_ids[..3]
            MATCH (target:Skill) WHERE target.id IN $seed_ids[3..]

            // Find shortest paths using CO_OCCURS_WITH
            MATCH path = shortestPath((source)-[:CO_OCCURS_WITH*1..{depth}]-(target))

            // Calculate path cost
            WITH source, target, path,
                 reduce(cost = 0.0, r IN relationships(path) | cost + r.cost) as path_cost,
                 1.0 / (1.0 + reduce(cost = 0.0, r IN relationships(path) | cost + r.cost)) as closeness

            // Get intermediate skills
            UNWIND nodes(path) as intermediate_skill

            // Get related jobs for each skill
            OPTIONAL MATCH (j:Job)-[:REQUIRES]->(intermediate_skill)
            WITH source, target, path, path_cost, closeness,
                 intermediate_skill,
                 count(DISTINCT j) as job_demand

            RETURN
                source AS source_skill,
                target AS target_skill,
                path_cost,
                closeness,
                collect(DISTINCT {{
                    skill: intermediate_skill,
                    job_demand: job_demand
                }}) AS path_skills

            LIMIT {cypher_limit}
        """,
    }

    return queries.get(intent)
```

### Alternative: Direct Dijkstra Query

For cases where we need true Dijkstra (not just shortestPath):

```python
"transition_path_dijkstra": """
    // Match source and target skills
    MATCH (source:Skill {id: $source_skill_id})
    MATCH (target:Skill {id: $target_skill_id})

    // Use APOC Dijkstra for weighted shortest path
    CALL apoc.algo.dijkstra(source, target, 'CO_OCCURS_WITH', 'cost')
    YIELD path, weight

    // Extract path details
    WITH path, weight,
         [n IN nodes(path) | n] AS path_nodes,
         [r IN relationships(path) | r] AS path_rels

    // Get job demand for each skill in path
    UNWIND path_nodes AS skill
    OPTIONAL MATCH (j:Job)-[:REQUIRES]->(skill)
    WITH path, weight, skill, count(DISTINCT j) AS job_demand

    RETURN
        weight AS total_distance,
        1.0 / (1.0 + weight) AS closeness,
        collect({
            skill_id: skill.id,
            skill_name: skill.name,
            job_demand: job_demand
        }) AS path_details
""",
```

---

## 3. Enhanced Entity Extraction

### Extract Source/Target Skills

**File**: `backend/app/services/entity_extraction_service.py`

Add transition-specific entity extraction:

```python
async def extract_transition_entities(
    self,
    query: str,
    query_embedding: List[float]
) -> Dict[str, List[Entity]]:
    """
    Extract source and target skills for transition queries.

    Looks for patterns like "from X to Y" or "switch X to Y"
    """
    # Regex patterns for transition queries
    transition_patterns = [
        r"(?:from|switch from|transition from)\s+(.+?)\s+(?:to|into)\s+(.+?)(?:\?|$)",
        r"(?:become|move to|switch to)\s+(.+?)\s+(?:from|as)\s+(.+?)(?:\?|$)",
        r"(.+?)\s+(?:to|->)\s+(.+?)(?:\?|$)",
    ]

    source_entities = []
    target_entities = []

    query_lower = query.lower()

    for pattern in transition_patterns:
        match = re.search(pattern, query_lower, re.IGNORECASE)
        if match:
            # Extract potential skill names
            source_text = match.group(1).strip()
            target_text = match.group(2).strip()

            # Match against graph
            source_skills = await self._match_skill_in_graph(source_text)
            target_skills = await self._match_skill_in_graph(target_text)

            for skill in source_skills:
                source_entities.append(Entity(
                    type="source_skill",
                    value=skill["name"],
                    confidence=skill["confidence"],
                    source="transition_pattern",
                    graph_node_id=skill["id"]
                ))

            for skill in target_skills:
                target_entities.append(Entity(
                    type="target_skill",
                    value=skill["name"],
                    confidence=skill["confidence"],
                    source="transition_pattern",
                    graph_node_id=skill["id"]
                ))

            break  # Use first matching pattern

    return {
        "source_skills": source_entities,
        "target_skills": target_entities
    }
```

---

## 4. Context Construction Updates

### Network Metrics Section

**File**: `backend/app/agents/nodes/context_construction.py`

Add network metrics formatting:

```python
def format_transition_context(
    path_results: Dict[str, Any],
    source_skills: List[str],
    target_skills: List[str]
) -> str:
    """
    Format transition path results for LLM context.
    """
    sections = []

    # Header with network statistics
    sections.append("""
======================================================================
SKILL TRANSITION ANALYSIS
======================================================================
""")

    # Path summary
    if path_results.get("path_exists"):
        sections.append(f"""
**Transition Path Found**
- Total Distance: {path_results['total_distance']:.3f}
- Closeness Score: {path_results['closeness']:.3f}
- Path Length: {len(path_results['path'])} skills
""")

        # Path visualization
        path_names = [p["name"] for p in path_results["path_details"]]
        path_str = " → ".join(path_names)
        sections.append(f"""
**Learning Path:**
{path_str}
""")

        # Skills breakdown
        sections.append("""
**Skills Analysis:**
""")
        for idx, skill in enumerate(path_results["path_details"]):
            marker = "✓" if skill["id"] in source_skills else "○"
            sections.append(f"  {marker} {skill['name']}")

    else:
        sections.append("""
**No Direct Path Found**
The skills are not connected in the co-occurrence network.
This may indicate a significant skill gap.
""")

    # Recommendations
    if path_results.get("closeness", 0) > 0.7:
        sections.append("""
**Transition Feasibility:** HIGH
The skills are closely related in the job market.
""")
    elif path_results.get("closeness", 0) > 0.4:
        sections.append("""
**Transition Feasibility:** MODERATE
Some bridging skills are needed.
""")
    else:
        sections.append("""
**Transition Feasibility:** CHALLENGING
Significant skill development required.
""")

    return "\n".join(sections)
```

### Update Main Context Builder

```python
async def context_construction_node(state: GraphRAGState) -> Dict[str, Any]:
    """Build context for LLM response generation."""

    # ... existing code ...

    # Check if this is a transition query
    if "transition_path" in state.intents:
        # Get transition-specific context
        transition_context = await _build_transition_context(state)
        context_sections.append(transition_context)

    # ... rest of existing code ...
```

---

## 5. Response Generation Updates

### Transition-Specific Prompts

**File**: `backend/app/agents/nodes/response_generation.py`

Add transition response template:

```python
TRANSITION_SYSTEM_PROMPT = """
You are a career advisor helping with skill transitions.

When analyzing transition paths:
1. Start with the closeness score interpretation
2. Explain the learning path step by step
3. Prioritize skills by job market demand
4. Suggest practical learning resources
5. Be encouraging but realistic about timelines

IMPORTANT:
- Reference the network metrics (closeness, path length)
- Mention specific skills in the path
- Include market demand data if available
- Provide actionable next steps
"""

TRANSITION_USER_PROMPT_TEMPLATE = """
TRANSITION CONTEXT:
{transition_context}

SKILLS ANALYSIS:
- Source skills: {source_skills}
- Target role/skills: {target_skills}
- Closeness score: {closeness}
- Path length: {path_length} skills

User's Question: {query}

Provide a comprehensive transition plan based on the network analysis.
"""
```

### Update Response Generator

```python
async def response_generation_node(state: GraphRAGState) -> Dict[str, Any]:
    """Generate LLM response."""

    # ... existing code ...

    # Use transition-specific prompts if needed
    if "transition_path" in state.intents:
        system_prompt = TRANSITION_SYSTEM_PROMPT
        user_prompt = TRANSITION_USER_PROMPT_TEMPLATE.format(
            transition_context=state.constructed_context,
            source_skills=state.metadata.get("source_skills", []),
            target_skills=state.metadata.get("target_skills", []),
            closeness=state.metadata.get("closeness", "N/A"),
            path_length=state.metadata.get("path_length", "N/A"),
            query=state.user_query
        )
    else:
        # Use existing prompts
        system_prompt = CAREER_ADVISOR_SYSTEM_PROMPT
        user_prompt = build_user_prompt(state)

    # ... rest of generation code ...
```

---

## 6. State Updates

### Update GraphRAGState

**File**: `backend/app/agents/graph.py`

```python
class GraphRAGState(BaseModel):
    # ... existing fields ...

    # Transition-specific fields
    transition_path: Optional[Dict[str, Any]] = None
    source_skills: Optional[List[str]] = None
    target_skills: Optional[List[str]] = None
    closeness_score: Optional[float] = None
    transition_index: Optional[float] = None
```

---

## 7. Workflow Updates

### Add Transition Node (Optional)

For complex transition queries, add a dedicated node:

```python
async def transition_analysis_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Dedicated node for transition path analysis.

    Only executed for transition_path intent.
    """
    if "transition_path" not in state.intents:
        return {"transition_analysis_skipped": True}

    # Get network metrics service
    metrics_service = await get_network_metrics_service()

    # Extract source and target skills
    source_skills = [e.graph_node_id for e in state.entities
                     if e.type == "source_skill"]
    target_skills = [e.graph_node_id for e in state.entities
                     if e.type == "target_skill"]

    if not source_skills or not target_skills:
        return {
            "transition_path": {"error": "Could not identify source/target skills"},
            "metadata": {**state.metadata, "transition_error": True}
        }

    # Calculate path for each source-target pair
    paths = []
    for src in source_skills:
        for tgt in target_skills:
            path = await metrics_service.get_shortest_path(src, tgt)
            if path["path_exists"]:
                paths.append(path)

    # Find best path (highest closeness)
    best_path = max(paths, key=lambda p: p["closeness"]) if paths else None

    return {
        "transition_path": best_path,
        "source_skills": source_skills,
        "target_skills": target_skills,
        "closeness_score": best_path["closeness"] if best_path else 0.0,
        "metadata": {
            **state.metadata,
            "transition_analysis_completed": True,
            "paths_found": len(paths)
        }
    }
```

### Update Workflow Graph

```python
# In langgraph_service.py

def build_workflow():
    workflow = StateGraph(GraphRAGState)

    # Add nodes
    workflow.add_node("query_understanding", query_understanding_node)
    workflow.add_node("vector_search", vector_search_node)
    workflow.add_node("graph_traversal", graph_traversal_node)
    workflow.add_node("transition_analysis", transition_analysis_node)  # NEW
    workflow.add_node("context_construction", context_construction_node)
    workflow.add_node("response_generation", response_generation_node)

    # Conditional edge for transition queries
    def should_analyze_transition(state):
        if "transition_path" in state.intents:
            return "transition_analysis"
        return "context_construction"

    # Add edges
    workflow.add_edge("query_understanding", "vector_search")
    workflow.add_edge("vector_search", "graph_traversal")
    workflow.add_conditional_edges(
        "graph_traversal",
        should_analyze_transition,
        {
            "transition_analysis": "transition_analysis",
            "context_construction": "context_construction"
        }
    )
    workflow.add_edge("transition_analysis", "context_construction")
    workflow.add_edge("context_construction", "response_generation")

    workflow.set_entry_point("query_understanding")
    workflow.set_finish_point("response_generation")

    return workflow.compile()
```

---

## 8. Example Flow

### Query: "How do I transition from Python developer to Go developer?"

**Step 1: Query Understanding**
```json
{
  "intents": ["transition_path", "skill_requirement"],
  "entities": [
    {"type": "source_skill", "value": "Python", "graph_node_id": "python-001"},
    {"type": "target_skill", "value": "Go", "graph_node_id": "golang-001"}
  ]
}
```

**Step 2: Vector Search**
```json
{
  "vector_results": [
    {"id": "python-001", "name": "Python", "score": 0.95},
    {"id": "golang-001", "name": "Go", "score": 0.92},
    {"id": "rest-api-001", "name": "REST APIs", "score": 0.85}
  ]
}
```

**Step 3: Graph Traversal**
```json
{
  "graph_context": [
    {"node_type": "Skill", "node_id": "python-001"},
    {"type": "CO_OCCURS_WITH", "weight": 45},
    {"node_type": "Skill", "node_id": "docker-001"}
  ]
}
```

**Step 4: Transition Analysis**
```json
{
  "transition_path": {
    "path_exists": true,
    "total_distance": 0.12,
    "closeness": 0.89,
    "path": ["python-001", "docker-001", "kubernetes-001", "golang-001"],
    "path_details": [
      {"id": "python-001", "name": "Python"},
      {"id": "docker-001", "name": "Docker"},
      {"id": "kubernetes-001", "name": "Kubernetes"},
      {"id": "golang-001", "name": "Go"}
    ]
  },
  "closeness_score": 0.89
}
```

**Step 5: Context Construction**
```
======================================================================
SKILL TRANSITION ANALYSIS
======================================================================

**Transition Path Found**
- Total Distance: 0.120
- Closeness Score: 0.89
- Path Length: 4 skills

**Learning Path:**
Python → Docker → Kubernetes → Go

**Skills Analysis:**
  ✓ Python (already known)
  ○ Docker (bridge skill)
  ○ Kubernetes (bridge skill)
  ○ Go (target skill)

**Transition Feasibility:** HIGH
The skills are closely related in the job market.
```

**Step 6: Response Generation**
```
Based on my analysis of the skill co-occurrence network, transitioning from
Python to Go has a high feasibility (closeness score: 0.89).

**Recommended Learning Path:**
1. **Docker** - Python developers commonly move into containerization
2. **Kubernetes** - Often paired with Docker and used heavily with Go
3. **Go** - Your target language, strongly connected to cloud-native tools

**Why this path works:**
- 45 jobs require both Python and Docker
- 38 jobs require both Docker and Kubernetes
- 52 jobs require both Kubernetes and Go

**Suggested Timeline:**
- Docker: 2-4 weeks (many concepts transfer from Python)
- Kubernetes: 4-6 weeks (hands-on practice essential)
- Go: 6-8 weeks (focus on Go idioms vs Python patterns)

Would you like me to suggest specific learning resources for any of these skills?
```

---

## 9. Success Criteria

1. **Intent Detection**: TRANSITION_PATH correctly identified for transition queries
2. **Path Finding**: Dijkstra paths computed correctly using CO_OCCURS_WITH.cost
3. **Context Quality**: Network metrics clearly displayed in context
4. **Response Quality**: LLM references network data in responses
5. **Performance**: Transition queries complete in < 2 seconds
6. **Fallback**: System handles cases where no path exists

---

*Next: Phase 5 - Testing Strategy*

---

## QA Results

**Reviewer**: Quinn (Test Architect)
**Review Date**: 2025-12-06
**Gate Status**: ✅ PASS

### Files Reviewed

| File | Lines | Status | Description |
|------|-------|--------|-------------|
| `backend/app/agents/nodes/transition_metrics.py` | 304 | ✅ New | Transition analysis node |
| `backend/app/agents/graph.py` | Updated | ✅ Modified | State fields + routing + workflow |
| `backend/app/services/intent_analysis_service.py` | Updated | ✅ Modified | `transition_path` patterns |
| `backend/app/agents/nodes/context_construction.py` | Updated | ✅ Modified | `_format_transition_context()` |
| `backend/app/agents/nodes/response_generation.py` | Updated | ✅ Modified | Transition guidance in prompts |
| `backend/tests/integration/test_langgraph_transition.py` | 337 | ✅ New | Transition tests |
| `backend/tests/integration/test_langgraph_workflow.py` | 175 | ✅ Existing | Base workflow tests |

**Total Test Coverage**: 512 lines across integration tests

### Acceptance Criteria Verification

| Criterion | Status |
|-----------|--------|
| `transition_path` intent patterns | ✅ Verified (13 patterns) |
| IntentArchetype for transition_path | ✅ Verified |
| GraphRAGState extended with transition fields | ✅ Verified |
| Conditional routing (`_should_run_transition_metrics`) | ✅ Verified |
| transition_metrics node implementation | ✅ Verified |
| NetworkMetricsService integration | ✅ Verified |
| Context construction updates | ✅ Verified |
| Response generation updates | ✅ Verified |
| Workflow graph updated | ✅ Verified |
| Integration tests | ✅ 18 test cases |

### Test Summary

**Integration Tests (`test_langgraph_transition.py`):**
- `TestTransitionRouting`: 5 tests (routing function unit tests)
- Workflow compilation: 2 tests
- Transition path workflows: 3 tests
- State field tests: 4 tests
- Non-transition workflows: 2 tests
- Context construction: 1 test
- Workflow metadata: 1 test

**Base Workflow Tests (`test_langgraph_workflow.py`):**
- Workflow compilation: 1 test
- Complete execution: 1 test
- Node execution order: 1 test
- Empty query validation: 1 test
- State immutability: 1 test
- Metadata tracking: 1 test

### Workflow Architecture Verified

```
understand_query → vector_search → graph_traversal
    → [if transition_path] → transition_metrics → construct_context
    → [else] → construct_context
→ generate_response → END
```

### NFR Validation

| NFR | Status | Notes |
|-----|--------|-------|
| Security | ✅ PASS | Uses authenticated NetworkMetricsService |
| Performance | ✅ PASS | Conditional execution - skips node when not needed |
| Reliability | ✅ PASS | Graceful fallback when no target job/skills found |
| Maintainability | ✅ PASS | Clean separation, proper logging, pipeline monitoring |

### Recommendations

**Future Enhancements (Low Priority):**
1. Add unit tests for `transition_metrics.py` helper functions (`_extract_source_skills`, `_extract_target_job`)
2. Add performance benchmarks for transition queries

### Quality Score: 88/100

Comprehensive integration that properly extends the LangGraph workflow with conditional routing. Tests are at integration level which is appropriate for this phase. Minor improvement would be adding unit tests for helper functions.

---

**Gate**: PASS
**Approved for**: Phase 5 - Testing Strategy
