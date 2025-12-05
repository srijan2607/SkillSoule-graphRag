# Story 3.5: Frontend Metric Display - Inline Citations

**Epic:** Epic 3 - Advanced Query Intelligence
**Story ID:** 3.5
**Estimated Effort:** 2-3 days

## User Story
**As a** user,
**I want** to see metric values displayed with visual indicators,
**so that** I can quickly identify high-leverage skills.

## Acceptance Criteria
1. ChatMessage component modified to parse and render metrics
2. MetricBadge component: color-coded (green >0.7, yellow 0.4-0.7, red <0.4), hover tooltip
3. Skill path visualization (optional, expandable)
4. Copy-to-clipboard on badge click

## Integration Verification
**IV1:** v1.1 messages without metrics still render correctly
**IV2:** 10 responses with metrics parse correctly
**IV3:** MetricBadge WCAG 2.1 AA compliant

## Dependencies
**Depends on:** Story 3.4
**Blocks:** Story 3.6

---

## Technical Implementation

### Components

**Primary Component:** `ChatMessage` (ENHANCED v2.0)
- **Location:** `frontend/src/components/chat/ChatMessage.tsx`
- **Method:** Enhanced to parse and render metrics

**New Component:** `MetricBadge` (NEW v2.0)
- **Location:** `frontend/src/components/metrics/MetricBadge.tsx`
- **Features:** Color-coded badges, hover tooltips, copy-to-clipboard

**Optional Component:** `SkillPathVisualization` (NEW v2.0)
- **Location:** `frontend/src/components/metrics/SkillPathVisualization.tsx`
- **Features:** D3.js skill path diagram (expandable)

### Metric Badge Component

From `source-tree.md`:

```tsx
interface MetricBadgeProps {
  label: string;
  value: number;
  type: 'centrality' | 'closeness' | 'transition_index';
}

export function MetricBadge({ label, value, type }: MetricBadgeProps) {
  // Color coding
  const getColor = (value: number) => {
    if (value > 0.7) return 'bg-green-100 text-green-800'; // High
    if (value > 0.4) return 'bg-yellow-100 text-yellow-800'; // Moderate
    return 'bg-red-100 text-red-800'; // Low
  };

  // Tooltip text
  const getTooltip = (type: string, value: number) => {
    switch (type) {
      case 'centrality':
        return `Centrality: ${value.toFixed(2)} - Measures skill importance in job market network`;
      case 'closeness':
        return `Closeness: ${value.toFixed(2)} - Measures skill similarity (1.0 = highly related)`;
      case 'transition_index':
        return `Transition Index: ${value.toFixed(2)} - Transition difficulty (1.0 = easy, 0.0 = hard)`;
    }
  };

  // Copy to clipboard
  const handleClick = () => {
    navigator.clipboard.writeText(`${label}: ${value.toFixed(2)}`);
    toast.success('Copied to clipboard!');
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium cursor-pointer ${getColor(value)}`}
      title={getTooltip(type, value)}
      onClick={handleClick}
    >
      {label}: {value.toFixed(2)}
    </span>
  );
}
```

### Testing

**Unit Test:** `frontend/src/components/metrics/MetricBadge.test.tsx`
- Test color coding (green >0.7, yellow 0.4-0.7, red <0.4)
- Validate tooltip text
- Test copy-to-clipboard functionality

**Integration Test:** `tests/integration/test_frontend_metrics.tsx`
- Render 10 responses with metrics
- Verify v1.1 messages without metrics render correctly
- Test WCAG 2.1 AA compliance (color contrast, keyboard navigation)

### Performance Targets

- **Render Time:** <50ms per metric badge
- **Accessibility:** WCAG 2.1 AA compliant (4.5:1 contrast ratio)
- **Responsive:** Works on mobile, tablet, desktop

### Security Considerations

From `security.md`:
- **XSS Prevention:** Sanitize metric values before rendering
- **Clipboard Permissions:** Request clipboard access permission
- **WCAG Compliance:** Ensure color-coded badges have text labels (not color-only)
