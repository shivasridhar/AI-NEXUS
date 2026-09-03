import os
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelAI API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Cloud database URL (Render/Neon)
    DATABASE_URL: str = ""

    # PostgreSQL config (used as fallback when DATABASE_URL is not set)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "sentinel"
    POSTGRES_PORT: str = "5433"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        import urllib.parse
        encoded_password = urllib.parse.quote(self.POSTGRES_PASSWORD, safe="")
        return (
            f"postgresql://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Neo4j config
    NEO4J_URI: str = os.getenv("NEO4J_URI") or os.getenv("NEO4J_URL") or "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    # Redis config
    REDIS_URL: str = "redis://localhost:6379"

    # Gemini config
    GEMINI_API_KEY: str = ""

    # JWT Security config
    # No hard default — must be set in production. App will log a critical warning if missing.
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Stage 1 limits and defaults
    MAX_RESULTS_PER_POLL: int = 1000
    MAX_BYTES_PER_POLL: int = 10485760  # 10MB
    DEDUP_WINDOW_SECONDS: int = 3600
    PUBLISHER_MAX_SIZE: int = 10000

    # Feature Flags
    ENABLE_GRAPH_EVIDENCE_ENGINE: bool = True

    # Google Auth — empty default; startup validation warns without crashing
    GOOGLE_CLIENT_ID: str = ""

    # CORS — optional extra frontend origin injected at runtime
    FRONTEND_URL: str = ""

    @field_validator("GOOGLE_CLIENT_ID", mode="after")
    @classmethod
    def validate_google_client_id(cls, v: str) -> str:
        if not v or "your-google-client-id" in v or "<MY_REAL_CLIENT_ID>" in v:
            # Log a warning but do NOT raise — let the app start so Render can serve health checks.
            # The /google route itself will return a 503 if GOOGLE_CLIENT_ID is unset.
            logger.warning(
                "GOOGLE_CLIENT_ID is missing or still a placeholder. "
                "Google Sign-In will be unavailable until this is set in your environment."
            )
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"
        str_strip_whitespace = True


settings = Settings()

# ── Startup diagnostics (safe — never print secrets in full) ──────────────────
logger.info("=== SentinelAI Backend Starting ===")
logger.info("POSTGRES_PORT = %s", settings.POSTGRES_PORT)
logger.info("NEO4J_URI = %s", settings.NEO4J_URI)
logger.info("NEO4J_USER = %s", settings.NEO4J_USER)
logger.info("NEO4J_PASSWORD set = %s", bool(settings.NEO4J_PASSWORD))
logger.info("NEO4J_DATABASE = %s", settings.NEO4J_DATABASE)
logger.info("REDIS_URL = %s", settings.REDIS_URL)
logger.info("GOOGLE_CLIENT_ID set = %s", bool(settings.GOOGLE_CLIENT_ID))
logger.info("SECRET_KEY set = %s", bool(settings.SECRET_KEY))
logger.info("FRONTEND_URL = %s", settings.FRONTEND_URL or "(not set)")

# Critical guard — SECRET_KEY is mandatory in production
if not settings.SECRET_KEY:
    logger.critical(
        "FATAL: SECRET_KEY environment variable is not set. "
        "JWT tokens cannot be signed. Set SECRET_KEY on your Render dashboard."
    )

# Plain prints for Render log visibility (mirrors previous behaviour)
print("POSTGRES_PORT =", settings.POSTGRES_PORT)
print("NEO4J_URI =", settings.NEO4J_URI)
print("NEO4J_USER =", settings.NEO4J_USER)
print("NEO4J_PASSWORD set =", bool(settings.NEO4J_PASSWORD))
print("NEO4J_DATABASE =", settings.NEO4J_DATABASE)
print("GOOGLE_CLIENT_ID set =", bool(settings.GOOGLE_CLIENT_ID))
