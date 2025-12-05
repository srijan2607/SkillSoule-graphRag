# Story 3.1: Query Understanding Node Enhancement - New Intent Types

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.1
**Estimated Effort:** 1-2 days

## User Story
**As a** LangGraph query pipeline,
**I want** to detect new query intent types for skill transfer and network metrics,
**so that** I can route queries to appropriate graph algorithms.

## Acceptance Criteria
1. Enhanced intent classification with new v2.0 intents: skill_transfer, learning_path, high_leverage_skills, transition_difficulty, skill_bridge
2. LLM-based classification returns: intent + confidence score
3. Multi-intent handling (confidence >0.5 for 2+ intents)
4. Fallback: general_query if confidence <0.4

## Integration Verification
**IV1:** v1.1 intents unchanged (20 sample queries)
**IV2:** New intents >80% accuracy (30 test queries)
**IV3:** Multi-intent queries detected correctly

## Dependencies
**Depends on:** None (LangGraph node enhancement)
**Blocks:** Story 3.2

---

## Technical Implementation

### Components

**Primary Service:** `QueryUnderstandingNode` (ENHANCED v2.0)
- **Location:** `backend/app/agents/nodes/query_understanding.py`
- **Method:** `classify_intent()` with new v2.0 intent types

**LLM Service:** `OpenRouterService`
- **Location:** `backend/app/services/openrouter_service.py`
- **Method:** `classify_query_intent()` for LLM-based classification

### New Intent Types

From `components.md`:

**v2.0 New Intents:**
- `skill_transfer`: "How do I transition from Python to Rust?"
- `learning_path`: "What's the learning path for machine learning?"
- `high_leverage_skills`: "Which skills give highest career impact?"
- `transition_difficulty`: "How hard is it to move from frontend to backend?"
- `skill_bridge`: "What intermediate skills connect Web Dev to Data Science?"

**Intent Classification Process:**
```python
def classify_intent(query: str) -> Dict:
    """
    Enhanced intent classification with v2.0 intents.

    Returns:
        {
            "primary_intent": str,
            "confidence": float (0-1),
            "secondary_intents": [{"intent": str, "confidence": float}],
            "is_multi_intent": bool
        }
    """
    # LLM-based classification
    classification = openrouter_service.classify_query_intent(
        query=query,
        intent_types=[...v1.1_intents, ...v2.0_intents]
    )

    # Multi-intent handling (confidence >0.5 for 2+ intents)
    multi_intents = [
        item for item in classification['all_intents']
        if item['confidence'] > 0.5
    ]

    # Fallback to general_query if confidence <0.4
    primary_intent = classification['primary_intent']
    if classification['primary_confidence'] < 0.4:
        primary_intent = 'general_query'

    return {
        'primary_intent': primary_intent,
        'confidence': classification['primary_confidence'],
        'secondary_intents': multi_intents[1:],  # Exclude primary
        'is_multi_intent': len(multi_intents) > 1
    }
```

### Testing

**Unit Test:** `tests/unit/test_query_understanding.py`
- Test new v2.0 intent detection (30 sample queries)
- Validate multi-intent handling (confidence >0.5)
- Test fallback to general_query (confidence <0.4)

**Integration Test:** `tests/integration/test_query_understanding.py`
- Run 50 sample queries (20 v1.1, 30 v2.0)
- Verify >80% accuracy for new intents
- Test v1.1 intent preservation (100% accuracy)

### Performance Targets

- **Classification Time:** <200ms (LLM API call)
- **Accuracy:** >80% for new v2.0 intents, 100% for v1.1 intents
- **Multi-Intent Detection:** >90% accuracy for 2+ intent queries

### Security Considerations

From `security.md`:
- **Input Validation:** Sanitize query text before LLM classification
- **Rate Limiting:** Max 100 classification requests per user per hour
- **Fallback Safety:** Default to general_query to prevent errors
