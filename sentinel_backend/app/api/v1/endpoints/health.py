from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from neo4j import Session as Neo4jSession
from typing import Dict, Any

from app.api.dependencies import get_db, get_neo4j_session

router = APIRouter()

@router.get("/health", response_model=Dict[str, Any])
def health_check(
    db: Session = Depends(get_db),
    graph: Neo4jSession = Depends(get_neo4j_session)
):
    status = {"status": "ok"}
    
    # Check Postgres
    try:
        db.execute(text("SELECT 1"))
        status["database"] = "ok"
    except Exception as e:
        status["database"] = f"error: {str(e)}"
        status["status"] = "error"
        
    # Check Neo4j
    try:
        result = graph.run("RETURN 1 AS n").data()
        if result and result[0]["n"] == 1:
            status["neo4j"] = "ok"
        else:
            status["neo4j"] = "error"
            status["status"] = "error"
    except Exception as e:
        status["neo4j"] = f"error: {str(e)}"
        status["status"] = "error"
        
    # Check Connectors (Integration Freshness)
    try:
        from app.models.integration import Integration
        from datetime import datetime, timezone
        
        integrations = db.query(Integration).all()
        connectors_status = {}
        for integration in integrations:
            connector_name = integration.provider
            if integration.status == "error":
                connectors_status[connector_name] = "error"
                status["status"] = "degraded"
            elif integration.last_sync_time:
                # Check if it has been synced recently (e.g. within last 24h as a baseline for freshness)
                time_diff = datetime.now(timezone.utc) - integration.last_sync_time
                if time_diff.total_seconds() > 86400: # 24 hours
                    connectors_status[connector_name] = "stale"
                    if status["status"] == "ok":
                        status["status"] = "degraded"
                else:
                    connectors_status[connector_name] = "ok"
            else:
                connectors_status[connector_name] = "pending"
                
        status["connectors"] = connectors_status
    except Exception as e:
        status["connectors"] = f"error: {str(e)}"
        status["status"] = "error"
        
    return status
