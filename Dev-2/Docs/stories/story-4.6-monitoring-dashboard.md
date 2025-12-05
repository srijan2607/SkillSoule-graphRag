# Story 4.6: Monitoring Dashboard for Research Metrics (Optional Stretch Goal)

**Epic:** Epic 4 - Research Validation Framework
**Story ID:** 4.6
**Estimated Effort:** 3-4 days
**Priority:** Optional (Phase 5 stretch goal)

## User Story
**As a** system administrator,
**I want** a real-time dashboard showing metric performance,
**so that** I can monitor system health.

## Acceptance Criteria
1. Admin dashboard `/admin/metrics-dashboard` (admin-only)
2. Shows: centrality health, closeness performance, TransitionIndex usage, validation metrics
3. Real-time updates (30s refresh)
4. Alerts: email/Slack for NFR violations or quality issues

## Integration Verification
**IV1:** Only admin role can access
**IV2:** Dashboard doesn't affect user query performance
**IV3:** Alerts tested by simulating issues

## Dependencies
**Depends on:** Epic 2-4 complete
**Blocks:** None (optional feature)

---

## Technical Implementation

### Components

**Primary Component:** `MetricsDashboard` (NEW v2.0, Optional)
- **Location:** `frontend/src/pages/admin/MetricsDashboard.tsx`
- **Endpoint:** `/admin/metrics-dashboard` (admin-only)

**Backend API:** `DashboardRouter`
- **Location:** `backend/app/routers/dashboard.py`
- **Endpoint:** `GET /api/admin/dashboard-metrics`

### Dashboard Metrics

**Centrality Health:**
- Current centrality computation status (last run, next scheduled)
- Top 10 skills by centrality (with trend over time)
- Centrality distribution histogram

**Closeness Performance:**
- Average closeness query time (p50, p95, p99)
- Query volume (queries/hour)
- Cache hit rate

**TransitionIndex Usage:**
- Number of TransitionIndex queries per day
- Average score distribution
- User feedback on transition recommendations

**Validation Metrics:**
- Expert validation agreement rate
- A/B test results (live updates)
- Closeness correlation coefficient

**System Health:**
- Neo4j connection status
- PostgreSQL connection status
- Redis cache status
- LLM API status

### Dashboard Implementation

```tsx
export function MetricsDashboard() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      const response = await fetch('/api/admin/dashboard-metrics');
      const data = await response.json();
      setMetrics(data);
    };

    // Initial fetch
    fetchMetrics();

    // Refresh every 30 seconds
    const interval = setInterval(fetchMetrics, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="admin-dashboard">
      <h1>Metrics Dashboard</h1>

      <div className="metrics-grid">
        {/* Centrality Health */}
        <Card title="Centrality Health">
          <p>Last Run: {metrics?.centrality_last_run}</p>
          <p>Next Scheduled: {metrics?.centrality_next_run}</p>
          <CentralityTrendChart data={metrics?.centrality_trend} />
        </Card>

        {/* Closeness Performance */}
        <Card title="Closeness Performance">
          <p>p50: {metrics?.closeness_p50}ms</p>
          <p>p95: {metrics?.closeness_p95}ms</p>
          <p>Cache Hit Rate: {metrics?.cache_hit_rate}%</p>
        </Card>

        {/* TransitionIndex Usage */}
        <Card title="TransitionIndex Usage">
          <p>Queries Today: {metrics?.transition_queries_today}</p>
          <ScoreDistributionChart data={metrics?.transition_score_distribution} />
        </Card>

        {/* Validation Metrics */}
        <Card title="Validation Metrics">
          <p>Expert Agreement: {metrics?.expert_agreement}%</p>
          <p>A/B Test Result: {metrics?.ab_test_improvement}%</p>
          <p>Correlation: {metrics?.closeness_correlation}</p>
        </Card>

        {/* System Health */}
        <Card title="System Health">
          <StatusIndicator label="Neo4j" status={metrics?.neo4j_status} />
          <StatusIndicator label="PostgreSQL" status={metrics?.postgres_status} />
          <StatusIndicator label="Redis" status={metrics?.redis_status} />
          <StatusIndicator label="LLM API" status={metrics?.llm_status} />
        </Card>
      </div>
    </div>
  );
}
```

### Alert System

```python
class AlertService:
    """Send alerts for NFR violations or quality issues."""

    async def check_nfr_violations(self):
        """Check for NFR violations and send alerts."""
        # NFR11: Centrality computation >30s
        if centrality_time > 30:
            await self.send_alert(
                "NFR11 Violation: Centrality computation took {centrality_time}s (target: <30s)"
            )

        # NFR12: Closeness query >500ms
        if closeness_p95 > 500:
            await self.send_alert(
                "NFR12 Violation: Closeness p95 is {closeness_p95}ms (target: <500ms)"
            )

    async def send_alert(self, message: str):
        """Send alert via email and Slack."""
        # Email
        await email_service.send(to="admin@example.com", subject="Metric Alert", body=message)

        # Slack
        await slack_client.post_message(channel="#alerts", text=message)
```

### Testing

**Unit Test:** `tests/unit/test_dashboard.py`
- Test metrics aggregation
- Validate alert triggering
- Test admin-only access

**Integration Test:** `tests/integration/test_dashboard.py`
- Render dashboard with live data
- Verify 30-second refresh
- Test alert system (simulate NFR violations)

### Performance Targets

- **Dashboard Load Time:** <1 second
- **Refresh Interval:** 30 seconds
- **No Impact on User Queries:** Dashboard queries run on read replicas

### Security Considerations

From `security.md`:
- **Admin-Only Access:** JWT + admin role check
- **Read Replicas:** Dashboard queries don't impact production DB
- **Alert Rate Limiting:** Max 10 alerts per hour (prevent spam)
