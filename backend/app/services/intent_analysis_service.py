"""
Deep Intent Analysis Service - Multi-layer query understanding.

Implements four-layer intent analysis:
1. Syntactic Analysis: Fast regex pattern matching
2. Semantic Analysis: Embedding similarity to intent archetypes
3. Entity-Informed Analysis: Graph context refinement
4. Query Decomposition: Multi-intent query planning
"""

import re
import time
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.models.intent import (
    IntentAnalysisResult,
    Entity,
    QueryExecutionPlan,
    QueryExecutionStep,
    ReasoningStep,
    IntentArchetype,
)
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.utils.logger import logger


class DeepIntentAnalyzer:
    """
    Multi-layer intent analysis system for deep query understanding.

    Provides four layers of analysis to accurately understand user intent
    and plan optimal query execution strategies.
    """

    # Intent patterns for Layer 1 (Syntactic Analysis)
    INTENT_PATTERNS = {
        "skill_relationship": [
            r"similar to",
            r"related (to|skills)",
            r"alternatives to",
            r"comparable to",
            r"versus|vs\b",
            r"compared to",
            r"difference between",
            r"substitute for",
        ],
        "skill_requirement": [
            r"what skills",
            r"skills for",
            r"skills needed",
            r"skills required",
            r"need to know",
            r"must know",
            r"should.*learn",
            r"skills do i need",
            r"technical requirements",
            r"prerequisites",
            # Framework/technology/tool queries (EXPANDED)
            r"what (framework|library|libraries|technology|technologies|tool|tools|language|languages)",
            r"(framework|library|technology|tool|language)s? (for|in|needed|required|used)",
            r"(most|best|top|popular|famous|in-demand|trending) (framework|library|technology|tool|language|skill)s?",
            r"which (framework|library|technology|tool|language)s?",
            r"demand for|in demand|market demand",
        ],
        "career_path": [
            r"transition",
            r"career path",
            r"how to become",
            r"switch to",
            r"move into",
            r"get into",
            r"roadmap to",
            r"become.*developer",
            r"become.*engineer",
            r"career progression",
        ],
        "salary_analysis": [
            r"\bsalar(y|ies)",  # salary OR salaries
            r"\bpay\b",
            r"compensation",
            r"wage",
            r"earn(ing)?",
            r"income",
            r"high-paying",
            r"well-paid",
            r"how much.*make",
            r"expect.*salary",
            r"what.*pay",
            r"pay range",
            r"pay scale",
        ],
        "company_query": [
            r"companies",
            r"employers",
            r"who hires",
            r"which companies",
            r"organizations",
            r"firms hiring",
            r"companies use",
            r"where.*work",
            r"which.*company",
        ],
        "transition_path": [
            r"transition from",
            r"switch from .* to",
            r"move from .* to",
            r"how (do i|can i|to) (become|transition|switch|move)",
            r"career path from",
            r"gap between .* and",
            r"skills gap",
            r"what skills .* need .* to become",
            r"bridge .* to",
            r"from .* to .*",
            r"skills to learn (for|to)",
            r"learning path",
            r"upskill from",
        ],
    }

    # Intent archetypes for Layer 2 (Semantic Analysis)
    # These will be precomputed and cached
    INTENT_ARCHETYPES: Dict[str, IntentArchetype] = {}

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        neo4j_repo: Optional[Neo4jRepository] = None,
    ):
        """
        Initialize deep intent analyzer.

        Args:
            embedding_service: Service for generating embeddings
            neo4j_repo: Repository for graph queries
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.neo4j_repo = neo4j_repo
        self.reasoning_trail: List[ReasoningStep] = []
        self._initialize_archetypes()

    def _initialize_archetypes(self):
        """
        Initialize intent archetypes with canonical queries.

        These will be used for semantic similarity matching.
        Embeddings are computed lazily on first use.
        """
        self.INTENT_ARCHETYPES = {
            "skill_requirement": IntentArchetype(
                intent_type="skill_requirement",
                canonical_queries=[
                    "What skills do I need to become a data scientist?",
                    "Required skills for software engineering roles",
                    "Technical prerequisites for ML engineer positions",
                    "What should I learn for backend development?",
                    "Skills needed for frontend developer job",
                ],
                keywords=["skills", "need", "required", "learn", "prerequisites"],
                confidence_threshold=0.65,
            ),
            "career_path": IntentArchetype(
                intent_type="career_path",
                canonical_queries=[
                    "How do I transition from backend to ML engineering?",
                    "Steps to become a senior software architect",
                    "Career progression from analyst to data scientist",
                    "How to move into DevOps from development?",
                    "Roadmap to become a full stack developer",
                ],
                keywords=["transition", "become", "career", "path", "roadmap"],
                confidence_threshold=0.65,
            ),
            "skill_relationship": IntentArchetype(
                intent_type="skill_relationship",
                canonical_queries=[
                    "What skills are similar to Python?",
                    "Technologies related to React development",
                    "Alternative frameworks to Django",
                    "What's comparable to AWS for cloud computing?",
                    "Differences between Vue and React",
                ],
                keywords=["similar", "related", "alternative", "versus", "compared"],
                confidence_threshold=0.70,
            ),
            "salary_analysis": IntentArchetype(
                intent_type="salary_analysis",
                canonical_queries=[
                    "What is the average salary for data scientists?",
                    "How much do ML engineers earn in India?",
                    "Salary expectations for senior developers",
                    "High-paying tech roles in India",
                    "Compensation for DevOps engineers",
                ],
                keywords=["salary", "pay", "earn", "compensation", "income"],
                confidence_threshold=0.65,
            ),
            "company_query": IntentArchetype(
                intent_type="company_query",
                canonical_queries=[
                    "Which companies hire Python developers?",
                    "Top employers for data scientists in India",
                    "Companies using React for frontend",
                    "Where do ML engineers work?",
                    "Organizations hiring DevOps engineers",
                ],
                keywords=["companies", "employers", "organizations", "hire", "work"],
                confidence_threshold=0.65,
            ),
            "transition_path": IntentArchetype(
                intent_type="transition_path",
                canonical_queries=[
                    "How do I transition from backend developer to ML engineer?",
                    "What skills do I need to switch from Python to Go?",
                    "Career path from data analyst to data scientist",
                    "Skills gap between frontend developer and full stack",
                    "Learning path to become a DevOps engineer from developer",
                ],
                keywords=["transition", "switch", "from", "to", "become", "gap", "path"],
                confidence_threshold=0.65,
            ),
        }

    async def _ensure_archetype_embeddings(self):
        """
        Ensure all intent archetypes have precomputed embeddings.

        Computes embeddings for canonical queries and stores average
        embedding as archetype representation.
        """
        for intent_type, archetype in self.INTENT_ARCHETYPES.items():
            if archetype.embedding is None:
                logger.info(
                    f"[IntentAnalyzer] Computing embeddings for {intent_type} archetype"
                )

                # Generate embeddings for all canonical queries
                embeddings = []
                for query in archetype.canonical_queries:
                    result = await self.embedding_service.generate_embedding(query)
                    embeddings.append(result["embedding"])

                # Average embeddings to create archetype representation
                archetype.embedding = np.mean(embeddings, axis=0).tolist()

                logger.info(
                    f"[IntentAnalyzer] Computed archetype embedding for {intent_type}: "
                    f"dim={len(archetype.embedding)}"
                )

    def _layer1_syntactic_analysis(self, query: str) -> List[str]:
        """
        Layer 1: Fast syntactic pattern matching using regex.

        Args:
            query: User query (will be lowercased)

        Returns:
            List of detected intent types
        """
        query_lower = query.lower()
        detected_intents = []

        for intent_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_intents.append(intent_type)
                    break  # One match per intent type is enough

        # Add reasoning
        if detected_intents:
            self.reasoning_trail.append(
                ReasoningStep(
                    step=len(self.reasoning_trail) + 1,
                    decision=f"Syntactic patterns matched: {detected_intents}",
                    rationale="Regex pattern matching against known intent signatures",
                    confidence=0.7,  # Syntactic matching is fairly reliable but not perfect
                    data_used=[f"Query text: '{query[:50]}...'"],
                )
            )

        return detected_intents

    async def _layer2_semantic_analysis(
        self, query: str, query_embedding: List[float]
    ) -> List[Tuple[str, float]]:
        """
        Layer 2: Semantic intent classification using embedding similarity.

        Compares query embedding to intent archetype embeddings.

        Args:
            query: User query text
            query_embedding: 384-dim embedding vector

        Returns:
            List of (intent_type, confidence) tuples sorted by confidence
        """
        # Ensure archetypes have embeddings
        await self._ensure_archetype_embeddings()

        semantic_scores = []

        for intent_type, archetype in self.INTENT_ARCHETYPES.items():
            if archetype.embedding is None:
                continue

            # Compute cosine similarity
            similarity = self._cosine_similarity(query_embedding, archetype.embedding)

            # Only include if above threshold
            if similarity >= archetype.confidence_threshold:
                semantic_scores.append((intent_type, float(similarity)))

        # Sort by confidence (descending)
        semantic_scores.sort(key=lambda x: x[1], reverse=True)

        # Add reasoning
        if semantic_scores:
            self.reasoning_trail.append(
                ReasoningStep(
                    step=len(self.reasoning_trail) + 1,
                    decision=f"Semantic similarity matches: {[(i, f'{c:.2f}') for i, c in semantic_scores[:3]]}",
                    rationale="Embedding cosine similarity to intent archetypes",
                    confidence=semantic_scores[0][1] if semantic_scores else 0.0,
                    data_used=[f"Query embedding dim={len(query_embedding)}"],
                )
            )

        return semantic_scores

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)

        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def _layer3_entity_refinement(
        self,
        syntactic_intents: List[str],
        semantic_intents: List[Tuple[str, float]],
        entities: List[Entity],
    ) -> List[Tuple[str, float]]:
        """
        Layer 3: Refine intent classification using entity context.

        Entity types can inform intent:
        - Skills + "similar" → skill_relationship
        - Job titles → skill_requirement or career_path
        - Companies → company_query
        - Salary mentions → salary_analysis

        Args:
            syntactic_intents: Results from Layer 1
            semantic_intents: Results from Layer 2
            entities: Extracted entities

        Returns:
            Refined list of (intent, confidence) tuples
        """
        # Start with semantic scores (more reliable than syntactic)
        refined_scores = {intent: score for intent, score in semantic_intents}

        # Boost scores based on entity alignment
        entity_types = [e.type for e in entities]

        for intent, score in list(refined_scores.items()):
            boost = 0.0

            if intent == "skill_relationship" and "skill" in entity_types:
                boost = 0.10  # Strong alignment
            elif intent == "skill_requirement" and ("job" in entity_types or "skill" in entity_types):
                boost = 0.08
            elif intent == "career_path" and "job" in entity_types:
                boost = 0.08
            elif intent == "company_query" and "company" in entity_types:
                boost = 0.12  # Very strong alignment
            elif intent == "salary_analysis" and "job" in entity_types:
                boost = 0.05

            if boost > 0:
                refined_scores[intent] = min(1.0, score + boost)

        # Add syntactic intents that weren't in semantic (with lower confidence)
        for intent in syntactic_intents:
            if intent not in refined_scores:
                refined_scores[intent] = 0.60  # Moderate confidence for syntax-only

        # Convert back to sorted list
        refined_list = sorted(refined_scores.items(), key=lambda x: x[1], reverse=True)

        # Add reasoning
        if refined_list:
            self.reasoning_trail.append(
                ReasoningStep(
                    step=len(self.reasoning_trail) + 1,
                    decision=f"Entity-refined intents: {[(i, f'{c:.2f}') for i, c in refined_list[:3]]}",
                    rationale=f"Entity context ({len(entities)} entities) used to refine confidence scores",
                    confidence=refined_list[0][1] if refined_list else 0.0,
                    data_used=[f"Entity types: {set(entity_types)}"],
                )
            )

        return refined_list

    def _layer4_query_decomposition(
        self,
        query: str,
        refined_intents: List[Tuple[str, float]],
        entities: List[Entity],
    ) -> QueryExecutionPlan:
        """
        Layer 4: Decompose query into execution plan.

        Creates structured plan for query execution based on detected intents.

        Args:
            query: Original user query
            refined_intents: Final intent classifications
            entities: Extracted entities

        Returns:
            QueryExecutionPlan with ordered steps
        """
        steps = []
        primary_intent = refined_intents[0][0] if refined_intents else "general"

        # Build execution steps based on primary intent
        if primary_intent == "skill_requirement":
            # Step 1: Vector search for job postings
            steps.append(
                QueryExecutionStep(
                    step_number=1,
                    query_type="neo4j_vector",
                    intent="skill_requirement",
                    reasoning="Find job postings relevant to query using embedding similarity",
                    expected_outcome="50-150 relevant job nodes",
                    parameters={"index": "job_embedding_idx", "k": 100},
                    confidence=0.85,
                )
            )

            # Step 2: Graph traversal for required skills
            steps.append(
                QueryExecutionStep(
                    step_number=2,
                    query_type="neo4j_cypher",
                    intent="skill_requirement",
                    reasoning="Traverse Job -[:REQUIRES]-> Skill relationships to find required skills",
                    expected_outcome="20-100 skill nodes with frequency counts",
                    parameters={"relationship": "REQUIRES", "aggregate": "count"},
                    confidence=0.90,
                )
            )

        elif primary_intent == "skill_relationship":
            # Step 1: Vector search for similar skills
            steps.append(
                QueryExecutionStep(
                    step_number=1,
                    query_type="neo4j_vector",
                    intent="skill_relationship",
                    reasoning="Find semantically similar skills using vector similarity",
                    expected_outcome="10-20 similar skill nodes",
                    parameters={"index": "skill_embedding_idx", "k": 15},
                    confidence=0.88,
                )
            )

            # Step 2: Graph traversal for skill co-occurrence
            steps.append(
                QueryExecutionStep(
                    step_number=2,
                    query_type="neo4j_cypher",
                    intent="skill_relationship",
                    reasoning="Find skills that frequently appear together in job postings",
                    expected_outcome="15-30 related skills with co-occurrence stats",
                    parameters={"relationship": "CO_OCCURS_WITH", "min_count": 5},
                    confidence=0.82,
                )
            )

        elif primary_intent == "career_path":
            # Step 1: Vector search for target role
            steps.append(
                QueryExecutionStep(
                    step_number=1,
                    query_type="neo4j_vector",
                    intent="career_path",
                    reasoning="Identify target job role mentioned in query",
                    expected_outcome="20-50 job nodes for target role",
                    parameters={"index": "job_embedding_idx", "k": 50},
                    confidence=0.80,
                )
            )

            # Step 2: Skill requirements for target role
            steps.append(
                QueryExecutionStep(
                    step_number=2,
                    query_type="neo4j_cypher",
                    intent="career_path",
                    reasoning="Find skills required for target role",
                    expected_outcome="30-80 required skills",
                    parameters={"relationship": "REQUIRES"},
                    confidence=0.85,
                )
            )

        elif primary_intent == "company_query":
            # Step 1: Vector search for relevant jobs
            steps.append(
                QueryExecutionStep(
                    step_number=1,
                    query_type="neo4j_vector",
                    intent="company_query",
                    reasoning="Find relevant job postings to identify companies",
                    expected_outcome="50-100 job nodes",
                    parameters={"index": "job_embedding_idx", "k": 100},
                    confidence=0.82,
                )
            )

            # Step 2: Company aggregation
            steps.append(
                QueryExecutionStep(
                    step_number=2,
                    query_type="neo4j_cypher",
                    intent="company_query",
                    reasoning="Group jobs by company and count postings",
                    expected_outcome="20-50 companies with job counts",
                    parameters={"aggregate_by": "company_name"},
                    confidence=0.88,
                )
            )

        else:
            # General fallback - basic vector search
            steps.append(
                QueryExecutionStep(
                    step_number=1,
                    query_type="neo4j_vector",
                    intent=primary_intent,
                    reasoning="General semantic search across all node types",
                    expected_outcome="Diverse mix of relevant nodes",
                    parameters={"k": 50},
                    confidence=0.70,
                )
            )

        # Calculate complexity score
        complexity_score = min(1.0, len(steps) * 0.25 + len(entities) * 0.1)
        requires_multi_hop = len(steps) > 1

        # Estimate total time
        total_time_estimate = sum(
            50.0 if step.query_type == "neo4j_vector" else 80.0 for step in steps
        )

        plan = QueryExecutionPlan(
            steps=steps,
            total_estimated_time_ms=total_time_estimate,
            complexity_score=complexity_score,
            requires_multi_hop=requires_multi_hop,
        )

        # Add reasoning
        self.reasoning_trail.append(
            ReasoningStep(
                step=len(self.reasoning_trail) + 1,
                decision=f"Generated {len(steps)}-step execution plan for {primary_intent}",
                rationale=f"Intent requires {'multi-hop' if requires_multi_hop else 'single-step'} graph queries",
                confidence=0.85,
                data_used=[f"Primary intent: {primary_intent}", f"Entities: {len(entities)}"],
            )
        )

        return plan

    async def analyze_intent(
        self, query: str, query_embedding: List[float], entities: List[Entity]
    ) -> IntentAnalysisResult:
        """
        Perform complete multi-layer intent analysis.

        Executes all four analysis layers and returns comprehensive result.

        Args:
            query: User query text
            query_embedding: 384-dim embedding vector
            entities: Extracted entities (from entity extraction service)

        Returns:
            IntentAnalysisResult with complete analysis
        """
        start_time = time.time()
        self.reasoning_trail = []  # Reset reasoning trail

        logger.info(f"[IntentAnalyzer] Starting multi-layer analysis for: {query[:50]}...")

        # Layer 1: Syntactic Analysis
        syntactic_intents = self._layer1_syntactic_analysis(query)
        logger.info(f"[IntentAnalyzer] Layer 1 (Syntactic): {syntactic_intents}")

        # Layer 2: Semantic Analysis
        semantic_intents = await self._layer2_semantic_analysis(query, query_embedding)
        logger.info(
            f"[IntentAnalyzer] Layer 2 (Semantic): {[(i, f'{c:.2f}') for i, c in semantic_intents[:3]]}"
        )

        # Layer 3: Entity-Informed Refinement
        refined_intents = self._layer3_entity_refinement(
            syntactic_intents, semantic_intents, entities
        )
        logger.info(
            f"[IntentAnalyzer] Layer 3 (Entity-Refined): {[(i, f'{c:.2f}') for i, c in refined_intents[:3]]}"
        )

        # Layer 4: Query Decomposition
        query_plan = self._layer4_query_decomposition(query, refined_intents, entities)
        logger.info(
            f"[IntentAnalyzer] Layer 4 (Decomposition): {len(query_plan.steps)} steps, "
            f"complexity={query_plan.complexity_score:.2f}"
        )

        # Extract primary and secondary intents
        primary_intent = refined_intents[0][0] if refined_intents else "general"
        primary_confidence = refined_intents[0][1] if refined_intents else 0.5
        secondary_intents = refined_intents[1:4]  # Top 3 secondary intents
        all_intents = [intent for intent, _ in refined_intents]

        # Calculate analysis time
        analysis_time_ms = (time.time() - start_time) * 1000

        result = IntentAnalysisResult(
            primary_intent=primary_intent,
            primary_confidence=primary_confidence,
            secondary_intents=secondary_intents,
            all_intents=all_intents,
            entities=entities,
            query_plan=query_plan,
            reasoning_trail=self.reasoning_trail,
            analysis_time_ms=analysis_time_ms,
            syntactic_intents=syntactic_intents,
            semantic_intents=semantic_intents,
        )

        logger.info(
            f"[IntentAnalyzer] Analysis complete in {analysis_time_ms:.2f}ms: "
            f"primary={primary_intent} ({primary_confidence:.2f}), "
            f"secondary={len(secondary_intents)}, "
            f"entities={len(entities)}"
        )

        return result
