"""
FastAPI application entry point for Graph RAG API.

Manages database connections (PostgreSQL via Prisma and Neo4j)
and provides API endpoints for the knowledge graph system.

Story 2.3: Added APScheduler for automated temporary file cleanup.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prisma import Prisma
from prisma.errors import PrismaError
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import ServiceUnavailable as Neo4jServiceUnavailable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.api import auth, ingest, admin, query, monitor, skills
from app.exceptions import AuthenticationError
from app.utils.file_cache import cleanup_expired_files
from app.middleware.error_handler import (
    validation_exception_handler,
    global_exception_handler,
    neo4j_connection_error_handler,
    postgres_connection_error_handler,
)

# Configure logger
logger = logging.getLogger(__name__)

# Global database clients
prisma_client = Prisma()
neo4j_driver = None

# Global scheduler for background tasks (Story 2.3)
file_cleanup_scheduler = AsyncIOScheduler()


async def validate_neo4j_indexes():
    """
    Validate that all required Neo4j vector indexes exist and are ONLINE.

    This is a critical infrastructure check (INFRA-001) to prevent runtime
    failures when vector search is attempted.

    Required indexes:
    - skill_embedding_idx (Skill.embedding, 384 dimensions, cosine similarity)
    - job_embedding_idx (Job.embedding, 384 dimensions, cosine similarity)
    - company_embedding_idx (Company.embedding, 384 dimensions, cosine similarity)

    Raises:
        RuntimeError: If any required index is missing or not ONLINE

    Returns:
        None: On successful validation
    """
    global neo4j_driver

    if not neo4j_driver:
        raise RuntimeError("Neo4j driver not initialized")

    required_indexes = ["skill_embedding_idx", "job_embedding_idx", "company_embedding_idx"]

    try:
        async with neo4j_driver.session() as session:
            # Query all indexes
            result = await session.run("SHOW INDEXES")
            records = await result.data()

            # Extract index names and states
            existing_indexes = {
                record["name"]: record.get("state", "UNKNOWN") for record in records
            }

            # Check for missing indexes
            missing_indexes = [idx for idx in required_indexes if idx not in existing_indexes]

            if missing_indexes:
                error_msg = (
                    f"CRITICAL: Missing Neo4j vector indexes: {missing_indexes}. "
                    f"Run backend/scripts/initial_setup.py to create required indexes."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Verify indexes are ONLINE
            offline_indexes = [idx for idx in required_indexes if existing_indexes[idx] != "ONLINE"]

            if offline_indexes:
                error_msg = (
                    f"CRITICAL: Neo4j vector indexes not ONLINE: {offline_indexes}. "
                    f"Current states: {[(idx, existing_indexes[idx]) for idx in offline_indexes]}"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info(f"✅ All {len(required_indexes)} Neo4j vector indexes validated (ONLINE)")
            print(f"✅ Neo4j vector indexes validated: {', '.join(required_indexes)}")

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        error_msg = f"Failed to validate Neo4j indexes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e


def cleanup_task():
    """
    Scheduled cleanup task for expired temporary files (Story 2.3).

    Runs every 15 minutes to remove expired files from cache.
    This prevents memory leaks from files that were never confirmed.
    """
    try:
        cleaned = cleanup_expired_files()
        if cleaned > 0:
            logger.info(f"File cleanup task: Removed {cleaned} expired temporary files")
    except Exception as e:
        logger.error(f"File cleanup task failed: {str(e)}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage database connections and background tasks lifecycle.

    Connects to both PostgreSQL (via Prisma) and Neo4j on startup,
    starts the file cleanup scheduler (Story 2.3), and cleanly
    disconnects/shuts down on exit.

    Args:
        app: FastAPI application instance

    Yields:
        None: Control flow during application runtime
    """
    global neo4j_driver

    # Startup: Connect to databases
    print("🔌 Connecting to databases...")
    try:
        await prisma_client.connect()
        print("✅ PostgreSQL connected via Prisma")
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")

    try:
        neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        print("✅ Neo4j driver initialized")

        # INFRASTRUCTURE FIX (INFRA-001): Validate vector indexes on startup
        print("🔍 Validating Neo4j vector indexes...")
        await validate_neo4j_indexes()

    except RuntimeError as e:
        # Infrastructure validation failed - this is a fatal error
        print(f"❌ CRITICAL: {str(e)}")
        print("❌ Application cannot start without required vector indexes")
        raise
    except Exception as e:
        print(f"❌ Neo4j initialization/validation failed: {e}")
        raise

    # Startup: Start file cleanup scheduler (Story 2.3)
    print("⏰ Starting file cleanup scheduler...")
    try:
        # Schedule cleanup every 15 minutes
        file_cleanup_scheduler.add_job(
            cleanup_task, "interval", minutes=15, id="file_cleanup", replace_existing=True
        )
        file_cleanup_scheduler.start()
        logger.info("File cleanup scheduler started (runs every 15 minutes)")
        print("✅ File cleanup scheduler started")
    except Exception as e:
        logger.error(f"Failed to start file cleanup scheduler: {str(e)}")
        print(f"❌ File cleanup scheduler failed: {e}")

    yield

    # Shutdown: Stop scheduler
    print("⏰ Stopping file cleanup scheduler...")
    try:
        file_cleanup_scheduler.shutdown(wait=False)
        logger.info("File cleanup scheduler stopped")
        print("✅ File cleanup scheduler stopped")
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {str(e)}")
        print(f"❌ Scheduler shutdown error: {e}")

    # Shutdown: Close connections
    print("🔌 Disconnecting from databases...")
    try:
        await prisma_client.disconnect()
        print("✅ PostgreSQL disconnected")
    except Exception as e:
        print(f"❌ PostgreSQL disconnection error: {e}")

    try:
        if neo4j_driver:
            await neo4j_driver.close()
            print("✅ Neo4j driver closed")
    except Exception as e:
        print(f"❌ Neo4j driver close error: {e}")


# Create FastAPI application
app = FastAPI(
    title="Graph RAG API",
    description="Knowledge Graph RAG System for Skills & Jobs",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow frontend requests
# IMPORTANT: Must be added BEFORE any routes/exception handlers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Frontend dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://richardson-blocked-lead-angels.trycloudflare.com",  # Cloudflare Tunnel Frontend
        "https://*.trycloudflare.com",  # Allow all Cloudflare tunnel domains
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Register rate limiter (Story 4.7: Rate limiting for query endpoint)
app.state.limiter = query.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Register exception handlers (Story 2.6: Global error handling)
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """
    Handle authentication errors with consistent response format.

    Args:
        request: The incoming request
        exc: The authentication exception raised

    Returns:
        JSONResponse: 401 Unauthorized with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "authentication_failed", "message": exc.detail},
        headers=exc.headers,
    )


# Story 2.6: System error handling
app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.add_exception_handler(Neo4jServiceUnavailable, neo4j_connection_error_handler)

app.add_exception_handler(PrismaError, postgres_connection_error_handler)

# Catch-all for unexpected errors (Story 2.6)
app.add_exception_handler(Exception, global_exception_handler)


# Register routers
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(admin.router)
app.include_router(query.router)
app.include_router(monitor.router)
app.include_router(skills.router)


@app.get("/")
async def root():
    """
    Root endpoint.

    Returns:
        dict: Welcome message and API information
    """
    return {"message": "Graph RAG API", "version": "1.0.0", "docs": "/docs", "health": "/health"}


@app.get("/stats")
async def get_graph_stats():
    """
    Get knowledge graph statistics.

    Returns counts of nodes (jobs, skills, companies) and last updated timestamp
    from the Neo4j knowledge graph.

    Returns:
        dict: Statistics including node counts and last updated time

    Response Codes:
        200: Successfully retrieved statistics
        503: Neo4j database unavailable
    """
    from fastapi.responses import JSONResponse
    from datetime import datetime

    try:
        if neo4j_driver is None:
            return JSONResponse(
                content={
                    "error": "Neo4j database unavailable",
                    "stats": {"jobs": 0, "skills": 0, "companies": 0, "lastUpdated": None},
                },
                status_code=503,
            )

        async with neo4j_driver.session() as session:
            # Get counts for each node type
            result = await session.run(
                """
                MATCH (j:Job)
                WITH count(j) as jobCount
                MATCH (s:Skill)
                WITH jobCount, count(s) as skillCount
                MATCH (c:Company)
                WITH jobCount, skillCount, count(c) as companyCount
                OPTIONAL MATCH (n)
                WHERE n.updated_at IS NOT NULL
                WITH jobCount, skillCount, companyCount, n
                ORDER BY n.updated_at DESC
                LIMIT 1
                RETURN jobCount, skillCount, companyCount, n.updated_at as lastUpdated
            """
            )

            record = await result.single()

            if record:
                last_updated = record["lastUpdated"]
                if last_updated:
                    # Calculate days ago
                    from datetime import timezone

                    now = datetime.now(timezone.utc)
                    last_updated_dt = datetime.fromisoformat(
                        str(last_updated).replace("Z", "+00:00")
                    )
                    days_ago = (now - last_updated_dt).days

                    if days_ago == 0:
                        last_updated_str = "today"
                    elif days_ago == 1:
                        last_updated_str = "1 day ago"
                    else:
                        last_updated_str = f"{days_ago} days ago"
                else:
                    last_updated_str = "never"

                return {
                    "jobs": record["jobCount"] or 0,
                    "skills": record["skillCount"] or 0,
                    "companies": record["companyCount"] or 0,
                    "lastUpdated": last_updated_str,
                }
            else:
                return {"jobs": 0, "skills": 0, "companies": 0, "lastUpdated": "never"}

    except Exception as e:
        logger.error(f"Error fetching graph stats: {str(e)}", exc_info=True)
        return JSONResponse(
            content={
                "error": "Failed to fetch statistics",
                "message": str(e),
                "stats": {"jobs": 0, "skills": 0, "companies": 0, "lastUpdated": None},
            },
            status_code=500,
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify database connectivity.

    Tests connections to both PostgreSQL and Neo4j databases and returns
    the status of each along with an overall service health status.

    Returns:
        dict: JSON response with service status and database connectivity info
            - service: Service name
            - version: API version
            - status: Overall status ("healthy" or "unhealthy")
            - databases: Dict with status of each database

    Response Codes:
        200: Service is healthy (all databases connected)
        503: Service is unhealthy (one or more databases disconnected)
    """
    from fastapi.responses import JSONResponse

    health_status = {
        "service": "graph-rag-api",
        "version": "1.0.0",
        "status": "healthy",
        "databases": {"postgresql": "unknown", "neo4j": "unknown"},
    }

    # Check PostgreSQL connection
    try:
        # Test connection with a simple query
        await prisma_client.query_raw("SELECT 1")
        health_status["databases"]["postgresql"] = "connected"
    except Exception as e:
        health_status["databases"]["postgresql"] = f"disconnected: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Neo4j connection
    try:
        if neo4j_driver is None:
            raise Exception("Neo4j driver not initialized")

        # Test connection with a simple Cypher query
        async with neo4j_driver.session() as session:
            result = await session.run("RETURN 1 as num")
            await result.single()
        health_status["databases"]["neo4j"] = "connected"
    except Exception as e:
        health_status["databases"]["neo4j"] = f"disconnected: {str(e)}"
        health_status["status"] = "unhealthy"

    # Return 503 if unhealthy, 200 if healthy
    status_code = 503 if health_status["status"] == "unhealthy" else 200

    return JSONResponse(content=health_status, status_code=status_code)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,  # Development only
    )
