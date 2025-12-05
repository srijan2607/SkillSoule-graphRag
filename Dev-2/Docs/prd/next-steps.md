# Next Steps

## UX Expert Consultation (Post-MVP)

**Prompt:**
> We've built a research-driven Career Intelligence AI System with network metrics (centrality, closeness, TransitionIndex). The system displays metric values in chat responses with inline badges. As a UX expert, review our interface design and recommend improvements for:
> 1. Metric visualization clarity (are badges intuitive or overwhelming?)
> 2. User comprehension of research concepts (how to explain centrality without jargon?)
> 3. Mobile responsiveness (metric badges on small screens)
> 4. Optional dashboard features (skill graph visualization, career roadmap planner)

## Architect Review (Post-MVP)

**Prompt:**
> We've implemented a skill-centric Neo4j graph with GDS centrality algorithms and enhanced LangGraph pipeline. As a system architect, review our implementation and recommend optimizations for:
> 1. Neo4j free tier performance (approaching 50K nodes, 175K relationships limit)
> 2. Centrality calculation frequency (currently on every CSV ingestion - too aggressive?)
> 3. Caching strategy (should we cache closeness results or recalculate per query?)
> 4. Scalability path to paid tier (what breaks first at 100K skills, 500K jobs?)

## Research Validation Next Steps (Phase 2)

1. **Collect expert evaluations**: Recruit 10 career counselors + hiring managers for validation studies
2. **Run A/B test**: Onboard 50 beta users, split into job-centric vs skill-centric groups
3. **Analyze correlation**: Compute Pearson coefficient for closeness vs expert ratings
4. **Publish results**: Write research paper or blog post on validation outcomes
5. **Refine algorithms**: Use validation feedback to adjust TransitionIndex weights, centrality thresholds

---

**End of PRD v2.0**

---
