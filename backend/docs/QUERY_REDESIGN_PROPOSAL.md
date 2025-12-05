# Query Mechanism Redesign: Deep Intent-Driven Architecture

**Status**: Proposal
**Date**: October 2025
**Objective**: Transform from conversational RAG to query-driven intelligence system

---

## Problem Statement

Current system prioritizes **presentation over precision**:
- Overly humanized responses hide query execution details
- Shallow intent detection (regex-based, single-pass)
- No transparency in decision-making process
- Doesn't leverage monitoring infrastructure
- Output format optimized for readability, not queryability

## Design Philosophy Shift

### FROM: Conversational Career Advisor
```
User: "What skills do I need for data science?"
System: "Great question! 😊 Based on 47 positions I found, here's what companies are looking for..."
```

### TO: Deep Intent Query Engine
```
User: "What skills do I need for data science?"

INTENT ANALYSIS:
├─ Primary: skill_requirement (confidence: 0.95)
├─ Secondary: career_path (confidence: 0.72)
└─ Entities: [data_science: role, skills: focus_area]

QUERY EXECUTION:
├─ Neo4j Vector Search: 89 relevant skill nodes (cosine > 0.75)
├─ Graph Traversal: 3-hop skill relationships → 247 connected nodes
├─ SQL Aggregation: Job postings requiring these skills (n=1,243)
└─ Execution Time: 127ms (vector: 45ms, graph: 58ms, sql: 24ms)

RESULTS:
Core Skills (required in 80%+ of data science roles):
  • Python (1,127/1,243 jobs, 90.7%)
  • SQL (1,089/1,243 jobs, 87.6%)
  • Statistics (1,012/1,243 jobs, 81.4%)

Emerging Skills (growth trend +40% YoY):
  • LLMs/Transformers (487/1,243 jobs, 39.2%)
  • MLOps (398/1,243 jobs, 32.0%)

QUERY METADATA:
  - Nodes accessed: 336
  - Relationships traversed: 1,284
  - Cache hit rate: 67%
  - Confidence score: 0.89
```

---

## Architecture Redesign

### 1. Multi-Layer Intent Analysis System

#### Current (Shallow):
```python
def detect_intent(query: str) -> str:
    # Simple regex matching
    if re.search(r"what skills", query.lower()):
        return "skill_requirement"
```

#### Proposed (Deep):
```python
class DeepIntentAnalyzer:
    """Multi-layer intent analysis with semantic understanding."""

    async def analyze_intent(self, query: str) -> IntentAnalysisResult:
        """
        Layer 1: Syntactic Analysis (regex patterns)
        Layer 2: Semantic Analysis (embedding similarity to intent archetypes)
        Layer 3: Entity Relationship Analysis (graph-informed context)
        Layer 4: Query Decomposition (complex/multi-intent queries)

        Returns:
            IntentAnalysisResult(
                primary_intent: str,
                confidence: float,
                secondary_intents: List[Tuple[str, float]],
                entities: List[Entity],
                query_plan: QueryExecutionPlan,
                reasoning: List[str]  # Transparent decision trail
            )
        """

        # Layer 1: Syntactic patterns (fast, broad coverage)
        syntactic_intents = self._detect_syntactic_patterns(query)

        # Layer 2: Semantic intent classification via embeddings
        query_embedding = await self.embedding_service.generate_embedding(query)
        semantic_intents = await self._classify_semantic_intent(query_embedding)

        # Layer 3: Entity-informed refinement
        entities = await self._extract_entities_with_graph_lookup(query)
        refined_intents = self._refine_with_entity_context(
            syntactic_intents,
            semantic_intents,
            entities
        )

        # Layer 4: Query decomposition for multi-intent queries
        query_plan = self._decompose_into_execution_plan(
            query,
            refined_intents,
            entities
        )

        return IntentAnalysisResult(
            primary_intent=refined_intents[0][0],
            confidence=refined_intents[0][1],
            secondary_intents=refined_intents[1:],
            entities=entities,
            query_plan=query_plan,
            reasoning=self._generate_reasoning_trail()
        )
```

#### Intent Archetypes (Semantic Templates)
```python
# Store embeddings of canonical queries for each intent type
INTENT_ARCHETYPES = {
    "skill_requirement": [
        "What skills do I need to become a data scientist?",
        "Required skills for software engineering roles",
        "Technical prerequisites for ML engineer positions"
    ],
    "career_path": [
        "How do I transition from backend to ML engineering?",
        "Steps to become a senior software architect",
        "Career progression from analyst to data scientist"
    ],
    "skill_relationship": [
        "What skills are similar to Python?",
        "Technologies related to React development",
        "Alternative frameworks to Django"
    ],
    # ... precompute embeddings for fast cosine comparison
}
```

### 2. Query-First Response Generation

#### Current System Prompt (Humanized):
```
"You are an experienced career advisor helping professionals..."
"**Warm & Encouraging:** Like a mentor, not a database"
"❌ NO technical citations"
"❌ NO database terminology"
```

#### Proposed System Prompt (Query-Driven):
```python
SYSTEM_PROMPT_V2 = """You are a data-driven query execution system analyzing the Indian tech job market graph.

## YOUR ROLE:
Extract precise insights from knowledge graph query results to answer user questions with maximum accuracy and transparency.

## RESPONSE STRUCTURE:

### 1. INTENT CONFIRMATION (2-3 sentences)
Restate the user's question showing deep understanding:
- Primary intent detected
- Key entities identified
- Query scope clarified

### 2. QUERY EXECUTION SUMMARY
Show what you searched and why:
- Neo4j vector search parameters
- Graph traversal patterns executed
- SQL aggregations performed
- Execution performance (timing, nodes accessed)

### 3. DATA FINDINGS (Structured)
Present results in clear, hierarchical format:
- Quantified insights with exact counts
- Confidence intervals where applicable
- Data source transparency (which nodes/relationships)
- Temporal context (data freshness, sample period)

### 4. QUERY LIMITATIONS
Explicitly state:
- What data was NOT available
- Assumptions made during analysis
- Confidence score and reasoning
- Suggested query refinements for better results

## CRITICAL RULES:
✅ DO expose query execution details
✅ DO show exact numbers and percentages
✅ DO cite node/relationship types
✅ DO indicate confidence scores
✅ DO explain reasoning transparently

❌ DON'T add conversational fluff
❌ DON'T hide technical details
❌ DON'T make assumptions beyond data
❌ DON'T use vague language ("many", "some", "often")

## OUTPUT FORMAT:
Use structured markdown with:
- Clear section headers
- Bullet points with exact metrics
- Code blocks for query patterns
- Tables for comparative data
- Confidence indicators: 🟢 High (>0.8) 🟡 Medium (0.6-0.8) 🔴 Low (<0.6)
"""
```

### 3. Transparent Output Format

```python
class QueryResponse(BaseModel):
    """Structured query response with full transparency."""

    # Intent Analysis Results
    intent_analysis: IntentAnalysisResult

    # Query Execution Details
    execution_summary: QueryExecutionSummary  # What queries ran
    neo4j_queries: List[ExecutedQuery]  # From monitoring system
    sql_queries: List[ExecutedQuery]  # From monitoring system

    # Data Results (Structured)
    primary_findings: Dict[str, Any]  # Main answer data
    supporting_data: Dict[str, Any]  # Context and relationships

    # Metadata & Transparency
    confidence_score: float  # Overall result confidence
    data_limitations: List[str]  # What's missing
    reasoning_trail: List[ReasoningStep]  # Decision trace

    # Performance Metrics
    total_time_ms: float
    breakdown_ms: Dict[str, float]  # Per-stage timing
    nodes_accessed: int
    relationships_traversed: int
    cache_hit_rate: float

    # Human-Readable Response (Generated from above)
    formatted_response: str


class ExecutedQuery(BaseModel):
    """Captured from your monitoring system."""
    query_id: str
    query_text: str
    query_type: str  # "neo4j_vector", "neo4j_cypher", "sql"
    parameters: Dict[str, Any]
    execution_time_ms: float
    result_count: int
    status: str
    reasoning: str  # WHY this query was chosen


class ReasoningStep(BaseModel):
    """Transparent decision trail."""
    step: int
    decision: str  # What was decided
    rationale: str  # Why it was decided
    confidence: float
    alternatives_considered: List[str]
```

### 4. Integration with Monitoring System

```python
class MonitoredQueryExecutor:
    """Execute queries with full transparency via monitoring integration."""

    def __init__(self):
        self.neo4j_monitoring = get_monitoring_service()
        self.sql_monitor = SQLMonitoringService()  # New

    async def execute_with_reasoning(
        self,
        query_plan: QueryExecutionPlan
    ) -> QueryExecutionResult:
        """
        Execute query plan with full traceability.

        All queries logged to monitoring system with:
        - Intent reasoning
        - Parameter selection logic
        - Alternative queries considered
        - Confidence in query choice
        """

        executed_queries = []

        for step in query_plan.steps:
            # Log intent before execution
            logger.info(
                f"[QueryExecution] Step {step.order}: {step.query_type}\n"
                f"Intent: {step.intent}\n"
                f"Reasoning: {step.reasoning}\n"
                f"Expected result: {step.expected_outcome}"
            )

            if step.query_type == "neo4j_vector":
                result = await self._execute_neo4j_vector(
                    step,
                    reasoning=step.reasoning
                )
            elif step.query_type == "neo4j_cypher":
                result = await self._execute_neo4j_cypher(
                    step,
                    reasoning=step.reasoning
                )
            elif step.query_type == "sql":
                result = await self._execute_sql(
                    step,
                    reasoning=step.reasoning
                )

            executed_queries.append(result)

            # Adaptive execution: adjust next steps based on results
            if result.result_count == 0:
                logger.warning(
                    f"[QueryExecution] No results for step {step.order}. "
                    f"Adapting query plan..."
                )
                query_plan = self._adapt_query_plan(query_plan, step, result)

        return QueryExecutionResult(
            executed_queries=executed_queries,
            total_time_ms=sum(q.execution_time_ms for q in executed_queries),
            success=all(q.status == "success" for q in executed_queries)
        )
```

### 5. Deep Semantic Entity Extraction

#### Current (Regex-Based):
```python
skill_patterns = [
    r"\b(python|java|javascript)\\b",
    # ... hardcoded patterns
]
```

#### Proposed (Graph-Informed + Semantic):
```python
class DeepEntityExtractor:
    """Extract entities using graph knowledge + semantic similarity."""

    async def extract_entities(
        self,
        query: str,
        query_embedding: List[float]
    ) -> List[EnrichedEntity]:
        """
        Multi-strategy entity extraction:

        1. Exact Match: Check if query tokens exist in graph
        2. Fuzzy Match: Levenshtein distance for typos/variations
        3. Semantic Match: Embedding similarity to known entities
        4. Contextual Expansion: Use graph relationships to infer related entities

        Example:
        Query: "What skills do ML engineers use for NLP?"

        Entities Found:
        - "ML engineers" → Job(title="Machine Learning Engineer")
          Method: semantic_match, confidence: 0.92
          Graph lookup: Found 247 exact job postings

        - "NLP" → Skill(name="Natural Language Processing")
          Method: exact_match, confidence: 1.0
          Graph expansion: Related skills [BERT, Transformers, spaCy]
        """

        entities = []

        # Strategy 1: Exact graph lookup (fast, high confidence)
        exact_matches = await self._exact_graph_lookup(query)
        entities.extend(exact_matches)

        # Strategy 2: Semantic similarity to known graph entities
        semantic_matches = await self._semantic_entity_matching(
            query,
            query_embedding
        )
        entities.extend(semantic_matches)

        # Strategy 3: Contextual expansion via graph relationships
        expanded_entities = await self._contextual_entity_expansion(entities)
        entities.extend(expanded_entities)

        # Strategy 4: Deduplication + confidence ranking
        entities = self._deduplicate_and_rank(entities)

        return entities

    async def _semantic_entity_matching(
        self,
        query: str,
        query_embedding: List[float]
    ) -> List[EnrichedEntity]:
        """
        Use vector search to find semantically similar entities.

        Example:
        Query mentions: "frontend developer"
        Vector search finds similar entities:
        - React Developer (similarity: 0.89)
        - UI Engineer (similarity: 0.87)
        - Frontend Engineer (similarity: 0.95) ← Use this
        """

        # Search across all entity types
        similar_skills = await self.neo4j_repo.vector_search_skills(
            query_embedding,
            k=20,
            min_score=0.75  # Require strong similarity
        )

        similar_jobs = await self.neo4j_repo.vector_search_jobs(
            query_embedding,
            k=20,
            min_score=0.75
        )

        # Convert to EnrichedEntity with provenance
        entities = []
        for skill in similar_skills:
            entities.append(EnrichedEntity(
                type="skill",
                value=skill["name"],
                confidence=skill["score"],
                source="semantic_vector_search",
                graph_node_id=skill["id"],
                metadata={
                    "similarity_score": skill["score"],
                    "extraction_method": "vector_search"
                }
            ))

        return entities
```

---

## Implementation Plan

### Phase 1: Intent Analysis Enhancement (Week 1)
**Files to modify:**
- `app/agents/nodes/query_understanding.py`
- New: `app/services/intent_analysis_service.py`
- New: `app/models/intent.py`

**Tasks:**
1. Create `DeepIntentAnalyzer` class
2. Precompute intent archetype embeddings
3. Implement multi-layer analysis
4. Add reasoning trail generation
5. Unit tests with edge cases

### Phase 2: Query Execution Transparency (Week 2)
**Files to modify:**
- `app/agents/nodes/vector_search.py`
- `app/agents/nodes/graph_traversal.py`
- `app/services/neo4j_monitoring_service.py` (extend)
- New: `app/services/sql_monitoring_service.py`

**Tasks:**
1. Enhance monitoring to capture query reasoning
2. Build `MonitoredQueryExecutor`
3. Implement adaptive query planning
4. Add confidence scoring to results
5. Integration tests with monitoring

### Phase 3: Response Generation Redesign (Week 3)
**Files to modify:**
- `app/agents/nodes/response_generation.py`
- `app/agents/nodes/context_construction.py`
- New: `app/models/query_response.py`

**Tasks:**
1. Replace system prompt with query-driven version
2. Implement structured `QueryResponse` model
3. Build formatting layer (structured → markdown)
4. Add confidence indicators
5. A/B test output quality

### Phase 4: Entity Extraction Upgrade (Week 4)
**Files to modify:**
- `app/agents/nodes/query_understanding.py`
- New: `app/services/entity_extraction_service.py`

**Tasks:**
1. Implement `DeepEntityExtractor`
2. Build semantic matching pipeline
3. Add graph-informed expansion
4. Create entity deduplication logic
5. Benchmark accuracy vs regex baseline

---

## Example Transformations

### Example 1: Skill Requirement Query

**Query**: "What skills do I need to become a machine learning engineer in India?"

**Current Output**:
```
Great question! 😊 Based on 127 ML engineer positions I analyzed, here's what companies are looking for:

**Core Technical Skills:**
- Python (found in 95% of positions)
- Machine Learning frameworks like TensorFlow and PyTorch
- Statistics and mathematics fundamentals

**Next Steps:**
1. Start with Python if you haven't already
2. Build projects to showcase your skills
3. Consider certifications in ML

Feel free to ask if you want to dive deeper into any area!
```

**Proposed Output**:
```markdown
## Intent Analysis
**Primary Intent:** skill_requirement (confidence: 0.94)
**Secondary Intent:** career_path (confidence: 0.68)
**Entities Detected:**
- machine_learning_engineer (type: job_title, source: exact_match)
- India (type: location, source: explicit)

## Query Execution

### Vector Search (45ms)
```cypher
CALL db.index.vector.queryNodes('job_embedding_idx', 150, $query_embedding)
WHERE node.location CONTAINS 'India'
YIELD node, score
```
**Results:** 127 job postings (cosine similarity > 0.75)

### Graph Traversal (58ms)
```cypher
MATCH (j:Job)-[:REQUIRES]->(s:Skill)
WHERE j.job_id IN $filtered_jobs
RETURN s, count(j) as job_count
ORDER BY job_count DESC
```
**Results:** 247 unique skills across 1,284 relationships

## Findings

### Core Skills (Required in 75%+ of positions)
| Skill | Jobs | Percentage | Avg Years Required |
|-------|------|------------|-------------------|
| Python | 121/127 | 95.3% 🟢 | 2.4 years |
| Statistics | 114/127 | 89.8% 🟢 | 1.8 years |
| TensorFlow/PyTorch | 108/127 | 85.0% 🟢 | 1.5 years |
| SQL | 95/127 | 74.8% 🟡 | 1.2 years |

### Emerging Skills (Growth Trend +35% YoY)
| Skill | Jobs | Trend | Confidence |
|-------|------|-------|------------|
| LLMs/Transformers | 67/127 | +48% 📈 | 🟢 0.91 |
| MLOps | 54/127 | +42% 📈 | 🟡 0.78 |
| Cloud (AWS/GCP) | 89/127 | +35% 📈 | 🟢 0.88 |

## Data Limitations
- Location data available for 127/150 filtered jobs (84.7%)
- Salary information not available in current dataset
- "Years required" inferred from job descriptions (confidence: 🟡 0.72)

## Execution Metadata
- **Total Time:** 127ms
  - Intent Analysis: 12ms
  - Vector Search: 45ms
  - Graph Traversal: 58ms
  - Response Generation: 12ms
- **Nodes Accessed:** 374
- **Cache Hit Rate:** 67%
- **Overall Confidence:** 🟢 0.89
```

### Example 2: Skill Relationship Query

**Query**: "What are alternatives to React for frontend development?"

**Current Output**:
```
If you're looking for alternatives to React, you have some great options!

**Similar Frameworks:**
- Vue.js - Known for being beginner-friendly with great documentation
- Angular - Full-featured framework from Google, popular in enterprises
- Svelte - Rising star that compiles away the framework

Each has its strengths! What's your specific use case? That'll help me recommend the best fit.
```

**Proposed Output**:
```markdown
## Intent Analysis
**Primary Intent:** skill_relationship (confidence: 0.96)
**Focus Entity:** React (type: skill, graph_id: skill_react_001)
**Context:** frontend_development

## Query Strategy
Executing multi-hop graph traversal to find:
1. Direct skill similarities (React -[:SIMILAR_TO]-> Alternative)
2. Job co-requirement patterns (Jobs requiring React also require X)
3. Framework category clustering (Frontend Framework group)

### Cypher Query #1: Direct Similarity (23ms)
```cypher
MATCH (react:Skill {name: 'React'})
     -[:SIMILAR_TO]-(alt:Skill)
WHERE alt.category = 'Frontend Framework'
RETURN alt,
       alt.similarity_score as score
ORDER BY score DESC
LIMIT 10
```
**Results:** 8 directly connected frameworks

### Cypher Query #2: Co-Requirement Analysis (67ms)
```cypher
MATCH (j:Job)-[:REQUIRES]->(react:Skill {name: 'React'})
MATCH (j)-[:REQUIRES]->(alt:Skill)
WHERE alt.category = 'Frontend Framework'
  AND alt.name <> 'React'
WITH alt, count(DISTINCT j) as co_occurrences
ORDER BY co_occurrences DESC
LIMIT 15
```
**Results:** 12 frameworks found in 847 React job postings

## Direct Alternatives (High Similarity)

### Tier 1: Strongest Alternatives (Similarity > 0.85)
| Framework | Similarity | Jobs Using Both | Adoption Trend |
|-----------|------------|-----------------|----------------|
| Vue.js | 0.92 🟢 | 423/847 (50%) | +28% YoY |
| Svelte | 0.88 🟢 | 187/847 (22%) | +65% YoY 📈 |
| Solid.js | 0.86 🟢 | 89/847 (11%) | +142% YoY 📈 |

### Tier 2: Alternative Approaches (Similarity 0.70-0.85)
| Framework | Similarity | Jobs Using Both | Notes |
|-----------|------------|-----------------|-------|
| Angular | 0.79 🟡 | 312/847 (37%) | Enterprise focus |
| Next.js | 0.75 🟡 | 589/847 (70%) | React-based framework |
| Remix | 0.71 🟡 | 134/847 (16%) | Full-stack React framework |

## Job Market Insights

**Framework Substitutability:**
- Vue.js: Can replace React in 78% of analyzed job requirements
- Svelte: Can replace React in 65% of requirements (confidence: 🟡 0.73)
- Angular: Different paradigm, 45% substitutable (confidence: 🔴 0.62)

**Transition Paths from React:**
```
React → Vue.js
  Learning curve: 2-4 weeks (based on developer surveys)
  Transferable concepts: Components, reactivity, state management
  Common in: Startups, small-medium projects

React → Svelte
  Learning curve: 3-6 weeks (paradigm shift)
  Transferable concepts: Components, props
  Common in: Performance-critical apps, modern startups
```

## Graph Traversal Details
- **Relationships Analyzed:** 2,847 (847 jobs × avg 3.36 skills/job)
- **Similarity Algorithm:** Cosine similarity on skill co-occurrence vectors
- **Data Freshness:** Job postings from last 90 days

## Execution Metadata
- **Total Time:** 98ms
  - Intent: 8ms
  - Query #1 (Direct): 23ms
  - Query #2 (Co-req): 67ms
- **Overall Confidence:** 🟢 0.91
```

---

## Benefits of Redesign

### 1. **Transparency**
- Every query execution is visible
- Reasoning trail shows decision-making
- Users understand how answers are derived

### 2. **Precision**
- Structured data > conversational text
- Quantified insights with exact metrics
- Explicit confidence indicators

### 3. **Debuggability**
- Monitor exactly what queries are running
- See intent analysis reasoning
- Identify where improvements are needed

### 4. **Extensibility**
- Clear separation of analysis/execution/presentation layers
- Easy to add new query types
- Pluggable intent analyzers

### 5. **Trust**
- Data limitations explicitly stated
- Confidence scores prevent overconfidence
- Provenance tracking for every fact

---

## Migration Strategy

### Backward Compatibility
Maintain both response styles during transition:

```python
class ResponseGenerationNode:
    async def generate_response(
        self,
        state: GraphRAGState,
        output_mode: str = "structured"  # or "conversational"
    ) -> Dict[str, Any]:

        if output_mode == "structured":
            # New query-driven format
            return await self._generate_structured_response(state)
        else:
            # Legacy conversational format
            return await self._generate_conversational_response(state)
```

### Feature Flags
```python
# app/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Query Engine Configuration
    ENABLE_DEEP_INTENT_ANALYSIS: bool = True
    ENABLE_STRUCTURED_RESPONSES: bool = True
    ENABLE_QUERY_REASONING_LOGS: bool = True

    # Response Style (for A/B testing)
    DEFAULT_RESPONSE_MODE: str = "structured"  # or "conversational"
```

---

## Metrics for Success

### Query Understanding Depth
- **Intent classification accuracy:** >90% (vs baseline ~70%)
- **Entity extraction recall:** >85% (vs baseline ~60%)
- **Multi-intent detection:** Support 2-3 intents per query

### Execution Transparency
- **Query provenance:** 100% of responses cite source queries
- **Reasoning trail:** Every decision logged with rationale
- **Confidence scoring:** All results have quantified confidence

### User Trust
- **Data limitation disclosure:** 100% of missing data acknowledged
- **Execution time:** <150ms p95 (current: <200ms)
- **Answer correctness:** >95% factually grounded in graph data

---

## Next Steps

1. **Review & Approval:** Team review of proposed architecture
2. **Prototype Phase:** Build proof-of-concept with one query type
3. **A/B Testing:** Compare structured vs conversational outputs
4. **Iterative Rollout:** Deploy phase by phase per implementation plan
5. **Monitoring Integration:** Ensure all queries flow through monitoring system

---

**Questions for Discussion:**
1. Do we maintain conversational mode as an option, or fully commit to structured?
2. What's the target audience tolerance for technical detail exposure?
3. Should confidence scores be user-facing or internal-only?
4. How do we handle queries where confidence is low (<0.6)?

---

*Document Version: 1.0*
*Last Updated: October 25, 2025*
*Author: Development Team*
