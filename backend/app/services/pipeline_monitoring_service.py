"""
Pipeline Monitoring Service for RAG Workflow Stage Tracking.

Tracks and broadcasts real-time progress through the 5-stage RAG pipeline:
1. Query Understanding (Intent Classification + Entity Extraction)
2. Vector Search (Semantic Similarity)
3. Graph Traversal (Relationship Navigation)
4. Context Construction (Knowledge Assembly)
5. Response Generation (LLM Completion)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """RAG pipeline stages."""
    QUERY_UNDERSTANDING = "query_understanding"
    VECTOR_SEARCH = "vector_search"
    GRAPH_TRAVERSAL = "graph_traversal"
    CONTEXT_CONSTRUCTION = "context_construction"
    RESPONSE_GENERATION = "response_generation"


class StageStatus(str, Enum):
    """Stage execution status."""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStageEvent:
    """
    Represents a single pipeline stage event.
    """
    stage: str
    status: str
    session_id: str
    user_id: str
    query: str
    timestamp: datetime
    duration_ms: Optional[float] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "stage": self.stage,
            "status": self.status,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "results": self.results,
            "error": self.error,
            "metadata": self.metadata
        }


class PipelineMonitoringService:
    """
    Service for monitoring and broadcasting RAG pipeline execution stages.

    Features:
    - Real-time stage tracking
    - WebSocket broadcasting to connected clients
    - Performance metrics per stage
    - Error tracking and reporting
    """

    def __init__(self):
        """Initialize pipeline monitoring service."""
        # WebSocket connections for real-time streaming
        self._websocket_connections: List[Any] = []

        # Active session tracking
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    async def emit_stage_event(
        self,
        stage: PipelineStage,
        status: StageStatus,
        session_id: str,
        user_id: str,
        query: str,
        duration_ms: Optional[float] = None,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a pipeline stage event to all connected WebSocket clients.

        Args:
            stage: Pipeline stage (query_understanding, vector_search, etc.)
            status: Stage status (started, completed, failed)
            session_id: Session identifier
            user_id: User identifier
            query: Original user query
            duration_ms: Stage execution time in milliseconds
            results: Stage results (intent, entities, search results, etc.)
            error: Error message if failed
            metadata: Additional metadata
        """
        event = PipelineStageEvent(
            stage=stage.value,
            status=status.value,
            session_id=session_id,
            user_id=user_id,
            query=query,
            timestamp=datetime.utcnow(),
            duration_ms=duration_ms,
            results=results,
            error=error,
            metadata=metadata
        )

        # Log event
        session_display = session_id[:8] + "..." if session_id else "unknown"
        logger.info(
            f"[PipelineMonitor] {stage.value} | {status.value} | "
            f"session={session_display} | duration={duration_ms}ms"
        )

        # Broadcast to WebSocket connections
        await self._broadcast_to_websockets(event)

        # Track in active sessions
        self._track_session_stage(session_id, event)

    async def emit_query_understanding(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Emit query understanding stage event.

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            intent: Detected intent (skill_requirement, career_path, etc.)
            confidence: Intent confidence score (0-1)
            entities: Extracted entities
            error: Error message if failed
        """
        results = None
        if intent:
            results = {
                "intent": intent,
                "confidence": confidence,
                "entities": entities or [],
                "entity_count": len(entities) if entities else 0
            }

        await self.emit_stage_event(
            stage=PipelineStage.QUERY_UNDERSTANDING,
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error
        )

    async def emit_vector_search(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        skills_found: int = 0,
        jobs_found: int = 0,
        companies_found: int = 0,
        total_results: int = 0,
        threshold: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Emit vector search stage event.

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            skills_found: Number of skills found
            jobs_found: Number of jobs found
            companies_found: Number of companies found
            total_results: Total results across all types
            threshold: Similarity threshold used
            error: Error message if failed
        """
        results = {
            "skills_found": skills_found,
            "jobs_found": jobs_found,
            "companies_found": companies_found,
            "total_results": total_results,
            "threshold": threshold
        }

        await self.emit_stage_event(
            stage=PipelineStage.VECTOR_SEARCH,
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error
        )

    async def emit_graph_traversal(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        nodes_accessed: int = 0,
        relationships_traversed: int = 0,
        traversal_patterns: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Emit graph traversal stage event.

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            nodes_accessed: Number of nodes accessed
            relationships_traversed: Number of relationships traversed
            traversal_patterns: Patterns used (e.g., ["REQUIRES", "SIMILAR_TO"])
            error: Error message if failed
        """
        results = {
            "nodes_accessed": nodes_accessed,
            "relationships_traversed": relationships_traversed,
            "traversal_patterns": traversal_patterns or []
        }

        await self.emit_stage_event(
            stage=PipelineStage.GRAPH_TRAVERSAL,
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error
        )

    async def emit_network_enrichment(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        skill_paths_count: int = 0,
        top_skills_count: int = 0,
        similar_jobs_count: int = 0,
        has_transition_metrics: bool = False,
        enrichment_intents: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Emit network enrichment stage event (Story 7.4).

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            skill_paths_count: Number of skill paths computed
            top_skills_count: Number of top skills retrieved
            similar_jobs_count: Number of similar jobs found
            has_transition_metrics: Whether transition metrics were calculated
            enrichment_intents: Intents processed (e.g., ["skill_bridge", "skill_importance"])
            error: Error message if failed
        """
        results = {
            "skill_paths_count": skill_paths_count,
            "top_skills_count": top_skills_count,
            "similar_jobs_count": similar_jobs_count,
            "has_transition_metrics": has_transition_metrics,
            "enrichment_intents": enrichment_intents or []
        }

        await self.emit_stage_event(
            stage=PipelineStage.GRAPH_TRAVERSAL,  # Using existing stage enum for now
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error,
            metadata={"enrichment_type": "network_metrics"}
        )

    async def emit_context_construction(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        context_length: int = 0,
        tokens_used: Optional[int] = None,
        truncated: bool = False,
        error: Optional[str] = None
    ) -> None:
        """
        Emit context construction stage event.

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            context_length: Context length in characters
            tokens_used: Approximate token count
            truncated: Whether context was truncated
            error: Error message if failed
        """
        results = {
            "context_length_chars": context_length,
            "tokens_estimated": tokens_used,
            "truncated": truncated
        }

        await self.emit_stage_event(
            stage=PipelineStage.CONTEXT_CONSTRUCTION,
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error
        )

    async def emit_response_generation(
        self,
        session_id: str,
        user_id: str,
        query: str,
        status: StageStatus,
        duration_ms: Optional[float] = None,
        response_length: int = 0,
        llm_model: Optional[str] = None,
        tokens_used: Optional[int] = None,
        retry_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """
        Emit response generation stage event.

        Args:
            session_id: Session ID
            user_id: User ID
            query: User query
            status: Stage status
            duration_ms: Execution time
            response_length: Response length in characters
            llm_model: LLM model used
            tokens_used: Tokens consumed
            retry_count: Number of retries needed
            error: Error message if failed
        """
        results = {
            "response_length_chars": response_length,
            "llm_model": llm_model,
            "tokens_used": tokens_used,
            "retry_count": retry_count
        }

        await self.emit_stage_event(
            stage=PipelineStage.RESPONSE_GENERATION,
            status=status,
            session_id=session_id,
            user_id=user_id,
            query=query,
            duration_ms=duration_ms,
            results=results,
            error=error
        )

    def register_websocket(self, websocket: Any) -> None:
        """Register a WebSocket connection for real-time pipeline monitoring."""
        self._websocket_connections.append(websocket)
        logger.info(
            f"[PipelineMonitor] WebSocket registered. "
            f"Total connections: {len(self._websocket_connections)}"
        )

    def unregister_websocket(self, websocket: Any) -> None:
        """Unregister a WebSocket connection."""
        if websocket in self._websocket_connections:
            self._websocket_connections.remove(websocket)
            logger.info(
                f"[PipelineMonitor] WebSocket unregistered. "
                f"Total connections: {len(self._websocket_connections)}"
            )

    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Get current pipeline progress for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with stage completion status and metrics
        """
        return self._active_sessions.get(session_id, {})

    async def _broadcast_to_websockets(self, event: PipelineStageEvent) -> None:
        """Broadcast pipeline stage event to all connected WebSockets."""
        if not self._websocket_connections:
            return

        message = json.dumps({
            "type": "pipeline_stage",
            **event.to_dict()
        })

        # Remove disconnected connections
        disconnected = []
        for ws in self._websocket_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning(f"[PipelineMonitor] WebSocket send failed: {str(e)}")
                disconnected.append(ws)

        # Clean up disconnected connections
        for ws in disconnected:
            self.unregister_websocket(ws)

    def _track_session_stage(
        self,
        session_id: str,
        event: PipelineStageEvent
    ) -> None:
        """Track stage completion in active sessions."""
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = {
                "started_at": event.timestamp,
                "stages": {}
            }

        self._active_sessions[session_id]["stages"][event.stage] = {
            "status": event.status,
            "duration_ms": event.duration_ms,
            "completed_at": event.timestamp
        }

        # Clean up old sessions (keep last 100)
        if len(self._active_sessions) > 100:
            oldest_sessions = sorted(
                self._active_sessions.keys(),
                key=lambda k: self._active_sessions[k]["started_at"]
            )[:10]
            for old_session in oldest_sessions:
                del self._active_sessions[old_session]


# Global pipeline monitoring service instance
_pipeline_monitoring_service: Optional[PipelineMonitoringService] = None


def get_pipeline_monitoring_service() -> PipelineMonitoringService:
    """
    Get or create the global pipeline monitoring service instance.

    Returns:
        PipelineMonitoringService instance
    """
    global _pipeline_monitoring_service
    if _pipeline_monitoring_service is None:
        _pipeline_monitoring_service = PipelineMonitoringService()
    return _pipeline_monitoring_service
