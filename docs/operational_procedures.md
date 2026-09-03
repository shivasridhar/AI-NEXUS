# SentinelAI Operational Procedures

## System Startup

### Local Development

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Verify services
docker-compose ps
# postgres: running (port 5433)
# neo4j:    running (ports 7474, 7687)
# redis:    running (port 6379)

# 3. Run database migrations
cd sentinel_backend
alembic upgrade head

# 4. Start backend
fastapi dev app/main.py
# Starts on http://localhost:8000
# Risk worker starts automatically via lifespan

# 5. Start frontend
cd sentinel_frontend
npm run dev
# Starts on http://localhost:3000
```

### Startup Verification

After startup, verify:

1. **Health check**: `GET http://localhost:8000/api/v1/health`
   - Expect: `{"status": "ok", "database": "ok", "neo4j": "ok"}`
2. **API docs**: `http://localhost:8000/api/v1/openapi.json`
3. **Neo4j browser**: `http://localhost:7474`
4. **Frontend**: `http://localhost:3000`

### Startup Order

```
PostgreSQL -> Redis -> Neo4j -> Backend (with risk worker) -> Frontend
```

Neo4j failure is non-fatal: the backend starts but graph features return 503.

---

## System Shutdown

```bash
# 1. Stop frontend (Ctrl+C)
# 2. Stop backend (Ctrl+C) - gracefully:
#    - Cancels risk worker
#    - Closes Neo4j connection
#    - Closes Redis client
# 3. Stop infrastructure
docker-compose down
# Add -v to also remove volumes (data loss!)
```

---

## Database Maintenance

### Run Migrations

```bash
cd sentinel_backend

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current migration version
alembic current

# View migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "description"
```

### Database Connection Check

```bash
# Use check_db.py
cd sentinel_backend
python check_db.py
```

### Backup Procedures

```bash
# PostgreSQL backup
docker exec sentinel_postgres pg_dump -U postgres sentinel > backup_$(date +%Y%m%d).sql

# PostgreSQL restore
docker exec -i sentinel_postgres psql -U postgres sentinel < backup_file.sql

# Neo4j backup (stop neo4j first)
docker exec sentinel_neo4j neo4j-admin database dump neo4j --to-path=/data/backups

# Redis backup (RDB snapshot)
docker exec sentinel_redis redis-cli BGSAVE
```

---

## Redis Cache Management

```bash
# Connect to Redis CLI
docker exec -it sentinel_redis redis-cli

# Check connectivity
PING  # Expect: PONG

# View blacklisted tokens
KEYS blacklist:*

# Check memory usage
INFO memory

# Flush all (CAUTION: clears token blacklist)
FLUSHALL
```

---

## Common Troubleshooting

### Backend won't start

| Symptom | Cause | Fix |
|---------|-------|-----|
| "FATAL: SECRET_KEY not set" | Missing env var | Set `SECRET_KEY` in `.env` |
| Database connection refused | PostgreSQL not running | `docker-compose up -d postgres` |
| Neo4j connection failed | Neo4j not running | `docker-compose up -d neo4j` (non-fatal) |
| Import errors | Wrong Python path | Ensure `conftest.py` is present |

### Frontend won't connect to API

| Symptom | Cause | Fix |
|---------|-------|-----|
| CORS errors | Origin not in allowlist | Add `FRONTEND_URL` to backend `.env` |
| 401 Unauthorized | Token expired | Login again / check token refresh |
| Network error | Backend not running | Start backend on port 8000 |

### Ingestion failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Job stuck in "running" | Worker crashed | Restart backend (known debt) |
| Duplicate events | Dedup window mismatch | Check `DEDUP_WINDOW_SECONDS` |
| Empty results | Invalid S3 bucket | Verify `s3_bucket_name` |

### AI investigation errors

| Error Code | Cause | Fix |
|------------|-------|-----|
| `AI_AUTH_FAILED` | Invalid API key | Check `GEMINI_API_KEY` |
| `AI_RATE_LIMITED` | Quota exceeded | Wait and retry, or upgrade plan |
| `AI_TIMEOUT` | Slow response | Retry (auto-retry 3x) |

---

## Event Bus Diagnostics

```python
# Check DLQ size (in Python/FastAPI shell)
from app.core.events.bus import event_bus
print(f"DLQ size: {event_bus.get_dlq_size()}")
```

If DLQ is growing:
1. Check handler error logs for root cause
2. Verify workspace_id/organization_id are set on published events
3. Check database connectivity (audit projector writes to DB)

---

## User & Workspace Management

### Create user (via API)

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Admin User",
    "email": "admin@example.com",
    "password": "SecurePass123!@#",
    "organization_name": "My Org",
    "workspace_name": "Production"
  }'
```

Registration auto-creates: Organization + Workspace + User (admin role)

### View current user

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

---

## Scaling Considerations

### Current Limitations (Known Debt)

1. **Risk worker**: Runs as `asyncio.create_task` in the main process. Should be a standalone worker for production.
2. **Event bus**: In-memory, synchronous publisher. Future: Kafka/RabbitMQ.
3. **Session management**: Token blacklist in Redis (single instance). Future: Redis Cluster.

### Scaling Path

| Component | Current | Production Recommendation |
|-----------|---------|--------------------------|
| Backend | Single process | Multiple Uvicorn workers or Gunicorn |
| Risk Worker | In-process task | Standalone container with heartbeat |
| Event Bus | In-memory | Kafka or Redis Streams |
| PostgreSQL | Single Docker | Managed (Neon, RDS, Cloud SQL) |
| Neo4j | Single Docker | Neo4j Aura (managed) |
| Redis | Single Docker | Redis Cloud / ElastiCache |
| Frontend | Vercel/Netlify | CDN with edge caching |

---

## Maintenance Windows

### Recommended Schedule

| Task | Frequency | Impact |
|------|-----------|--------|
| Database migrations | Per release | Brief downtime |
| PostgreSQL VACUUM | Weekly (auto) | None |
| Redis memory check | Weekly | None |
| Neo4j backup | Daily | None |
| Log rotation | Daily | None |
| Token blacklist cleanup | Automatic (TTL) | None |
| Dependency updates | Monthly | Requires testing |

---

## Incident Response Template

### Step 1: Identify
- Check `/api/v1/health` endpoint
- Review application logs for errors
- Check DLQ for failed events

### Step 2: Contain
- If API is down: check database and Neo4j connectivity
- If AI features fail: verify `GEMINI_API_KEY` and quota
- If auth fails: verify `SECRET_KEY` is set and Redis is running

### Step 3: Resolve
- Apply fix or configuration change
- Restart affected service
- Verify health check returns "ok"

### Step 4: Post-Mortem
- Document root cause
- Review audit logs for timeline
- Update troubleshooting guide if new issue pattern
