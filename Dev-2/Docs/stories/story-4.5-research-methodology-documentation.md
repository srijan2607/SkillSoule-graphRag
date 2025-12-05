# Story 4.5: Research Methodology Documentation

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.5
**Estimated Effort:** 2-3 days

## User Story
**As a** future researcher or auditor,
**I want** comprehensive documentation of algorithms and validation results,
**so that** methods can be replicated.

## Acceptance Criteria
1. Documentation: mathematical formulas (LaTeX), algorithm implementations, validation results, limitations
2. Research citations: "Ties that Bind" bibliography, methodology comparison table
3. Transparency markers: research-validated vs heuristic vs experimental
4. Publication: internal `/docs/research-methodology.md` + public GitHub README

## Integration Verification
**IV1:** All metrics have documented formulas
**IV2:** 2 external researchers confirm reproducibility
**IV3:** Every heuristic has "not validated" disclaimer

## Dependencies
**Depends on:** Stories 4.1-4.4 (validation results)
**Blocks:** None (documentation story)

---

## Technical Implementation

### Components

**Documentation Files:**
- **Location:** `/Users/srijan26/Desktop/Dev/Dev-2/Docs/research/`
- **Files:**
  - `research-methodology.md` - Complete research methodology documentation
  - `validation-results.md` - Expert validation and A/B test results
  - `metric-formulas.md` - Mathematical formulas (LaTeX)
  - `limitations.md` - Known limitations and future work

### Research Methodology Document Structure

```markdown
# Research Methodology Documentation

## 1. Mathematical Formulas (LaTeX)

### Eigenvector Centrality
$$
Ax = \lambda x
$$
Where $A$ is adjacency matrix, $x$ is eigenvector, $\lambda$ is eigenvalue.

### Shortest Path Closeness
$$
\text{Closeness}(A, B) = \frac{1}{1 + d(A, B)}
$$
Where $d(A, B)$ is shortest path distance.

### TransitionIndex (Heuristic)
$$
\text{TransitionIndex} = 0.5 \cdot \text{AvgCloseness} + 0.3 \cdot \text{CoreOverlap} + 0.2 \cdot \text{MarketDemand}
$$

## 2. Algorithm Implementations

### Eigenvector Centrality Algorithm
- **Implementation:** Neo4j GDS `gds.eigenvector.write()`
- **Configuration:**
  - Max iterations: 100
  - Tolerance: 0.0001
  - Graph projection: SIMILAR_TO, COMPLEMENTS (undirected)

### Dijkstra Shortest Path
- **Implementation:** Neo4j GDS `gds.shortestPath.dijkstra.stream()`
- **Edge Weights:** $w(s_1, s_2) = \frac{1}{\text{co\_occurrence\_count}(s_1, s_2)}$

## 3. Validation Results

### Expert Validation (Story 4.1, 4.2)
- **Skill Transfer Agreement:** 82% (target: >80%)
- **Learning Path Average Rating:** 4.2/5.0 (target: >4.0)

### Closeness Correlation (Story 4.3)
- **Pearson Correlation:** 0.74 (target: >0.7)
- **Inter-Rater Reliability (Cronbach's α):** 0.76 (target: >0.7)
- **Statistical Significance:** p = 0.003 (p < 0.05)

### A/B Testing (Story 4.4)
- **Group B Improvement:** 18% (target: >15%)
- **T-test:** p = 0.012 (p < 0.05, significant)

## 4. Research Citations

### Primary Citations
- Freeman, L. C. (1978). "Centrality in social networks conceptual clarification." Social Networks, 1(3), 215-239.
- Dijkstra, E. W. (1959). "A note on two problems in connexion with graphs." Numerische Mathematik, 1(1), 269-271.

### Methodology Comparison
| Metric | Research-Validated | Heuristic | Experimental |
|--------|-------------------|-----------|--------------|
| Eigenvector Centrality | ✅ Freeman (1978) | ❌ | ❌ |
| Shortest Path Closeness | ✅ Dijkstra (1959) | ❌ | ❌ |
| TransitionIndex | ❌ | ✅ (Not validated) | ❌ |
| Innovation Index | ❌ | ❌ | ✅ (Beta) |

## 5. Transparency Markers

### Research-Validated Metrics
- **Eigenvector Centrality:** Validated by Freeman (1978)
- **Shortest Path Closeness:** Based on Dijkstra's algorithm (1959)

### Heuristic Metrics (NOT Research-Validated)
- **TransitionIndex:** Heuristic score based on static job market data, not observed user trajectories
- **Disclaimer:** "This is a heuristic score, not research-validated career trajectories"

### Experimental Metrics (Beta)
- **Innovation Index:** Experimental classification, UI deferred until validation

## 6. Limitations

### Data Limitations
- **Static Snapshot:** Job market data from single point in time
- **No User Trajectories:** No observed career transition data
- **Geographic Bias:** Data primarily from US/India job markets

### Algorithmic Limitations
- **Heuristic Weights:** TransitionIndex weights (50%-30%-20%) not optimized
- **Prerequisite Inference:** TRANSITIONS_TO relationships are approximations

### Future Work
- Collect longitudinal user trajectory data
- Optimize TransitionIndex weights through ML
- Expand dataset to global job markets
```

### Testing

**Unit Test:** `tests/unit/test_documentation.py`
- Validate all metrics have documented formulas
- Verify research citations complete
- Check transparency markers present

**Integration Test:** `tests/integration/test_documentation.py`
- External researchers review documentation (reproducibility check)
- Verify all heuristic metrics have disclaimers
- Validate LaTeX formulas render correctly

### Performance Targets

- **Documentation Completeness:** 100% of metrics documented
- **External Reproducibility:** 2 researchers confirm reproducibility
- **Disclaimer Coverage:** 100% of heuristic metrics have disclaimers

### Security Considerations

From `security.md`:
- **Data Anonymization:** Anonymize user data in published results
- **Citation Accuracy:** Verify all research paper citations correct
- **Transparency:** Clearly distinguish validated vs heuristic vs experimental
