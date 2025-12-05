# Fixes-2: Context Visibility and Limit Removal

**Created**: 2025-10-28  
**Status**: Approved  
**Priority**: High

---

## Problem Statement

The current query mechanism has two major issues:

1. **Context Truncation**: The context builder has a hard-coded 4000 token limit that truncates graph data when exceeded, reducing response quality
2. **Context Visibility**: There is no way to inspect the actual context being passed to the LLM, making debugging and optimization difficult

---

## Current Implementation Analysis

### Context Construction Node
**File**: `backend/app/agents/nodes/context_construction.py`

**Current Behavior**:
```python
# Line ~75: Hard-coded token limit check
if exceeds_token_limit(full_context, limit=4000):
    logger.warning(f"[ContextConstruction] Context exceeds 4000 tokens...")
    full_context, token_count = _truncate_context(...)
    was_truncated = True
```

**Issues**:
- Arbitrary 4000 token limit reduces context quality
- Truncation removes valuable graph relationship data
- No configurable setting for limit
- Better context = better LLM responses

### Query Response Model
**File**: `backend/app/models/query.py`

**Current Fields**:
```python
class QueryResponse(BaseModel):
    query: str
    response: str
    sources: List[SourceNode]
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]]
    # ❌ Missing: constructed_context field
```

**Issues**:
- Context is constructed but never returned to client
- No way to debug what context LLM received
- Cannot analyze context quality vs response quality

### LangGraph Service
**File**: `backend/app/services/langgraph_service.py`

**Current Behavior**:
```python
return {
    "response": response_text,
    "sources": sources,
    "metadata": metadata,
    "processing_time_ms": total_time_ms,
    "metrics": metrics_summary,
    # ❌ Missing: constructed_context not extracted from state
}
```

---

## Proposed Solutions

### Solution 1: Remove Context Token Limits

**Rationale**: Modern LLMs support large context windows (32K-128K tokens). Our 4000 token limit is unnecessarily restrictive.

**Changes Required**:

1. **Remove hard-coded limit in `context_construction.py`**:
   ```python
   # BEFORE (Line ~75)
   if exceeds_token_limit(full_context, limit=4000):
       # Truncate...
   
   # AFTER
   # Remove this check entirely
   # Allow full context to be passed to LLM
   # LLM will handle context window limits naturally
   ```

2. **Remove truncation logic**:
   ```python
   # BEFORE
   full_context, token_count = _truncate_context(...)
   was_truncated = True
   
   # AFTER
   # No truncation needed
   token_count = count_tokens(full_context)
   was_truncated = False
   ```

3. **Keep token counting for monitoring**:
   ```python
   # Still count tokens for metrics/monitoring
   token_count = count_tokens(full_context)
   logger.info(f"[ContextConstruction] Context: {token_count} tokens, {len(full_context)} chars")
   ```

**Benefits**:
- ✅ Full graph context preserved
- ✅ Better LLM responses with complete information
- ✅ No arbitrary data loss
- ✅ LLM handles context window limits naturally

**Risks**:
- ⚠️ Very large contexts may hit LLM API limits (but LLM will return error, not silently truncate)
- ⚠️ Increased API costs (but better quality responses)

**Mitigation**:
- Keep token counting for monitoring
- Log warnings for contexts >10K tokens
- Allow users to see context size in response

---

### Solution 2: Add Context Visibility API

**Rationale**: Developers and users need to inspect the actual context being passed to the LLM for debugging and optimization.

**Changes Required**:

#### 2.1 Update QueryResponse Model

**File**: `backend/app/models/query.py`

```python
class QueryResponse(BaseModel):
    """Response model for query execution results."""
    
    query: str
    response: str
    sources: List[SourceNode]
    processing_time_ms: float
    metadata: Optional[Dict[str, Any]]
    
    # NEW FIELD
    constructed_context: Optional[str] = Field(
        default=None,
        description="Full context string passed to LLM (for debugging/transparency)"
    )
    
    # NEW FIELD
    context_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context statistics (token_count, char_count, sections)"
    )
```

**Benefits**:
- ✅ Full transparency of context passed to LLM
- ✅ Easy debugging of context quality
- ✅ Users can understand how their query was processed

#### 2.2 Update LangGraph Service

**File**: `backend/app/services/langgraph_service.py`

```python
# Extract constructed_context from state
constructed_context = result.get("constructed_context", "")

return {
    "response": response_text,
    "sources": sources,
    "metadata": metadata,
    "processing_time_ms": total_time_ms,
    "metrics": metrics_summary,
    
    # NEW FIELDS
    "constructed_context": constructed_context,
    "context_stats": {
        "token_count": metadata.get("context_token_count", 0),
        "char_count": metadata.get("context_char_count", 0),
        "truncated": metadata.get("context_truncated", False),
        "vector_results_count": metadata.get("vector_results_count", 0),
        "graph_nodes_count": metadata.get("graph_nodes_count", 0)
    }
}
```

#### 2.3 Update Query API Endpoint

**File**: `backend/app/api/query.py`

```python
# Return response with context included
return QueryResponse(
    query=query_data.query,
    response=response_text,
    sources=sources,
    processing_time_ms=processing_time_ms,
    metadata=metadata,
    
    # NEW FIELDS
    constructed_context=result.get("constructed_context"),
    context_stats=result.get("context_stats")
)
```

#### 2.4 Store Context in Query History

**Update query history logging to include context**:

```python
# Store constructed_context in metadata for later retrieval
metadata["constructed_context"] = result.get("constructed_context", "")

await query_history_repo.create_query_history(
    user_id=current_user_id,
    session_id=session_id,
    query_text=query_data.query,
    response_text=response_text,
    metadata=json.dumps(metadata, default=serialize_metadata)
)
```

#### 2.5 Create New Context Retrieval Endpoint (Optional)

**File**: `backend/app/api/query.py`

```python
@router.get(
    "/history/{query_id}/context",
    summary="Retrieve context for historical query",
    description="Get the constructed context for a previous query by ID"
)
async def get_query_context(
    query_id: str,
    current_user_id: str = Depends(get_current_user),
    query_history_repo: QueryHistoryRepository = Depends(get_query_history_repository)
):
    """
    Retrieve constructed context for a historical query.
    
    Useful for:
    - Debugging why a query produced certain results
    - Understanding what data was available to LLM
    - Analyzing context quality vs response quality
    """
    # Fetch query history record
    query_record = await query_history_repo.get_query_by_id(query_id)
    
    if not query_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Verify ownership
    if query_record.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Extract context from metadata
    metadata = json.loads(query_record.metadata)
    constructed_context = metadata.get("constructed_context", "")
    
    return {
        "query_id": query_id,
        "query": query_record.query_text,
        "constructed_context": constructed_context,
        "context_stats": {
            "token_count": metadata.get("context_token_count", 0),
            "char_count": metadata.get("context_char_count", 0),
            "truncated": metadata.get("context_truncated", False)
        },
        "created_at": query_record.created_at.isoformat()
    }
```

**Benefits**:
- ✅ Retrieve context for any historical query
- ✅ Debug queries after the fact
- ✅ Analyze patterns in context quality

---

## Implementation Plan

### Phase 1: Remove Context Limits ✅

**Files to Modify**:
1. `backend/app/agents/nodes/context_construction.py`
   - Remove `exceeds_token_limit()` check
   - Remove `_truncate_context()` function call
   - Keep token counting for monitoring only

**Testing**:
- Test with queries that previously hit 4000 token limit
- Verify full context is passed to LLM
- Check LLM handles large contexts correctly

**Estimated Time**: 30 minutes

---

### Phase 2: Add Context to Response ✅

**Files to Modify**:
1. `backend/app/models/query.py`
   - Add `constructed_context` field
   - Add `context_stats` field

2. `backend/app/services/langgraph_service.py`
   - Extract `constructed_context` from state
   - Build `context_stats` from metadata

3. `backend/app/api/query.py`
   - Return context in QueryResponse
   - Store context in query_history metadata

**Testing**:
- Execute query via API
- Verify response includes `constructed_context`
- Verify `context_stats` has correct values
- Check context is stored in database

**Estimated Time**: 45 minutes

---

### Phase 3: Add Context Retrieval Endpoint (Optional) ⚪

**Files to Modify**:
1. `backend/app/api/query.py`
   - Add new `GET /query/history/{query_id}/context` endpoint

2. `backend/app/repositories/query_history_repository.py`
   - Add `get_query_by_id()` method if not exists

**Testing**:
- Create query and note its ID
- Retrieve context using new endpoint
- Verify context matches original
- Test authorization (user can only access own queries)

**Estimated Time**: 45 minutes

---

## Total Estimated Time

- Phase 1: 30 minutes
- Phase 2: 45 minutes
- Phase 3: 45 minutes (optional)

**Total**: 2 hours (with optional endpoint)

---

## Testing Strategy

### Unit Tests

```python
# test_context_construction.py

async def test_no_context_truncation():
    """Test that large contexts are NOT truncated."""
    # Create state with large graph context (10K+ tokens)
    state = GraphRAGState(
        user_query="test query",
        user_id="user_123",
        vector_results=[...],  # 50 results
        graph_context=[...]    # 200 nodes
    )
    
    result = await context_construction_node(state)
    
    # Should NOT be truncated
    assert result["metadata"]["context_truncated"] == False
    assert result["metadata"]["context_token_count"] > 4000
```

### Integration Tests

```python
# test_query_api.py

async def test_query_returns_context():
    """Test that query response includes constructed_context."""
    response = await client.post(
        "/query/ask",
        json={"query": "What skills are needed for backend development?"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify context fields exist
    assert "constructed_context" in data
    assert "context_stats" in data
    assert data["context_stats"]["token_count"] > 0
```

### Manual Testing

1. Execute query with complex question
2. Inspect response JSON
3. Verify `constructed_context` contains:
   - User query section
   - Top matching nodes
   - Graph relationships
   - Market summary
4. Verify context is NOT truncated (even if >4000 tokens)
5. Check context quality leads to better LLM response

---

## Rollback Plan

If issues arise:

1. **Revert context limit removal**:
   ```bash
   git revert <commit-hash>
   ```

2. **Add configurable limit** (if needed):
   ```python
   # In config.py
   CONTEXT_TOKEN_LIMIT: int = Field(default=10000)  # Increase from 4000
   
   # In context_construction.py
   if exceeds_token_limit(full_context, limit=settings.CONTEXT_TOKEN_LIMIT):
       # Truncate only if exceeds new higher limit
   ```

---

## Success Criteria

### Phase 1: Remove Limits
- ✅ Contexts >4000 tokens are NOT truncated
- ✅ Full graph context is preserved
- ✅ Token counting still works for monitoring
- ✅ No errors from LLM API (handles large contexts)

### Phase 2: Context Visibility
- ✅ QueryResponse includes `constructed_context` field
- ✅ QueryResponse includes `context_stats` field
- ✅ Context is stored in query_history metadata
- ✅ Frontend can display context in debug view

### Phase 3: Context Retrieval (Optional)
- ✅ New endpoint `/query/history/{query_id}/context` works
- ✅ Returns full context for historical queries
- ✅ Proper authorization (user can only access own queries)
- ✅ Useful for debugging and analysis

---

## Future Enhancements

1. **Context Optimization Analysis**:
   - Track correlation between context size and response quality
   - Identify optimal context structure for different intent types

2. **Context Compression**:
   - Intelligent summarization of graph context if needed
   - Preserve most relevant information while reducing tokens

3. **Frontend Context Viewer**:
   - Visual display of context structure
   - Highlight sections (query, vector results, graph relationships)
   - Expandable/collapsible sections

4. **Context Caching**:
   - Cache constructed contexts for similar queries
   - Reduce context construction time

---

## Notes

- **Why remove limits?**: Modern LLMs (GPT-4, Claude 3, Llama 3.3) support 32K-128K token context windows. Our 4000 token limit is unnecessarily restrictive from an older era.

- **Why expose context?**: Transparency and debuggability are crucial for AI systems. Users should understand what data the LLM is using to generate responses.

- **Performance Impact**: Minimal. Context construction time remains the same. API response size increases, but context is text (compresses well).

- **Cost Impact**: Potentially higher LLM API costs (more input tokens), but offset by better response quality and fewer retry queries.

---

## Approval Required

Please review this plan and approve before implementation.

**Questions**:
1. Should we implement all 3 phases or just Phase 1 & 2?
2. Any concerns about removing context limits?
3. Should context be optional in response (add `include_context` query param)?

---

**Status**: ⏳ Awaiting approval to proceed with implementation
