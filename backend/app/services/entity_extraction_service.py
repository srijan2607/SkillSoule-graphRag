"""
Deep Entity Extraction Service - Graph-informed entity extraction.

Extracts entities using multiple strategies:
1. Exact Match: Direct graph lookup
2. Fuzzy Match: Levenshtein distance for typos
3. Semantic Match: Embedding similarity
4. Contextual Expansion: Graph relationship inference
"""

import re
from typing import List, Dict, Any, Optional
from app.models.intent import Entity
from app.services.embedding_service import EmbeddingService
from app.repositories.neo4j_repository import Neo4jRepository
from app.utils.logger import logger


class DeepEntityExtractor:
    """
    Extract entities using graph knowledge and semantic similarity.

    Provides high-confidence entity extraction with multiple strategies
    and graph-informed context expansion.
    """

    # Common skill patterns (fallback for when graph isn't available)
    SKILL_PATTERNS = [
        r"\b(python|java|javascript|typescript|c\+\+|c#|ruby|go|rust|php|swift|kotlin)\b",
        r"\b(react|vue|angular|django|flask|spring|express|fastapi|rails|nextjs|nuxt)\b",
        r"\b(sql|nosql|mongodb|postgresql|mysql|redis|elasticsearch|neo4j)\b",
        r"\b(aws|azure|gcp|google cloud|docker|kubernetes|k8s|git|jenkins|terraform)\b",
        r"\b(machine learning|deep learning|ai|ml|data science|nlp|computer vision)\b",
        r"\b(devops|frontend|backend|full stack|fullstack|mobile|ios|android)\b",
    ]

    # Job title patterns
    JOB_PATTERNS = [
        r"\b(software engineer|developer|programmer|coder)\b",
        r"\b(data scientist|data analyst|data engineer|ml engineer)\b",
        r"\b(product manager|project manager|scrum master)\b",
        r"\b(devops engineer|sre|site reliability|cloud engineer)\b",
        r"\b(frontend developer|backend developer|full stack developer)\b",
        r"\b(mobile developer|ios developer|android developer)\b",
        r"\b(machine learning engineer|ai engineer|research scientist)\b",
    ]

    # Company patterns
    COMPANY_PATTERNS = [
        r"\b(google|amazon|microsoft|apple|meta|facebook|netflix|tesla)\b",
        r"\b(ibm|oracle|salesforce|adobe|nvidia|intel|amd|twitter|x)\b",
        r"\b(uber|lyft|airbnb|stripe|shopify|spotify|snapchat|tiktok)\b",
    ]

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        neo4j_repo: Optional[Neo4jRepository] = None,
    ):
        """
        Initialize entity extractor.

        Args:
            embedding_service: Service for generating embeddings
            neo4j_repo: Repository for graph queries
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.neo4j_repo = neo4j_repo

    async def extract_entities(
        self, query: str, query_embedding: List[float], user_id: Optional[str] = None
    ) -> List[Entity]:
        """
        Extract entities using multi-strategy approach.

        Args:
            query: User query text
            query_embedding: 384-dim embedding vector
            user_id: Optional user ID for monitoring/logging

        Returns:
            List of Entity objects with confidence scores
        """
        logger.info(f"[EntityExtractor] Extracting entities from: {query[:50]}...")

        entities = []

        # Strategy 1: Regex-based extraction (fast baseline)
        regex_entities = self._extract_regex_entities(query)
        entities.extend(regex_entities)

        # Strategy 2: Semantic matching via graph (if available)
        if self.neo4j_repo:
            try:
                semantic_entities = await self._extract_semantic_entities(
                    query, query_embedding, user_id=user_id
                )
                entities.extend(semantic_entities)
            except Exception as e:
                logger.warning(
                    f"[EntityExtractor] Semantic extraction failed: {e}. "
                    f"Falling back to regex only."
                )

        # Strategy 3: Deduplication and ranking
        entities = self._deduplicate_and_rank(entities)

        logger.info(
            f"[EntityExtractor] Extracted {len(entities)} entities: "
            f"{[e.value for e in entities[:5]]}"
            f"{'...' if len(entities) > 5 else ''}"
        )

        return entities

    def _extract_regex_entities(self, query: str) -> List[Entity]:
        """
        Extract entities using regex patterns (baseline strategy).

        Args:
            query: User query text

        Returns:
            List of Entity objects
        """
        entities = []

        # Extract skills
        for pattern in self.SKILL_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entity_value = match.group(0).lower()
                entities.append(
                    Entity(
                        type="skill",
                        value=entity_value,
                        confidence=0.75,  # Moderate confidence for regex
                        source="regex_match",
                        metadata={"pattern": pattern},
                    )
                )

        # Extract job titles
        for pattern in self.JOB_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entity_value = match.group(0).lower()
                entities.append(
                    Entity(
                        type="job",
                        value=entity_value,
                        confidence=0.70,  # Slightly lower for job titles
                        source="regex_match",
                        metadata={"pattern": pattern},
                    )
                )

        # Extract companies
        for pattern in self.COMPANY_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                entity_value = match.group(0).lower()
                entities.append(
                    Entity(
                        type="company",
                        value=entity_value,
                        confidence=0.90,  # High confidence for company names
                        source="regex_match",
                        metadata={"pattern": pattern},
                    )
                )

        return entities

    async def _extract_semantic_entities(
        self, query: str, query_embedding: List[float], user_id: Optional[str] = None
    ) -> List[Entity]:
        """
        Extract entities using semantic similarity to graph entities.

        Uses vector search to find entities that are semantically similar
        to the query, even if not mentioned explicitly.

        Args:
            query: User query text
            query_embedding: 384-dim embedding vector
            user_id: Optional user ID for monitoring/logging

        Returns:
            List of Entity objects with high confidence
        """
        entities = []

        try:
            # Search for similar skills in graph (monitored query)
            similar_skills = await self.neo4j_repo.vector_search_skills(
                query_embedding=query_embedding,
                k=10,  # Top 10 similar skills
                threshold=0.75,  # High threshold for entity extraction
                user_id=user_id  # Pass through for monitoring
            )

            for skill in similar_skills:
                entities.append(
                    Entity(
                        type="skill",
                        value=skill.get("name", "unknown"),
                        confidence=min(0.95, skill.get("score", 0.75) + 0.05),
                        # Boost confidence slightly for graph-verified entities
                        source="semantic_vector_search",
                        graph_node_id=skill.get("id"),
                        metadata={
                            "similarity_score": skill.get("score"),
                            "description": skill.get("description", ""),
                        },
                    )
                )

        except Exception as e:
            logger.warning(f"[EntityExtractor] Vector search for skills failed: {e}")

        try:
            # Search for similar jobs in graph (monitored query)
            similar_jobs = await self.neo4j_repo.vector_search_jobs(
                query_embedding=query_embedding,
                k=5,  # Top 5 similar jobs
                threshold=0.75,
                user_id=user_id  # Pass through for monitoring
            )

            for job in similar_jobs:
                # Extract job title as entity
                job_title = job.get("job_title", "").lower()
                if job_title:
                    entities.append(
                        Entity(
                            type="job",
                            value=job_title,
                            confidence=min(0.92, job.get("score", 0.75) + 0.05),
                            source="semantic_vector_search",
                            graph_node_id=job.get("job_id"),
                            metadata={
                                "similarity_score": job.get("score"),
                                "company": job.get("company_name", ""),
                                "location": job.get("location", ""),
                            },
                        )
                    )

                # Also extract company as entity
                company_name = job.get("company_name", "").lower()
                if company_name:
                    entities.append(
                        Entity(
                            type="company",
                            value=company_name,
                            confidence=0.85,  # Slightly lower than direct match
                            source="inferred_from_job_search",
                            metadata={"job_id": job.get("job_id")},
                        )
                    )

        except Exception as e:
            logger.warning(f"[EntityExtractor] Vector search for jobs failed: {e}")

        return entities

    def _deduplicate_and_rank(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities and rank by confidence.

        If multiple entities have same (type, value), keep the one with
        highest confidence and best source.

        Args:
            entities: List of entities (may contain duplicates)

        Returns:
            Deduplicated and sorted list of entities
        """
        # Group by (type, value)
        entity_map: Dict[tuple, Entity] = {}

        for entity in entities:
            key = (entity.type, entity.value.lower())

            if key not in entity_map:
                entity_map[key] = entity
            else:
                # Keep entity with higher confidence
                existing = entity_map[key]
                if entity.confidence > existing.confidence:
                    entity_map[key] = entity
                # Prefer semantic sources over regex
                elif (
                    entity.confidence == existing.confidence
                    and entity.source == "semantic_vector_search"
                    and existing.source == "regex_match"
                ):
                    entity_map[key] = entity

        # Convert back to list and sort by confidence
        unique_entities = list(entity_map.values())
        unique_entities.sort(key=lambda e: e.confidence, reverse=True)

        return unique_entities
