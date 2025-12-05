# Story 3.3: Context Construction Node Enhancement - Research Citations

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.3
**Estimated Effort:** 1-2 days

## User Story
**As a** user,
**I want** to understand which research methodology was used,
**so that** I can trust AI recommendations.

## Acceptance Criteria
1. Context includes: graph_stats, metrics (centrality/closeness/TransitionIndex), methodology, validation_status
2. Research paper citation included when using closeness/centrality
3. Context JSON structure defined

## Integration Verification
**IV1:** All metric queries include graph_stats and methodology
**IV2:** Heuristic metrics marked "heuristic, not validated"
**IV3:** v1.1 context structure preserved

## Dependencies
**Depends on:** Story 3.2
**Blocks:** Story 3.4

---

## Technical Implementation

### Components

**Primary Service:** `ContextConstructionNode` (ENHANCED v2.0)
- **Location:** `backend/app/agents/nodes/context_construction.py`
- **Method:** Enhanced with graph_stats, metrics, methodology, citations

### Context JSON Structure

From `components.md`:

```json
{
  "query": "How do I transition from Python to Rust?",
  "graph_stats": {
    "nodes_explored": 35,
    "relationships_traversed": 58,
    "relationship_types": ["PREREQUISITE_OF", "COMPLEMENTS", "SIMILAR_TO"]
  },
  "metrics": {
    "closeness": {
      "Python_to_Rust": 0.42,
      "distance": 1.38,
      "path": ["Python", "Systems Programming", "Rust"],
      "path_length": 2
    },
    "centrality": {
      "Python": 0.95,
      "Rust": 0.68
    },
    "transition_index": {
      "score": 0.52,
      "interpretation": "Moderate Pivot",
      "is_validated": false
    }
  },
  "methodology": {
    "metric_type": "closeness",
    "research_paper": "Freeman, L. C. (1978). Centrality in social networks",
    "validation_status": "heuristic, not research-validated",
    "disclaimer": "Metric calculated using static job market data, not observed user trajectories"
  },
  "vector_results": [...],
  "graph_context": [...]
}
```

### Context Formatting

```python
def construct_context(state: GraphRAGState) -> str:
    """
    Enhanced context construction with metrics and citations.
    """
    context_parts = []

    # 1. Graph Statistics (NEW v2.0)
    if state.metadata.get('graph_nodes_count'):
        context_parts.append(f"""
=== GRAPH STATISTICS ===
Nodes explored: {state.metadata['graph_nodes_count']}
Relationships traversed: {state.metadata['graph_relationships_count']}
Relationship types: {', '.join(state.metadata.get('relationship_types', []))}
""")

    # 2. Metrics (NEW v2.0)
    if 'metrics' in state.metadata:
        metrics = state.metadata['metrics']
        context_parts.append(f"""
=== METRICS ===
Closeness (Python → Rust): {metrics['closeness']['Python_to_Rust']:.2f}
Distance: {metrics['closeness']['distance']:.2f}
Path: {' → '.join(metrics['closeness']['path'])}
""")

    # 3. Methodology & Citations (NEW v2.0)
    if 'methodology' in state.metadata:
        method = state.metadata['methodology']
        context_parts.append(f"""
=== METHODOLOGY ===
Metric Type: {method['metric_type']}
Research Citation: {method['research_paper']}
Validation Status: {method['validation_status']}
Disclaimer: {method['disclaimer']}
""")

    # 4. Vector Results (v1.1)
    context_parts.append(format_vector_results(state.vector_results))

    # 5. Graph Context (v1.1)
    context_parts.append(format_graph_context(state.graph_context))

    return '\n\n'.join(context_parts)
```

### Testing

**Unit Test:** `tests/unit/test_context_construction.py`
- Test graph_stats inclusion
- Validate metrics formatting
- Test research citation inclusion

**Integration Test:** `tests/integration/test_context_construction.py`
- Verify all metric queries include graph_stats and methodology
- Test heuristic metrics marked "not validated"
- Verify v1.1 context structure preserved

### Performance Targets

- **Context Construction Time:** <100ms
- **Context Size:** <4000 tokens (maintain v1.1 limit)
- **Token Optimization:** Prioritize metrics > vector results if token budget exceeded

### Security Considerations

From `security.md`:
- **Disclaimer Enforcement:** Always include validation_status for heuristic metrics
- **Citation Accuracy:** Validate research paper references
- **Token Limits:** Truncate context if exceeds 4000 tokens
