# Story: Chat UI Foundation (Layout, Messages, Input)

**Story ID**: EPIC-002-STORY-001  
**Epic**: Epic 2 - Chat Interface & RAG Integration  
**Priority**: High  
**Estimated Effort**: 2-3 days  
**Dependencies**: EPIC-001 (Authentication & Core Layout)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** a clean chat interface where I can type messages and see conversation history,  
**So that** I can interact with the AI career assistant naturally.

---

## Acceptance Criteria

### Functional Requirements

1. **Chat Screen Layout**
   - Full-screen layout with message thread area (top 85%) and fixed input area (bottom 15%)
   - Message thread scrollable vertically
   - Input area fixed at bottom (doesn't scroll with messages)
   - Empty state: "Ask me anything about careers, skills, and jobs!" (centered, gray text)

2. **Message Bubbles**
   - User messages: right-aligned, blue background (#2563EB), white text, max-width 70%
   - Assistant messages: left-aligned, gray background (#F3F4F6), dark text, max-width 70%
   - Message bubbles have rounded corners (12-16px radius)
   - Padding: 12-16px inside bubbles
   - Adequate spacing between messages (12px vertical gap)

3. **Input Field**
   - Textarea input (multiline support)
   - Placeholder: "Type your question..."
   - Send button (paper airplane icon or "Send" text)
   - Input expands vertically up to 5 lines (auto-resize)
   - Enter key sends message, Shift+Enter adds new line

4. **Message State Management**
   - Add user message to state immediately after send
   - Display user message in chat thread
   - Message state stored in React state (array of message objects)
   - Each message: `{id, role: 'user'|'assistant', content, timestamp}`

5. **Auto-scroll**
   - Automatically scroll to bottom when new message added
   - Smooth scroll animation (400ms)
   - If user scrolled up manually, show "New message ▼" button to scroll to bottom

### Integration Requirements

6. **Responsive Design**
   - Mobile (<640px): Full-screen chat, input spans full width
   - Tablet (640px-1024px): Centered chat area, max-width 800px
   - Desktop (≥1024px): Centered chat area, max-width 900px
   - Message bubbles adapt to screen width (always max 70% of container)

7. **Navigation Integration**
   - Chat screen accessible at `/chat` route (protected)
   - Top navigation bar persists (from EPIC-001-STORY-002)
   - "Chat" link in nav bar highlighted when on `/chat`

### Quality Requirements

8. **Accessibility**
   - Textarea has label (can be visually hidden)
   - Send button has aria-label: "Send message"
   - Message thread has role="log" for screen readers
   - Keyboard navigation: Tab to textarea, Tab to send button, Enter sends

9. **Performance**
   - Render up to 50 messages efficiently (no virtual scrolling needed for MVP)
   - Smooth scrolling (no jank during auto-scroll)
   - Input field responsive (no lag while typing)

10. **Code Quality**
    - Separate components: ChatScreen, MessageBubble, ChatInput
    - Message state in parent component (ChatScreen)
    - Clean component separation (presentation vs logic)

---

## Technical Notes

### Component Structure

```
src/
├── screens/
│   └── ChatScreen.jsx         # Main chat screen
├── components/
│   ├── MessageBubble.jsx      # Individual message bubble
│   ├── ChatInput.jsx          # Input field + send button
│   ├── ChatThread.jsx         # Scrollable message container
│   └── TypingIndicator.jsx    # Animated dots (for next story)
```

### Message State Example

```javascript
const [messages, setMessages] = useState([]);

const handleSend = (text) => {
  const userMessage = {
    id: Date.now(),
    role: 'user',
    content: text,
    timestamp: new Date()
  };
  
  setMessages(prev => [...prev, userMessage]);
  
  // API call to RAG endpoint happens in EPIC-002-STORY-002
};
```

---

## Definition of Done

- [x] Chat screen layout renders correctly
- [x] User messages display right-aligned with blue background
- [x] Assistant messages display left-aligned with gray background
- [x] Input field accepts text, expands to 5 lines max
- [x] Send button sends message (adds to state, displays in thread)
- [x] Enter key sends message, Shift+Enter adds new line
- [x] Auto-scroll to bottom on new message
- [x] Empty state displays when no messages
- [x] Responsive design tested (mobile, tablet, desktop)
- [x] Keyboard navigation works
- [x] Screen reader tested

---

## Dependencies

- EPIC-001-STORY-002 (Application Shell with Navigation)
- React Router configured

---

**Story Status**: ✅ Ready for Development
