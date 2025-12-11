# Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GDS not installed | Medium | High | Fall back to stored centrality, skip path visualization |
| Large graph performance | Medium | Medium | Use LIMIT, cap enrichment to 50 nodes |
| Breaking existing queries | Low | High | Keep old intents working, network enrichment is additive |
| Frontend bundle size | Low | Low | Lazy load NetworkInsightsPanel |

---
