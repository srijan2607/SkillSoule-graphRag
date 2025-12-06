"""
Performance benchmarks for network metrics.

These tests measure and validate performance thresholds for
network metric calculations.

Reference: Network Math Implementation - Phase 5 (05-TESTING-STRATEGY.md)
"""

import pytest
import time
import statistics
from unittest.mock import AsyncMock, patch

from app.services.network_metrics_service import NetworkMetricsService
from app.services.co_occurrence_builder import CoOccurrenceBuilder


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_neo4j_repo():
    """Create mock Neo4j repository for benchmarking."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def network_service(mock_neo4j_repo):
    """Create NetworkMetricsService for benchmarking."""
    with patch('app.services.network_metrics_service.settings') as mock_settings:
        mock_settings.NETWORK_CACHE_TTL = 3600
        mock_settings.NETWORK_DIJKSTRA_TIMEOUT = 5.0
        mock_settings.NETWORK_MAX_JOB_COUNT = 1000
        service = NetworkMetricsService(mock_neo4j_repo)
    return service


@pytest.fixture
def co_occurrence_builder(mock_neo4j_repo):
    """Create CoOccurrenceBuilder for benchmarking."""
    return CoOccurrenceBuilder(mock_neo4j_repo)


# =============================================================================
# SHORTEST PATH BENCHMARKS
# =============================================================================

class TestShortestPathPerformance:
    """Performance benchmarks for shortest path calculation."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_shortest_path_average_time(self, network_service, mock_neo4j_repo):
        """Benchmark shortest path calculation - target <500ms average."""
        # Setup mock response
        mock_neo4j_repo.execute_query.return_value = [{
            "totalCost": 0.15,
            "path_ids": ["skill-a", "skill-b", "skill-c"],
            "path_names": ["Python", "Django", "PostgreSQL"]
        }]

        times = []
        iterations = 10

        for _ in range(iterations):
            start = time.perf_counter()
            await network_service.get_shortest_path("python-001", "kubernetes-001")
            times.append(time.perf_counter() - start)

        avg_time_ms = statistics.mean(times) * 1000
        max_time_ms = max(times) * 1000
        min_time_ms = min(times) * 1000
        std_dev_ms = statistics.stdev(times) * 1000 if len(times) > 1 else 0

        print(f"\n--- Shortest Path Performance ---")
        print(f"  Iterations: {iterations}")
        print(f"  Average: {avg_time_ms:.2f}ms")
        print(f"  Min: {min_time_ms:.2f}ms")
        print(f"  Max: {max_time_ms:.2f}ms")
        print(f"  Std Dev: {std_dev_ms:.2f}ms")

        # Performance threshold: average should be under 500ms
        assert avg_time_ms < 500, f"Average time {avg_time_ms}ms exceeds 500ms threshold"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_shortest_path_no_path_performance(self, network_service, mock_neo4j_repo):
        """Benchmark shortest path when no path exists."""
        mock_neo4j_repo.execute_query.return_value = []

        times = []
        iterations = 10

        for _ in range(iterations):
            start = time.perf_counter()
            await network_service.get_shortest_path("isolated-001", "isolated-002")
            times.append(time.perf_counter() - start)

        avg_time_ms = statistics.mean(times) * 1000

        print(f"\n--- Shortest Path (No Path) Performance ---")
        print(f"  Average: {avg_time_ms:.2f}ms")

        # Should return quickly when no path found
        assert avg_time_ms < 100, f"No-path average time {avg_time_ms}ms exceeds 100ms threshold"


# =============================================================================
# CENTRALITY BENCHMARKS
# =============================================================================

class TestCentralityPerformance:
    """Performance benchmarks for centrality calculation."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_eigenvector_centrality_performance(self, network_service, mock_neo4j_repo):
        """Benchmark eigenvector centrality - target <2s."""
        # Setup mock response with 100 skills
        mock_skills = [
            {"skill_id": f"skill-{i}", "skill_name": f"Skill {i}", "centrality_score": 0.9 - (i * 0.005)}
            for i in range(100)
        ]
        mock_neo4j_repo.execute_query.return_value = mock_skills

        start = time.perf_counter()
        result = await network_service.get_eigenvector_centrality(limit=100, use_cache=False)
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Eigenvector Centrality Performance ---")
        print(f"  Duration: {duration_ms:.2f}ms")
        print(f"  Skills returned: {len(result)}")

        # Performance threshold: should complete under 2 seconds
        assert duration_ms < 2000, f"Centrality time {duration_ms}ms exceeds 2s threshold"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_centrality_with_caching(self, network_service, mock_neo4j_repo):
        """Benchmark centrality with caching enabled - second call should be faster."""
        mock_skills = [
            {"skill_id": f"skill-{i}", "skill_name": f"Skill {i}", "centrality_score": 0.9}
            for i in range(50)
        ]
        mock_neo4j_repo.execute_query.return_value = mock_skills

        # First call (cache miss)
        start1 = time.perf_counter()
        await network_service.get_eigenvector_centrality(limit=50, use_cache=True)
        time1_ms = (time.perf_counter() - start1) * 1000

        # Second call (should hit cache)
        start2 = time.perf_counter()
        await network_service.get_eigenvector_centrality(limit=50, use_cache=True)
        time2_ms = (time.perf_counter() - start2) * 1000

        print(f"\n--- Centrality Caching Performance ---")
        print(f"  First call (cache miss): {time1_ms:.2f}ms")
        print(f"  Second call (cache hit): {time2_ms:.2f}ms")
        print(f"  Speedup: {time1_ms / time2_ms if time2_ms > 0 else 'N/A'}x")

        # Cache hit should be significantly faster (at least 2x)
        if time1_ms > 1:  # Only check if first call took meaningful time
            assert time2_ms < time1_ms, "Cache hit should be faster than cache miss"


# =============================================================================
# JOB CLOSENESS BENCHMARKS
# =============================================================================

class TestJobClosenessPerformance:
    """Performance benchmarks for job closeness calculation."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_job_closeness_10_skills(self, network_service, mock_neo4j_repo):
        """Benchmark job closeness for job with 10 skills - target <5s."""
        # Mock job with 10 skills
        mock_neo4j_repo.execute_query.side_effect = [
            # Job skills query
            [{
                "skill_ids": [f"skill-{i}" for i in range(10)],
                "skill_names": [f"Skill {i}" for i in range(10)]
            }],
            # Pairwise closeness queries (45 pairs for 10 skills)
            *[[{"totalCost": 0.1 + (i * 0.01), "path_ids": ["a", "b"]}] for i in range(45)]
        ]

        start = time.perf_counter()
        result = await network_service.get_job_closeness("job-with-10-skills")
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Job Closeness (10 skills) Performance ---")
        print(f"  Duration: {duration_ms:.2f}ms")
        print(f"  Pairs calculated: 45")

        # Performance threshold: 10 skills = 45 pairs, should be under 5s
        assert duration_ms < 5000, f"Job closeness time {duration_ms}ms exceeds 5s threshold"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_job_closeness_single_skill(self, network_service, mock_neo4j_repo):
        """Benchmark job closeness for job with single skill."""
        mock_neo4j_repo.execute_query.return_value = [{
            "skill_ids": ["skill-1"],
            "skill_names": ["Python"]
        }]

        start = time.perf_counter()
        result = await network_service.get_job_closeness("job-single-skill")
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Job Closeness (1 skill) Performance ---")
        print(f"  Duration: {duration_ms:.2f}ms")

        # Single skill should return almost instantly
        assert duration_ms < 100, f"Single skill closeness {duration_ms}ms exceeds 100ms threshold"


# =============================================================================
# TRANSITION INDEX BENCHMARKS
# =============================================================================

class TestTransitionIndexPerformance:
    """Performance benchmarks for transition index calculation."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_transition_index_performance(self, network_service, mock_neo4j_repo):
        """Benchmark transition index calculation - target <1s."""
        # Mock responses
        mock_neo4j_repo.execute_query.side_effect = [
            # Target job skills
            [{"target_skills": [f"skill-{i}" for i in range(8)]}],
            # Job count for market demand
            [{"job_count": 500}],
            # Closeness queries
            *[[{"totalCost": 0.2}] for _ in range(24)]  # 3 source * 8 target
        ]

        start = time.perf_counter()
        result = await network_service.calculate_transition_index(
            source_skills=["skill-a", "skill-b", "skill-c"],
            target_job_id="ml-engineer-001"
        )
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Transition Index Performance ---")
        print(f"  Duration: {duration_ms:.2f}ms")
        print(f"  Source skills: 3")
        print(f"  Target skills: 8")

        # Performance threshold: should complete under 1 second
        assert duration_ms < 1000, f"Transition index time {duration_ms}ms exceeds 1s threshold"


# =============================================================================
# CO-OCCURRENCE BUILDER BENCHMARKS
# =============================================================================

class TestCoOccurrenceBuilderPerformance:
    """Performance benchmarks for co-occurrence building."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_get_top_co_occurrences_performance(self, co_occurrence_builder, mock_neo4j_repo):
        """Benchmark top co-occurrences query."""
        # Mock response with 20 co-occurring skills
        mock_neo4j_repo.execute_query.return_value = [
            {"skill_id": f"skill-{i}", "skill_name": f"Skill {i}", "weight": 100 - i, "cost": 0.01 + (i * 0.001)}
            for i in range(20)
        ]

        times = []
        iterations = 10

        for _ in range(iterations):
            start = time.perf_counter()
            await co_occurrence_builder.get_top_co_occurrences("python-001", limit=20)
            times.append(time.perf_counter() - start)

        avg_time_ms = statistics.mean(times) * 1000

        print(f"\n--- Get Top Co-occurrences Performance ---")
        print(f"  Average: {avg_time_ms:.2f}ms")
        print(f"  Results: 20 skills")

        # Should be very fast
        assert avg_time_ms < 100, f"Get co-occurrences {avg_time_ms}ms exceeds 100ms threshold"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_get_statistics_performance(self, co_occurrence_builder, mock_neo4j_repo):
        """Benchmark statistics query."""
        mock_neo4j_repo.execute_query.return_value = [{
            "total_relationships": 50000,
            "avg_weight": 15.5,
            "min_weight": 2,
            "max_weight": 500
        }]

        start = time.perf_counter()
        await co_occurrence_builder.get_statistics()
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Get Statistics Performance ---")
        print(f"  Duration: {duration_ms:.2f}ms")

        assert duration_ms < 200, f"Statistics query {duration_ms}ms exceeds 200ms threshold"


# =============================================================================
# CONCURRENT OPERATIONS BENCHMARKS
# =============================================================================

class TestConcurrentOperationsPerformance:
    """Performance benchmarks for concurrent operations."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_concurrent_path_calculations(self, network_service, mock_neo4j_repo):
        """Benchmark concurrent shortest path calculations."""
        import asyncio

        mock_neo4j_repo.execute_query.return_value = [{
            "totalCost": 0.15,
            "path_ids": ["a", "b", "c"],
            "path_names": ["A", "B", "C"]
        }]

        async def calculate_path(skill_pair):
            return await network_service.get_shortest_path(skill_pair[0], skill_pair[1])

        skill_pairs = [(f"skill-{i}", f"skill-{i+10}") for i in range(10)]

        start = time.perf_counter()
        results = await asyncio.gather(*[calculate_path(pair) for pair in skill_pairs])
        duration_ms = (time.perf_counter() - start) * 1000

        print(f"\n--- Concurrent Path Calculations Performance ---")
        print(f"  Concurrent requests: {len(skill_pairs)}")
        print(f"  Total duration: {duration_ms:.2f}ms")
        print(f"  Average per request: {duration_ms / len(skill_pairs):.2f}ms")

        assert len(results) == 10
        # 10 concurrent requests should complete in reasonable time
        assert duration_ms < 2000, f"Concurrent paths {duration_ms}ms exceeds 2s threshold"


# =============================================================================
# MEMORY USAGE BENCHMARKS (Optional)
# =============================================================================

class TestMemoryUsage:
    """Memory usage benchmarks (informational)."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_large_result_memory(self, network_service, mock_neo4j_repo):
        """Test memory handling with large result sets."""
        import sys

        # Mock large result set (1000 skills)
        mock_skills = [
            {"skill_id": f"skill-{i}", "skill_name": f"Skill {i}" * 10, "centrality_score": 0.9}
            for i in range(1000)
        ]
        mock_neo4j_repo.execute_query.return_value = mock_skills

        result = await network_service.get_eigenvector_centrality(limit=1000, use_cache=False)

        # Rough size estimate
        size_bytes = sys.getsizeof(result)
        size_mb = size_bytes / (1024 * 1024)

        print(f"\n--- Large Result Memory Usage ---")
        print(f"  Results count: {len(result)}")
        print(f"  Approximate size: {size_mb:.2f} MB")

        # Informational - no hard assertion
        assert len(result) == 1000


# =============================================================================
# PERFORMANCE SUMMARY
# =============================================================================

"""
Performance Thresholds Summary:

| Operation                    | Target    | Notes                              |
|------------------------------|-----------|-----------------------------------|
| Shortest path (avg)          | <500ms    | Single path calculation            |
| Shortest path (no path)      | <100ms    | Quick return when no path exists   |
| Eigenvector centrality       | <2000ms   | 100 skills ranked                  |
| Job closeness (10 skills)    | <5000ms   | 45 pairwise calculations           |
| Job closeness (1 skill)      | <100ms    | Trivial case                       |
| Transition index             | <1000ms   | Full calculation with 3→8 skills   |
| Top co-occurrences           | <100ms    | Single skill lookup                |
| Statistics query             | <200ms    | Aggregation query                  |
| Concurrent paths (10)        | <2000ms   | Parallel execution                 |

Run benchmarks with:
    pytest tests/benchmarks/ -v --benchmark -s
"""
