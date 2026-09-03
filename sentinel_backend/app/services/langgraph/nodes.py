import json
import logging
import time
from app.services.langgraph.state import WorkflowState
from app.services.ai.evidence_collector import EvidenceCollector
from app.db.session import SessionLocal
from app.graph.session import neo4j_manager
from app.services.langgraph.adapters import adapt_to_risk_evidence
from app.services.prompts.prompt_manager import PromptManager
from app.services.ai.prompt_builder import PromptBuilder
from app.services.ai.ai_analyst_service import AIAnalystService
from app.schemas.ai_response import AIResponse
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class TransientAIError(Exception):
    pass


def validate_input(state: WorkflowState) -> WorkflowState:
    """
    Validates the initial request parameters (identity_id, workspace_id).
    Raises errors early if the request is malformed.
    """
    state.node_history.append("validate_input")
    if not state.identity_id or not state.workspace_id:
        raise ValueError("Missing required fields: identity_id and workspace_id")
    return state

def retrieve_evidence(state: WorkflowState) -> WorkflowState:
    """
    Retrieves relational, graph, and vector evidence via RAG nodes.
    Populates the state.evidence field.
    """
    state.node_history.append("retrieve_evidence")
    
    start_time = time.time()
    db = SessionLocal()
    graph = neo4j_manager.get_session()
    
    try:
        collector = EvidenceCollector(db, graph)
        raw_evidence = collector.collect_evidence(state.identity_id, state.workspace_id)
        
        if "error" in raw_evidence:
            raise ValueError(f"Evidence collection failed: {raw_evidence['error']}")
            
        risk_evidence = adapt_to_risk_evidence(raw_evidence)
        state.evidence = risk_evidence
        
        duration = time.time() - start_time
        num_items = len(risk_evidence.recent_activity)
        
        logger.info(json.dumps({
            "event": "EVIDENCE_RETRIEVAL_SUCCESS",
            "request_id": state.request_id,
            "identity_id": state.identity_id,
            "workspace_id": state.workspace_id,
            "duration_ms": round(duration * 1000, 2),
            "evidence_items": num_items
        }))
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "EVIDENCE_RETRIEVAL_FAILED",
            "request_id": state.request_id,
            "identity_id": state.identity_id,
            "workspace_id": state.workspace_id,
            "error": str(e)
        }))
        state.error_message = str(e)
    finally:
        db.close()
        graph.close()
        
    return state

def _invoke_ai_with_retry(prompt: str, request_id: str, identity_id: str, workspace_id: str) -> dict:
    analyst = AIAnalystService()
    
    # Actually call the underlying service
    result = analyst.call_llm(
        prompt=prompt,
        workspace_id=workspace_id,
        identity_id=identity_id,
        investigation_id=request_id
    )
    
    if not result.get("success"):
        code = result.get("code")
        msg = result.get("message")
        
        # Retry only for transient failures
        if code in ["AI_TIMEOUT", "AI_RATE_LIMITED", "AI_SERVICE_UNAVAILABLE", "UNKNOWN_ERROR"]:
            raise TransientAIError(f"Transient provider failure ({code}): {msg}")
        else:
            # Programmer errors, invalid inputs, auth failed, json parsing (which shouldn't be retried per requirements)
            raise ValueError(f"Non-transient AI failure ({code}): {msg}")
            
    return result

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(TransientAIError),
    reraise=True
)
def _generate_draft_retryable(prompt: str, request_id: str, identity_id: str, workspace_id: str) -> dict:
    return _invoke_ai_with_retry(prompt, request_id, identity_id, workspace_id)

def generate_ai_draft(state: WorkflowState) -> WorkflowState:
    """
    Calls the LLM with the provided evidence to generate an initial draft response.
    Populates the state.ai_draft field.
    """
    state.node_history.append("generate_ai_draft")
    
    if not state.evidence:
        raise ValueError("Cannot generate AI draft: RiskEvidence is missing from state.")
        
    start_time = time.time()
    state.generation_started_at = start_time
    
    try:
        # Load templates (Not injecting them to PromptBuilder since it doesn't accept templates, 
        # but we use PromptManager as instructed and reuse prompt_builder for the base structure)
        manager = PromptManager()
        sys_prompt = manager.get_system_prompt("v1")
        
        # Convert evidence back to dict for the legacy builder
        evidence_dict = state.evidence.model_dump()
        base_prompt = PromptBuilder.build_investigation_prompt(evidence_dict)
        
        # Combine them
        full_prompt = sys_prompt + "\n\n" + base_prompt
        
        # Call AI with tenacity retry
        raw_response = _generate_draft_retryable(
            prompt=full_prompt, 
            request_id=state.request_id,
            identity_id=state.identity_id,
            workspace_id=state.workspace_id
        )
        
        # Validate schema
        try:
            ai_draft = AIResponse(**raw_response)
        except ValidationError as e:
            raise ValueError(f"Schema validation failed: {e}")
            
        state.ai_draft = ai_draft
        state.generation_completed_at = time.time()
        duration_ms = (state.generation_completed_at - start_time) * 1000
        state.latency_ms = duration_ms
        
        state.provider_name = "google"
        state.model_name = "gemini-3.5-flash"
        state.prompt_version = "v1"
        
        logger.info(json.dumps({
            "event": "AI_GENERATION_SUCCESS",
            "request_id": state.request_id,
            "identity_id": state.identity_id,
            "workspace_id": state.workspace_id,
            "execution_time_ms": round(duration_ms, 2),
            "provider_name": state.provider_name,
            "model_name": state.model_name,
            "prompt_version": state.prompt_version,
            "success": True
        }))
        
        return state
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(json.dumps({
            "event": "AI_GENERATION_FAILED",
            "request_id": state.request_id,
            "identity_id": state.identity_id,
            "workspace_id": state.workspace_id,
            "execution_time_ms": round(duration_ms, 2),
            "provider_name": "google",
            "model_name": "gemini-3.5-flash",
            "prompt_version": "v1",
            "success": False,
            "error": str(e)
        }))
        state.error_message = str(e)
        return state

def extract_claims(state: WorkflowState) -> WorkflowState:
    """
    Parses the ai_draft to extract factual claims requiring verification.
    Populates state.extracted_claims.
    """
    state.node_history.append("extract_claims")
    from app.services.verification.claim_extractor import ClaimExtractor
    
    start_time = time.time()
    
    try:
        if not state.ai_draft:
            raise ValueError("Cannot extract claims: AI draft is missing from state.")
            
        extractor = ClaimExtractor()
        claims = extractor.extract(state.ai_draft)
        
        state.extracted_claims = claims
        
        logger.info(json.dumps({
            "event": "CLAIMS_EXTRACTION_SUCCESS",
            "request_id": state.request_id,
            "claims_count": len(claims),
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        }))
    except Exception as e:
        logger.error(f"Claim extraction failed: {e}")
        state.error_message = f"Claim extraction failed: {str(e)}"
        
    return state

def verify_claims(state: WorkflowState) -> WorkflowState:
    """
    Cross-references extracted claims against the RiskEvidence to prevent hallucinations.
    Populates state.verification_results.
    """
    state.node_history.append("verify_claims")
    from app.services.verification.verifier import Verifier
    
    start_time = time.time()
    
    try:
        if not state.evidence:
            raise ValueError("Cannot verify claims: RiskEvidence is missing from state.")
            
        verifier = Verifier()
        results = verifier.verify(state.extracted_claims, state.evidence)
        
        state.verification_results = results
        
        verified_count = sum(1 for r in results if r.is_verified)
        
        logger.info(json.dumps({
            "event": "CLAIMS_VERIFICATION_SUCCESS",
            "request_id": state.request_id,
            "verified_count": verified_count,
            "unverified_count": len(results) - verified_count,
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        }))
    except Exception as e:
        logger.error(f"Claim verification failed: {e}")
        state.error_message = f"Claim verification failed: {str(e)}"
        
    return state

def calculate_confidence(state: WorkflowState) -> WorkflowState:
    """
    Computes an overall confidence score based on the verification results.
    Populates state.confidence_score.
    """
    state.node_history.append("calculate_confidence")
    from app.services.verification.confidence_engine import ConfidenceEngine
    
    try:
        if not state.evidence:
            raise ValueError("Cannot calculate confidence: RiskEvidence is missing from state.")
            
        engine = ConfidenceEngine()
        score = engine.calculate(state.verification_results, state.evidence)
        
        state.confidence_score = score
        
        logger.info(json.dumps({
            "event": "CONFIDENCE_CALCULATION_SUCCESS",
            "request_id": state.request_id,
            "confidence_score": score
        }))
    except Exception as e:
        logger.error(f"Confidence calculation failed: {e}")
        state.error_message = f"Confidence calculation failed: {str(e)}"
        
    return state

def attach_citations(state: WorkflowState) -> WorkflowState:
    """
    Generates human-readable citations mapping claims back to specific graph nodes/edges.
    Populates state.citations.
    """
    state.node_history.append("attach_citations")
    from app.services.verification.citation_engine import CitationEngine
    
    start_time = time.time()
    
    try:
        if not state.evidence:
            raise ValueError("Cannot attach citations: RiskEvidence is missing from state.")
            
        engine = CitationEngine()
        citations = engine.generate_citations(state.verification_results, state.evidence)
        
        state.citations = citations
        
        logger.info(json.dumps({
            "event": "CITATION_ATTACHMENT_SUCCESS",
            "request_id": state.request_id,
            "citation_count": len(citations),
            "duration_ms": round((time.time() - start_time) * 1000, 2)
        }))
    except Exception as e:
        logger.error(f"Citation attachment failed: {e}")
        state.error_message = f"Citation attachment failed: {str(e)}"
        
    return state

def build_verified_response(state: WorkflowState) -> WorkflowState:
    """
    Compiles the final, corrected response into the VerifiedResponse schema.
    Populates state.final_response.
    """
    state.node_history.append("build_verified_response")
    from app.schemas.verified_response import VerifiedResponse
    
    try:
        if not state.ai_draft:
            raise ValueError("Cannot build final response: AI draft is missing from state.")
            
        original = state.ai_draft.model_dump()
        final = original.copy()
        
        # Ensure findings is a list
        if "findings" not in final or not final["findings"]:
            final["findings"] = []
            
        # Clean up unsupported claims from the final response text
        for result in state.verification_results:
            if not result.is_verified and result.correction:
                # Replace unsupported text with the correction (or remove it)
                final["executive_summary"] = final["executive_summary"].replace(result.claim, "")
                final["risk_assessment"] = final["risk_assessment"].replace(result.claim, "")
                final["attack_path_analysis"] = final["attack_path_analysis"].replace(result.claim, "")
                for f in final["findings"]:
                    f["description"] = f["description"].replace(result.claim, "")
                    
        final_response = AIResponse(**final)
        
        is_fully_verified = all(r.is_verified for r in state.verification_results) if state.verification_results else True
        
        state.final_response = VerifiedResponse(
            original_response=state.ai_draft,
            verifications=state.verification_results,
            is_fully_verified=is_fully_verified,
            confidence_score=state.confidence_score,
            citations=state.citations,
            final_response=final_response
        )
        
        logger.info(json.dumps({
            "event": "VERIFIED_RESPONSE_BUILT",
            "request_id": state.request_id,
            "is_fully_verified": is_fully_verified
        }))
    except Exception as e:
        logger.error(f"Build verified response failed: {e}")
        state.error_message = f"Build verified response failed: {str(e)}"
        
    return state
