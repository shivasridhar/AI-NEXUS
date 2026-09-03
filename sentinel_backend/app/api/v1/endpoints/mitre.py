"""
MITRE ATT&CK and Compliance API endpoints.
Exposes the deterministic MITRE mapping and compliance analysis.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.dependencies import get_db, get_current_workspace
from app.models.risk_score import RiskScore
from app.models.tenant import Workspace
from app.services.risk_engine.mitre_mapper import MitreMapper
from app.services.risk_engine.compliance_mapper import ComplianceMapper

router = APIRouter()
mitre_mapper = MitreMapper()
compliance_mapper = ComplianceMapper()


@router.get("/techniques")
def get_workspace_mitre_techniques(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Returns all MITRE ATT&CK techniques observed across the workspace's
    risk evidence data.
    """
    scores = db.query(RiskScore).filter(
        RiskScore.workspace_id == workspace.id
    ).all()

    all_techniques = []
    seen_ids = set()

    for score in scores:
        evidence = score.risk_evidence or {}
        techniques = evidence.get("mitre_techniques", [])
        for tech in techniques:
            tid = tech.get("technique_id", "")
            if tid and tid not in seen_ids:
                seen_ids.add(tid)
                all_techniques.append(tech)

    # Sort by tactic kill-chain order
    if all_techniques:
        chain = mitre_mapper.get_attack_chain([t["technique_id"] for t in all_techniques])
        return {"techniques": chain, "total": len(chain)}

    return {"techniques": all_techniques, "total": len(all_techniques)}


@router.get("/compliance")
def get_workspace_compliance(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace)
):
    """
    Returns compliance posture scores across all frameworks
    based on observed MITRE techniques.
    """
    scores = db.query(RiskScore).filter(
        RiskScore.workspace_id == workspace.id
    ).all()

    all_technique_ids = set()
    for score in scores:
        evidence = score.risk_evidence or {}
        techniques = evidence.get("mitre_techniques", [])
        for tech in techniques:
            tid = tech.get("technique_id", "")
            if tid:
                all_technique_ids.add(tid)

    if not all_technique_ids:
        return {
            "compliance_scores": {},
            "total_techniques": 0,
            "message": "No MITRE techniques observed yet. Upload security events to generate compliance data."
        }

    compliance_scores = compliance_mapper.get_compliance_score(list(all_technique_ids))

    return {
        "compliance_scores": compliance_scores,
        "total_techniques": len(all_technique_ids),
    }
