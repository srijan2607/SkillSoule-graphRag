# Files to Create/Modify

## New Files
| File | Purpose |
|------|---------|
| `backend/app/services/skill_normalizer.py` | Skill name canonicalization (with display names) |
| `backend/app/services/co_occurrence_builder.py` | CO_OCCURS_WITH edge builder (with stoplist) |
| `backend/app/services/job_similarity_builder.py` | SIMILAR_JOB via GDS nodeSimilarity |
| `backend/app/agents/nodes/network_enrichment.py` | Network metrics enrichment node (MVP) |
| `backend/scripts/migrate_neo4j_schema.py` | Schema migration (normalize → dedupe → constraint) |
| `frontend/src/components/NetworkInsightsPanel.tsx` | Network insights UI |
| `backend/tests/unit/test_skill_normalizer.py` | Normalizer tests |
| `backend/tests/unit/test_co_occurrence_builder.py` | Co-occurrence builder tests |
| `backend/tests/unit/test_job_similarity_builder.py` | Similarity builder tests |
| `backend/tests/integration/test_network_enrichment.py` | Enrichment node tests |

## Modified Files
| File | Changes |
|------|---------|
| `backend/app/agents/graph.py` | Add network_enrichment node to workflow |
| `backend/app/agents/nodes/query_understanding.py` | Add new intent patterns |
| `backend/app/agents/nodes/graph_traversal.py` | Add hybrid scoring |
| `backend/app/agents/nodes/context_construction.py` | Add network section builder |
| `backend/app/services/batch_processor.py` | Add deduplication, normalization |
| `backend/app/services/ingestion_service.py` | Add auto-enrichment |
| `backend/app/api/ingest.py` | Enhanced status endpoint |
| `backend/app/api/query.py` | Include network_insights in response |
| `backend/app/models/query.py` | Add NetworkInsights model |
| `frontend/src/components/ChatMessage.tsx` | Render NetworkInsightsPanel |

---
