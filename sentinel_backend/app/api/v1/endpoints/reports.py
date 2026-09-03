from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import logging
import json
from neo4j import Session as GraphSession

logger = logging.getLogger(__name__)

from app.api.dependencies import get_db, get_current_workspace, get_current_active_user, get_neo4j_session
from app.services.report_engine import ReportEngineService
from app.models.tenant import Workspace, User
from app.services.report_pipeline.report_storage import ReportStorage
from app.models.risk_finding import RiskFinding
from app.models.machine_identity import MachineIdentity
from app.models.risk_score import RiskScore
from app.services.report_pipeline.entity_pdf_generator import EntityPDFGenerator

router = APIRouter()

class ReportGenerateRequest(BaseModel):
    name: str
    report_type: str
    filters: Dict[str, Any]

@router.get("/statistics")
def get_report_statistics(
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    service = ReportEngineService(db)
    stats = service.get_report_statistics(str(workspace.id))
    return stats

@router.get("/")
def get_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    service = ReportEngineService(db)
    reports = service.get_reports(str(workspace.id), skip=skip, limit=limit)
    return {
        "data": [
            {
                "id": str(r.id),
                "name": r.name,
                "type": r.type,
                "status": r.status,
                "file_url": r.file_url,
                "csv_url": r.csv_url,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in reports
        ]
    }

@router.post("/generate")
def generate_report(
    req: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    service = ReportEngineService(db)
    report = service.generate_report(
        background_tasks=background_tasks,
        workspace_id=str(workspace.id),
        organization_id=str(workspace.organization_id),
        name=req.name,
        report_type=req.report_type,
        filters=req.filters,
        user_id=str(current_user.id)
    )
    return {
        "id": str(report.id),
        "name": report.name,
        "status": report.status,
        "file_url": report.file_url
    }

@router.get("/{report_id}/download")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    logger.info(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "STARTED"}))
    from app.models.report import Report
    report = db.query(Report).filter(
        Report.id == uuid.UUID(report_id),
        Report.workspace_id == workspace.id
    ).first()
    
    if not report:
        logger.warning(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": "Report not found"}))
        raise HTTPException(status_code=404, detail="Report not found")
        
    if report.status == "FAILED":
        logger.warning(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": "Report generation failed"}))
        raise HTTPException(status_code=400, detail="Unable to generate report.")
    elif report.status != "COMPLETED":
        logger.warning(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": "Not completed"}))
        raise HTTPException(status_code=400, detail="Report generation not completed")
        
    if not report.file_url:
        logger.error(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": "Missing file_url"}))
        raise HTTPException(status_code=404, detail="PDF generation failed.")
        
    storage = ReportStorage()
    try:
        file_bytes = storage.get_file(report.file_url)
    except FileNotFoundError:
        logger.error(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": "File not found in storage"}))
        raise HTTPException(status_code=404, detail="Download unavailable.")
    except Exception as e:
        logger.error(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "FAILED", "reason": f"Storage error: {e}"}))
        raise HTTPException(status_code=503, detail="Storage unavailable.")
    
    from fastapi.responses import StreamingResponse
    import io
    
    logger.info(json.dumps({"workspace_id": str(workspace.id), "report_id": report_id, "action": "DOWNLOAD", "status": "SUCCESS"}))
    return StreamingResponse(
        io.BytesIO(file_bytes), 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={report.name.replace(' ', '_')}.pdf"}
    )

class ReportExportRequest(BaseModel):
    identity_id: Optional[str] = None
    finding_id: Optional[str] = None

@router.post("/export")
def export_entity_report(
    req: ReportExportRequest,
    db: Session = Depends(get_db),
    graph: GraphSession = Depends(get_neo4j_session),
    workspace: Workspace = Depends(get_current_workspace),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    if not req.identity_id and not req.finding_id:
        raise HTTPException(status_code=400, detail="Either identity_id or finding_id must be provided")

    pdf_generator = EntityPDFGenerator()

    if req.finding_id:
        try:
            finding_uuid = uuid.UUID(req.finding_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid finding ID format")

        finding = db.query(RiskFinding).filter(
            RiskFinding.id == finding_uuid,
            RiskFinding.workspace_id == workspace.id
        ).first()

        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        identity = db.query(MachineIdentity).filter(
            MachineIdentity.id == finding.identity_id,
            MachineIdentity.workspace_id == workspace.id
        ).first()

        if not identity:
            raise HTTPException(status_code=404, detail="Associated machine identity not found")

        # Gather Explainability & Graph Evidence details
        evidence = {}
        try:
            from app.services.graph_evidence.explainability_service import ExplainabilityService
            service = ExplainabilityService(db, graph)
            evidence = service.generate_finding_details(str(finding.id), str(workspace.id), str(finding.identity_id))
        except Exception as e:
            logger.error(f"Failed to gather graph evidence for PDF: {e}")
            evidence = {
                "explainability": f"Dynamic rule-based fallback explanation: This finding shows {finding.finding_type} vulnerability for identity {identity.arn}.",
                "graph_metrics": {},
                "risk_factors": []
            }

        pdf_bytes = pdf_generator.generate_finding_report(finding, identity, evidence)
        filename = f"finding_report_{str(finding.id)[:8]}.pdf"

    else:  # identity_id is provided
        try:
            identity_uuid = uuid.UUID(req.identity_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid identity ID format")

        identity = db.query(MachineIdentity).filter(
            MachineIdentity.id == identity_uuid,
            MachineIdentity.workspace_id == workspace.id
        ).first()

        if not identity:
            raise HTTPException(status_code=404, detail="Identity not found")

        # Get findings
        findings = db.query(RiskFinding).filter(
            RiskFinding.identity_id == identity.id,
            RiskFinding.workspace_id == workspace.id
        ).all()

        # Get latest risk score
        latest_risk = db.query(RiskScore).filter(
            RiskScore.identity_id == identity.id,
            RiskScore.workspace_id == workspace.id
        ).order_by(RiskScore.calculated_at.desc()).first()

        risk_score = latest_risk.score if latest_risk else 0
        risk_severity = latest_risk.severity if latest_risk else "Low"

        # Get attack path
        attack_path_data = {}
        try:
            from app.services.attack_path_service import AttackPathService
            attack_path_service = AttackPathService(graph)
            attack_path_data = attack_path_service.get_attack_path(identity.arn, str(workspace.id))
        except Exception as e:
            logger.error(f"Failed to fetch attack path for identity PDF: {e}")

        pdf_bytes = pdf_generator.generate_identity_report(
            identity, findings, risk_score, risk_severity, attack_path_data
        )
        filename = f"identity_report_{str(identity.id)[:8]}.pdf"

    from fastapi.responses import StreamingResponse
    import io

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
