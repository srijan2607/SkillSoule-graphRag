#!/usr/bin/env python3
"""
Batch script to build skill co-occurrence relationships.

This script builds the CO_OCCURS_WITH relationships between skills based on
their co-occurrence in job requirements. These relationships are the foundation
for network math calculations (Dijkstra, closeness, etc.)

Usage:
    python scripts/build_co_occurrence.py [--clear] [--min-weight N] [--create-indexes]

Options:
    --clear           Clear existing CO_OCCURS_WITH before building
    --min-weight N    Minimum co-occurrence count (default: 2)
    --create-indexes  Create/verify required indexes
    --validate        Validate data after build

Example:
    cd backend
    python scripts/build_co_occurrence.py --clear --min-weight 2 --create-indexes

Reference: Network Math Implementation - Phase 1 (01-DATA-LAYER.md)
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.co_occurrence_builder import CoOccurrenceBuilder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_graph_stats(repo: Neo4jRepository) -> dict:
    """Get basic graph statistics."""
    query = """
    MATCH (s:Skill) WITH count(s) as skills
    MATCH (j:Job) WITH skills, count(j) as jobs
    MATCH ()-[r:REQUIRES]->() WITH skills, jobs, count(r) as requires
    RETURN skills, jobs, requires
    """
    result = await repo.execute_query(query)
    if result:
        return {
            "skills_count": result[0]["skills"],
            "jobs_count": result[0]["jobs"],
            "requires_count": result[0]["requires"]
        }
    return {"skills_count": 0, "jobs_count": 0, "requires_count": 0}


async def main(clear: bool, min_weight: int, create_indexes: bool, validate: bool):
    """Main entry point for co-occurrence build."""
    logger.info("=" * 60)
    logger.info("SKILL CO-OCCURRENCE BUILD")
    logger.info("=" * 60)
    logger.info(f"Clear existing: {clear}")
    logger.info(f"Minimum weight: {min_weight}")
    logger.info(f"Create indexes: {create_indexes}")
    logger.info(f"Validate after: {validate}")
    logger.info("")

    # Initialize repository
    repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )

    try:
        await repo.connect()
        logger.info("Connected to Neo4j")

        # Get initial stats
        initial_stats = await get_graph_stats(repo)
        logger.info(f"Graph statistics:")
        logger.info(f"  - Skills: {initial_stats['skills_count']:,}")
        logger.info(f"  - Jobs: {initial_stats['jobs_count']:,}")
        logger.info(f"  - REQUIRES relationships: {initial_stats['requires_count']:,}")
        logger.info("")

        # Initialize builder
        builder = CoOccurrenceBuilder(repo)
        builder.min_weight = min_weight

        # Create indexes if requested
        if create_indexes:
            logger.info("Creating indexes...")
            index_result = await builder.create_indexes()
            logger.info(f"Indexes created: {index_result['indexes_created']}")
            if index_result['errors']:
                logger.warning(f"Index errors: {index_result['errors']}")
            logger.info("")

        # Build co-occurrences
        logger.info("Building co-occurrence relationships...")
        result = await builder.build_all(clear_existing=clear)

        # Log results
        logger.info("")
        logger.info("=" * 60)
        logger.info("BUILD RESULTS")
        logger.info("=" * 60)
        logger.info(f"Status: {result.get('status', 'unknown')}")

        if result.get('relationships_deleted'):
            logger.info(f"Relationships deleted: {result['relationships_deleted']:,}")

        logger.info(f"Relationships created: {result.get('relationships_created', 0):,}")
        logger.info(f"Duration: {result.get('duration_seconds', 0):.2f}s")

        if result.get('total_co_occurrence_relationships'):
            logger.info("")
            logger.info("Statistics:")
            logger.info(f"  - Total relationships: {result['total_co_occurrence_relationships']:,}")
            logger.info(f"  - Average weight: {result.get('average_weight', 0):.2f}")
            logger.info(f"  - Weight range: {result.get('min_weight', 0)} - {result.get('max_weight', 0)}")

        if result.get('error'):
            logger.error(f"Error: {result['error']}")
            sys.exit(1)

        # Validate if requested
        if validate:
            logger.info("")
            logger.info("Validating data integrity...")
            validation = await builder.validate_data()
            logger.info(f"Total relationships: {validation['total_relationships']:,}")
            logger.info(f"Valid: {validation['is_valid']}")
            if validation['issues']:
                for issue in validation['issues']:
                    logger.warning(f"  - {issue}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("BUILD COMPLETE")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Build failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        await repo.close()
        logger.info("Disconnected from Neo4j")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build skill co-occurrence relationships",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full rebuild with indexes
    python scripts/build_co_occurrence.py --clear --create-indexes --validate

    # Incremental build (keep existing, add new)
    python scripts/build_co_occurrence.py --min-weight 3

    # Just create indexes
    python scripts/build_co_occurrence.py --create-indexes
        """
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing CO_OCCURS_WITH relationships before building"
    )
    parser.add_argument(
        "--min-weight",
        type=int,
        default=2,
        help="Minimum co-occurrence count for creating relationship (default: 2)"
    )
    parser.add_argument(
        "--create-indexes",
        action="store_true",
        help="Create/verify required indexes on CO_OCCURS_WITH relationships"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate data integrity after build"
    )

    args = parser.parse_args()
    asyncio.run(main(args.clear, args.min_weight, args.create_indexes, args.validate))
