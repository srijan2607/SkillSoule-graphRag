# Real-Time Query Processing Visualization in Chat

**Created**: October 25, 2025  
**Status**: ✅ Complete and Integrated

---

## Overview

Users can now see **in real-time** how their questions are being processed by the backend. When a user submits a query in the chat, a beautiful expandable panel appears showing all the Neo4j database queries being executed behind the scenes, complete with:

- ✅ Query type classification (READ, WRITE, VECTOR_SEARCH, GRAPH_TRAVERSAL)
- ✅ Execution time for each query
- ✅ Success/failure status
- ✅ Result counts
- ✅ Source identification
- ✅ Total processing time and success rate

---

## User Experience

### Before Query
User types a question like "What skills do I need for data science?" and clicks send.

### During Processing
1. **"AI is thinking..." indicator appears** with animated brain icon
2. **Query Processing panel expands below** showing:
   - Live connection status (green pulsing dot)
   - "Waiting for queries..." message
3. **As backend executes Neo4j queries**, they appear in real-time:
   ```
   ✓ VECTOR_SEARCH     45.2ms     10 results
   CALL db.index.vector.queryNodes('skill_embedding_idx', 15, $query_embedding)...
   Source: vector_search_skills
   
   ✓ GRAPH_TRAVERSAL   123.4ms    25 results  
   MATCH (s:Skill)-[:REQUIRED_FOR]->(j:Job) WHERE s.id IN $skill_ids...
   Source: query_pipeline
   
   ✓ READ             12.1ms     5 results
   MATCH (c:Company)-[:OFFERS]->(j:Job) WHERE j.id IN $job_ids...
   Source: company_lookup
   ```

4. **Summary footer shows**:
   - Total Time: 180.7ms
   - Success Rate: 100%

### After Response
- Query Processing panel remains visible with all executed queries
- User can collapse/expand to review what happened
- Next query clears the panel and starts fresh

---

## Technical Implementation

### 1. Frontend Components

#### **`QueryProcessingView.jsx`**
```
Connects to: ws://127.0.0.1:8000/monitor/live
Purpose: Real-time query log streaming
Features:
  - WebSocket connection with auto-reconnect
  - Session ID filtering (only shows queries for current chat message)
  - Expandable/collapsible panel
  - Color-coded query types
  - Execution time tracking
  - Success rate calculation
```

#### **`TypingIndicator.jsx` (Enhanced)**
```
Now accepts: sessionId prop
Purpose: Container for query processing visualization
Shows:
  - Animated "AI is thinking..." message
  - Elapsed time counter
  - QueryProcessingView component below
```

### 2. Session ID Tracking

**Frontend (useChat.ts)**:
```typescript
// Generate unique session ID for each query
const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
setCurrentSessionId(sessionId);

// Pass to API
await sendQuery(content.trim(), token, sessionId);
```

**API Layer (api.ts)**:
```typescript
export interface QueryRequest {
  query: string;
  session_id?: string;  // Optional session tracking
}

// Include in request body
const requestBody: QueryRequest = { query };
if (sessionId) {
  requestBody.session_id = sessionId;
}
```

**Backend (query.py)**:
```python
class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # For real-time tracking

# Pass through to LangGraph
result = await langgraph_service.execute_query(
    query=query_data.query,
    user_id=current_user_id,
    session_id=query_data.session_id  # <-- Passed to workflow
)
```

**LangGraph Service (langgraph_service.py)**:
```python
async def execute_query(
    self,
    query: str,
    user_id: str,
    session_id: Optional[str] = None  # <-- Received
) -> Dict[str, Any]:
    # Include in state metadata
    initial_state = GraphRAGState(
        user_query=query,
        user_id=user_id,
        metadata={
            "metrics": metrics,
            "query_id": query_id,
            "session_id": session_id  # <-- Available to all agents
        },
    )
```

### 3. WebSocket Filtering

**Backend (monitor.py)**:
```python
# Already broadcasts all queries with session_id in queryLog
{
    "query_text": "MATCH (s:Skill)...",
    "operation_type": "READ",
    "execution_time_ms": 45.2,
    "session_id": "session-1234567890-abc123",  # <-- Included
    "status": "success",
    ...
}
```

**Frontend (QueryProcessingView.jsx)**:
```javascript
ws.onmessage = (event) => {
    const queryLog = JSON.parse(event.data);
    
    // Only show queries from this specific session
    if (queryLog.session_id === sessionId) {
        setQueries(prev => [...prev, queryLog]);
    }
};
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Types Query                            │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Frontend: Generate session_id = "session-1729876543-xyz789"    │
│           Show TypingIndicator with QueryProcessingView         │
│           Connect WebSocket to /monitor/live                    │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ API Request: POST /query/ask                                    │
│ Body: { query: "...", session_id: "session-1729876543-xyz789" }│
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Backend: LangGraph Workflow Executes                            │
│          session_id passed to state.metadata                    │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Agents Execute Neo4j Queries:                                   │
│   - Intent Classifier → Neo4j READ query                        │
│   - Vector Search → Neo4j VECTOR_SEARCH query                   │
│   - Subgraph Extraction → Neo4j GRAPH_TRAVERSAL query           │
│   - Response Generator → (no Neo4j, uses LLM)                   │
│                                                                  │
│ Each query logged with session_id to:                           │
│   1. PostgreSQL (via Prisma)                                    │
│   2. In-memory cache                                            │
│   3. WebSocket broadcast                                        │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ WebSocket Message Received:                                     │
│ {                                                               │
│   "query_text": "CALL db.index.vector.queryNodes(...)",        │
│   "operation_type": "VECTOR_SEARCH",                            │
│   "execution_time_ms": 45.2,                                    │
│   "result_count": 10,                                           │
│   "status": "success",                                          │
│   "session_id": "session-1729876543-xyz789",  ← MATCHED!        │
│   "source": "vector_search_skills",                             │
│   "timestamp": "2025-10-25T20:15:30.123Z"                       │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ QueryProcessingView Displays Query in Real-Time:                │
│                                                                  │
│   ✓ VECTOR_SEARCH     45.2ms     10 results                     │
│   CALL db.index.vector.queryNodes('skill_embedding_idx'...      │
│   Source: vector_search_skills                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                       (Repeat for each query)
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Final Response Returned to User                                 │
│ QueryProcessingView Shows Summary:                              │
│   Total Time: 180.7ms                                           │
│   Success Rate: 100%                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Visual Design

### Panel Header (Collapsible)
```
┌──────────────────────────────────────────────────────────────┐
│ 🗄️● Query Processing               3 queries executed    ▼   │
└──────────────────────────────────────────────────────────────┘
     ↑                                                       ↑
Green pulsing dot = WebSocket connected              Expand/collapse
```

### Query Entry (Expanded)
```
┌──────────────────────────────────────────────────────────────┐
│ ✓ | VECTOR_SEARCH     45.2ms     10 results                   │
│   | CALL db.index.vector.queryNodes('skill_embedding_idx'...  │
│   | Source: vector_search_skills                              │
└──────────────────────────────────────────────────────────────┘
```

### Summary Footer
```
┌──────────────────────────────────────────────────────────────┐
│ Total Time: 180.7ms             Success Rate: 100%           │
└──────────────────────────────────────────────────────────────┘
```

---

## Color Scheme

### Query Type Badges
- **READ**: Blue (`text-blue-600 bg-blue-50`)
- **WRITE**: Purple (`text-purple-600 bg-purple-50`)
- **VECTOR_SEARCH**: Pink (`text-pink-600 bg-pink-50`)
- **GRAPH_TRAVERSAL**: Indigo (`text-indigo-600 bg-indigo-50`)
- **OTHER**: Slate (`text-slate-600 bg-slate-50`)

### Status Icons
- **Success**: ✓ Green (`text-green-600`)
- **Failure**: ✗ Red (`text-red-600`)

### Live Connection
- **Connected**: 🟢 Green pulsing animation
- **Disconnected**: 🔴 Gray (attempts reconnect after 3s)

---

## Performance Considerations

### WebSocket Efficiency
- **Single connection** shared for entire chat session
- **Filtered client-side** by session_id (no backend filtering needed)
- **Auto-cleanup** when component unmounts
- **Keep-alive pings** every 30 seconds

### Memory Management
- Queries stored **per session** (not global)
- Old queries cleared when new query starts
- Maximum 50 queries cached in `QueryProcessingView`

### Network Usage
- **~100 bytes per query log** (compressed JSON)
- **Minimal overhead** for typical chat session (3-10 queries)
- **No polling** required (pure push via WebSocket)

---

## User Benefits

### 1. **Transparency**
Users see exactly what the system is doing:
- "Why is it taking so long?" → See complex graph traversal executing
- "What data is it using?" → See vector search pulling relevant skills
- "Is it working?" → See queries executing in real-time

### 2. **Education**
Power users learn how RAG works:
- See the sequence: Vector search → Graph traversal → LLM generation
- Understand query complexity (simple vs multi-hop)
- Learn about database query types

### 3. **Trust**
Builds confidence in the system:
- No black box - everything is visible
- See data sources being queried
- Verify system is actually working (not frozen)

### 4. **Debugging**
Helps identify issues:
- Slow queries highlighted
- Failed queries shown with error status
- Source identification for troubleshooting

---

## Future Enhancements

### Planned
- [ ] **Query explain plans** - Show Neo4j execution plan on hover
- [ ] **Performance tips** - Suggest optimizations for slow queries
- [ ] **Query replay** - Re-run specific queries from history
- [ ] **Export logs** - Download query logs for analysis
- [ ] **Dark mode** - Theme for query processing panel

### Ideas
- [ ] **Visual graph** - Show nodes/relationships being queried
- [ ] **Cost estimation** - Show compute cost per query
- [ ] **Cache hits** - Highlight queries served from cache
- [ ] **Parallel execution** - Show concurrent queries with threading

---

## Configuration

### Enable/Disable Feature
```javascript
// In QueryProcessingView.jsx
const ENABLE_MONITORING = true;  // Set to false to disable

// Or via environment variable
const ENABLE_MONITORING = import.meta.env.VITE_ENABLE_QUERY_MONITORING !== 'false';
```

### Adjust WebSocket URL
```javascript
// In QueryProcessingView.jsx
const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://127.0.0.1:8000'}/monitor/live`;
```

### Backend Session Tracking
```python
# In backend .env
NEO4J_MONITORING_ENABLED=true  # Must be enabled for this feature
```

---

## Troubleshooting

### Queries Not Appearing

**Symptom**: Panel shows "Waiting for queries..." but queries are executing.

**Causes**:
1. Session ID mismatch
2. WebSocket not connected
3. Backend monitoring disabled

**Solutions**:
1. Check browser console for `sessionId` being sent
2. Verify WebSocket connection (green dot in panel header)
3. Check backend: `NEO4J_MONITORING_ENABLED=true`
4. Ensure agents pass `session_id` to Neo4j queries

### WebSocket Keeps Disconnecting

**Symptom**: Green dot turns gray, reconnects repeatedly.

**Solutions**:
1. Check backend is running: `curl http://127.0.0.1:8000/health`
2. Verify CORS allows WebSocket connections
3. Check firewall/proxy not blocking WS connections
4. Review backend logs for connection errors

### Queries from Other Sessions Appearing

**Symptom**: Seeing queries that don't match current chat message.

**Solutions**:
1. Clear browser cache and reload
2. Verify `session_id` is unique per query
3. Check filtering logic in `QueryProcessingView.jsx`:
   ```javascript
   if (queryLog.session_id === sessionId) {
       setQueries(prev => [...prev, queryLog]);
   }
   ```

---

## Testing

### Manual Testing Checklist
- [x] Submit query → Panel appears
- [x] Queries appear in real-time as they execute
- [x] Query types color-coded correctly
- [x] Execution times displayed
- [x] Summary shows total time and success rate
- [x] Panel collapsible/expandable
- [x] WebSocket reconnects on disconnect
- [x] Next query clears previous queries
- [x] No queries from other users' sessions

### Test Queries
```
Simple (1-2 queries):
"What is Python?"

Medium (3-5 queries):
"What skills do I need for data science?"

Complex (5-10 queries):
"Find me machine learning jobs at tech companies that require Python and pay over $100k"
```

---

## Analytics Opportunities

With session-based tracking, you can now:

1. **Analyze query patterns** per user conversation
2. **Measure workflow efficiency** (which agents execute which queries)
3. **Identify bottlenecks** (which queries consistently slow)
4. **A/B test workflows** (compare query sequences)
5. **Audit user sessions** (full query trail for support tickets)

---

**Built with ❤️ for transparency and user trust**
