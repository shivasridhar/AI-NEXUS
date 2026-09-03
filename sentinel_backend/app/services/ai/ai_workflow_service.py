import time
import logging
from typing import Dict, Any
from app.services.langgraph.workflow import create_workflow
from app.services.langgraph.state import WorkflowState
from app.schemas.verified_response import VerifiedResponse

logger = logging.getLogger(__name__)

class AIWorkflowService:
    """
    Orchestrates the LangGraph AI workflow pipeline and handles its lifecycle.
    """
    
    def __init__(self):
        self.app = create_workflow()
        
    def run_investigation(self, identity_id: str, workspace_id: str, investigation_id: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # Initialize state
        state = WorkflowState(
            request_id=investigation_id,
            identity_id=identity_id,
            workspace_id=workspace_id,
            start_time=start_time
        )
        
        try:
            # Execute workflow
            final_state_dict = self.app.invoke(state.model_dump())
            
            # The invoke method might return a dict rather than the pydantic model depending on LangGraph version
            if isinstance(final_state_dict, dict):
                final_state = WorkflowState(**final_state_dict)
            else:
                final_state = final_state_dict
                
            # Log overall metrics
            duration_ms = (time.time() - start_time) * 1000
            logger.info({
                "event": "WORKFLOW_COMPLETED",
                "request_id": investigation_id,
                "duration_ms": duration_ms,
                "has_error": bool(final_state.error_message),
                "nodes_executed": len(final_state.node_history)
            })
            
            if final_state.error_message:
                return {
                    "success": False,
                    "code": "WORKFLOW_ERROR",
                    "message": final_state.error_message
                }
                
            if not final_state.final_response:
                return {
                    "success": False,
                    "code": "MISSING_RESPONSE",
                    "message": "Workflow completed but no final response was generated."
                }
                
            # Wrap response into dict maintaining backwards compatibility
            resp_dict = final_state.final_response.model_dump()
            
            # Extract standard fields from AIResponse embedded in VerifiedResponse
            return {
                "success": True,
                "executive_summary": resp_dict["final_response"]["executive_summary"],
                "risk_assessment": resp_dict["final_response"]["risk_assessment"],
                "attack_path_analysis": resp_dict["final_response"]["attack_path_analysis"],
                "findings": resp_dict["final_response"]["findings"],
                "recommendations": resp_dict["final_response"]["recommendations"],
                "confidence_score": resp_dict["confidence_score"],
                "citations": resp_dict.get("citations", []),
                "verified_response": resp_dict  # Include full enterprise payload
            }
            
        except Exception as e:
            logger.error(f"Uncaught workflow exception: {e}")
            return {
                "success": False,
                "code": "UNEXPECTED_ERROR",
                "message": "An unexpected error occurred during AI analysis."
            }
