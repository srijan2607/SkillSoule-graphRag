# Story: Source Citations & Chat Management

**Story ID**: EPIC-002-STORY-003  
**Epic**: Epic 2 - Chat Interface & RAG Integration  
**Priority**: Medium  
**Estimated Effort**: 1-2 days  
**Dependencies**: EPIC-002-STORY-002 (RAG Query Integration)  
**Status**: Ready for Development

---

## User Story

**As an** authenticated user,  
**I want** to see which graph nodes informed the AI's answer and manage my conversation,  
**So that** I can verify sources and start fresh conversations when needed.

---

## Acceptance Criteria

### Functional Requirements

1. **Source Citations Display**
   - Below each assistant message, show expandable "Sources" section
   - Collapsed state: "Based on 5 jobs, 3 skills, 2 companies" (clickable)
   - Expanded state: List of source nodes with metadata
   - Each source: Type icon + Name + brief metadata
   - Example: "🏢 Google | Company | Tech Industry"

2. **Source Expansion/Collapse**
   - Click "Sources" summary → expands to show full list
   - Click again → collapses back to summary
   - Chevron icon rotates to indicate state (▼ collapsed, ▲ expanded)
   - Expansion smooth (200-300ms animation)

3. **Source Details**
   - Each source shows: Icon, Type, Name, Key metadata
   - Job sources: Job title, Company, Location (if available)
   - Skill sources: Skill name, Category, Subcategory
   - Company sources: Company name, Industry
   - Limit displayed sources to 10, show "...and 5 more" if >10

4. **Clear Chat Functionality**
   - "Clear Chat" button in top-right of chat area
   - Click → show confirmation dialog: "Clear conversation history?"
   - Confirm → clear all messages from state, show empty state
   - Cancel → close dialog, no action
   - Cleared conversation cannot be recovered (no undo)

5. **No Results Handling**
   - If API returns empty sources array → show "No specific sources (general knowledge)"
   - If answer is: "I don't have information..." → no sources shown

### Integration Requirements

6. **Source Data Format**
   - Sources from API: `[{type: 'job'|'skill'|'company', id, name, metadata: {}}]`
   - Parse and display based on type
   - Handle missing metadata gracefully (show "N/A" for missing fields)

7. **State Management**
   - Source expansion state stored per message (not global)
   - Each message object: `{..., sourcesExpanded: boolean}`
   - Clear chat resets message array to `[]`

### Quality Requirements

8. **User Experience**
   - Source expansion feels responsive (no delay)
   - Clear chat confirmation prevents accidental data loss
   - Sources easy to scan (clear icons, formatting)

9. **Accessibility**
   - Sources section keyboard accessible (Tab, Enter to expand/collapse)
   - Clear chat confirmation dialog keyboard accessible (ESC to cancel, Enter to confirm)
   - Screen reader announces source count and expansion state

10. **Performance**
    - Rendering 10+ sources doesn't cause lag
    - Expansion animation smooth (60 FPS)

---

## Technical Notes

### Source Citation Component

```javascript
const SourceCitation = ({ sources }) => {
  const [expanded, setExpanded] = useState(false);
  
  if (!sources || sources.length === 0) return null;
  
  const summary = `Based on ${sources.filter(s => s.type === 'job').length} jobs, 
                   ${sources.filter(s => s.type === 'skill').length} skills, 
                   ${sources.filter(s => s.type === 'company').length} companies`;
  
  return (
    <div className="mt-2">
      <button onClick={() => setExpanded(!expanded)} className="text-sm text-gray-600">
        {expanded ? '▲' : '▼'} Sources: {summary}
      </button>
      {expanded && (
        <div className="mt-2 space-y-1">
          {sources.slice(0, 10).map(source => (
            <SourceItem key={source.id} source={source} />
          ))}
          {sources.length > 10 && <div className="text-xs text-gray-500">...and {sources.length - 10} more</div>}
        </div>
      )}
    </div>
  );
};
```

### Clear Chat Dialog

```javascript
const ClearChatDialog = ({ isOpen, onConfirm, onCancel }) => (
  <Dialog open={isOpen} onClose={onCancel}>
    <Dialog.Panel>
      <Dialog.Title>Clear conversation history?</Dialog.Title>
      <Dialog.Description>
        This will remove all messages. This action cannot be undone.
      </Dialog.Description>
      <div className="mt-4 flex gap-2">
        <Button onClick={onConfirm} variant="danger">Clear</Button>
        <Button onClick={onCancel} variant="secondary">Cancel</Button>
      </div>
    </Dialog.Panel>
  </Dialog>
);
```

---

## Definition of Done

- [x] Source citations display below assistant messages
- [x] Summary shows count by type (jobs, skills, companies)
- [x] Click sources → expands to show list
- [x] Each source shows icon, type, name, metadata
- [x] Limit to 10 sources, show "...and X more" if needed
- [x] Clear chat button shows confirmation dialog
- [x] Confirm → clears all messages, shows empty state
- [x] Cancel → closes dialog, no action
- [x] Keyboard navigation works
- [x] Screen reader tested

---

## Dependencies

- EPIC-002-STORY-002 (RAG Query Integration with sources data)
- Headless UI Dialog component

---

**Story Status**: ✅ Ready for Development
