from typing import Any, Dict

from fastapi import APIRouter, Depends
from neo4j import Session as GraphSession
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_workspace, get_db, get_neo4j_session
from app.models.tenant import Workspace
from app.services.telemetry_service import TelemetryService

router = APIRouter()


@router.get("/summary", response_model=Dict[str, Any])
def get_dashboard_summary(
    db: Session = Depends(get_db),
    graph: GraphSession = Depends(get_neo4j_session),
    workspace: Workspace = Depends(get_current_workspace),
):
    return TelemetryService.get_dashboard_summary(db, graph, workspace.id)


@router.get("/recent-findings")
def get_recent_findings(
    limit: int = 10,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    return TelemetryService.get_recent_findings(db, workspace.id, limit)


@router.get("/recent-events")
def get_recent_events(
    limit: int = 15,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    return TelemetryService.get_recent_events(
        db, workspace.id, limit, format_for_ingestion=False
    )


@router.get("/top-attack-paths")
def get_top_attack_paths(
    limit: int = 3,
    graph: GraphSession = Depends(get_neo4j_session),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    return TelemetryService.get_top_attack_paths(graph, workspace.id, limit)
