"""
Application configuration loaded from environment variables.

Uses pydantic-settings to load and validate configuration from .env file.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationError
from functools import lru_cache
from typing import List
import sys
import logging

# Setup basic logging for config validation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    APP_ENV: str = "development"  # development, staging, production
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database - PostgreSQL
    DATABASE_URL: str

    # Database - Neo4j
    NEO4J_URI: str
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # OpenRouter API
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.3-8b-instruct:free"

    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_MODEL_VERSION: str = "all-MiniLM-L6-v2:2024-01"
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_BATCH_SIZE: int = 32  # Optimal for CPU/GPU
    EMBEDDING_RETRY_MAX: int = 3

    # Legacy settings (deprecated - use EMBEDDING_MODEL_NAME)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # CSV Processing
    MAX_FILE_SIZE_MB: int = 500  # Increased to 500MB for larger datasets
    BATCH_SIZE: int = 1000  # Process records in batches of 1000
    MAX_BATCH_SIZE: int = 5000  # Maximum allowed batch size for validation

    # Skill Similarity Configuration
    SIMILARITY_THRESHOLD: float = 0.7  # Minimum similarity score (0.0-1.0)
    SIMILARITY_TOP_K: int = 5  # Top N most similar skills per skill
    SIMILARITY_BATCH_SIZE: int = 100  # Skills processed per batch

    # Graph Traversal Configuration (Enhanced for Deep RAG)
    GRAPH_TRAVERSAL_DEPTH: int = 4  # Maximum traversal depth (1-5 hops)
    GRAPH_SEED_NODES: int = 50  # Number of seed nodes from vector search
    GRAPH_MAX_NODES: int = 500  # Maximum nodes to return (0 = unlimited)
    GRAPH_MAX_RELATIONSHIPS: int = 1000  # Maximum relationships (0 = unlimited)
    GRAPH_CYPHER_LIMIT: int = 500  # LIMIT clause in Cypher queries
    GRAPH_ENABLE_DEEP_TRAVERSAL: bool = True  # Enable comprehensive graph exploration

    # Network Metrics Configuration (for CO_OCCURS_WITH relationships)
    NETWORK_MIN_CO_OCCURRENCE: int = 2  # Minimum jobs for edge creation
    NETWORK_DIJKSTRA_TIMEOUT: float = 5.0  # Dijkstra query timeout (seconds)
    NETWORK_CACHE_TTL: int = 3600  # Centrality cache TTL (seconds)
    NETWORK_BATCH_SIZE: int = 1000  # Batch size for co-occurrence build

    # Generic Skills Stoplist - excluded from CO_OCCURS_WITH building
    # These hyper-common skills flatten the graph and reduce signal quality
    NETWORK_GENERIC_SKILLS_STOPLIST: List[str] = [
        # Soft Skills (hyper-common)
        "Communication",
        "Communication Skills",
        "Problem Solving",
        "Problem-Solving",
        "Teamwork",
        "Team Work",
        "Leadership",
        "Time Management",
        "Critical Thinking",
        "Attention to Detail",
        "Analytical Skills",
        "Interpersonal Skills",
        "Work Ethic",
        "Adaptability",
        "Collaboration",
        # Basic Tools (ubiquitous)
        "Microsoft Office",
        "MS Office",
        "Microsoft Excel",
        "MS Excel",
        "Excel",
        "Microsoft Word",
        "MS Word",
        "Word",
        "PowerPoint",
        "Microsoft PowerPoint",
        "Outlook",
        "Google Workspace",
        "G Suite",
        # Basic Computer Skills
        "Computer Skills",
        "Basic Computer Skills",
        "Typing",
        "Email",
        "Internet",
    ]

    # Admin endpoint control
    ALLOW_NETWORK_ADMIN: bool = False  # Set true for dev environments

    # GDS Configuration (if using Neo4j Graph Data Science)
    GDS_PROJECTION_NAME: str = "skillNetwork"
    GDS_EIGENVECTOR_ITERATIONS: int = 100
    GDS_EIGENVECTOR_TOLERANCE: float = 1e-7

    # CORS (comma-separated string in .env, parsed to list)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Validators for critical environment variables
    @field_validator("NEO4J_URI")
    @classmethod
    def validate_neo4j_uri(cls, v: str) -> str:
        """Validate Neo4j URI format."""
        if not v.startswith(("neo4j://", "neo4j+s://", "neo4j+ssc://", "bolt://", "bolt+s://")):
            raise ValueError(
                "Invalid Neo4j URI format. Must start with neo4j://, neo4j+s://, "
                "neo4j+ssc://, bolt://, or bolt+s://"
            )
        return v

    @field_validator("OPENROUTER_API_KEY")
    @classmethod
    def validate_openrouter_key(cls, v: str) -> str:
        """Validate OpenRouter API key format."""
        if not v.startswith("sk-or-"):
            raise ValueError(
                "Invalid OpenRouter API key format. Must start with 'sk-or-'"
            )
        if len(v) < 20:
            raise ValueError(
                "OpenRouter API key too short. Expected at least 20 characters."
            )
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key length for security."""
        if len(v) < 32:
            raise ValueError(
                "JWT secret must be at least 32 characters for security. "
                f"Current length: {len(v)}"
            )
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate PostgreSQL database URL format."""
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "Invalid PostgreSQL database URL. Must start with postgresql:// or postgres://"
            )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance with validation.

    Uses lru_cache to ensure settings are loaded only once
    and reused across the application. Validates all environment
    variables and exits with error code 1 if validation fails.

    Returns:
        Settings: Application configuration instance

    Raises:
        SystemExit: If environment validation fails
    """
    try:
        settings_instance = Settings()
        logger.info("✅ All environment variables validated successfully")
        logger.info(f"   - Neo4j URI: {settings_instance.NEO4J_URI[:20]}...")
        logger.info(f"   - Database URL: {settings_instance.DATABASE_URL.split('@')[0]}...")
        logger.info(f"   - OpenRouter API: configured")
        logger.info(f"   - JWT Secret: configured ({len(settings_instance.JWT_SECRET)} chars)")
        logger.info(f"   - Environment: {settings_instance.APP_ENV}")
        return settings_instance
    except ValidationError as e:
        logger.error("❌ Environment variable validation failed!")
        logger.error("")
        logger.error("Validation Errors:")
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            logger.error(f"  • {field}: {message}")
        logger.error("")
        logger.error("Please check your .env file and ensure all required variables are set correctly.")
        logger.error("See .env.example for reference.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {str(e)}")
        sys.exit(1)


# Global settings instance - validated on import
settings = get_settings()
