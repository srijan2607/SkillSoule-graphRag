#!/usr/bin/env python3
"""
Initial database setup script.

Creates Neo4j constraints, indexes, and vector indexes for the Graph RAG system.

Usage:
    python scripts/initial_setup.py

Requirements:
    - .env file with database credentials
    - Neo4j database running and accessible
    - PostgreSQL database running and accessible
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.repositories.neo4j_repository import Neo4jRepository
from app.services.vector_index_service import VectorIndexService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_constraints(neo4j_repo: Neo4jRepository):
    """
    Create Neo4j constraints for unique node IDs.

    Constraints ensure data integrity and enable faster lookups.
    """
    constraints = [
        # Skill constraints
        "CREATE CONSTRAINT skill_id_unique IF NOT EXISTS FOR (s:Skill) REQUIRE s.id IS UNIQUE",

        # Job constraints
        "CREATE CONSTRAINT job_id_unique IF NOT EXISTS FOR (j:Job) REQUIRE j.job_id IS UNIQUE",

        # Company constraints
        "CREATE CONSTRAINT company_name_unique IF NOT EXISTS FOR (c:Company) REQUIRE c.company_name IS UNIQUE",

        # Location constraints
        "CREATE CONSTRAINT location_name_unique IF NOT EXISTS FOR (l:Location) REQUIRE l.location_name IS UNIQUE",

        # Category constraints
        "CREATE CONSTRAINT category_id_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.category_id IS UNIQUE",

        # Subcategory constraints
        "CREATE CONSTRAINT subcategory_id_unique IF NOT EXISTS FOR (sub:Subcategory) REQUIRE sub.subcategory_id IS UNIQUE",
    ]

    logger.info("Creating Neo4j constraints...")
    for constraint in constraints:
        try:
            await neo4j_repo.execute_query(constraint)
            # Extract constraint name from query
            constraint_name = constraint.split()[2]
            logger.info(f"  ✅ Constraint created: {constraint_name}")
        except Exception as e:
            # Constraint may already exist - that's okay
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.debug(f"  ℹ️  Constraint already exists (skipped)")
            else:
                logger.error(f"  ❌ Failed to create constraint: {str(e)}")
                raise


async def create_indexes(neo4j_repo: Neo4jRepository):
    """
    Create Neo4j indexes for faster queries.

    Indexes improve query performance for common search patterns.
    """
    indexes = [
        # Skill indexes
        "CREATE INDEX skill_name_idx IF NOT EXISTS FOR (s:Skill) ON (s.name)",

        # Job indexes
        "CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.job_title)",
        "CREATE INDEX job_company_idx IF NOT EXISTS FOR (j:Job) ON (j.company_name)",

        # Company indexes
        "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.company_name)",
    ]

    logger.info("Creating Neo4j indexes...")
    for index in indexes:
        try:
            await neo4j_repo.execute_query(index)
            # Extract index name from query
            index_name = index.split()[2]
            logger.info(f"  ✅ Index created: {index_name}")
        except Exception as e:
            # Index may already exist - that's okay
            if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                logger.debug(f"  ℹ️  Index already exists (skipped)")
            else:
                logger.error(f"  ❌ Failed to create index: {str(e)}")
                raise


async def run_initial_setup():
    """
    Run initial database setup.

    Creates:
    1. Neo4j constraints (unique IDs)
    2. Neo4j indexes (name, title)
    3. Vector indexes (embeddings)
    """
    logger.info("=" * 60)
    logger.info("Starting initial database setup...")
    logger.info("=" * 60)

    # Initialize Neo4j repository
    neo4j_repo = Neo4jRepository(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD
    )

    try:
        # Connect to Neo4j
        logger.info("\n🔌 Connecting to Neo4j...")
        await neo4j_repo.connect()
        logger.info("✅ Neo4j connection established")

        # Step 1: Create constraints
        logger.info("\n📋 Step 1: Creating constraints...")
        await create_constraints(neo4j_repo)
        logger.info("✅ Constraints created successfully")

        # Step 2: Create regular indexes
        logger.info("\n📋 Step 2: Creating indexes...")
        await create_indexes(neo4j_repo)
        logger.info("✅ Indexes created successfully")

        # Step 3: Create vector indexes
        logger.info("\n📋 Step 3: Creating vector indexes...")
        vector_index_service = VectorIndexService(neo4j_repo)
        results = await vector_index_service.create_vector_indexes()

        for index_name, status in results.items():
            if status == "created":
                logger.info(f"  ✅ {index_name}: {status}")
            elif status == "already_exists":
                logger.info(f"  ℹ️  {index_name}: {status}")
            else:
                logger.error(f"  ❌ {index_name}: {status}")

        # Step 4: Verify vector indexes
        logger.info("\n📋 Step 4: Verifying vector indexes...")
        health = await vector_index_service.verify_vector_indexes()

        all_healthy = True
        for index_name, status in health.items():
            if status.get("exists") and status.get("state") == "ONLINE":
                logger.info(
                    f"  ✅ {index_name}: ONLINE "
                    f"(entities: {status.get('entity_count', 0)})"
                )
            else:
                logger.warning(
                    f"  ⚠️  {index_name}: {status.get('state', 'NOT_FOUND')}"
                )
                all_healthy = False

        # Final summary
        logger.info("\n" + "=" * 60)
        if all_healthy:
            logger.info("✅ Initial database setup completed successfully!")
        else:
            logger.warning("⚠️  Setup completed with warnings - some indexes may still be populating")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ Initial setup failed: {str(e)}", exc_info=True)
        raise

    finally:
        # Close Neo4j connection
        await neo4j_repo.close()
        logger.info("\n🔌 Neo4j connection closed")


if __name__ == "__main__":
    try:
        asyncio.run(run_initial_setup())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)
