"""
Graph Traversal Node - Traverses Neo4j graph based on query intent.

This node receives vector search results and query intent, then performs
intent-based graph traversal to discover related nodes and relationships.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.agents.graph import GraphRAGState
from app.utils.logger import logger
from app.dependencies import get_neo4j_repository
from app.utils.metrics import QueryMetrics
from app.config import settings
from app.services.pipeline_monitoring_service import (
    get_pipeline_monitoring_service,
    StageStatus
)


def generate_traversal_query(
    intent: str, seed_node_ids: List[str], node_type: str, depth: int = None
) -> Optional[str]:
    """
    Generate intent-specific Cypher traversal query.

    Args:
        intent: Query intent type
        seed_node_ids: List of node IDs to start traversal from
        node_type: Type of seed nodes ("Skill", "Job", "Company")
        depth: Traversal depth (uses settings.GRAPH_TRAVERSAL_DEPTH if None)

    Returns:
        Cypher query string or None if intent not recognized
    """
    if not seed_node_ids:
        return None

    # Use configured depth if not provided
    if depth is None:
        depth = settings.GRAPH_TRAVERSAL_DEPTH

    # Validate depth parameter (1-5 range for deep traversal)
    depth = max(1, min(depth, 5))

    # Get configured LIMIT for Cypher queries
    cypher_limit = settings.GRAPH_CYPHER_LIMIT

    # Base queries for each intent type
    # Note: Using variable-length patterns [*1..{depth}] for configurable traversal depth

    # Adaptive career_path query based on seed node type
    if node_type == "Skill":
        career_path_query = f"""
            MATCH (s:Skill) WHERE s.id IN $seed_ids
            MATCH path1 = (s)-[sim:SIMILAR_TO*1..{depth}]-(similar:Skill)
            MATCH (j:Job)-[req:REQUIRES]->(s)
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
            WITH DISTINCT s, sim, similar, j, req, cat
            RETURN
                s AS skill_node,
                sim AS similar_rel,
                similar AS similar_skill_node,
                j AS job_node,
                req AS requires_rel,
                cat AS category_node
            LIMIT {cypher_limit}
        """
    else:  # Job nodes or other types
        career_path_query = f"""
            MATCH (j:Job) WHERE j.job_id IN $seed_ids
            MATCH (j)-[req1:REQUIRES]->(s:Skill)
            MATCH (s)-[sim:SIMILAR_TO*1..{depth}]-(similar:Skill)
            MATCH (j2:Job)-[req2:REQUIRES]->(similar)
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
            WITH DISTINCT j, req1, s, sim, similar, j2, req2, cat
            RETURN
                j AS job_node,
                req1 AS requires_rel,
                s AS skill_node,
                sim AS similar_rel,
                similar AS similar_skill_node,
                j2 AS related_job_node,
                req2 AS related_requires_rel,
                cat AS category_node
            LIMIT {cypher_limit}
        """

    queries = {
        "skill_requirement": f"""
            MATCH (j:Job) WHERE j.job_id IN $seed_ids
            MATCH path = (j)-[req:REQUIRES*1..{depth}]->(s:Skill)
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
            OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
            WITH DISTINCT j, req, s, cat, sub
            RETURN
                j AS job_node,
                req AS requires_rel,
                s AS skill_node,
                cat AS category_node,
                sub AS subcategory_node
            LIMIT {cypher_limit}
        """,
        "career_path": career_path_query,
        "salary_analysis": f"""
            MATCH (j:Job) WHERE j.job_id IN $seed_ids
            MATCH (j)-[:REQUIRES]->(s:Skill)
            MATCH (j)-[:POSTED_BY]->(c:Company)
            OPTIONAL MATCH (j)-[:LOCATED_IN]->(loc:Location)
            WITH DISTINCT j, s, c, loc
            RETURN
                j AS job_node,
                s AS skill_node,
                c AS company_node,
                loc AS location_node
            ORDER BY j.max_salary DESC
            LIMIT {cypher_limit}
        """,
        "skill_relationship": f"""
            MATCH (s:Skill) WHERE s.id IN $seed_ids
            OPTIONAL MATCH path = (s)-[sim:SIMILAR_TO*1..{depth}]-(related:Skill)
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:Category)
            OPTIONAL MATCH (s)-[:BELONGS_TO_SUBCATEGORY]->(sub:Subcategory)
            WITH DISTINCT s, sim, related, cat, sub
            RETURN
                s AS skill_node,
                sim AS similar_rel,
                related AS related_skill_node,
                cat AS category_node,
                sub AS subcategory_node
            LIMIT {cypher_limit}
        """,
        "company_query": f"""
            MATCH (j:Job) WHERE j.job_id IN $seed_ids
            MATCH (j)-[:POSTED_BY]->(c:Company)
            MATCH (j)-[:REQUIRES]->(s:Skill)
            OPTIONAL MATCH (j)-[:LOCATED_IN]->(loc:Location)
            OPTIONAL MATCH (c)-[:POSTED_BY]-(other_jobs:Job)
            OPTIONAL MATCH (other_jobs)-[:REQUIRES]->(related_skills:Skill)
            WITH DISTINCT c, j, s, loc, other_jobs, related_skills
            RETURN
                c AS company_node,
                j AS job_node,
                s AS skill_node,
                loc AS location_node,
                other_jobs AS related_job_node,
                related_skills AS related_skill_node
            LIMIT {cypher_limit}
        """,
    }

    return queries.get(intent)


def sanitize_neo4j_value(value: Any) -> Any:
    """
    Convert Neo4j-specific types to Python-serializable types.

    Args:
        value: Any value that might contain Neo4j types

    Returns:
        Python-serializable value
    """
    # Handle Neo4j DateTime objects
    if hasattr(value, '__class__') and 'neo4j' in value.__class__.__module__:
        if hasattr(value, 'to_native'):
            return value.to_native()
        elif hasattr(value, 'iso_format'):
            return value.iso_format()
        else:
            return str(value)

    # Handle dictionaries recursively
    if isinstance(value, dict):
        return {k: sanitize_neo4j_value(v) for k, v in value.items()}

    # Handle lists recursively
    if isinstance(value, list):
        return [sanitize_neo4j_value(item) for item in value]

    # Return as-is for standard Python types
    return value


def extract_seed_node_ids(
    vector_results: List[Dict[str, Any]], top_k: int = None
) -> tuple[List[str], str]:
    """
    Extract seed node IDs from vector search results.

    Args:
        vector_results: Vector search results with node_type and id
        top_k: Number of top results to use as seeds (uses settings.GRAPH_SEED_NODES if None)

    Returns:
        Tuple of (seed_node_ids, node_type)
    """
    if not vector_results:
        return [], ""

    # Use configured seed node count if not provided
    if top_k is None:
        top_k = settings.GRAPH_SEED_NODES

    # Take top K results as seed nodes
    top_results = vector_results[:top_k]

    # Extract IDs and determine node type from first result
    seed_ids = [result.get("id") for result in top_results if result.get("id")]
    node_type = top_results[0].get("node_type", "") if top_results else ""

    return seed_ids, node_type


def format_graph_results(raw_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Format raw Neo4j results into structured graph context.

    Args:
        raw_results: Raw results from Neo4j query

    Returns:
        Structured dict with {nodes: [...], relationships: [...]}\n"""
    # Node type inference mapping based on key patterns
    NODE_TYPE_PATTERNS = {
        "skill": "Skill",
        "job": "Job",
        "company": "Company",
        "category": "Category",
        "subcategory": "Subcategory",
        "location": "Location",
    }

    nodes = []
    relationships = []
    seen_nodes = set()
    seen_relationships = set()

    for record in raw_results:
        for key, value in record.items():
            if value is None:
                continue

            # Handle node objects (check for common node properties)
            if isinstance(value, dict) and any(
                prop in value for prop in ["id", "job_id", "company_name", "category_id"]
            ):
                # Determine node type and ID
                node_id = (
                    value.get("id")
                    or value.get("job_id")
                    or value.get("company_name")
                    or value.get("category_id")
                    or value.get("subcategory_id")
                )

                if node_id and node_id not in seen_nodes:
                    # Infer node type from key name using pattern matching
                    node_type = "Unknown"
                    key_lower = key.lower()
                    for pattern, type_name in NODE_TYPE_PATTERNS.items():
                        if pattern in key_lower:
                            node_type = type_name
                            break

                    # Sanitize properties to remove Neo4j-specific types
                    properties = {
                        k: sanitize_neo4j_value(v) for k, v in value.items() if k not in ["id", "job_id"]
                    }

                    # Extract name field for better display
                    name = None
                    if "name" in value:
                        name = value["name"]
                    elif "skill_name" in value:
                        name = value["skill_name"]
                    elif "company_name" in value:
                        name = value["company_name"]
                    elif "job_title" in value:
                        name = value["job_title"]
                    elif "category_name" in value:
                        name = value["category_name"]

                    node_data = {
                        "node_id": node_id,
                        "node_type": node_type,
                        "properties": properties,
                    }

                    # Add name field if found
                    if name:
                        node_data["name"] = name

                    nodes.append(node_data)
                    seen_nodes.add(node_id)

            # Handle relationship objects (check for _rel suffix in alias names)
            # Neo4j queries use aliases like requires_rel, similar_rel, etc.
            # Note: Variable-length patterns like [r:REQUIRES*1..2] return LISTS of relationships
            elif key.endswith("_rel"):
                # Handle both single relationships and lists of relationships
                rel_values = value if isinstance(value, list) else [value] if value else []

                for rel_obj in rel_values:
                    if rel_obj is None:
                        continue

                    # Neo4j Python driver returns Relationship objects, not dicts
                    # Extract type from the relationship object
                    if hasattr(rel_obj, 'type'):
                        rel_type = rel_obj.type
                    elif isinstance(rel_obj, dict) and "type" in rel_obj:
                        rel_type = rel_obj.get("type")
                    else:
                        rel_type = key.replace("_rel", "").upper()

                    # Extract properties
                    if hasattr(rel_obj, 'items'):
                        # It's a dict-like object
                        rel_props = {k: v for k, v in rel_obj.items() if k != "type"}
                    elif hasattr(rel_obj, '__dict__'):
                        # It's a Relationship object - access properties attribute
                        rel_props = dict(rel_obj.get('properties', {})) if hasattr(rel_obj, 'get') else {}
                    else:
                        rel_props = {}

                    # Sanitize properties to remove Neo4j-specific types
                    rel_props = {k: sanitize_neo4j_value(v) for k, v in rel_props.items()}

                    # Create a unique relationship identifier
                    rel_id = f"{rel_type}_{id(rel_obj)}"

                    if rel_id not in seen_relationships:
                        relationships.append(
                            {
                                "type": rel_type,
                                "properties": rel_props,
                            }
                        )
                        seen_relationships.add(rel_id)

    # Apply configured limits (0 = unlimited)
    max_nodes = settings.GRAPH_MAX_NODES if settings.GRAPH_MAX_NODES > 0 else len(nodes)
    max_rels = settings.GRAPH_MAX_RELATIONSHIPS if settings.GRAPH_MAX_RELATIONSHIPS > 0 else len(relationships)

    return {
        "nodes": nodes[:max_nodes],
        "relationships": relationships[:max_rels],
    }


async def graph_traversal_node(state: GraphRAGState) -> Dict[str, Any]:
    """
    Traverse Neo4j graph based on query intents and vector results.

    MULTI-INTENT SUPPORT: This node now handles multiple detected intents,
    running separate Cypher queries for each intent and merging results.

    This node performs intent-based graph traversal starting from seed nodes
    identified in vector search results. It discovers related nodes and
    relationships to enrich the context for response generation.

    Args:
        state: Current graph state with vector_results and intents

    Returns:
        Dict with graph_results containing nodes and relationships
    """
    # Start timing
    metrics = state.metadata.get("metrics")
    if isinstance(metrics, QueryMetrics):
        metrics.start_timer("graph_traversal")

    # Get pipeline monitoring
    pipeline_monitor = get_pipeline_monitoring_service()
    session_id = state.metadata.get("session_id", "unknown")
    user_id = state.metadata.get("user_id", "unknown")

    # Emit stage started
    await pipeline_monitor.emit_graph_traversal(
        session_id=session_id,
        user_id=user_id,
        query=state.user_query,
        status=StageStatus.STARTED
    )

    try:
        vector_results = state.vector_results or []
        # Support both multi-intent (new) and single-intent (backward compatibility)
        intents = state.intents or [state.intent] if state.intent else ["general"]

        logger.info(
            f"[GraphTraversal] Starting multi-intent traversal | "
            f"intents={intents} | vector_results={len(vector_results)}"
        )

        # Handle cases with no vector results or unknown intents
        if not vector_results or all(i in ["general", "unknown"] for i in intents):
            logger.info("[GraphTraversal] No traversal needed - returning empty context")
            return {
                "graph_context": [],
                "metadata": {
                    **state.metadata,
                    "graph_traversal_skipped": True,
                    "skip_reason": "no_vector_results" if not vector_results else "general_intent",
                },
            }

        # Extract seed node IDs from vector results (uses configured GRAPH_SEED_NODES)
        seed_ids, node_type = extract_seed_node_ids(vector_results)

        logger.info(
            f"[GraphTraversal] Extracted seed nodes | "
            f"node_type={node_type} | seed_ids={seed_ids[:5]}... | total={len(seed_ids)}"
        )

        if not seed_ids:
            logger.warning("[GraphTraversal] No valid seed IDs found in vector results")
            return {
                "graph_context": [],
                "metadata": {**state.metadata, "graph_traversal_error": "no_seed_ids"},
            }

        # Execute queries for ALL detected intents and merge results
        neo4j_repo = await get_neo4j_repository()

        try:
            all_raw_results = []
            executed_intents = []

            # Run query for EACH intent
            for intent in intents:
                if intent in ["general", "unknown"]:
                    continue

                cypher_query = generate_traversal_query(
                    intent=intent,
                    seed_node_ids=seed_ids,
                    node_type=node_type,
                    depth=None,  # Uses configured GRAPH_TRAVERSAL_DEPTH
                )

                if not cypher_query:
                    logger.warning(f"[GraphTraversal] No query generated for intent: {intent}")
                    continue

                logger.info(
                    f"[GraphTraversal] Executing query for intent={intent} | "
                    f"node_type={node_type} | depth={settings.GRAPH_TRAVERSAL_DEPTH}\n"
                    f"Query: {cypher_query[:200]}..."
                )

                # Execute intent-specific query
                raw_results = await neo4j_repo.execute_query(cypher_query, {"seed_ids": seed_ids})

                logger.info(
                    f"[GraphTraversal] Executed query for intent={intent} | "
                    f"raw_records={len(raw_results)}"
                )

                all_raw_results.extend(raw_results)
                executed_intents.append(intent)

            # Format ALL results into structured graph context
            graph_results = format_graph_results(all_raw_results)

            logger.info(
                f"[GraphTraversal] Multi-intent traversal complete | "
                f"executed_intents={executed_intents} | "
                f"nodes={len(graph_results['nodes'])} | "
                f"relationships={len(graph_results['relationships'])}"
            )

            # End timing
            duration_ms = 0.0
            if isinstance(metrics, QueryMetrics):
                duration_ms = metrics.end_timer("graph_traversal")
                logger.info(f"[GraphTraversal] Completed in {duration_ms:.2f}ms")

            # Emit stage completed
            await pipeline_monitor.emit_graph_traversal(
                session_id=session_id,
                user_id=user_id,
                query=state.user_query,
                status=StageStatus.COMPLETED,
                duration_ms=duration_ms,
                nodes_accessed=len(graph_results["nodes"]),
                relationships_traversed=len(graph_results["relationships"]),
                traversal_patterns=executed_intents
            )

            return {
                "graph_context": graph_results["nodes"] + graph_results["relationships"],
                "metadata": {
                    **state.metadata,
                    "graph_traversal_completed": True,
                    "graph_nodes_count": len(graph_results["nodes"]),
                    "graph_relationships_count": len(graph_results["relationships"]),
                    "traversal_intents": executed_intents,
                    "seed_nodes_used": len(seed_ids),
                },
            }

        finally:
            await neo4j_repo.close()

    except Exception as e:
        logger.error(f"[GraphTraversal] Failed: {str(e)}", exc_info=True)

        # End timing even on error
        duration_ms = 0.0
        if isinstance(metrics, QueryMetrics):
            duration_ms = metrics.end_timer("graph_traversal")

        # Emit stage failed
        await pipeline_monitor.emit_graph_traversal(
            session_id=session_id,
            user_id=user_id,
            query=state.user_query,
            status=StageStatus.FAILED,
            duration_ms=duration_ms,
            error=str(e)
        )

        return {
            "graph_context": [],
            "metadata": {**state.metadata, "graph_traversal_error": str(e)},
        }
