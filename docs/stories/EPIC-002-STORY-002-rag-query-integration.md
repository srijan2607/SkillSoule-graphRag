# Story: RAG Query Integration & Response Handling

**Story ID**: EPIC-002-STORY-002  
**Epic**: Epic 2 - Chat Interface & RAG Integration  
**Priority**: High  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-002-STORY-001 (Chat UI Foundation)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** to send questions to the AI and receive intelligent answers,  
**So that** I can get career insights powered by the knowledge graph.

---

## Acceptance Criteria

### Functional Requirements

1. **Query Submission**
   - On send button click or Enter key → POST query to `/query` endpoint
   - Include JWT token in Authorization header: `Bearer {token}`
   - Request body: `{query: "user's question text"}`
   - Disable input field during query processing
   - Disable send button during query processing

2. **Typing Indicator**
   - Show animated typing indicator (three dots) while waiting for LLM response
   - Typing indicator appears as assistant message bubble
   - Animation: three dots pulsing sequentially (800ms loop, 160ms stagger)
   - Remove typing indicator when response received

3. **Response Display**
   - Parse response: `{answer: string, sources: []}`
   - Display `answer` as assistant message bubble
   - Add assistant message to conversation state
   - Auto-scroll to show response

4. **Timeout Handling**
   - Set 10-second timeout for API request
   - If timeout → remove typing indicator, show error message
   - Error message: "Request timed out. The question might be too complex. Please try rephrasing or try again."
   - Show "Retry" button in error message

5. **API Error Handling**
   - Handle 400 error: Show "Invalid query. Please try rephrasing your question."
   - Handle 401 error: Logout user, redirect to login (handled by global interceptor)
   - Handle 500 error: Show "Sorry, something went wrong. Please try again."
   - Handle network error: Show "Unable to connect. Please check your internet connection."
   - All errors displayed as system messages (centered, orange background)

6. **Multiple Rapid Queries**
   - Disable input while query is in progress
   - If user tries to send while processing → show tooltip: "Please wait for current response"
   - Queue management not needed for MVP (one query at a time)

### Integration Requirements

7. **API Integration**
   - Endpoint: POST `${API_BASE_URL}/query`
   - Headers: `{ 'Content-Type': 'application/json', 'Authorization': 'Bearer {token}' }`
   - Request: `{ query: string }`
   - Response: `{ answer: string, sources: [{type, id, name, metadata}] }`
   - Store sources in message object for display in EPIC-002-STORY-003

8. **Loading State Management**
   - `isLoading` state tracks query in progress
   - Input field disabled when `isLoading === true`
   - Send button shows spinner when `isLoading === true`

### Quality Requirements

9. **User Experience**
   - Response time goal: <5 seconds for typical queries
   - Typing indicator provides clear feedback (user knows system is working)
   - Error messages are user-friendly (no technical jargon)
   - Retry option available for all errors

10. **Error Recovery**
    - User can retry after any error
    - Retry button sends same query again
    - Failed queries remain in message history (marked as errors)

---

## Technical Notes

### API Service

```javascript
const queryRAG = async (query, token) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
  
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ query }),
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Query failed');
    }
    
    return await response.json(); // { answer, sources }
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Request timed out');
    }
    throw err;
  }
};
```

### Message Handling

```javascript
const handleSend = async (text) => {
  // Add user message
  const userMessage = { id: Date.now(), role: 'user', content: text };
  setMessages(prev => [...prev, userMessage]);
  
  // Show typing indicator
  setIsLoading(true);
  
  try {
    const { answer, sources } = await queryRAG(text, token);
    
    // Add assistant response
    const assistantMessage = {
      id: Date.now() + 1,
      role: 'assistant',
      content: answer,
      sources: sources
    };
    setMessages(prev => [...prev, assistantMessage]);
  } catch (err) {
    // Add error message
    const errorMessage = {
      id: Date.now() + 1,
      role: 'error',
      content: err.message
    };
    setMessages(prev => [...prev, errorMessage]);
  } finally {
    setIsLoading(false);
  }
};
```

---

## Definition of Done

- [x] Query sent to POST `/query` endpoint with JWT token
- [x] Typing indicator displays while waiting for response
- [x] Response parsed and displayed as assistant message
- [x] 10-second timeout implemented with error message
- [x] API errors handled (400, 401, 500, network)
- [x] Input disabled during query processing
- [x] Send button shows loading spinner during query
- [x] Retry button works for failed queries
- [x] Error messages user-friendly
- [x] Response time <5s for typical queries (measured in testing)

---

## Dependencies

- EPIC-002-STORY-001 (Chat UI Foundation)
- Backend POST `/query` endpoint deployed
- JWT token available from AuthContext

---

**Story Status**: ✅ Ready for Development
