# SentinelAI Monitoring & Observability Guide

## Overview

SentinelAI implements health checks, structured logging, an event bus with dead letter queue (DLQ), and audit logging for observability. This guide documents what is currently implemented and recommends additional monitoring.

---

## Health Check Endpoint

**Endpoint**: `GET /api/v1/health`

Checks the health of all infrastructure components:

```json
{
  "status": "ok",           // "ok" | "degraded" | "error"
  "database": "ok",         // PostgreSQL: SELECT 1
  "neo4j": "ok",            // Neo4j: RETURN 1
  "connectors": {
    "aws": "ok"             // Per-integration status
  }
}
```

### Status Logic

| Component | Check | Failure Impact |
|-----------|-------|----------------|
| PostgreSQL | `SELECT 1` | status -> "error" |
| Neo4j | `RETURN 1 AS n` | status -> "error" |
| Connectors | Integration status + last_sync_time | status -> "degraded" |

### Connector Freshness

- **ok**: Last sync within 24 hours
- **stale**: Last sync > 24 hours ago
- **error**: Integration status is "error"
- **pending**: Never synced

---

## Application Logging

### Python Logging

SentinelAI uses Python's built-in `logging` module throughout:

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Operation completed")
logger.warning("Non-critical issue")
logger.error("Error occurred", exc_info=True)
logger.critical("Fatal: SECRET_KEY not set")
```

### Structured Logging (AI Services)

AI service calls produce structured JSON logs:

```python
logger.info(json.dumps({
    "stage": "AI_SUMMARY_GENERATION",
    "status": "STARTED"
}))

logger.error(json.dumps({
    "event": "AI_INVESTIGATION_FAILED",
    "workspace_id": workspace_id,
    "provider": "gemini-3.5-flash",
    "latency_ms": 1234.56,
    "failure_reason": str(e),
    "exception_type": "ValueError"
}))
```

### Startup Diagnostics

At startup, the backend logs:
- Database connection details (port, URI)
- Whether secrets are configured (boolean only, never values)
- CORS allowed origins
- Neo4j connection success/failure
- Risk worker start status

---

## Event Bus & Dead Letter Queue

**File**: `sentinel_backend/app/core/events/bus.py`

### Architecture

```
Publishers (auth, ingestion, etc.)
  |
  v
EventBus (singleton)
  |-- validate(event)  -- fails --> DLQ
  |-- dispatch to subscribers
  |     |-- retry 3x with error logging
  |     |-- all retries fail --> DLQ
  |
  v
Subscribers (AuditProjector, etc.)
```

### Event Types

| Event Type | Usage |
|-----------|-------|
| `AuditEvent` | Authentication, user actions, system changes |
| `GraphEvent` | Graph operations |
| `RiskEvent` | Risk score changes |
| `NotificationEvent` | User-facing notifications |
| `ReportEvent` | Report generation lifecycle |
| `InvestigationEvent` | AI investigation events |

### Event Contract (BaseEvent)

All events include:
- `event_id` (UUID)
- `workspace_id`, `organization_id` (tenant isolation)
- `timestamp`
- `actor`, `actor_type` (who triggered)
- `module`, `action`, `category`
- `severity` (INFO, WARNING, ERROR, CRITICAL)
- `status` (SUCCESS, FAILURE, PARTIAL, DENIED)
- `resource_type`, `resource_id`
- `correlation_id`, `parent_event_id`, `root_event_id` (tracing)
- `duration_ms`
- `metadata` (extensible: IP, request_id, trace_id, cloud_provider, etc.)

### Dead Letter Queue (DLQ)

Events route to DLQ when:
1. Missing `workspace_id` or `organization_id` (validation failure)
2. Handler fails after 3 retry attempts

```python
event_bus.get_dlq_size()  # Check DLQ depth
```

### Monitoring the Event Bus

- DLQ size indicates failed event processing
- Handler errors are logged with event_id and handler name
- Subscriber registration is logged at startup

---

## Audit Logging

### Audit Log Storage

All audit events are persisted to the `audit_logs` PostgreSQL table via the `AuditProjector`.

**Queryable fields**: actor, action, category, severity, status, workspace_id, timestamp, correlation_id

### What Gets Audited

| Action | Module | Category |
|--------|--------|----------|
| LOGIN_SUCCESS | Authentication | AUTHENTICATION |
| ACCOUNT_CREATED | Authentication | AUTHENTICATION |
| ACCOUNT_LINKED | Authentication | AUTHENTICATION |
| Ingestion events | Ingestion | DATA_INGESTION |
| Report generation | Reports | REPORTING |
| AI investigation | AI | INVESTIGATION |

### Audit Log API

`GET /api/v1/audit-logs/` - Query audit logs with filters (workspace-scoped)

---

## Notification System

Notifications are stored in the `notifications` table and served via:

`GET /api/v1/notifications/` - List notifications for current workspace

Types: `CRITICAL`, `PATH`, etc.

---

## Rate Limiting

Global rate limit: **200 requests/minute** (configurable via SlowAPI)

Per-endpoint limits:
- `/auth/register`: 5/minute
- `/auth/login`: 10/minute
- `/auth/google`: 10/minute

Rate limit exceeded returns standard error with `RateLimitExceeded` handler.

---

## Error Handling

### Global Exception Handlers

| Exception | Status | Response Code |
|-----------|--------|---------------|
| `HTTPException` | Varies | `HTTP_ERROR` |
| `RequestValidationError` | 422 | `VALIDATION_ERROR` |
| Unhandled `Exception` | 500 | `INTERNAL_SERVER_ERROR` |

All errors follow the format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [...]
  }
}
```

---

## Recommended Monitoring Additions

### Metrics to Track

| Metric | Source | Priority |
|--------|--------|----------|
| API response time (p50, p95, p99) | Middleware | High |
| Error rate by endpoint | Exception handlers | High |
| Active database connections | SQLAlchemy pool | High |
| Neo4j query latency | Graph session | Medium |
| Redis connectivity | Health check | Medium |
| DLQ depth | EventBus | High |
| AI API call latency | AIAnalystService | Medium |
| Ingestion throughput (events/sec) | Ingestion pipeline | High |
| Risk findings generated/day | Risk worker | Medium |

### Recommended Tools

| Tool | Purpose |
|------|---------|
| Prometheus + Grafana | Metrics collection and dashboards |
| Sentry | Error tracking and alerting |
| ELK Stack / Loki | Log aggregation |
| PgHero | PostgreSQL performance monitoring |
| Redis CLI `INFO` | Redis memory and connection stats |

### Health Check Integration

Use the `/api/v1/health` endpoint for:
- Load balancer health checks
- Uptime monitoring (e.g., UptimeRobot, Pingdom)
- Kubernetes liveness/readiness probes
