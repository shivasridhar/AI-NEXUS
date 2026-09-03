import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from neo4j import Session as GraphSession

from app.services.graph_evidence.engine import GraphEvidenceEngine
from app.services.ai.ai_analyst_service import AIAnalystService
from app.services.graph_evidence.prompting.explainability_prompt import ExplainabilityPromptBuilder
from app.services.graph_evidence.validators.hallucination_validator import HallucinationValidator

logger = logging.getLogger(__name__)

class ExplainabilityService:
    def __init__(self, db: Session, graph: GraphSession):
        self.engine = GraphEvidenceEngine(db, graph)
        self.ai_service = AIAnalystService()
        self.prompt_builder = ExplainabilityPromptBuilder()
        self.validator = HallucinationValidator()

    def generate_finding_details(self, finding_id: str, workspace_id: str, identity_id: str) -> Dict[str, Any]:
        """
        Orchestrates evidence gathering and LLM explainability generation.
        """
        logger.info(f"Generating full explainability payload for finding {finding_id}")
        
        # 1. Gather verified graph evidence
        payload = self.engine.build_evidence(finding_id, workspace_id, identity_id)
        
        # 2. Extract components to build the prompt
        evidence = {
            "attack_path": payload.get("attack_path") or {},
            "related_entities": payload.get("related_entities", []),
            "related_assets": payload.get("related_assets", [])
        }
        metrics = payload.get("graph_metrics", {})
        risk_factors = payload.get("risk_factors", [])
        
        # 3. Build prompt
        prompt = self.prompt_builder.build_prompt(evidence, metrics, risk_factors)
        
        # 4. Generate Explainability via AI Analyst Service
        try:
            from app.services.ai.ai_analyst_service import GeminiRateLimitError
            raw_explanation = self.ai_service.generate_finding_explanation(prompt)
            
            # 5. Handle success/failure
            if raw_explanation:
                validated_explanation = self.validator.validate(raw_explanation, evidence)
                payload["explainability"] = validated_explanation
                payload["ai_status"] = "success"
            else:
                logger.warning(f"AI Explainability failed for finding {finding_id}. Using fallback.")
                payload["explainability"] = self._generate_fallback(risk_factors, metrics, evidence)
                payload["ai_status"] = "unavailable"
        except GeminiRateLimitError as re:
            logger.warning("AI Explainability rate limited (429) for finding {finding_id}: %s", re)
            payload["explainability"] = (
                "⚠️ Gemini API rate limit exceeded (429). "
                "Displaying dynamic rule-based graph analysis context below:\n\n"
                + self._generate_fallback(risk_factors, metrics, evidence)
            )
            payload["ai_status"] = "rate_limited"
            
        return payload

    def _generate_fallback(self, risk_factors: list, metrics: dict, evidence: dict) -> str:
        """
        Generates a dynamic rule-based explanation based on the graph evidence if AI is unavailable.
        """
        explanation = "Based on our Graph Evidence Analysis, this finding represents a localized risk without direct critical asset exposure.\n\n"
        if risk_factors:
            explanation += "**Identified Risk Factors:**\n"
            for rf in risk_factors:
                explanation += f"- {rf.get('factor', 'Risk condition')}: {rf.get('description', '')}\n"
        
        explanation += "\n**Graph Context Metrics:**\n"
        if metrics:
            explanation += f"- Reachable Critical Assets: {metrics.get('reachable_critical_assets', 0)}\n"
            explanation += f"- Connected Graph Entities: {metrics.get('connected_components', 0)}\n"
            explanation += f"- Shortest Path Hops: {metrics.get('shortest_path_hops', 'N/A')}\n"
            explanation += f"- Cycle Detected: {'Yes' if metrics.get('cycle_detected') else 'No'}\n"
            
        explanation += "\n**Recommendation:** Monitor identity behavior for anomalous privilege escalation."
        
        return explanation.strip()
