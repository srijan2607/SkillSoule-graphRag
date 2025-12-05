"""Embedding generation service using HuggingFace Transformers."""
from sentence_transformers import SentenceTransformer
from typing import List, Optional
from datetime import datetime, UTC
import logging
import time
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Singleton embedding service for generating semantic embeddings.

    Uses sentence-transformers library with all-MiniLM-L6-v2 model.
    Model is loaded once on service initialization (singleton pattern).

    Features:
    - Batch processing (32-64 texts per call)
    - Automatic retry with exponential backoff
    - Version tracking for embedding model migrations
    - Zero vector fallback for empty/None texts
    """

    # Class-level singleton instance
    _instance: Optional['EmbeddingService'] = None
    _model: Optional[SentenceTransformer] = None

    # Model configuration
    CURRENT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    CURRENT_MODEL_VERSION = "all-MiniLM-L6-v2:2024-01"
    EMBEDDING_DIMENSIONS = 384
    BATCH_SIZE = 32  # Optimal for CPU/GPU performance
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = [1, 2, 4]  # Exponential backoff

    def __new__(cls):
        """Singleton pattern: Return same instance on every call."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_model()
        return cls._instance

    def _initialize_model(self) -> None:
        """
        Load sentence-transformer model once on first instantiation.

        This method is called only once due to singleton pattern.
        Subsequent service instantiations reuse the loaded model.
        """
        if self._model is None:
            logger.info(f"Loading embedding model: {self.CURRENT_MODEL_NAME}")
            start_time = time.time()

            self._model = SentenceTransformer(self.CURRENT_MODEL_NAME)

            load_time = time.time() - start_time
            logger.info(
                f"Embedding model loaded successfully in {load_time:.2f}s "
                f"(version: {self.CURRENT_MODEL_VERSION})"
            )

    async def generate_embedding(self, text: str) -> dict:
        """
        Generate 384-dimensional embedding for single text.

        Args:
            text: Input text to embed (can be empty or None)

        Returns:
            dict: {
                "embedding": List[float],  # 384 dimensions
                "model_version": str,      # "all-MiniLM-L6-v2:2024-01"
                "generated_at": datetime   # UTC timestamp
            }

        Example:
            >>> service = EmbeddingService()
            >>> result = await service.generate_embedding("Python programming")
            >>> len(result["embedding"])
            384
        """
        # Handle empty or None text
        if not text or not text.strip():
            logger.warning("Empty text provided, returning zero vector")
            return {
                "embedding": [0.0] * self.EMBEDDING_DIMENSIONS,
                "model_version": self.CURRENT_MODEL_VERSION,
                "generated_at": datetime.now(UTC)
            }

        # Generate embedding with retry logic
        embedding_vector = await self._generate_with_retry([text])

        return {
            "embedding": embedding_vector[0].tolist(),
            "model_version": self.CURRENT_MODEL_VERSION,
            "generated_at": datetime.now(UTC)
        }

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[dict]:
        """
        Generate embeddings for batch of texts.

        Args:
            texts: List of input texts (can contain empty/None values)
            batch_size: Custom batch size (default: 32)

        Returns:
            List[dict]: List of embedding dicts (same format as generate_embedding)

        Performance:
            - CPU: ~100-150 embeddings/second
            - GPU: ~500-1000 embeddings/second

        Example:
            >>> texts = ["Python", "JavaScript", "Java", ""]
            >>> results = await service.generate_batch_embeddings(texts)
            >>> len(results)
            4
            >>> results[3]["embedding"]  # Empty text
            [0.0, 0.0, 0.0, ...]  # Zero vector
        """
        if not texts:
            return []

        batch_size = batch_size or self.BATCH_SIZE
        results = []

        # Process texts in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Separate empty and valid texts
            valid_indices = []
            valid_texts = []

            for idx, text in enumerate(batch):
                if text and text.strip():
                    valid_indices.append(i + idx)
                    valid_texts.append(text)

            # Generate embeddings for valid texts
            if valid_texts:
                embeddings = await self._generate_with_retry(valid_texts, batch_size)

                # Map embeddings back to original indices
                embedding_map = {
                    valid_indices[j]: embeddings[j].tolist()
                    for j in range(len(valid_texts))
                }
            else:
                embedding_map = {}

            # Build results with zero vectors for empty texts
            for idx in range(i, min(i + batch_size, len(texts))):
                if idx in embedding_map:
                    embedding = embedding_map[idx]
                else:
                    embedding = [0.0] * self.EMBEDDING_DIMENSIONS

                results.append({
                    "embedding": embedding,
                    "model_version": self.CURRENT_MODEL_VERSION,
                    "generated_at": datetime.now(UTC)
                })

        logger.info(
            f"Generated {len(results)} embeddings "
            f"({len([r for r in results if r['embedding'][0] != 0.0])} non-zero)"
        )

        return results

    async def _generate_with_retry(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ):
        """
        Generate embeddings with retry logic and exponential backoff.

        Args:
            texts: List of valid (non-empty) texts
            batch_size: Batch size for encoding

        Returns:
            numpy.ndarray: Embeddings array

        Raises:
            RuntimeError: If all retries fail
        """
        batch_size = batch_size or self.BATCH_SIZE

        for attempt in range(self.MAX_RETRIES):
            try:
                # Generate embeddings using SentenceTransformer
                embeddings = self._model.encode(
                    texts,
                    convert_to_tensor=False,
                    batch_size=batch_size,
                    show_progress_bar=False
                )

                # Validate dimensions
                if embeddings.shape[1] != self.EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Invalid embedding dimensions: {embeddings.shape[1]} "
                        f"(expected {self.EMBEDDING_DIMENSIONS})"
                    )

                return embeddings

            except Exception as e:
                attempt_num = attempt + 1

                if attempt_num < self.MAX_RETRIES:
                    backoff_time = self.RETRY_BACKOFF_SECONDS[attempt]
                    logger.warning(
                        f"Embedding generation failed (attempt {attempt_num}/{self.MAX_RETRIES}): {str(e)}. "
                        f"Retrying in {backoff_time}s..."
                    )
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(
                        f"Embedding generation failed after {self.MAX_RETRIES} attempts: {str(e)}"
                    )
                    raise RuntimeError(
                        f"Failed to generate embeddings after {self.MAX_RETRIES} retries"
                    ) from e
