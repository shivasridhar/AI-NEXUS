import logging
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.api.v1.api import api_router
from app.graph.session import neo4j_manager
import asyncio
from app.workers.risk_worker import risk_worker
from app.core.redis_client import close_redis_client
from app.core.limiter import limiter
# Initialize Enterprise Projections
from app.projections.audit_projector import audit_projector

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — Neo4j connection is best-effort: if it fails the app still serves
    # HTTP/Postgres routes. Graph routes will return 503 individually.
    try:
        neo4j_manager.connect()
        logger.info("Neo4j connected successfully.")
    except Exception as neo4j_err:
        logger.critical(
            "Neo4j connection failed at startup: %s — "
            "Graph features will be unavailable but the rest of the API is still running.",
            neo4j_err,
        )
        
    # [KNOWN DEBT - Stage 4] TEMPORARY local-dev pattern:
    # Before cloud deployment, this must be replaced with a standalone worker
    # process/container with proper crash recovery (heartbeat + handling for jobs 
    # orphaned in "running" state after a restart).
    worker_task = asyncio.create_task(risk_worker())
    logger.info("Risk worker started.")
    yield
    # Shutdown
    try:
        neo4j_manager.close()
    except Exception:
        pass
    
    # Cancel worker
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
        
    # Close Redis client
    await close_redis_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)
app.state.limiter = limiter

_ALLOWED_ORIGINS = [
    "https://ai-nexus-2eas.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://sentinel14.netlify.app",
    "https://sentinelai-repo-with-git-wxvp.vercel.app",
    "https://sentinelai-repo-with-git-gld6-five.vercel.app",
]

if settings.FRONTEND_URL:
    _extra = settings.FRONTEND_URL.rstrip("/")
    if _extra not in _ALLOWED_ORIGINS:
        _ALLOWED_ORIGINS.append(_extra)
        logger.info("CORS: added FRONTEND_URL origin → %s", _extra)

logger.info("CORS allowed origins: %s", _ALLOWED_ORIGINS)

_ALLOWED_ORIGIN_REGEX_STRING = r"^https://sentinelai-repo-with-git(?:-[a-zA-Z0-9]+)*\.vercel\.app$"
_ALLOWED_ORIGIN_REGEX = re.compile(_ALLOWED_ORIGIN_REGEX_STRING)

def _add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    origin = request.headers.get("origin")
    if origin and (origin in _ALLOWED_ORIGINS or _ALLOWED_ORIGIN_REGEX.match(origin)):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
    return response

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": []
            }
        },
    )
    return _add_cors_headers(request, response)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    response = JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors()
            }
        },
    )
    return _add_cors_headers(request, response)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal Server Error",
                "details": []
            }
        },
    )
    return _add_cors_headers(request, response)

# ─────────────────────────────────────────────────────────────────────────────
# CORS — Must be added BEFORE any other middleware and BEFORE include_router.
#
# CRITICAL RULES:
#   1. allow_methods=["*"] — do NOT enumerate; "*" is required so the
#      Access-Control-Allow-Methods response header contains all methods,
#      satisfying any preflight regardless of what the browser requests.
#   2. allow_headers=["*"] — do NOT enumerate a partial list.
#      The x-workspace-id header sent by our frontend would be rejected by
#      a browser preflight if it is not in the explicit allow_headers list.
#      Using "*" covers all custom headers automatically.
#   3. allow_credentials=True — required for Authorization header forwarding.
#   4. Never use allow_origins=["*"] when allow_credentials=True — that is
#      an invalid combination per the CORS spec. Always use explicit origins.
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=_ALLOWED_ORIGIN_REGEX_STRING,
    allow_credentials=True,
    allow_methods=["*"],   # Covers GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
    allow_headers=["*"],   # Covers Authorization, Content-Type, x-workspace-id, etc.
    expose_headers=["*"],
    max_age=600,           # Preflight cache: 10 minutes — reduces OPTIONS round-trips
)

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    response = JSONResponse(
        status_code=429,
        content={"detail": "Too many requests, please try again later."}
    )
    return _add_cors_headers(request, response)

app.add_middleware(SlowAPIMiddleware)

# Routers are included AFTER middleware so CORS wraps all routes
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
