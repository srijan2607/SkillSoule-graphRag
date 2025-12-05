"""LangGraph RAG workflow execution service."""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from app.agents.graph import GraphRAGState, create_rag_workflow
from app.models.query import SourceNode
from app.utils.logger import logger
from app.utils.metrics import QueryMetrics


class LangGraphService:
    """Service for executing LangGraph RAG workflow."""

    def __init__(self):
        """Initialize LangGraph service with compiled workflow."""
        self.workflow = create_rag_workflow()
        logger.info("[LangGraphService] Workflow compiled successfully")

    async def execute_query(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute RAG workflow for a user query with conversation context.

        Args:
            query: Natural language query text
            user_id: ID of user making the query
            session_id: Optional session ID for tracking query processing
            conversation_history: Optional list of previous Q&A pairs in this conversation

        Returns:
            Dictionary with:
                - response (str): Generated response
                - sources (List[SourceNode]): Source nodes cited
                - metadata (dict): Additional execution metadata

        Raises:
            Exception: If workflow execution fails
        """
        try:
            history_context = ""
            if conversation_history:
                logger.info(
                    f"[LangGraphService] Executing query with {len(conversation_history)} "
                    f"previous messages for session={session_id[:8] if session_id else 'new'}..."
                )
                # Format conversation history for context
                history_context = "\n".join([
                    f"User: {msg['query']}\nAssistant: {msg['response'][:200]}..."
                    for msg in conversation_history
                ])
            else:
                logger.info(
                    f"[LangGraphService] Executing query for user={user_id}, "
                    f"session={session_id[:8] if session_id else 'new'}: {query[:50]}..."
                )

            # Create QueryMetrics instance for timing collection
            query_id = str(uuid.uuid4())
            metrics = QueryMetrics(query_id=query_id, user_id=user_id, query_text=query)

            # Create initial state with metrics, session_id, and conversation history in metadata
            initial_state = GraphRAGState(
                user_query=query,
                user_id=user_id,
                metadata={
                    "metrics": metrics,
                    "query_id": query_id,
                    "session_id": session_id,
                    "conversation_history": conversation_history or [],
                    "history_context": history_context
                },
            )

            # Execute workflow with 200-second timeout for reasoning models (DeepSeek-R1, o1, etc.)
            # Increased from 60s to support multi-intent queries + reasoning models
            try:
                result = await asyncio.wait_for(
                    self.workflow.ainvoke(initial_state),
                    timeout=200.0,  # 3min 20sec buffer for reasoning models
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"[LangGraphService] Workflow execution timed out after 200 seconds for user={user_id}"
                )
                raise Exception(
                    "Query processing timed out. This query is very complex - please try breaking it into smaller questions."
                )

            # Extract response
            response_text = result.get("final_response", "")
            if not response_text:
                logger.warning("[LangGraphService] Empty response generated")
                response_text = "I apologize, but I couldn't generate a response for your query. Please try rephrasing."

            # Extract sources from vector and graph results
            sources = self._extract_sources(result)

            # Extract metadata
            metadata = result.get("metadata", {})
            metadata["intent"] = result.get("intent")

            # Log metrics (JSON format) and check performance targets
            metrics.log_metrics()

            # Extract metrics summary for response
            metrics_summary = metrics.to_dict()
            total_time_ms = metrics.get_total_time()

            # Extract constructed_context from state
            constructed_context = result.get("constructed_context", "")

            # Build context_stats from metadata
            context_stats = {
                "token_count": metadata.get("context_token_count", 0),
                "char_count": metadata.get("context_char_count", 0),
                "truncated": metadata.get("context_truncated", False),
                "vector_results_count": metadata.get("vector_results_count", 0),
                "graph_nodes_count": metadata.get("graph_nodes_count", 0)
            }

            logger.info(
                f"[LangGraphService] Query executed successfully: {len(sources)} sources, "
                f"total_time={total_time_ms:.2f}ms, context_tokens={context_stats['token_count']}"
            )

            return {
                "response": response_text,
                "sources": sources,
                "metadata": metadata,
                "processing_time_ms": total_time_ms,
                "metrics": metrics_summary,
                "constructed_context": constructed_context,
                "context_stats": context_stats
            }

        except Exception as e:
            logger.error(f"[LangGraphService] Workflow execution failed: {str(e)}", exc_info=True)
            raise Exception(f"Failed to execute query: {str(e)}")

    def _extract_sources(self, state: Dict[str, Any]) -> List[SourceNode]:
        """
        Extract and deduplicate source nodes from workflow state.

        Args:
            state: Final workflow state

        Returns:
            List of SourceNode objects
        """
        sources = []
        seen_node_ids = set()

        # Extract from vector_results
        vector_results = state.get("vector_results", [])
        if vector_results:
            for item in vector_results:
                node_id = item.get("id") or item.get("node_id")
                if node_id and node_id not in seen_node_ids:
                    sources.append(
                        SourceNode(
                            node_type=item.get("label") or item.get("type", "Unknown"),
                            node_id=node_id,
                            properties=item.get("properties", {}),
                        )
                    )
                    seen_node_ids.add(node_id)

        # Extract from graph_context
        graph_context = state.get("graph_context", [])
        if graph_context:
            for item in graph_context:
                # Skip relationships (they have 'type' but no 'node_id')
                if item.get("type") and not item.get("node_id") and not item.get("node_type"):
                    continue

                # Handle node objects
                if "nodes" in item:
                    for node in item["nodes"]:
                        node_id = node.get("id") or node.get("node_id")
                        if node_id and node_id not in seen_node_ids:
                            sources.append(
                                SourceNode(
                                    node_type=node.get("node_type") or node.get("label") or node.get("type", "Unknown"),
                                    node_id=node_id,
                                    properties=node.get("properties", {}),
                                )
                            )
                            seen_node_ids.add(node_id)
                # Handle direct node references from graph traversal
                else:
                    node_id = item.get("id") or item.get("node_id")
                    if node_id and node_id not in seen_node_ids:
                        sources.append(
                            SourceNode(
                                node_type=item.get("node_type") or item.get("label") or item.get("type", "Unknown"),
                                node_id=node_id,
                                properties=item.get("properties", {}),
                            )
                        )
                        seen_node_ids.add(node_id)

        logger.info(f"[LangGraphService] Extracted {len(sources)} unique sources")
        return sources
