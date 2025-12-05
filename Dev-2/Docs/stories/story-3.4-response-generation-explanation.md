# Story 3.4: Response Generation Node Enhancement - Metric Explanation

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.4
**Estimated Effort:** 1-2 days

## User Story
**As a** user,
**I want** AI responses to explain metric values in plain language,
**so that** I understand what they mean for career decisions.

## Acceptance Criteria
1. LLM prompt enhanced with metric explanation instructions
2. Response includes: values with units, plain language interpretation, actionable insights
3. Research citations in responses
4. Conversational tone maintained

## Integration Verification
**IV1:** 5 beta users can explain centrality/closeness in own words
**IV2:** 100% queries cite research paper when using metrics
**IV3:** Tone matches v1.1 conversational style

## Dependencies
**Depends on:** Story 3.3
**Blocks:** Story 3.5

---

## Technical Implementation

### Components

**Primary Service:** `ResponseGenerationNode` (ENHANCED v2.0)
- **Location:** `backend/app/agents/nodes/response_generation.py`
- **Method:** Enhanced LLM prompts with metric explanation instructions

**LLM Service:** `OpenRouterService`
- **Location:** `backend/app/services/openrouter_service.py`
- **Method:** `generate_completion()` with enhanced system prompts

### Enhanced LLM Prompts

From `components.md`:

**System Prompt Enhancement:**
```python
system_prompt = """You are a career advisor with expertise in network metrics and graph analytics.

METRIC EXPLANATION GUIDELINES:
1. Values with units: "Centrality: 0.85 (on 0-1 scale)"
2. Plain language interpretation: "Python has very high centrality (0.95), meaning it's a core skill in the job market network"
3. Actionable insights: "Learning Python opens doors to 15+ related skills"
4. Research citations: "Based on eigenvector centrality (Freeman, 1978)"

RESPONSE STRUCTURE:
- Start with direct answer
- Explain metric values in plain language
- Include research citation when using centrality/closeness
- Provide actionable next steps
- Maintain conversational tone

DISCLAIMER FOR HEURISTIC METRICS:
When using TransitionIndex or innovation indices, include:
"Note: This is a heuristic score based on static job market data, not research-validated career trajectories."
"""
```

**Example Response:**
```markdown
Based on the network analysis, **Python has very high centrality (0.95/1.0)**, meaning it's a core skill that connects to many other in-demand technologies.

**Skill Transfer to Rust:**
The closeness score between Python and Rust is **0.42** (moderate connection). The learning path traverses through Systems Programming concepts, with an estimated distance of 1.38 hops in the skill network.

**What this means for you:**
- Moderate difficulty transition (not immediate, but feasible)
- Intermediate skills: Systems Programming, Memory Management
- Estimated learning time: 40-60 hours for basic proficiency

**Research Foundation:**
Metric calculated using eigenvector centrality (Freeman, L. C., 1978) and shortest-path closeness based on skill co-occurrence in 40,000 job postings.

**Next Steps:**
1. Strengthen systems programming fundamentals
2. Learn memory management concepts
3. Build small projects in Rust to practice
```

### Testing

**Unit Test:** `tests/unit/test_response_generation.py`
- Test metric explanation formatting
- Validate research citation inclusion
- Test disclaimer for heuristic metrics

**Integration Test:** `tests/integration/test_response_generation.py`
- 5 beta users evaluate responses (can explain metrics in own words)
- Verify 100% queries cite research paper when using metrics
- Validate conversational tone matches v1.1

### Performance Targets

- **LLM Response Time:** <1.5 seconds (same as v1.1)
- **Explanation Quality:** >80% user comprehension (beta testing)
- **Citation Accuracy:** 100% correct research citations

### Security Considerations

From `security.md`:
- **Disclaimer Enforcement:** Always include disclaimer for heuristic metrics
- **Citation Validation:** Verify research paper citations are accurate
- **LLM Prompt Injection:** Sanitize user queries before LLM prompt construction
