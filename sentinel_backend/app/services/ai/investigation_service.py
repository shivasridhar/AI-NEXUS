from typing import Dict, Any
from app.services.ai.ai_workflow_service import AIWorkflowService

class InvestigationService:
    def __init__(self, db=None, graph=None):
        # We accept db and graph for backward compatibility of API endpoints,
        # but LangGraph nodes (specifically retrieve_evidence) now manage their own connections internally.
        self.workflow_service = AIWorkflowService()

    def investigate(self, identity_id: str, workspace_id: str, investigation_id: str = None) -> Dict[str, Any]:
        """
        Delegates to the Enterprise LangGraph workflow.
        """
        return self.workflow_service.run_investigation(
            identity_id=identity_id, 
            workspace_id=workspace_id, 
            investigation_id=investigation_id
        )
