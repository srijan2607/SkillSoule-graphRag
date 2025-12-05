#!/usr/bin/env python3
"""
Weekly database monitoring script for context storage.

Purpose: Monitor query_history table growth from context storage
Run via cron: 0 9 * * 1 /path/to/monitor_context_storage.py

Usage:
    python3 scripts/monitor_context_storage.py

Output: Weekly report with metrics and threshold checks
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prisma import Prisma
from app.utils.logger import logger


async def monitor_context_storage():
    """
    Execute weekly monitoring query and check thresholds.

    Checks:
    - Total queries in last 7 days
    - Average metadata size
    - Total metadata storage
    - Maximum metadata size

    Alerts:
    - Warning: avg_size >30KB or total >100MB/week
    - Critical: avg_size >50KB or total >200MB/week
    """
    db = Prisma()

    try:
        await db.connect()
        logger.info("[Monitoring] Starting weekly context storage check")

        # Execute monitoring query
        query = """
            SELECT
              COUNT(*) as total_queries,
              COALESCE(AVG(LENGTH(metadata::text)), 0) as avg_metadata_size_bytes,
              COALESCE(SUM(LENGTH(metadata::text))/(1024*1024), 0) as total_metadata_mb,
              COALESCE(MAX(LENGTH(metadata::text)), 0) as max_metadata_size_bytes
            FROM query_history
            WHERE created_at > NOW() - INTERVAL '7 days'
        """

        result = await db.query_raw(query)

        if not result or len(result) == 0:
            logger.warning("[Monitoring] No data returned from monitoring query")
            print("⚠️  No data found in query_history table")
            return

        stats = result[0]

        # Extract metrics
        total_queries = int(stats.get('total_queries', 0))
        avg_size = float(stats.get('avg_metadata_size_bytes', 0))
        total_mb = float(stats.get('total_metadata_mb', 0))
        max_size = float(stats.get('max_metadata_size_bytes', 0))

        # Check thresholds
        warnings = []
        critical = []

        # Total metadata checks
        if total_mb > 200:
            critical.append(
                f"Critical: Total metadata {total_mb:.2f} MB/week exceeds 200 MB threshold"
            )
        elif total_mb > 100:
            warnings.append(
                f"Warning: Total metadata {total_mb:.2f} MB/week exceeds 100 MB threshold"
            )

        # Average size checks
        if avg_size > 50000:
            critical.append(
                f"Critical: Average metadata size {avg_size:.0f} bytes exceeds 50KB threshold"
            )
        elif avg_size > 30000:
            warnings.append(
                f"Warning: Average metadata size {avg_size:.0f} bytes exceeds 30KB threshold"
            )

        # Maximum size checks
        if max_size > 100000:
            warnings.append(
                f"Warning: Maximum metadata size {max_size:.0f} bytes exceeds 100KB"
            )

        # Print report
        print("=" * 70)
        print(f"📊 Weekly Context Storage Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print(f"   Total queries (7 days):    {total_queries:,}")
        print(f"   Avg metadata size:          {avg_size:,.0f} bytes ({avg_size/1024:.1f} KB)")
        print(f"   Total metadata (7 days):    {total_mb:.2f} MB")
        print(f"   Max metadata size:          {max_size:,.0f} bytes ({max_size/1024:.1f} KB)")
        print("=" * 70)

        # Print alerts
        if critical:
            print("\n🔴 CRITICAL ALERTS:")
            for alert in critical:
                print(f"   • {alert}")
                logger.error(f"[Monitoring] {alert}")

        if warnings:
            print("\n🟡 WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
                logger.warning(f"[Monitoring] {warning}")

        if not critical and not warnings:
            print("\n✅ All metrics within normal ranges")
            logger.info("[Monitoring] All metrics within normal ranges")

        # Recommendations
        if critical or warnings:
            print("\n📋 Recommended Actions:")
            if total_mb > 200:
                print("   • Execute emergency cleanup (queries >30 days old)")
                print("   • Implement context compression")
                print("   • Increase database storage capacity")
            elif total_mb > 100:
                print("   • Review archival policy (consider 60-day retention)")
                print("   • Analyze query patterns for optimization")
                print("   • Consider context compression")
            if avg_size > 30000:
                print("   • Investigate queries with large contexts")
                print("   • Optimize context construction if possible")

        print("\n📖 For detailed monitoring guide, see: backend/docs/database-monitoring.md")
        print("=" * 70)

        # Log completion
        logger.info(
            f"[Monitoring] Weekly check complete: "
            f"{total_queries} queries, {total_mb:.2f} MB, "
            f"avg={avg_size:.0f} bytes"
        )

    except Exception as e:
        logger.error(f"[Monitoring] Failed to execute monitoring query: {str(e)}", exc_info=True)
        print(f"\n❌ Error: Failed to execute monitoring query")
        print(f"   {str(e)}")
        print("\n   Please check database connection and permissions")
        raise

    finally:
        await db.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(monitor_context_storage())
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {str(e)}")
        sys.exit(1)
