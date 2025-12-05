"""
Admin API endpoints for system management and monitoring.

Provides health checks, monitoring, and administrative operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging

from app.middleware.auth import get_current_user
from app.services.vector_index_service import VectorIndexService
from app.repositories.neo4j_repository import Neo4jRepository
from app.dependencies import get_neo4j_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_vector_index_service(
    neo4j_repo: Neo4jRepository = Depends(get_neo4j_repository)
) -> VectorIndexService:
    """Dependency injection for VectorIndexService."""
    return VectorIndexService(neo4j_repo)


@router.get("/vector-indexes/health")
async def vector_indexes_health(
    user_id: str = Depends(get_current_user),
    vector_index_service: VectorIndexService = Depends(get_vector_index_service)
) -> Dict[str, Any]:
    """
    Check health status of all vector indexes.

    Requires authentication (JWT token in Authorization header).

    Returns:
        dict: {
            "status": "healthy" | "unhealthy",
            "unhealthy_indexes": [...],  # Only if status = "unhealthy"
            "indexes": {
                "skill_embedding_idx": {
                    "exists": true,
                    "state": "ONLINE",
                    "population_percent": 100.0,
                    "entity_count": 15234
                },
                "job_embedding_idx": {...},
                "company_embedding_idx": {...}
            }
        }

    Health Criteria:
    - exists = true (index created)
    - state = "ONLINE" (index ready)
    - population_percent = 100.0 (fully populated)

    Example Response (Healthy):
        {
            "status": "healthy",
            "indexes": {
                "skill_embedding_idx": {
                    "exists": true,
                    "state": "ONLINE",
                    "population_percent": 100.0,
                    "entity_count": 15234
                },
                ...
            }
        }

    Example Response (Unhealthy):
        {
            "status": "unhealthy",
            "unhealthy_indexes": ["company_embedding_idx"],
            "indexes": {
                "skill_embedding_idx": {...},
                "job_embedding_idx": {...},
                "company_embedding_idx": {
                    "exists": true,
                    "state": "POPULATING",
                    "population_percent": 65.5,
                    "entity_count": 5000
                }
            }
        }
    """
    try:
        logger.info(f"Health check requested by user: {user_id}")

        # Get health status of all vector indexes
        health_status = await vector_index_service.verify_vector_indexes()

        # Check if any indexes are unhealthy
        unhealthy = [
            name for name, status in health_status.items()
            if not status.get("exists", False) or status.get("state") != "ONLINE"
        ]

        if unhealthy:
            logger.warning(f"Unhealthy vector indexes detected: {unhealthy}")
            return {
                "status": "unhealthy",
                "unhealthy_indexes": unhealthy,
                "indexes": health_status
            }

        logger.info("All vector indexes are healthy")
        return {
            "status": "healthy",
            "indexes": health_status
        }

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@router.post("/vector-indexes/create")
async def create_vector_indexes(
    user_id: str = Depends(get_current_user),
    vector_index_service: VectorIndexService = Depends(get_vector_index_service)
) -> Dict[str, Any]:
    """
    Create all vector indexes (idempotent operation).

    Requires authentication (JWT token in Authorization header).

    Returns:
        dict: {
            "message": "Vector indexes created successfully",
            "results": {
                "skill_embedding_idx": "created" | "already_exists",
                "job_embedding_idx": "created" | "already_exists",
                "company_embedding_idx": "created" | "already_exists"
            }
        }

    Example Response:
        {
            "message": "Vector indexes created successfully",
            "results": {
                "skill_embedding_idx": "created",
                "job_embedding_idx": "already_exists",
                "company_embedding_idx": "created"
            }
        }
    """
    try:
        logger.info(f"Vector index creation requested by user: {user_id}")

        results = await vector_index_service.create_vector_indexes()

        # Check if any errors occurred
        errors = {k: v for k, v in results.items() if v.startswith("error:")}

        if errors:
            logger.error(f"Vector index creation errors: {errors}")
            return {
                "message": "Vector indexes created with errors",
                "results": results,
                "errors": errors
            }

        logger.info("Vector indexes created successfully")
        return {
            "message": "Vector indexes created successfully",
            "results": results
        }

    except Exception as e:
        logger.error(f"Vector index creation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector index creation failed: {str(e)}"
        )


@router.post("/vector-indexes/{index_name}/rebuild")
async def rebuild_vector_index(
    index_name: str,
    user_id: str = Depends(get_current_user),
    vector_index_service: VectorIndexService = Depends(get_vector_index_service)
) -> Dict[str, Any]:
    """
    Rebuild a corrupted vector index.

    WARNING: Only use if index state != "ONLINE".
    Normal embedding updates do NOT require rebuild (Neo4j 5.x+ auto-updates).

    Args:
        index_name: Name of the index to rebuild
            (skill_embedding_idx | job_embedding_idx | company_embedding_idx)

    Returns:
        dict: {
            "action": "rebuild" | "skip",
            "reason": str,
            "new_state": str
        }

    Example Response (Rebuild):
        {
            "action": "rebuild",
            "reason": "corrupted_state_FAILED",
            "new_state": "ONLINE"
        }

    Example Response (Skip - Healthy):
        {
            "action": "skip",
            "reason": "index_healthy",
            "new_state": "ONLINE"
        }
    """
    try:
        logger.warning(
            f"Vector index rebuild requested by user {user_id}: {index_name}"
        )

        result = await vector_index_service.rebuild_index_if_corrupted(index_name)

        if result["action"] == "skip":
            logger.info(f"Index rebuild skipped: {result['reason']}")
        else:
            logger.info(f"Index rebuilt: {index_name} -> {result['new_state']}")

        return result

    except Exception as e:
        logger.error(f"Vector index rebuild failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector index rebuild failed: {str(e)}"
        )
