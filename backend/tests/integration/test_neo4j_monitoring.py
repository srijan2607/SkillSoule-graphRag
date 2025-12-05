"""
Integration tests for Neo4j Query Monitoring System.

Tests the complete monitoring flow from query execution to logging.
"""

import pytest
from app.services.neo4j_monitoring_service import Neo4jMonitoringService
from app.repositories.monitored_neo4j_repository import MonitoredNeo4jRepository


@pytest.mark.asyncio
async def test_monitoring_service_log_query(prisma_client):
    """Test basic query logging to PostgreSQL."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    log_id = await monitoring_service.log_query(
        query_text="MATCH (s:Skill) RETURN s LIMIT 10",
        parameters={},
        execution_time_ms=45.2,
        result_count=10,
        status="success",
        source="test",
        metadata={"test": True}
    )

    assert log_id is not None

    # Verify log was stored in database
    log = await prisma_client.neo4jquerylog.find_unique(
        where={"id": log_id}
    )

    assert log is not None
    assert log.query_text == "MATCH (s:Skill) RETURN s LIMIT 10"
    assert log.operation_type == "READ"
    assert log.execution_time_ms == 45.2
    assert log.result_count == 10
    assert log.status == "success"
    assert log.source == "test"


@pytest.mark.asyncio
async def test_monitoring_service_execute_and_log(prisma_client):
    """Test execute_and_log wrapper function."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    # Mock query function
    async def mock_query():
        return [{"id": "1", "name": "Python"}, {"id": "2", "name": "JavaScript"}]

    results = await monitoring_service.execute_and_log(
        query_func=mock_query,
        query_text="MATCH (s:Skill) RETURN s.id as id, s.name as name",
        parameters={},
        source="test_execute_and_log"
    )

    assert results == [{"id": "1", "name": "Python"}, {"id": "2", "name": "JavaScript"}]

    # Verify query was logged
    logs = await prisma_client.neo4jquerylog.find_many(
        where={"source": "test_execute_and_log"},
        order={"created_at": "desc"},
        take=1
    )

    assert len(logs) == 1
    assert logs[0].status == "success"
    assert logs[0].result_count == 2


@pytest.mark.asyncio
async def test_monitoring_service_execute_and_log_error(prisma_client):
    """Test execute_and_log with query error."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    # Mock query function that raises error
    async def mock_query_error():
        raise Exception("Test error: Invalid Cypher syntax")

    with pytest.raises(Exception, match="Invalid Cypher syntax"):
        await monitoring_service.execute_and_log(
            query_func=mock_query_error,
            query_text="INVALID CYPHER QUERY",
            parameters={},
            source="test_error"
        )

    # Verify error was logged
    logs = await prisma_client.neo4jquerylog.find_many(
        where={"source": "test_error"},
        order={"created_at": "desc"},
        take=1
    )

    assert len(logs) == 1
    assert logs[0].status == "error"
    assert "Invalid Cypher syntax" in logs[0].error_message


@pytest.mark.asyncio
async def test_monitoring_service_get_recent_queries(prisma_client):
    """Test retrieving recent queries from in-memory cache."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    # Log multiple queries
    for i in range(5):
        await monitoring_service.log_query(
            query_text=f"MATCH (s:Skill) WHERE s.id = 'test-{i}' RETURN s",
            parameters={"id": f"test-{i}"},
            execution_time_ms=10.0 + i,
            result_count=1,
            status="success",
            source="test_recent"
        )

    # Get recent queries
    recent_queries = monitoring_service.get_recent_queries(limit=5)

    assert len(recent_queries) >= 5
    # Queries should be in reverse chronological order (most recent first)
    assert recent_queries[0]["query_text"] == "MATCH (s:Skill) WHERE s.id = 'test-4' RETURN s"


@pytest.mark.asyncio
async def test_monitoring_service_get_metrics(prisma_client):
    """Test performance metrics aggregation."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    # Log queries of different types
    await monitoring_service.log_query(
        query_text="MATCH (s:Skill) RETURN s",
        execution_time_ms=50.0,
        status="success",
        source="test_metrics"
    )

    await monitoring_service.log_query(
        query_text="CREATE (s:Skill {id: 'new'}) RETURN s",
        execution_time_ms=100.0,
        status="success",
        source="test_metrics"
    )

    await monitoring_service.log_query(
        query_text="CALL db.index.vector.queryNodes('idx', 10, $embedding) YIELD node",
        execution_time_ms=75.0,
        status="success",
        source="test_metrics"
    )

    metrics = monitoring_service.get_metrics()

    assert metrics["total_queries"] >= 3
    assert metrics["successful_queries"] >= 3
    assert metrics["avg_execution_time_ms"] > 0
    assert metrics["operation_counts"]["READ"] >= 1
    assert metrics["operation_counts"]["WRITE"] >= 1
    assert metrics["operation_counts"]["VECTOR_SEARCH"] >= 1


@pytest.mark.asyncio
async def test_query_classification(prisma_client):
    """Test automatic query operation type classification."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    test_cases = [
        ("MATCH (s:Skill) RETURN s", "READ"),
        ("CREATE (s:Skill {id: '1'}) RETURN s", "WRITE"),
        ("MERGE (s:Skill {id: '1'}) SET s.name = 'Python'", "WRITE"),
        ("CALL db.index.vector.queryNodes('idx', 10, $embedding) YIELD node", "VECTOR_SEARCH"),
        ("MATCH (s:Skill)-[:SIMILAR_TO*2]->(related) RETURN related", "GRAPH_TRAVERSAL"),
    ]

    for query_text, expected_type in test_cases:
        classified_type = monitoring_service._classify_query(query_text)
        assert classified_type == expected_type, \
            f"Query '{query_text}' should be classified as {expected_type}, got {classified_type}"


@pytest.mark.asyncio
async def test_search_queries_with_filters(prisma_client):
    """Test searching query logs with various filters."""
    monitoring_service = Neo4jMonitoringService(prisma_client)

    # Create queries with different attributes
    await monitoring_service.log_query(
        query_text="MATCH (s:Skill) RETURN s",
        operation_type="READ",
        execution_time_ms=50.0,
        status="success",
        source="search_test",
        session_id="session-1"
    )

    await monitoring_service.log_query(
        query_text="CREATE (s:Skill) RETURN s",
        operation_type="WRITE",
        execution_time_ms=100.0,
        status="success",
        source="search_test",
        session_id="session-2"
    )

    # Search by operation_type
    read_queries = await monitoring_service.search_queries(
        operation_type="READ",
        source="search_test",
        limit=10
    )
    assert len(read_queries) >= 1
    assert all(q["operation_type"] == "READ" for q in read_queries)

    # Search by session_id
    session_queries = await monitoring_service.search_queries(
        session_id="session-1",
        source="search_test",
        limit=10
    )
    assert len(session_queries) >= 1
    assert all(q["session_id"] == "session-1" for q in session_queries)


# Note: WebSocket testing requires special setup and is typically done with end-to-end tests
# Using tools like pytest-asyncio with websockets library
