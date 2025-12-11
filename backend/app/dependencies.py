"""Dependency injection setup for FastAPI."""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, Header
from prisma import Prisma
from app.repositories.user_repository import UserRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.neo4j_repository import Neo4jRepository
from app.repositories.query_history_repository import QueryHistoryRepository
from app.services.auth_service import AuthService
from app.services.ingestion_service import IngestionService
from app.services.csv_validation_service import CSVValidationService
from app.services.error_logging_service import ErrorLoggingService
from app.services.embedding_service import EmbeddingService
from app.services.batch_processor import BatchProcessor
from app.services.langgraph_service import LangGraphService
from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder
from app.services.openrouter_service import OpenRouterService
from app.config import settings
from app.utils.jwt import verify_jwt_token
from app.models.user import User


def get_prisma() -> Prisma:
    """
    Get Prisma client singleton from main app.

    Returns:
        Prisma client instance
    """
    from app.main import prisma_client
    return prisma_client


def get_user_repository() -> UserRepository:
    """
    Get UserRepository instance.

    Returns:
        UserRepository instance
    """
    return UserRepository(get_prisma())


def get_auth_service() -> AuthService:
    """
    Get AuthService instance.

    Returns:
        AuthService instance
    """
    return AuthService(get_user_repository())


def get_ingestion_repository() -> IngestionRepository:
    """
    Get IngestionRepository instance.

    Returns:
        IngestionRepository instance
    """
    return IngestionRepository(get_prisma())


def get_csv_validation_service() -> CSVValidationService:
    """
    Get CSVValidationService instance.

    Returns:
        CSVValidationService instance
    """
    return CSVValidationService()


def get_embedding_service() -> EmbeddingService:
    """
    Get EmbeddingService instance (singleton).

    Returns:
        EmbeddingService singleton instance with loaded model
    """
    return EmbeddingService()


async def get_batch_processor() -> BatchProcessor:
    """
    Get BatchProcessor instance.

    Returns:
        BatchProcessor instance with all dependencies
    """
    return BatchProcessor(
        neo4j_repo=await get_neo4j_repository(),
        embedding_service=get_embedding_service(),
        error_logger=get_error_logging_service(),
        ingestion_repo=get_ingestion_repository()
    )


async def get_ingestion_service() -> IngestionService:
    """
    Get IngestionService instance.

    Returns:
        IngestionService instance with batch processor for background processing
    """
    return IngestionService(
        get_ingestion_repository(),
        get_csv_validation_service(),
        await get_batch_processor()
    )


def get_error_logging_service() -> ErrorLoggingService:
    """
    Get ErrorLoggingService instance.

    Returns:
        ErrorLoggingService instance
    """
    return ErrorLoggingService(get_prisma())


async def get_neo4j_repository() -> Neo4jRepository:
    """
    Get Neo4jRepository instance with active connection.

    Returns:
        Connected Neo4jRepository instance
    """
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )
    await repo.connect()
    return repo


def get_query_history_repository() -> QueryHistoryRepository:
    """
    Get QueryHistoryRepository instance.

    Returns:
        QueryHistoryRepository instance
    """
    return QueryHistoryRepository(get_prisma())


@lru_cache()
def get_langgraph_service() -> LangGraphService:
    """
    Get LangGraphService instance (cached singleton).

    Returns:
        LangGraphService instance with compiled workflow

    Note (Story 4.7 - ARCH-001):
        This uses @lru_cache to create a singleton pattern for the LangGraphService.
        The workflow compilation is expensive, so we cache the instance.
        Monitor for potential memory leaks or state pollution if the workflow
        maintains state across requests. If issues arise, consider switching
        to request-scoped instances instead of singleton.
    """
    return LangGraphService()


def get_prisma_client() -> Prisma:
    """
    Get Prisma client instance for dependency injection.

    Alias for get_prisma() to match naming convention in monitoring API.

    Returns:
        Prisma client instance
    """
    return get_prisma()


async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[User]:
    """
    Get current authenticated user if token is provided, otherwise return None.

    This is a non-blocking version of get_current_user that allows endpoints
    to optionally use authentication without requiring it.

    Args:
        authorization: Optional Authorization header with Bearer token

    Returns:
        User object if authenticated, None otherwise

    Example:
        >>> @router.get("/data")
        >>> async def get_data(user: Optional[User] = Depends(get_current_user_optional)):
        ...     if user:
        ...         return {"data": "authenticated"}
        ...     return {"data": "anonymous"}
    """
    if not authorization:
        return None

    try:
        # Extract token from "Bearer <token>" format
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None

        # Verify JWT token
        payload = verify_jwt_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            return None

        # Fetch user from database
        user_repo = get_user_repository()
        user = await user_repo.get_user_by_id(user_id)

        return user

    except Exception:
        # Silently fail for optional authentication
        return None


async def get_network_metrics_service() -> NetworkMetricsService:
    """
    Get NetworkMetricsService instance.

    Returns:
        NetworkMetricsService instance with Neo4j repository
    """
    repo = await get_neo4j_repository()
    return NetworkMetricsService(repo)


async def get_co_occurrence_builder() -> CoOccurrenceBuilder:
    """
    Get CoOccurrenceBuilder instance.

    Returns:
        CoOccurrenceBuilder instance with Neo4j repository
    """
    return CoOccurrenceBuilder(repo)


def get_openrouter_service() -> OpenRouterService:
    """
    Get OpenRouterService instance.

    Returns:
        OpenRouterService instance
    """
    return OpenRouterService()
