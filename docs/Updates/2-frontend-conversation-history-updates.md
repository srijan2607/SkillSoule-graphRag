# Frontend Updates Required - Conversation History Support

## Overview

The backend now supports conversation history with follow-up questions. This document outlines all frontend changes needed to implement the conversational chat experience.

## What's New in Backend

✅ Backend now accepts optional `session_id` in query requests
✅ Backend retrieves last 5 messages when `session_id` is provided
✅ LLM understands conversation context for follow-up questions
✅ Fully backward compatible - works with or without `session_id`

## Required Frontend Changes

### 1. State Management

#### Add Session State
```typescript
// In your Chat component or context
const [sessionId, setSessionId] = useState<string | null>(null);
const [conversationMessages, setConversationMessages] = useState<Message[]>([]);
```

#### Message Interface
```typescript
interface Message {
  id: string;
  query: string;
  response: string;
  sources?: SourceNode[];
  metadata?: any;
  timestamp: string;
  isLoading?: boolean;
  error?: string;
}

interface SourceNode {
  node_type: string;
  node_id: string;
  properties: Record<string, any>;
}
```

### 2. API Request Changes

#### UPDATE: Query API Call

**Before (current implementation):**
```typescript
const response = await fetch('/api/query/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: userInput
  })
});
```

**After (with conversation support):**
```typescript
const response = await fetch('/api/query/ask', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    query: userInput,
    session_id: sessionId  // Include if exists (follow-up query)
  })
});

const data = await response.json();

// Store session_id on first message if new conversation
if (!sessionId && conversationMessages.length === 0) {
  // Generate and store session_id for future queries
  const newSessionId = crypto.randomUUID();
  setSessionId(newSessionId);
}
```

### 3. UI Components to Add

#### A. "New Chat" Button

Add a button to start a fresh conversation:

```tsx
// In Chat header or sidebar
<button
  onClick={() => {
    setSessionId(null);
    setConversationMessages([]);
  }}
  className="btn-new-chat"
>
  <PlusIcon />
  New Conversation
</button>
```

**When to Show:**
- Always visible in chat interface
- Optionally show in sidebar for conversation list

#### B. Conversation Indicator

Show active conversation status:

```tsx
// In Chat header
{sessionId && conversationMessages.length > 0 && (
  <div className="conversation-indicator">
    <div className="indicator-dot"></div>
    <span>Ongoing conversation ({conversationMessages.length} messages)</span>
    <button
      onClick={() => {
        setSessionId(null);
        setConversationMessages([]);
      }}
      className="btn-end-conversation"
    >
      End & Start New
    </button>
  </div>
)}
```

#### C. Input Placeholder Updates

Update placeholder based on conversation state:

```tsx
<input
  type="text"
  placeholder={
    conversationMessages.length === 0
      ? "Ask me anything about careers, skills, or jobs..."
      : "Ask a follow-up question..."
  }
  value={currentInput}
  onChange={(e) => setCurrentInput(e.target.value)}
/>
```

### 4. Complete Chat Component Example

```tsx
import React, { useState } from 'react';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  query: string;
  response: string;
  sources?: any[];
  timestamp: string;
  isLoading?: boolean;
  error?: string;
}

const ChatInterface: React.FC = () => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentInput.trim() || isLoading) return;

    const userQuery = currentInput;
    setCurrentInput('');

    // Add user message with loading state
    const tempMessage: Message = {
      id: uuidv4(),
      query: userQuery,
      response: '',
      timestamp: new Date().toISOString(),
      isLoading: true
    };

    setMessages([...messages, tempMessage]);
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');

      const response = await fetch('/api/query/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: userQuery,
          session_id: sessionId  // Include if exists
        })
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();

      // Generate session_id on first message
      if (!sessionId && messages.length === 0) {
        const newSessionId = crypto.randomUUID();
        setSessionId(newSessionId);
      }

      // Update message with actual response
      setMessages(prev => prev.map(msg =>
        msg.id === tempMessage.id
          ? {
              ...msg,
              response: data.response,
              sources: data.sources,
              isLoading: false
            }
          : msg
      ));

    } catch (error) {
      console.error('Query failed:', error);

      // Update message with error
      setMessages(prev => prev.map(msg =>
        msg.id === tempMessage.id
          ? {
              ...msg,
              error: 'Failed to get response. Please try again.',
              isLoading: false
            }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  const startNewConversation = () => {
    setSessionId(null);
    setMessages([]);
    setCurrentInput('');
  };

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="header-left">
          <h2>Career Assistant</h2>
          {sessionId && messages.length > 0 && (
            <span className="conversation-badge">
              {messages.length} messages
            </span>
          )}
        </div>
        <div className="header-right">
          {messages.length > 0 && (
            <button
              onClick={startNewConversation}
              className="btn-new-chat"
            >
              New Conversation
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <h3>Start a conversation</h3>
            <p>Ask me anything about careers, skills, or the job market!</p>
            <div className="example-queries">
              <p>Try asking:</p>
              <button onClick={() => setCurrentInput("What skills do I need for data science?")}>
                What skills do I need for data science?
              </button>
              <button onClick={() => setCurrentInput("Which frameworks are popular for web development?")}>
                Which frameworks are popular?
              </button>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="message-group">
              {/* User Query */}
              <div className="message user-message">
                <div className="message-content">{message.query}</div>
                <div className="message-timestamp">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>

              {/* Assistant Response */}
              <div className="message assistant-message">
                {message.isLoading ? (
                  <div className="loading-indicator">
                    <div className="spinner"></div>
                    <span>Thinking...</span>
                  </div>
                ) : message.error ? (
                  <div className="error-message">
                    <span className="error-icon">⚠️</span>
                    {message.error}
                  </div>
                ) : (
                  <>
                    <div className="message-content">
                      {/* Render markdown response */}
                      <ReactMarkdown>{message.response}</ReactMarkdown>
                    </div>
                    {message.sources && message.sources.length > 0 && (
                      <div className="sources">
                        <details>
                          <summary>
                            📚 {message.sources.length} sources
                          </summary>
                          <ul>
                            {message.sources.slice(0, 5).map((source, idx) => (
                              <li key={idx}>
                                {source.node_type}: {source.node_id}
                              </li>
                            ))}
                          </ul>
                        </details>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="chat-input-form">
        <input
          type="text"
          value={currentInput}
          onChange={(e) => setCurrentInput(e.target.value)}
          placeholder={
            messages.length === 0
              ? "Ask me anything about careers, skills, or jobs..."
              : "Ask a follow-up question..."
          }
          disabled={isLoading}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={!currentInput.trim() || isLoading}
          className="btn-send"
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
};

export default ChatInterface;
```

### 5. Styling Recommendations

```css
/* Chat Container */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 1200px;
  margin: 0 auto;
}

/* Header */
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}

.conversation-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #3b82f6;
  color: white;
  border-radius: 9999px;
  font-size: 0.875rem;
  margin-left: 1rem;
}

.btn-new-chat {
  padding: 0.5rem 1rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-new-chat:hover {
  background: #e5e7eb;
}

/* Messages */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  background: #f9fafb;
}

.message-group {
  margin-bottom: 2rem;
}

.message {
  max-width: 80%;
  padding: 1rem 1.5rem;
  border-radius: 1rem;
  margin-bottom: 0.5rem;
}

.user-message {
  margin-left: auto;
  background: #3b82f6;
  color: white;
  border-bottom-right-radius: 0.25rem;
}

.assistant-message {
  background: white;
  border: 1px solid #e5e7eb;
  border-bottom-left-radius: 0.25rem;
}

/* Loading State */
.loading-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Input Form */
.chat-input-form {
  display: flex;
  gap: 1rem;
  padding: 1.5rem 2rem;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.chat-input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 1rem;
}

.chat-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.btn-send {
  padding: 0.75rem 2rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-send:hover:not(:disabled) {
  background: #2563eb;
}

.btn-send:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-state h3 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
  color: #111827;
}

.empty-state p {
  color: #6b7280;
  margin-bottom: 2rem;
}

.example-queries {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.example-queries button {
  padding: 0.75rem 1.5rem;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  max-width: 500px;
}

.example-queries button:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

/* Sources */
.sources {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.sources details {
  cursor: pointer;
}

.sources summary {
  font-weight: 500;
  color: #6b7280;
  user-select: none;
}

.sources ul {
  margin-top: 0.5rem;
  padding-left: 1.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}
```

### 6. User Experience Flows

#### Flow 1: New Conversation
```
1. User arrives at chat page
2. Input placeholder: "Ask me anything about careers..."
3. User types: "What skills do I need for data science?"
4. Frontend generates session_id (crypto.randomUUID())
5. POST /api/query/ask with { query, session_id }
6. Response displayed
7. Input placeholder changes to: "Ask a follow-up question..."
```

#### Flow 2: Follow-up Questions
```
1. User in active conversation (has session_id)
2. User types: "What about salaries?"
3. POST /api/query/ask with { query, session_id: SAME_ID }
4. Backend retrieves last 5 messages
5. LLM understands "salaries" refers to data science
6. Contextual response displayed
```

#### Flow 3: New Conversation
```
1. User clicks "New Conversation" button
2. Clear session_id (setSessionId(null))
3. Clear messages (setMessages([]))
4. Input placeholder resets to: "Ask me anything..."
5. Next query starts fresh conversation
```

### 7. Optional Enhancements

#### A. Conversation List (Sidebar)

```tsx
// Store multiple conversations
const [conversations, setConversations] = useState<{
  [sessionId: string]: Message[]
}>({});

const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

// Sidebar component
<div className="conversations-sidebar">
  <h3>Conversations</h3>
  {Object.entries(conversations).map(([sessionId, messages]) => (
    <div
      key={sessionId}
      onClick={() => setActiveSessionId(sessionId)}
      className={`conversation-item ${
        activeSessionId === sessionId ? 'active' : ''
      }`}
    >
      <div className="conversation-preview">
        {messages[0]?.query.slice(0, 40)}...
      </div>
      <div className="conversation-meta">
        {messages.length} messages
      </div>
    </div>
  ))}
</div>
```

#### B. Export Conversation

```tsx
const exportConversation = () => {
  const conversationText = messages
    .map(msg => `User: ${msg.query}\n\nAssistant: ${msg.response}\n\n---\n`)
    .join('\n');

  const blob = new Blob([conversationText], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `conversation-${sessionId}.txt`;
  a.click();
};
```

#### C. Share Conversation

```tsx
const shareConversation = async () => {
  const shareUrl = `${window.location.origin}/chat/${sessionId}`;

  if (navigator.share) {
    await navigator.share({
      title: 'Career Chat Conversation',
      url: shareUrl
    });
  } else {
    navigator.clipboard.writeText(shareUrl);
    // Show "Link copied!" toast
  }
};
```

### 8. Testing Checklist

#### Manual Testing

- [ ] First query creates new session (no session_id sent)
- [ ] Follow-up query includes session_id
- [ ] "New Conversation" button clears session
- [ ] Placeholder text changes based on conversation state
- [ ] Messages display correctly in chronological order
- [ ] Loading state shows while waiting for response
- [ ] Error handling works (show error message)
- [ ] Sources display correctly (if present)
- [ ] Markdown rendering works in responses
- [ ] Mobile responsive layout

#### API Integration Testing

- [ ] POST /api/query/ask without session_id works
- [ ] POST /api/query/ask with session_id works
- [ ] Response includes all expected fields
- [ ] Session persistence across multiple queries
- [ ] Error responses handled gracefully

### 9. Dependencies to Install

```bash
# If not already installed
npm install uuid
npm install react-markdown  # For markdown rendering

# Types
npm install --save-dev @types/uuid
```

### 10. Environment Variables

No new environment variables needed - uses existing `VITE_API_URL`.

## Summary of Changes

### Files to Modify:
1. **Chat Component** (e.g., `src/pages/Chat.tsx` or `src/components/ChatInterface.tsx`)
   - Add session state management
   - Update API call to include session_id
   - Add "New Conversation" button
   - Update input placeholder based on state

2. **API Service** (e.g., `src/utils/api.ts`)
   - Update query function signature to accept optional session_id

3. **Types** (e.g., `src/types/index.ts`)
   - Add Message interface
   - Update QueryRequest to include session_id

### New Features:
- ✅ Session-based conversation tracking
- ✅ Follow-up question support
- ✅ Conversation continuity indicator
- ✅ "New Conversation" functionality
- ✅ Context-aware input placeholders

### Backward Compatibility:
✅ All changes are additive - existing functionality continues to work
✅ session_id is optional - queries work with or without it

---

**Priority**: High
**Effort**: 4-6 hours
**Impact**: Significantly improved user experience with natural conversations

**Questions?** Refer to `conversation-history-implementation.md` for backend details.
