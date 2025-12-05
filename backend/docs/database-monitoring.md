# Database Monitoring Guide - Context Storage

**Purpose**: Monitor database growth from context storage and establish archival policies

**Created**: 2025-10-28
**Owner**: Development Team
**Review Frequency**: Weekly

---

## Overview

Following the implementation of context visibility (fixes-2), the `query_history` table now stores full constructed contexts in the `metadata` JSON field. This significantly increases storage requirements and necessitates active monitoring.

---

## Weekly Monitoring Query

Execute this query **every week** to track context storage growth:

```sql
-- Weekly monitoring query for context storage growth
SELECT
  COUNT(*) as total_queries,
  AVG(LENGTH(metadata::text)) as avg_metadata_size_bytes,
  SUM(LENGTH(metadata::text))/(1024*1024) as total_metadata_mb,
  MAX(LENGTH(metadata::text)) as max_metadata_size_bytes
FROM query_history
WHERE created_at > NOW() - INTERVAL '7 days';
```

### Expected Values

| Metric | Typical Range | Alert Threshold |
|--------|---------------|-----------------|
| `total_queries` | 100-1000/week | >5000/week |
| `avg_metadata_size_bytes` | 5,000-15,000 bytes | >50,000 bytes |
| `total_metadata_mb` | 5-50 MB/week | >200 MB/week |
| `max_metadata_size_bytes` | 20,000-50,000 bytes | >100,000 bytes |

### Alert Conditions

**🟡 Warning** (Review in 1 week):
- `total_metadata_mb` > 100 MB/week
- `avg_metadata_size_bytes` > 30,000 bytes

**🔴 Critical** (Immediate action):
- `total_metadata_mb` > 200 MB/week
- `max_metadata_size_bytes` > 100,000 bytes
- Database size approaching limit

---

## Context Token Counting Performance

Monitor context construction timing from application logs:

```bash
# Extract context construction timings
grep "ContextConstruction" logs/app.log | grep "Completed in" | awk '{print $NF}' | sort -n | tail -20

# Statistical summary
grep "ContextConstruction" logs/app.log | grep "Completed in" | awk '{print $NF}' | awk '{
  count++;
  sum+=$1;
  sumsq+=$1*$1
}
END {
  if (count > 0) {
    avg=sum/count;
    stddev=sqrt(sumsq/count - avg*avg);
    print "Count:", count;
    print "Average:", avg "ms";
    print "Std Dev:", stddev "ms";
  }
}'
```

### Expected Values

| Metric | Typical Range | Alert Threshold |
|--------|---------------|-----------------|
| Average timing | 20-50 ms | >100 ms |
| 95th percentile | <80 ms | >200 ms |
| Maximum timing | <150 ms | >500 ms |

### Alert Conditions

**🟡 Warning**:
- Average timing > 100 ms
- 95th percentile > 200 ms

**🔴 Critical**:
- Average timing > 200 ms
- Maximum timing > 1000 ms (1 second)

---

## Database Archival Strategy

### Policy

**Retention Periods**:
- **Active queries** (0-30 days): Keep all data
- **Recent queries** (31-90 days): Keep all data, consider context compression
- **Old queries** (>90 days): Archive or delete based on business needs

### Archival Options

#### Option 1: Delete Old Queries (Recommended for MVP)

```sql
-- Delete queries older than 90 days
-- Run monthly via cron job or scheduled task
DELETE FROM query_history
WHERE created_at < NOW() - INTERVAL '90 days';

-- Check rows affected before committing
-- Expected: 1000-5000 rows/month
```

#### Option 2: Archive to Cold Storage (Future Enhancement)

```sql
-- Export to archive table
INSERT INTO query_history_archive
SELECT * FROM query_history
WHERE created_at < NOW() - INTERVAL '90 days';

-- Then delete from active table
DELETE FROM query_history
WHERE created_at < NOW() - INTERVAL '90 days';
```

#### Option 3: Context Compression (Advanced)

```python
# Compress context strings before archival
import gzip
import json

def compress_context(metadata_json):
    """Compress constructed_context in metadata before archival."""
    metadata = json.loads(metadata_json)

    if "constructed_context" in metadata:
        # Compress context string
        context_bytes = metadata["constructed_context"].encode('utf-8')
        compressed = gzip.compress(context_bytes)

        # Store as base64 for JSON compatibility
        import base64
        metadata["constructed_context_compressed"] = base64.b64encode(compressed).decode('ascii')
        del metadata["constructed_context"]  # Remove uncompressed

    return json.dumps(metadata)
```

---

## Automated Monitoring Setup

### PostgreSQL Cron Job (Recommended)

```sql
-- Install pg_cron extension (once)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule weekly monitoring query
SELECT cron.schedule(
    'weekly-context-monitoring',
    '0 9 * * 1',  -- Every Monday at 9 AM
    $$
    SELECT
      COUNT(*) as total_queries,
      AVG(LENGTH(metadata::text)) as avg_size,
      SUM(LENGTH(metadata::text))/(1024*1024) as total_mb
    FROM query_history
    WHERE created_at > NOW() - INTERVAL '7 days';
    $$
);

-- Schedule monthly cleanup (delete queries >90 days old)
SELECT cron.schedule(
    'monthly-context-cleanup',
    '0 2 1 * *',  -- First day of month at 2 AM
    $$
    DELETE FROM query_history
    WHERE created_at < NOW() - INTERVAL '90 days';
    $$
);
```

### Python Monitoring Script

```python
#!/usr/bin/env python3
"""
Weekly database monitoring script for context storage.
Run via cron: 0 9 * * 1 /path/to/monitor_context_storage.py
"""
import asyncio
from prisma import Prisma
from datetime import datetime, timedelta

async def monitor_context_storage():
    """Execute weekly monitoring query and check thresholds."""
    db = Prisma()
    await db.connect()

    # Execute monitoring query
    query = """
        SELECT
          COUNT(*) as total_queries,
          AVG(LENGTH(metadata::text)) as avg_metadata_size_bytes,
          SUM(LENGTH(metadata::text))/(1024*1024) as total_metadata_mb,
          MAX(LENGTH(metadata::text)) as max_metadata_size_bytes
        FROM query_history
        WHERE created_at > NOW() - INTERVAL '7 days'
    """

    result = await db.query_raw(query)
    stats = result[0]

    # Check thresholds
    warnings = []
    critical = []

    if stats['total_metadata_mb'] > 200:
        critical.append(f"Critical: Total metadata {stats['total_metadata_mb']:.2f} MB/week exceeds 200 MB threshold")
    elif stats['total_metadata_mb'] > 100:
        warnings.append(f"Warning: Total metadata {stats['total_metadata_mb']:.2f} MB/week exceeds 100 MB threshold")

    if stats['avg_metadata_size_bytes'] > 50000:
        critical.append(f"Critical: Average metadata size {stats['avg_metadata_size_bytes']:.0f} bytes exceeds 50K threshold")
    elif stats['avg_metadata_size_bytes'] > 30000:
        warnings.append(f"Warning: Average metadata size {stats['avg_metadata_size_bytes']:.0f} bytes exceeds 30K threshold")

    # Log results
    print(f"📊 Weekly Context Storage Report - {datetime.now().isoformat()}")
    print(f"   Total queries: {stats['total_queries']}")
    print(f"   Avg metadata size: {stats['avg_metadata_size_bytes']:.0f} bytes")
    print(f"   Total metadata: {stats['total_metadata_mb']:.2f} MB")
    print(f"   Max metadata size: {stats['max_metadata_size_bytes']:.0f} bytes")

    if critical:
        print("\n🔴 CRITICAL ALERTS:")
        for alert in critical:
            print(f"   {alert}")

    if warnings:
        print("\n🟡 WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")

    if not critical and not warnings:
        print("\n✅ All metrics within normal ranges")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(monitor_context_storage())
```

**Setup Cron Job**:
```bash
# Edit crontab
crontab -e

# Add weekly monitoring (every Monday at 9 AM)
0 9 * * 1 cd /path/to/backend && python3 scripts/monitor_context_storage.py >> logs/monitoring.log 2>&1
```

---

## Dashboard Queries (Optional)

### Growth Trend (Last 4 Weeks)

```sql
SELECT
  DATE_TRUNC('week', created_at) as week_start,
  COUNT(*) as queries,
  SUM(LENGTH(metadata::text))/(1024*1024) as metadata_mb,
  AVG(LENGTH(metadata::text)) as avg_size_bytes
FROM query_history
WHERE created_at > NOW() - INTERVAL '4 weeks'
GROUP BY DATE_TRUNC('week', created_at)
ORDER BY week_start;
```

### Top Largest Contexts

```sql
SELECT
  id,
  query_text,
  LENGTH(metadata::text) as metadata_size_bytes,
  created_at
FROM query_history
ORDER BY LENGTH(metadata::text) DESC
LIMIT 10;
```

### Storage by User (if multi-tenant)

```sql
SELECT
  user_id,
  COUNT(*) as queries,
  SUM(LENGTH(metadata::text))/(1024*1024) as total_mb,
  AVG(LENGTH(metadata::text)) as avg_bytes
FROM query_history
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY user_id
ORDER BY total_mb DESC
LIMIT 20;
```

---

## Action Plan Based on Monitoring

### If Growth Rate is Normal (<50 MB/week)
✅ Continue weekly monitoring
✅ Execute monthly cleanup (>90 days)
✅ No action required

### If Growth Rate is High (50-200 MB/week)
⚠️ Increase monitoring frequency to daily
⚠️ Analyze query patterns for optimization
⚠️ Consider context compression
⚠️ Review archival policy (reduce to 60 days)

### If Growth Rate is Critical (>200 MB/week)
🔴 **Immediate actions**:
1. Execute emergency cleanup (>30 days)
2. Identify and optimize largest contexts
3. Implement context compression
4. Consider making context optional via query parameter
5. Increase database storage capacity

---

## Contact & Escalation

**Primary Owner**: Backend Development Team
**Database Admin**: [DBA Name/Email]
**Escalation Path**: Tech Lead → Engineering Manager

**Documentation Last Updated**: 2025-10-28
