"""Query API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from time import time
import json
import uuid
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.models.query import (
    QueryRequest,
    QueryResponse,
    NetworkInsights,
    SkillPathResult,
    SimilarJobResult,
    TopSkillResult,
)
from app.services.langgraph_service import LangGraphService
from app.repositories.query_history_repository import QueryHistoryRepository
from app.middleware.auth import get_current_user
from app.dependencies import get_langgraph_service, get_query_history_repository
from app.utils.logger import logger


def serialize_metadata(obj):
    """JSON serializer for objects not serializable by default json encoder."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Configure rate limiter (10 requests per minute per user)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/query", tags=["Query"])


@router.post(
    "/ask",
    response_model=QueryResponse,
    summary="Execute natural language query",
    description="Process a natural language query through the RAG workflow and return AI-generated response"
)
@limiter.limit("10/minute")
async def ask_question(
    request: Request,
    query_data: QueryRequest,
    current_user_id: str = Depends(get_current_user),
    langgraph_service: LangGraphService = Depends(get_langgraph_service),
    query_history_repo: QueryHistoryRepository = Depends(get_query_history_repository)
) -> QueryResponse:
    """
    Process natural language query through RAG workflow.

    Args:
        query_data: User query request
        current_user_id: User ID from JWT token
        langgraph_service: LangGraph workflow service
        query_history_repo: Repository for query logging

    Returns:
        Query response with generated answer, sources, and processing time

    Raises:
        400: Empty query
        401: Invalid or missing JWT token
        422: Validation error
        500: Internal server error (LangGraph execution failure)
    """
    # Validate query (additional checks beyond Pydantic validation)
    query_text = query_data.query.strip()

    if not query_text:
        logger.warning(f"[QueryAPI] Empty query from user={current_user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )

    if len(query_text) < 3:
        logger.warning(f"[QueryAPI] Query too short from user={current_user_id}: {len(query_text)} chars")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query too short. Minimum 3 characters required."
        )

    if len(query_text) > 500:
        logger.warning(f"[QueryAPI] Query too long from user={current_user_id}: {len(query_text)} chars")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query too long. Maximum 500 characters allowed."
        )

    # Session expiration configuration (24 hours)
    SESSION_EXPIRATION_HOURS = 24

    # Generate session_id if not provided (for conversation tracking)
    session_id = query_data.session_id or str(uuid.uuid4())

    # Retrieve conversation history for this session
    conversation_history = []
    if query_data.session_id:  # Only retrieve if session_id was provided (follow-up query)
        try:
            history_records = await query_history_repo.get_conversation_history(
                session_id=session_id,
                limit=5,  # Last 5 messages for context
                max_age_hours=SESSION_EXPIRATION_HOURS
            )

            # Check if session expired (no records found within time window)
            if not history_records:
                logger.info(
                    f"[QueryAPI] Session {session_id[:8]}... expired "
                    f"(no records within {SESSION_EXPIRATION_HOURS}h). Creating new session."
                )
                session_id = str(uuid.uuid4())  # Generate new session
            else:
                conversation_history = [
                    {
                        "query": record.query_text,
                        "response": record.response_text,
                        "timestamp": record.created_at.isoformat()
                    }
                    for record in history_records
                ]
                logger.info(
                    f"[QueryAPI] Retrieved {len(conversation_history)} previous messages "
                    f"for session={session_id[:8]}..."
                )
        except Exception as e:
            logger.warning(
                f"[QueryAPI] Failed to retrieve conversation history: {str(e)}. "
                "Proceeding without history."
            )

    # Start timer
    start_time = time()

    response_text = ""
    sources = []
    metadata = {}

    try:
        # Execute LangGraph workflow with conversation context
        result = await langgraph_service.execute_query(
            query=query_data.query,
            user_id=current_user_id,
            session_id=session_id,
            conversation_history=conversation_history
        )

        response_text = result["response"]
        sources = result["sources"]
        metadata = result.get("metadata", {})

        # Extract context data from result
        constructed_context = result.get("constructed_context", "")
        context_stats = result.get("context_stats", {})

        # Extract and transform network_enrichment to NetworkInsights
        network_insights = None
        network_enrichment = metadata.get("network_enrichment")
        if network_enrichment:
            try:
                network_insights = NetworkInsights(
                    skill_paths=[
                        SkillPathResult(**path) for path in network_enrichment.get("skill_paths", [])
                    ],
                    similar_jobs=[
                        SimilarJobResult(**job) for job in network_enrichment.get("similar_jobs", [])
                    ],
                    top_skills=[
                        TopSkillResult(**skill) for skill in network_enrichment.get("top_skills_by_centrality", [])
                    ],
                    transition_feasibility=network_enrichment.get("transition_feasibility"),
                    graph_stats=network_enrichment.get("graph_stats"),
                )
                logger.info(f"[QueryAPI] Network insights included in response")
            except Exception as insights_error:
                logger.warning(f"[QueryAPI] Failed to transform network insights: {str(insights_error)}")
                # Continue without network insights if transformation fails

        # Get processing time from metrics (more accurate than simple timer)
        processing_time_ms = result.get("processing_time_ms", (time() - start_time) * 1000)

        # Add detailed metrics to metadata
        if "metrics" in result:
            metadata["metrics"] = result["metrics"]

        # Add processing time to metadata
        metadata["processing_time_ms"] = processing_time_ms

        # Store constructed_context in metadata for database logging
        metadata["constructed_context"] = constructed_context
        metadata["context_stats"] = context_stats

        logger.info(
            f"[QueryAPI] Query processed successfully: "
            f"user={current_user_id}, time={processing_time_ms:.2f}ms, sources={len(sources)}, "
            f"context_tokens={context_stats.get('token_count', 0)}"
        )

        # Log to PostgreSQL with session_id for conversation tracking
        try:
            await query_history_repo.create_query_history(
                user_id=current_user_id,
                session_id=session_id,
                query_text=query_data.query,
                response_text=response_text,
                metadata=json.dumps(metadata, default=serialize_metadata)
            )
        except Exception as log_error:
            logger.error(f"[QueryAPI] Failed to log query: {str(log_error)}")
            # Don't fail the request if logging fails

        # Return response with context data
        return QueryResponse(
            query=query_data.query,
            response=response_text,
            sources=sources,
            processing_time_ms=processing_time_ms,
            metadata=metadata,
            constructed_context=constructed_context,
            context_stats=context_stats,
            network_insights=network_insights
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 400 for empty query)
        raise

    except Exception as e:
        processing_time_ms = (time() - start_time) * 1000

        logger.error(
            f"[QueryAPI] Query execution failed: user={current_user_id}, "
            f"error={str(e)}, time={processing_time_ms:.2f}ms"
        )

        # Log failed query to database
        try:
            error_metadata = {
                "error": str(e),
                "processing_time_ms": processing_time_ms
            }
            await query_history_repo.create_query_history(
                user_id=current_user_id,
                session_id=session_id,
                query_text=query_data.query,
                response_text=f"ERROR: {str(e)}",
                metadata=json.dumps(error_metadata)
            )
        except Exception as log_error:
            logger.error(f"[QueryAPI] Failed to log error: {str(log_error)}")

        # Return 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {str(e)}"
        )


@router.get(
    "/history/{query_id}/context",
    summary="Retrieve context for historical query",
    description="Get the constructed context for a previous query by ID (useful for debugging and analysis)"
)
async def get_query_context(
    query_id: str,
    current_user_id: str = Depends(get_current_user),
    query_history_repo: QueryHistoryRepository = Depends(get_query_history_repository)
) -> dict:
    """
    Retrieve constructed context for a historical query.

    This endpoint is useful for:
    - Debugging why a query produced certain results
    - Understanding what data was available to the LLM
    - Analyzing context quality vs response quality

    Args:
        query_id: Query history record ID
        current_user_id: User ID from JWT token
        query_history_repo: Repository for query history operations

    Returns:
        Dictionary with query details and constructed context

    Raises:
        404: Query not found
        403: Access denied (query belongs to different user)
        500: Internal server error
    """
    try:
        # Fetch query history record
        query_record = await query_history_repo.find_by_id(query_id)

        if not query_record:
            logger.warning(f"[QueryAPI] Query not found: query_id={query_id}, user={current_user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Query not found"
            )

        # Verify ownership (user can only access their own queries)
        if query_record.user_id != current_user_id:
            logger.warning(
                f"[QueryAPI] Access denied: query_id={query_id}, "
                f"owner={query_record.user_id}, requester={current_user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: This query belongs to a different user"
            )

        # Extract context from metadata
        metadata = json.loads(query_record.metadata)
        constructed_context = metadata.get("constructed_context", "")
        context_stats = metadata.get("context_stats", {})

        logger.info(
            f"[QueryAPI] Context retrieved: query_id={query_id}, user={current_user_id}, "
            f"context_tokens={context_stats.get('token_count', 0)}"
        )

        # Return context data
        return {
            "query_id": query_id,
            "query": query_record.query_text,
            "response_preview": query_record.response_text[:200] + "..." if len(query_record.response_text) > 200 else query_record.response_text,
            "constructed_context": constructed_context,
            "context_stats": context_stats,
            "created_at": query_record.created_at.isoformat()
        }

    except HTTPException:
        # Re-raise HTTP exceptions (404, 403)
        raise

    except Exception as e:
        logger.error(
            f"[QueryAPI] Failed to retrieve context: query_id={query_id}, "
            f"user={current_user_id}, error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve context: {str(e)}"
        )
