# Rollback Strategy

1. **Query Pipeline**: Network enrichment node is additive - remove from workflow to rollback
2. **Neo4j Schema**: New properties are additive - safe to ignore
3. **SIMILAR_JOB relationships**: Delete with `MATCH ()-[r:SIMILAR_JOB]->() DELETE r`
4. **Frontend**: Remove NetworkInsightsPanel import to rollback
5. **Ingestion**: Disable auto-enrichment flag in config

---

*Generated: 2025-12-06*
*Version: 1.0*
*Status: DRAFT - Awaiting Approval*
