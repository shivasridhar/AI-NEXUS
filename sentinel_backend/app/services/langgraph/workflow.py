from langgraph.graph import StateGraph, END
from app.services.langgraph.state import WorkflowState
from app.services.langgraph.nodes import (
    validate_input,
    retrieve_evidence,
    generate_ai_draft,
    extract_claims,
    verify_claims,
    calculate_confidence,
    attach_citations,
    build_verified_response
)

def check_errors(state: WorkflowState) -> str:
    """
    Conditional router that checks if an error occurred in the previous node.
    Returns the next node if successful, or END if an error is present.
    """
    if state.error_message:
        return END
    return "next"

def create_workflow() -> StateGraph:
    """
    Defines the structural execution graph for the Member 3 AI intelligence layer.
    """
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("validate_input", validate_input)
    workflow.add_node("retrieve_evidence", retrieve_evidence)
    workflow.add_node("generate_ai_draft", generate_ai_draft)
    workflow.add_node("extract_claims", extract_claims)
    workflow.add_node("verify_claims", verify_claims)
    workflow.add_node("calculate_confidence", calculate_confidence)
    workflow.add_node("attach_citations", attach_citations)
    workflow.add_node("build_verified_response", build_verified_response)
    
    # Define execution edges with conditional routing
    workflow.set_entry_point("validate_input")
    
    workflow.add_conditional_edges("validate_input", check_errors, {"next": "retrieve_evidence", END: END})
    workflow.add_conditional_edges("retrieve_evidence", check_errors, {"next": "generate_ai_draft", END: END})
    workflow.add_conditional_edges("generate_ai_draft", check_errors, {"next": "extract_claims", END: END})
    workflow.add_conditional_edges("extract_claims", check_errors, {"next": "verify_claims", END: END})
    workflow.add_conditional_edges("verify_claims", check_errors, {"next": "calculate_confidence", END: END})
    workflow.add_conditional_edges("calculate_confidence", check_errors, {"next": "attach_citations", END: END})
    workflow.add_conditional_edges("attach_citations", check_errors, {"next": "build_verified_response", END: END})
    
    workflow.add_edge("build_verified_response", END)
    
    return workflow.compile()
