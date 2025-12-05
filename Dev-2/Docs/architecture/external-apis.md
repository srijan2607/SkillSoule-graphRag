# External APIs

## OpenRouter API

- **Purpose:** LLM inference for natural language response generation
- **Documentation:** https://openrouter.ai/docs
- **Base URL:** https://openrouter.ai/api/v1
- **Authentication:** Bearer token (API key in `Authorization` header)
- **Rate Limits:** Free tier: ~10 requests/min (model-dependent)

**Key Endpoints Used:**
- `POST /chat/completions` - Generate chat completion (OpenAI-compatible format)

**Integration Notes:**
- Existing v1.1 integration preserved
- v2.0 enhancement: Updated system/user prompts to cite network metrics (FR41)
- Circuit breaker pattern implemented (3 retries, exponential backoff)
- Error handling: Return generic response on API failure (avoid exposing errors to user)

## HuggingFace Inference API (Optional)

- **Purpose:** Embedding generation (alternative to local inference)
- **Documentation:** https://huggingface.co/docs/api-inference
- **Base URL:** https://api-inference.huggingface.co/models
- **Authentication:** Bearer token (API key in `Authorization` header)
- **Rate Limits:** Free tier: ~1000 requests/day

**Key Endpoints Used:**
- `POST /sentence-transformers/all-mpnet-base-v2` - Generate embeddings

**Integration Notes:**
- **Current Implementation:** Local inference using HuggingFace Transformers library (CPU-only)
- **Future Enhancement:** Migrate to HuggingFace API if local inference too slow (>2s per query)
- **Trade-off:** API reduces local compute but adds network latency + rate limit dependency

## Neo4j Aura (Cloud Database)

- **Purpose:** Managed Neo4j graph database hosting
- **Documentation:** https://neo4j.com/docs/aura/
- **Base URL:** neo4j+s://<instance-id>.databases.neo4j.io
- **Authentication:** Username/password (Bolt protocol)
- **Rate Limits:** Free tier: 50K nodes, 175K relationships (storage limit, not request rate)

**Key Features Used:**
- Vector indexes for similarity search (v1.1)
- Neo4j GDS for centrality, shortest path (v2.0 NEW)
- Cypher query language
- APOC procedures (if available on free tier)

**Integration Notes:**
- Free tier Neo4j GDS support confirmed (eigenvector centrality, Dijkstra algorithms available)
- Risk: Free tier may have query timeout limits (<30s); mitigation in Risk 1

---
