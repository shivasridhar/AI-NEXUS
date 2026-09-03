from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from neo4j import Session as GraphSession
from typing import Dict, Any

from app.api.dependencies import get_db, get_neo4j_session, get_current_workspace
from app.models.machine_identity import MachineIdentity
from app.models.tenant import User, Workspace
from app.services.attack_path_service import AttackPathService

router = APIRouter()

from typing import List
from app.models.risk_score import RiskScore

@router.get("", response_model=List[Dict[str, Any]])
def list_identities(db: Session = Depends(get_db), workspace: Workspace = Depends(get_current_workspace)):
    identities = db.query(MachineIdentity).filter(MachineIdentity.workspace_id == workspace.id).all()
    results = []
    for ident in identities:
        latest_risk = db.query(RiskScore).filter(RiskScore.identity_id == ident.id, RiskScore.workspace_id == workspace.id).order_by(RiskScore.calculated_at.desc()).first()
        results.append({
            "id": str(ident.id),
            "arn": ident.arn,
            "identity_type": ident.identity_type,
            "account_id": ident.account_id,
            "first_seen": ident.first_seen,
            "last_seen": ident.last_seen,
            "total_events": ident.total_events,
            "risk_score": latest_risk.score if latest_risk else 0,
            "risk_severity": latest_risk.severity if latest_risk else "Low"
        })
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results

@router.get("/{identity_id}/attack-path", response_model=Dict[str, Any])
def get_identity_attack_path(
    identity_id: str,
    db: Session = Depends(get_db),
    graph: GraphSession = Depends(get_neo4j_session),
    workspace: Workspace = Depends(get_current_workspace)
):
    identity = db.query(MachineIdentity).filter(MachineIdentity.id == identity_id, MachineIdentity.workspace_id == workspace.id).first()
    if not identity:
        raise HTTPException(status_code=404, detail="Identity not found")
        
    try:
        service = AttackPathService(graph)
        graph_data = service.get_attack_path(identity.arn, str(workspace.id))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching attack path for {identity.arn}: {e}", exc_info=True)
        graph_data = {"nodes": [], "edges": []}
        
    return graph_data
