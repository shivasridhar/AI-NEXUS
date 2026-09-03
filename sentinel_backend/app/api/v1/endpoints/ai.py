from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from neo4j import Session as GraphSession
from typing import List, Optional
from pydantic import BaseModel, Field

from app.api.dependencies import get_db, get_neo4j_session, get_current_workspace
from app.services.ai.investigation_service import InvestigationService
from app.schemas.ai_response import Finding, Recommendation
from app.schemas.claims import Citation
from app.schemas.verified_response import VerifiedResponse
from app.models.tenant import Workspace
import uuid

router = APIRouter()


class InvestigateRequest(BaseModel):
    identity_id: str
    force_refresh: bool = False  # Accepted for API compatibility; cache invalidation not yet implemented


class InvestigateResponse(BaseModel):
    success: bool = True
    code: Optional[str] = None
    message: Optional[str] = None
    # Core narrative fields from the verified final_response
    executive_summary: Optional[str] = None
    risk_assessment: Optional[str] = None
    attack_path_analysis: Optional[str] = None
    # Structured nested objects — NOT List[str]
    findings: List[Finding] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    # Verification pipeline outputs
    confidence_score: Optional[float] = None
    citations: List[Citation] = Field(default_factory=list)
    # Full enterprise payload for consumers that need the complete verification audit trail
    verified_response: Optional[VerifiedResponse] = None


@router.post("/investigate", response_model=InvestigateResponse)
def investigate_identity(
    request: InvestigateRequest,
    db: Session = Depends(get_db),
    graph: GraphSession = Depends(get_neo4j_session),
    workspace: Workspace = Depends(get_current_workspace)
):
    investigation_id = str(uuid.uuid4())
    try:
        service = InvestigationService(db, graph)
        report = service.investigate(request.identity_id, str(workspace.id), investigation_id)

        # We always return HTTP 200 with the sanitized payload to prevent UI crashes
        if "error" in report and "success" not in report:
            # Handle legacy error dict from EvidenceCollector if any
            return {
                "success": False,
                "code": "UNKNOWN_ERROR",
                "message": report["error"]
            }

        return report
    except Exception as e:
        # Fallback for completely unhandled errors outside the AI service
        return {
            "success": False,
            "code": "UNKNOWN_ERROR",
            "message": "An unexpected error occurred while setting up the investigation."
        }
