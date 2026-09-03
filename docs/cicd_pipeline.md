# SentinelAI CI/CD Pipeline

## Overview

SentinelAI uses **GitHub Actions** for continuous integration with path-filtered test triggers. Deployment targets include **Render** (backend), **Vercel/Netlify** (frontend).

## GitHub Actions Workflow

### CloudTrail Regression Tests

**File**: `.github/workflows/cloudtrail-regression.yml`

```yaml
name: CloudTrail Regression Tests
on:
  push:
    branches: [main, master]
    paths:
      - 'sentinel_backend/app/services/cloudtrail_parser.py'
      - 'sentinel_backend/app/services/ingestion.py'
      - 'sentinel_backend/app/services/ingestion_pipeline/**'
      - 'sentinel_backend/app/services/connectors/**'
  pull_request:
    branches: [main, master]
    paths: [same as above]
```

### Pipeline Stages

```
Trigger (push/PR to main)
  |
  v
[1] Checkout Code
  |
  v
[2] Setup Python 3.12 (with pip cache)
  |
  v
[3] Install Dependencies
  |   pip install -r requirements.txt
  |   pip install pytest pytest-asyncio testcontainers[postgres]
  |
  v
[4] Run CloudTrail Regression Suite
  |   pytest tests/test_cloudtrail_regression.py -v
  |
  v
[5] Report Results
```

### Service Containers

The CI workflow provisions:

| Service | Image | Config |
|---------|-------|--------|
| PostgreSQL | `postgres:15` | User: test_user, DB: sentinel_test, Port: 5432 |

Health check: `pg_isready` (interval: 10s, timeout: 5s, retries: 5)

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` / `master` | Production-ready code |
| Feature branches | Development work, PRs target main |

## Deployment Targets

### Backend (Render)

- **Platform**: Render
- **Runtime**: Python 3.12
- **Entry point**: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Environment**: Configured via Render dashboard
- **Critical env vars**: `SECRET_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`, `NEO4J_*`, `REDIS_URL`

### Frontend (Vercel / Netlify)

- **Vercel**: Primary deployment (`ai-nexus-2eas.vercel.app`)
- **Netlify**: Secondary deployment (`sentinel14.netlify.app`)
- **Build command**: `npm run build`
- **Output**: `.next/` directory

**`netlify.toml`**:
```toml
[build]
  command = "npm run build"
  publish = ".next"
```

## Pre-Flight Checks

**File**: `scripts/preflight.sh`

Run before deployment to validate:
- Environment variables are set
- Database connectivity
- Dependencies installed
- Tests pass

```bash
bash scripts/preflight.sh
```

## Local Development

```bash
# Backend
cd sentinel_backend
pip install -e ".[dev]"
fastapi dev app/main.py

# Frontend
cd sentinel_frontend
npm install
npm run dev
```

## Rollback Procedures

1. **Backend**: Redeploy previous commit via Render dashboard
2. **Frontend**: Redeploy previous build via Vercel/Netlify dashboard
3. **Database**: `alembic downgrade -1` to revert last migration
