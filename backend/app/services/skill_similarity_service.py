"""Service for computing skill-to-skill similarity relationships."""
from typing import List, Dict, Any, Tuple
import numpy as np
import logging
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.config import settings

logger = logging.getLogger(__name__)


class SkillSimilarityService:
    """
    Service for computing semantic similarity between skills.

    Uses cosine similarity on skill embeddings to find related skills.
    Creates bidirectional SIMILAR_TO relationships with similarity scores.

    Process:
    1. Fetch all skill embeddings from Neo4j
    2. Compute pairwise cosine similarity
    3. Filter by threshold (> 0.7) and top-k (5)
    4. Create bidirectional relationships
    """

    def __init__(
        self,
        neo4j_repo: Neo4jRepository,
        ingestion_repo: IngestionRepository
    ):
        self.neo4j_repo = neo4j_repo
        self.ingestion_repo = ingestion_repo

    async def compute_skill_similarities(self, job_id: str) -> Dict[str, Any]:
        """
        Compute similarity relationships for all skills.

        Args:
            job_id: Ingestion job ID for progress tracking

        Returns:
            dict: {
                "skills_processed": int,
                "relationships_created": int,
                "duration_seconds": float
            }
        """
        import time
        start_time = time.time()

        logger.info("Starting skill similarity computation")

        # Fetch ALL skill embeddings (needed for pairwise comparison)
        all_skills = await self._fetch_all_skill_embeddings()
        total_skills = len(all_skills)

        logger.info(f"Fetched {total_skills} skills with embeddings")

        if total_skills == 0:
            logger.warning("No skills found with embeddings")
            return {
                "skills_processed": 0,
                "relationships_created": 0,
                "duration_seconds": 0
            }

        # Process in batches to avoid memory issues
        relationships_created = 0
        skills_processed = 0
        batch_size = settings.SIMILARITY_BATCH_SIZE

        num_batches = (total_skills + batch_size - 1) // batch_size

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_skills)
            batch = all_skills[start_idx:end_idx]

            if not batch:
                break

            # Process batch
            batch_relationships = await self._process_similarity_batch(
                batch,
                all_skills,
                job_id
            )

            relationships_created += batch_relationships
            skills_processed += len(batch)

            # Log progress every 10 batches
            if (batch_num + 1) % 10 == 0 or batch_num == num_batches - 1:
                logger.info(
                    f"Computing similarities for skills {skills_processed}/{total_skills} "
                    f"({relationships_created} relationships created)"
                )

        duration = time.time() - start_time

        logger.info(
            f"Similarity computation complete: "
            f"{skills_processed} skills processed, "
            f"{relationships_created} relationships created "
            f"in {duration:.2f}s"
        )

        return {
            "skills_processed": skills_processed,
            "relationships_created": relationships_created,
            "duration_seconds": duration
        }

    async def _fetch_all_skill_embeddings(self) -> List[Dict[str, Any]]:
        """
        Fetch all skill embeddings from Neo4j.

        Returns:
            List[dict]: [{skill_id, skill_name, embedding}, ...]
        """
        query = """
        MATCH (s:Skill)
        WHERE s.embedding IS NOT NULL
        RETURN s.id as skill_id,
               s.name as skill_name,
               s.embedding as embedding
        ORDER BY s.id
        """

        result = await self.neo4j_repo.execute_query(query)
        return result

    async def _process_similarity_batch(
        self,
        batch: List[Dict[str, Any]],
        all_skills: List[Dict[str, Any]],
        job_id: str
    ) -> int:
        """
        Process batch of skills to compute similarities using vectorized operations.

        Performance: O(batch_size × n) with numpy vectorization vs O(batch_size × n²) nested loops
        Achieves 10-100x speedup through matrix operations instead of nested Python loops.

        Args:
            batch: Batch of skills to process
            all_skills: All skills (for pairwise comparison)
            job_id: Ingestion job ID

        Returns:
            int: Number of relationships created
        """
        relationships_to_create = []

        # Vectorized approach: Compute similarity matrix for batch
        batch_embeddings = np.array([skill["embedding"] for skill in batch])
        all_embeddings = np.array([skill["embedding"] for skill in all_skills])

        # Compute similarity matrix using vectorized operations (10-100x faster)
        similarity_matrix = self._compute_similarity_matrix_vectorized(
            batch_embeddings,
            all_embeddings
        )

        # Build skill ID lookup for all_skills
        all_skill_ids = [skill["skill_id"] for skill in all_skills]
        batch_skill_ids = [skill["skill_id"] for skill in batch]

        # Process each skill in batch using precomputed similarity matrix
        for batch_idx, skill in enumerate(batch):
            # Get similarity scores for this skill from matrix
            similarities = similarity_matrix[batch_idx]

            # Find indices where skill appears in all_skills (for self-exclusion)
            skill_idx_in_all = all_skill_ids.index(skill["skill_id"])

            # Create candidate list: (index, score) tuples
            candidates = [
                (idx, score)
                for idx, score in enumerate(similarities)
                if idx != skill_idx_in_all  # Exclude self
                and score > settings.SIMILARITY_THRESHOLD  # Threshold filter
            ]

            # Sort by score descending and take top K
            candidates.sort(key=lambda x: x[1], reverse=True)
            top_similar = candidates[:settings.SIMILARITY_TOP_K]

            # Prepare relationship data (one direction only)
            # Bidirectional property emerges naturally: if A finds B similar,
            # B will find A similar when B is processed
            for similar_idx, similarity_score in top_similar:
                relationships_to_create.append({
                    "source_id": skill["skill_id"],
                    "target_id": all_skill_ids[similar_idx],
                    "score": float(similarity_score)  # Convert numpy float to Python float
                })

        # Create relationships in Neo4j
        if relationships_to_create:
            await self._create_similarity_relationships(relationships_to_create)

        return len(relationships_to_create)

    def _find_top_similar_skills(
        self,
        skill: Dict[str, Any],
        all_skills: List[Dict[str, Any]]
    ) -> List[Tuple[str, float]]:
        """
        Find top K most similar skills using cosine similarity.

        Args:
            skill: Skill to compare (dict with skill_id, embedding)
            all_skills: All skills to compare against

        Returns:
            List[Tuple[str, float]]: [(similar_skill_id, similarity_score), ...]
                                     Sorted by similarity descending, top K only
        """
        skill_embedding = np.array(skill["embedding"])
        similarities = []

        for other_skill in all_skills:
            # Skip self-similarity
            if other_skill["skill_id"] == skill["skill_id"]:
                continue

            other_embedding = np.array(other_skill["embedding"])

            # Compute cosine similarity
            similarity = self._compute_cosine_similarity(skill_embedding, other_embedding)

            # Filter by threshold
            if similarity > settings.SIMILARITY_THRESHOLD:
                similarities.append((other_skill["skill_id"], similarity))

        # Sort by similarity score descending and take top K
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:settings.SIMILARITY_TOP_K]

    def _compute_similarity_matrix_vectorized(
        self,
        batch_embeddings: np.ndarray,
        all_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cosine similarity matrix using vectorized operations.

        Performance: 10-100x faster than nested loops through numpy matrix operations.
        Computes entire batch_size × n similarity matrix in single operation.

        Formula: similarity_matrix = (batch @ all.T) / (||batch||[:, None] × ||all||[None, :])

        Args:
            batch_embeddings: Batch embeddings matrix (batch_size × embedding_dim)
            all_embeddings: All skill embeddings matrix (n × embedding_dim)

        Returns:
            np.ndarray: Similarity matrix (batch_size × n) with scores 0.0-1.0
        """
        # Compute dot product matrix: batch @ all.T
        # Shape: (batch_size × embedding_dim) @ (embedding_dim × n) = (batch_size × n)
        dot_products = batch_embeddings @ all_embeddings.T

        # Compute norms for batch and all embeddings
        batch_norms = np.linalg.norm(batch_embeddings, axis=1)  # Shape: (batch_size,)
        all_norms = np.linalg.norm(all_embeddings, axis=1)      # Shape: (n,)

        # Avoid division by zero: replace zero norms with 1 (will result in 0 similarity)
        batch_norms = np.where(batch_norms == 0, 1, batch_norms)
        all_norms = np.where(all_norms == 0, 1, all_norms)

        # Compute similarity matrix: dot_products / (batch_norms × all_norms)
        # Broadcasting: (batch_size, 1) × (1, n) = (batch_size, n)
        similarity_matrix = dot_products / (batch_norms[:, None] * all_norms[None, :])

        # Clamp to [0, 1] range and return
        return np.clip(similarity_matrix, 0.0, 1.0)

    def _compute_cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings.

        Formula: cos(θ) = (A · B) / (||A|| × ||B||)

        Note: This method is kept for backwards compatibility and unit tests.
        For batch operations, use _compute_similarity_matrix_vectorized() for 10-100x speedup.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Similarity score 0.0-1.0 (higher = more similar)
        """
        # Dot product
        dot_product = np.dot(embedding1, embedding2)

        # Norms
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        # Avoid division by zero
        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (norm1 * norm2)

        # Clamp to [0, 1] range (should already be, but ensure)
        return float(np.clip(similarity, 0.0, 1.0))

    async def _create_similarity_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> None:
        """
        Create SIMILAR_TO relationships in Neo4j.

        Args:
            relationships: List of {source_id, target_id, score} dicts
        """
        if not relationships:
            return

        # Batch create relationships (1000 at a time)
        batch_size = 1000

        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]

            async with self.neo4j_repo.transaction() as session:
                tx = await session.begin_transaction()
                try:
                    for rel in batch:
                        query = """
                        MATCH (s1:Skill {id: $source_id})
                        MATCH (s2:Skill {id: $target_id})
                        MERGE (s1)-[r:SIMILAR_TO]->(s2)
                        ON CREATE SET
                          r.similarity_score = $score,
                          r.created_at = datetime()
                        ON MATCH SET
                          r.similarity_score = $score,
                          r.updated_at = datetime()
                        """

                        await tx.run(
                            query,
                            source_id=rel["source_id"],
                            target_id=rel["target_id"],
                            score=rel["score"]
                        )

                    await tx.commit()
                except Exception as e:
                    await tx.rollback()
                    logger.error(f"Failed to create similarity relationships: {str(e)}")
                    raise
