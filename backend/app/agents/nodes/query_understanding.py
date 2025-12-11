"""
Query Understanding Node - Analyzes user query to extract intent and entities.

NOW USES DEEP INTENT ANALYSIS:
- Multi-layer intent classification (syntactic + semantic + entity-informed)
- Graph-informed entity extraction with semantic matching
- Transparent reasoning trails for all decisions
- Structured query execution planning
"""

from typing import Dict, Any, List
import re
from app.agents.graph import GraphRAGState
from app.services.embedding_service import EmbeddingService
from app.services.intent_analysis_service import DeepIntentAnalyzer
from app.services.entity_extraction_service import DeepEntityExtractor
from app.repositories.monitored_neo4j_repository import MonitoredNeo4jRepository
from app.models.intent import Entity
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics
from app.config import get_settings
from app.dependencies import get_prisma
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)

settings = get_settings()


def detect_intents(query: str) -> List[str]:
    """
    Classify ALL query intents using keyword matching (multi-intent support).

    Args:
        query: User query text (lowercase)

    Returns:
        List[str]: All detected intent types. Returns ["general"] if no matches.
    """
    query_lower = query.lower()
    detected_intents = []

    # Intent patterns with priority order (most specific first)
    intent_patterns = [
        # Skill relationship queries (most specific - check first to avoid false matches)
        (
            r"similar to|related (to|skills)|alternatives to|comparable to|versus|vs\b|compared to",
            "skill_relationship",
        ),
        # Career transition queries (NEW - Story 7.4)
        (
            r"transition\s+from\s+(.+?)\s+to\s+(.+)|"
            r"switch\s+(?:career|job)\s+(?:from|to)|"
            r"move\s+from\s+(.+?)\s+(?:to|into)\s+(.+)|"
            r"become\s+a\s+(.+?)\s+from\s+(.+)",
            "career_transition",
        ),
        # Skill bridge queries (NEW - Story 7.4)
        (
            r"path\s+(?:from|between)\s+(.+?)\s+(?:to|and)\s+(.+)|"
            r"bridge\s+(?:skills?|gap)|"
            r"connect(?:ion)?\s+(?:from|between)\s+(.+)|"
            r"skill\s+path",
            "skill_bridge",
        ),
        # Skill importance queries (NEW - Story 7.4)
        (
            r"(?:most\s+)?important\s+skills?|"
            r"top\s+skills?|"
            r"high(?:est)?\s+(?:demand|centrality)|"
            r"valuable\s+skills?",
            "skill_importance",
        ),
        # Job similarity queries (NEW - Story 7.4)
        (
            r"similar\s+(?:jobs?|positions?|roles?)|"
            r"related\s+(?:jobs?|positions?)|"
            r"jobs?\s+like\s+(.+)",
            "job_similarity",
        ),
        # Skill requirement queries (EXPANDED to include framework/technology queries)
        (
            r"what skills|skills for|skills needed|skills required|need to know|must know|should.*learn|skills do i need|"
            r"what (framework|library|libraries|technology|technologies|tool|tools|language|languages)|"
            r"(framework|library|technology|tool|language)s? (for|in|needed|required|used)|"
            r"(most|best|top|popular|famous|in-demand|trending) (framework|library|technology|tool|language|skill)s?|"
            r"which (framework|library|technology|tool|language)s?|"
            r"demand for|in demand|market demand",
            "skill_requirement",
        ),
        # Career path queries
        (
            r"career path|how to become|get into|roadmap to|become.*developer|become.*engineer",
            "career_path",
        ),
        # Salary analysis queries (EXPANDED to include "salaries" plural and "how much" queries)
        (
            r"\bsalar(y|ies)|pay\b|compensation|wage|earn(ing)?|income|high-paying|well-paid|"
            r"how much.*make|expect.*salary|what.*pay|pay range|pay scale",
            "salary_analysis",
        ),
        # Company queries
        (
            r"companies|employers|who hires|which companies|organizations|firms hiring|companies use|where.*shift|where.*work",
            "company_query",
        ),
    ]

    # Check ALL patterns and collect matches
    for pattern, intent_type in intent_patterns:
        if re.search(pattern, query_lower):
            detected_intents.append(intent_type)

    # Default intent if no match
    if not detected_intents:
        detected_intents.append("general")

    return detected_intents


def detect_intent(query: str) -> str:
    """
    Classify primary query intent (backward compatibility).

    Args:
        query: User query text

    Returns:
        str: Primary intent type
    """
    intents = detect_intents(query)
    return intents[0] if intents else "general"


def extract_entities(query: str) -> List[Dict[str, Any]]:
    """
    Extract entities from query using simple regex patterns.

    Args:
        query: User query text

    Returns:
        List of entities with type, value, and confidence
    """
    entities = []

    # Common skill patterns (programming languages, frameworks, tools)
    skill_patterns = [
        r"\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|php|swift|kotlin)\b",
        r"\b(react|vue|angular|django|flask|spring|express|fastapi|rails)\b",
        r"\b(sql|nosql|mongodb|postgresql|mysql|redis|elasticsearch)\b",
        r"\b(aws|azure|gcp|docker|kubernetes|git|jenkins|terraform)\b",
        r"\b(machine learning|deep learning|ai|data science|devops|frontend|backend)\b",
    ]

    for pattern in skill_patterns:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        for match in matches:
            skill_name = match.group(0).lower()
            entities.append({"type": "skill", "value": skill_name, "confidence": 0.8})

    # Job title patterns
    job_patterns = [
        r"\b(software engineer|developer|data scientist|data analyst|product manager)\b",
        r"\b(devops engineer|frontend developer|backend developer|full stack)\b",
        r"\b(machine learning engineer|ai engineer|cloud engineer)\b",
    ]

    for pattern in job_patterns:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        for match in matches:
            job_title = match.group(0).lower()
            entities.append({"type": "job", "value": job_title, "confidence": 0.7})

    # Company name patterns (common tech companies)
    company_patterns = [
        r"\b(google|amazon|microsoft|apple|meta|facebook|netflix|tesla)\b",
        r"\b(ibm|oracle|salesforce|adobe|nvidia|intel|amd|twitter|x)\b",
    ]

    for pattern in company_patterns:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        for match in matches:
            company_name = match.group(0).lower()
            entities.append({"type": "company", "value": company_name, "confidence": 0.9})

    # Deduplicate entities
    seen = set()
    unique_entities = []
    for entity in entities:
        key = (entity["type"], entity["value"])
        if key not in seen:
            seen.add(key)
            unique_entities.append(entity)

    return unique_entities


async def query_understanding_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Analyze user query using DEEP MULTI-LAYER INTENT ANALYSIS.

    NEW CAPABILITIES:
    1. Generate query embedding for vector similarity search (384-dim)
    2. MULTI-LAYER intent classification:
       - Layer 1: Syntactic (regex patterns)
       - Layer 2: Semantic (embedding similarity to archetypes)
       - Layer 3: Entity-informed (graph context refinement)
       - Layer 4: Query decomposition (execution planning)
    3. Graph-informed entity extraction with semantic matching
    4. Transparent reasoning trails

    Args:
        state: Current graph state with user_query

    Returns:
        Dict with query_embedding, intent, entities, metadata, and intent_analysis
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("query_understanding")

    # Get pipeline monitoring service
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", state.user_id)
    user_query = state.user_query

    # Emit stage started event
    await pipeline_monitor.emit_query_understanding(
        session_id=session_id,
        user_id=user_id,
        query=user_query,
        status=StageStatus.STARTED
    )

    try:
        logger.info(f"[QueryUnderstanding] Processing query: {user_query[:50]}...")

        # Step 1: Generate query embedding
        embedding_service = EmbeddingService()
        embedding_result = await embedding_service.generate_embedding(user_query)
        query_embedding = embedding_result["embedding"]

        logger.info(
            f"[QueryUnderstanding] Generated embedding: dim={len(query_embedding)}, "
            f"model={embedding_result['model_version']}"
        )

        # Step 2: Deep entity extraction (graph-informed with monitoring)
        try:
            # Initialize MONITORED Neo4j repository for entity extraction
            # This enables real-time query tracking in the monitoring dashboard
            prisma_client = get_prisma()
            session_id = state.metadata.get("session_id")
            user_id = state.metadata.get("user_id", state.user_id)

            neo4j_repo = MonitoredNeo4jRepository(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                prisma_client=prisma_client,
                session_id=session_id,
                enable_monitoring=True
            )
            await neo4j_repo.connect()

            entity_extractor = DeepEntityExtractor(
                embedding_service=embedding_service,
                neo4j_repo=neo4j_repo,
            )
            extracted_entities = await entity_extractor.extract_entities(
                user_query, query_embedding, user_id=user_id
            )

            # Close connection
            await neo4j_repo.close()

        except Exception as e:
            logger.warning(
                f"[QueryUnderstanding] Graph-informed entity extraction failed: {e}. "
                f"Falling back to regex."
            )
            # Fallback to old regex-based extraction
            old_entities = extract_entities(user_query)
            extracted_entities = [
                Entity(
                    type=e["type"],
                    value=e["value"],
                    confidence=e["confidence"],
                    source="regex_fallback",
                )
                for e in old_entities
            ]

        logger.info(
            f"[QueryUnderstanding] Extracted {len(extracted_entities)} entities: "
            f"{[e.value for e in extracted_entities[:3]]}"
            f"{'...' if len(extracted_entities) > 3 else ''}"
        )

        # Step 3: Deep intent analysis (4 layers)
        intent_analyzer = DeepIntentAnalyzer(embedding_service=embedding_service)
        intent_analysis = await intent_analyzer.analyze_intent(
            query=user_query,
            query_embedding=query_embedding,
            entities=extracted_entities,
        )

        # Log intent analysis completion with full details for monitoring
        logger.info(
            f"[QueryUnderstanding] Deep analysis complete: "
            f"primary={intent_analysis.primary_intent} ({intent_analysis.primary_confidence:.2f}), "
            f"secondary={len(intent_analysis.secondary_intents)}, "
            f"plan_steps={len(intent_analysis.query_plan.steps)}, "
            f"reasoning_steps={len(intent_analysis.reasoning_trail)}"
        )

        # Detailed intent analysis log for monitoring dashboard visibility
        logger.info(
            f"[IntentAnalysis] session_id={session_id}, user_id={user_id}, "
            f"intent={intent_analysis.primary_intent}, "
            f"confidence={intent_analysis.primary_confidence:.3f}, "
            f"entities={len(extracted_entities)}, "
            f"query_complexity={intent_analysis.query_plan.complexity_score:.2f}, "
            f"multi_hop={intent_analysis.query_plan.requires_multi_hop}"
        )

        # End timing
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("query_understanding")
            logger.info(f"[QueryUnderstanding] Completed in {duration_ms:.2f}ms")

        # Emit stage completed event
        await pipeline_monitor.emit_query_understanding(
            session_id=session_id,
            user_id=user_id,
            query=user_query,
            status=StageStatus.COMPLETED,
            duration_ms=duration_ms,
            intent=intent_analysis.primary_intent,
            confidence=intent_analysis.primary_confidence,
            entities=[
                {
                    "type": e.type,
                    "value": e.value,
                    "confidence": e.confidence
                }
                for e in extracted_entities
            ]
        )

        # Convert Entity objects to dict for backward compatibility
        entities_dict = [
            {
                "type": e.type,
                "value": e.value,
                "confidence": e.confidence,
                "source": e.source,
                "graph_node_id": e.graph_node_id,
            }
            for e in extracted_entities
        ]

        return {
            "query_embedding": query_embedding,
            "intent": intent_analysis.primary_intent,  # Primary for backward compat
            "intents": intent_analysis.all_intents,  # All detected intents
            "entities": entities_dict,  # Backward compatible dict format
            "metadata": {
                **state.metadata,
                "query_understanding_completed": True,
                "intent_confidence": intent_analysis.primary_confidence,
                "embedding_model": embedding_result["model_version"],
                "entities_count": len(extracted_entities),
                "detected_intents_count": len(intent_analysis.all_intents),
                # NEW: Deep analysis metadata
                "intent_analysis": intent_analysis.dict(),  # Full analysis result
                "query_plan": intent_analysis.query_plan.dict(),  # Execution plan
                "reasoning_trail": [r.dict() for r in intent_analysis.reasoning_trail],
                "analysis_layers": {
                    "syntactic_intents": intent_analysis.syntactic_intents,
                    "semantic_intents": [
                        (i, float(c)) for i, c in intent_analysis.semantic_intents
                    ],
                    "entity_count": len(extracted_entities),
                    "plan_complexity": intent_analysis.query_plan.complexity_score,
                },
            },
        }

    except Exception as e:
        logger.error(f"[QueryUnderstanding] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("query_understanding")

        # Emit stage failed event
        await pipeline_monitor.emit_query_understanding(
            session_id=session_id,
            user_id=user_id,
            query=user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "query_embedding": [0.0] * 384,  # Zero vector fallback
            "intent": "unknown",
            "entities": [],
            "metadata": {
                **state.metadata,
                "query_understanding_error": str(e),
                "query_understanding_completed": False,
            },
        }
