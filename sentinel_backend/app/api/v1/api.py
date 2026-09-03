from fastapi import APIRouter
from app.api.v1.endpoints import health, ingestion, identities, ai, dashboard, auth, organizations, integrations, analytics, notifications, audit_logs, reports, findings, mitre, alerts, soc, ai_conversations
from app.api.v1.websockets import updates

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(organizations.router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion Pipeline"])
api_router.include_router(identities.router, prefix="/identities", tags=["Machine Identities"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Risk Analytics"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Analyst"])
api_router.include_router(ai_conversations.router, prefix="/ai-conversations", tags=["AI Conversations"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(findings.router, prefix="/findings", tags=["Findings"])
api_router.include_router(mitre.router, prefix="/mitre", tags=["MITRE ATT&CK & Compliance"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts Simulation (Stage 1)"])
api_router.include_router(soc.router, prefix="/soc", tags=["SOC Core Engine"])
api_router.include_router(updates.router, prefix="/ws", tags=["Real-Time WebSockets"])
