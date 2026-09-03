# SentinelAI Environment Configuration Guide

## Overview

SentinelAI uses **Pydantic Settings** (`pydantic_settings.BaseSettings`) for configuration management. Variables are loaded from `.env` files and environment variables, with environment variables taking precedence.

## Environment Variables Reference

### Core Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PROJECT_NAME` | No | "SentinelAI API" | Application display name |
| `VERSION` | No | "1.0.0" | API version |
| `API_V1_STR` | No | "/api/v1" | API route prefix |

### Security (CRITICAL)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **YES** | (empty) | JWT signing key. Generate with: `python -c "import secrets; print(secrets.token_hex(32))"`. App logs FATAL error if missing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | 30 | JWT access token lifetime in minutes |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | No | 10080 | JWT refresh token lifetime (default: 7 days) |

### PostgreSQL Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Preferred | (empty) | Full connection string (takes priority). Format: `postgresql://user:pass@host/db` |
| `POSTGRES_SERVER` | Fallback | "localhost" | PostgreSQL host |
| `POSTGRES_USER` | Fallback | "postgres" | Database user |
| `POSTGRES_PASSWORD` | Fallback | (empty) | Database password (URL-encoded automatically) |
| `POSTGRES_DB` | Fallback | "sentinel" | Database name |
| `POSTGRES_PORT` | Fallback | "5433" | Database port |

**Priority**: If `DATABASE_URL` is set, it is used directly. Otherwise, individual `POSTGRES_*` variables are combined.

### Neo4j Graph Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEO4J_URI` | Yes | "bolt://localhost:7687" | Neo4j Bolt connection URI |
| `NEO4J_USER` | Yes | "neo4j" | Neo4j username |
| `NEO4J_USERNAME` | No | (empty) | Alternative username field |
| `NEO4J_PASSWORD` | Yes | (empty) | Neo4j password |
| `NEO4J_DATABASE` | No | "neo4j" | Neo4j database name |

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | "redis://localhost:6379" | Redis connection URL (used for token blacklisting) |

### AI / Gemini

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | (empty) | Google Gemini API key for AI features |

### Google OAuth

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | No | (empty) | Google OAuth client ID. If not set, Google Sign-In returns 503. Placeholder values are detected and warned. |

### CORS / Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FRONTEND_URL` | No | (empty) | Additional frontend origin for CORS. Added to the hardcoded allowlist. |

**Hardcoded CORS origins**:
- `https://ai-nexus-2eas.vercel.app`
- `http://localhost:3000`
- `http://localhost:3001`
- `https://sentinel14.netlify.app`

### Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_GRAPH_EVIDENCE_ENGINE` | No | true | Enable/disable graph-based evidence collection |

### Stage 1 Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_RESULTS_PER_POLL` | 1000 | Maximum events per ingestion poll |
| `MAX_BYTES_PER_POLL` | 10485760 (10MB) | Maximum data per poll |
| `DEDUP_WINDOW_SECONDS` | 3600 (1hr) | Deduplication time window |
| `PUBLISHER_MAX_SIZE` | 10000 | Max events in publisher buffer |

### Frontend Environment

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000/api/v1`) |

---

## Docker Compose Services

```yaml
services:
  postgres:     # Port 5433:5432, DB: sentinel
  neo4j:        # Ports 7474 (HTTP), 7687 (Bolt)
  redis:        # Port 6379, with health check
```

## Setup Instructions

### 1. Copy Example Environment

```bash
cd sentinel_backend
cp .env.example .env
```

### 2. Configure Required Variables

At minimum, set these in `.env`:
```bash
SECRET_KEY=<generate-with-secrets-module>
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5433/sentinel
NEO4J_PASSWORD=your-neo4j-password
GEMINI_API_KEY=your-gemini-api-key
```

### 3. Start Infrastructure

```bash
docker-compose up -d
```

### 4. Run Migrations

```bash
cd sentinel_backend
alembic upgrade head
```

### 5. Start Backend

```bash
cd sentinel_backend
fastapi dev app/main.py
```

### 6. Start Frontend

```bash
cd sentinel_frontend
npm install
npm run dev
```

## Startup Diagnostics

The backend logs these diagnostics at startup:
- `POSTGRES_PORT`, `NEO4J_URI`, `NEO4J_USER`
- Whether `NEO4J_PASSWORD`, `GOOGLE_CLIENT_ID`, `SECRET_KEY` are set (boolean, not values)
- `FRONTEND_URL` if configured
- CORS allowed origins list

**Critical warnings**:
- Missing `SECRET_KEY` logs a FATAL message (JWT signing will fail)
- Missing/placeholder `GOOGLE_CLIENT_ID` logs a warning (Google Sign-In disabled)
- Neo4j connection failure at startup is non-fatal (graph features degraded, API still runs)

## Secrets Management Best Practices

1. Never commit `.env` files with real credentials (`.env` is in `.gitignore`)
2. Use platform secret management (Render dashboard, Vercel env vars)
3. Rotate `SECRET_KEY` periodically (invalidates all existing JWTs)
4. `encrypted_credentials` field in integrations table stores provider secrets with encryption
5. Generate strong keys: `python -c "import secrets; print(secrets.token_hex(32))"`
