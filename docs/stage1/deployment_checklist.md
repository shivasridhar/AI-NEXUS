# Stage 1 Deployment Checklist

This document provides the necessary steps and automated checks to run before deploying the SentinelAI Stage 1 system.

## 1. Preflight Verification (Automated)

Instead of manually ticking off boxes, Stage 1 provides an automated preflight script that verifies Docker, database connections, environment variables, Alembic migrations, and the live API/Frontend.

**Run the script from the repository root:**
```bash
./scripts/preflight.sh
```

**What it checks:**
- **Environment:** Verifies `.env` files and required variables (`DATABASE_URL`, `SECRET_KEY`, `NEXT_PUBLIC_API_URL`) are present.
- **Docker:** Verifies Docker daemon is running and `docker-compose.yml` is valid.
- **Databases:** Pings PostgreSQL (port 5433) and Neo4j (port 7687).
- **Migrations:** Ensures `alembic current` passes without errors.
- **API & Frontend:** Hits `http://localhost:8000/api/v1/health` and `http://localhost:3000` to verify live endpoints.

**Action Required:** If any check emits a `[FAIL]`, resolve the underlying issue before proceeding with the deployment.

---

## 2. Architecture Caveat: Kafka

> [!NOTE]
> **Kafka is intentionally NOT part of this Stage 1 deployment.** 
> The system currently relies on a synchronous in-memory `SecurityEventPublisher` as its final integration point. The absence of Kafka containers or topics is the expected, correct configuration for Stage 1. Do not flag its absence as an infrastructure oversight during deployment reviews.

---

## 3. Rollback Procedure

If a critical flaw is discovered immediately post-deployment, follow this rapid rollback procedure to hide Stage 1 ingestion features from end users while preserving core app functionality.

### Frontend Rollback (Hide Routes)
1. Open `sentinel_frontend/src/config/navigation.ts` (or the sidebar equivalent).
2. Comment out the `/integrations` and `/ingestion` menu items.
3. Trigger a frontend redeploy (or restart the Next.js service). This instantly removes user access to the broken views.

### Backend Rollback (Disable API)
1. Open `sentinel_backend/app/main.py`.
2. Locate the inclusion of the `ingestion` router:
   ```python
   # Comment this line out:
   # app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["Ingestion"])
   ```
3. Restart the FastAPI service. Any lingering background calls will gracefully fail with HTTP 404.

