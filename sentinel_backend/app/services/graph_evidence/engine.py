import logging
import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from neo4j import Session as GraphSession

from app.models.risk_finding import RiskFinding
from app.services.graph_evidence.collectors.collectors import (
    AttackPathCollector, IdentityCollector, ResourceCollector, 
    PolicyCollector, CloudTrailCollector, RelationshipCollector, GraphMetricsCollector
)
from app.services.graph_evidence.reasoning.graph_reasoning import GraphReasoner
from app.services.graph_evidence.risk_factors.registry import RiskFactorRegistry
from app.services.graph_evidence.confidence.confidence_engine import ConfidenceEngine
from app.core.config import settings

logger = logging.getLogger(__name__)

class GraphEvidenceEngine:
    def __init__(self, db: Session, graph: GraphSession):
        self.db = db
        self.graph = graph
        
        self.collectors = [
            AttackPathCollector(db, graph),
            IdentityCollector(db, graph),
            ResourceCollector(db, graph),
            PolicyCollector(db, graph),
            CloudTrailCollector(db, graph),
            RelationshipCollector(db, graph),
            GraphMetricsCollector(db, graph)
        ]
        
        self.reasoner = GraphReasoner(graph)
        self.risk_registry = RiskFactorRegistry()
        self.confidence_engine = ConfidenceEngine()
        
    def build_evidence(self, finding_id: str, workspace_id: str, identity_id: str) -> Dict[str, Any]:
        """
        Main orchestration method for the Graph Evidence Engine.
        Collects graph evidence, coordinates reasoning and risk factors,
        computes confidence, and formats the output.
        """
        logger.info(f"Building graph evidence for finding {finding_id}")
        
        # 1. Coordinate Collectors
        evidence = self._collect_evidence(finding_id, workspace_id, identity_id)
        
        # 2. Graph Reasoning
        metrics = self._perform_reasoning(evidence, identity_id, workspace_id)
        
        # 3. Risk Factor Registry
        risk_factors = self._evaluate_risk_factors(evidence, metrics)
        
        # 4. Confidence Engine
        confidence = self._compute_confidence(evidence, metrics, risk_factors)
        
        # Format payload
        payload = {
            "confidence": confidence,
            "graph_metrics": metrics,
            "risk_factors": risk_factors,
            "attack_path": evidence.get("attack_path"),
            "related_entities": evidence.get("related_entities", []),
            "related_assets": evidence.get("related_assets", []),
            "supporting_evidence": evidence.get("raw", {}),
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "evidence_status": "complete",
            "evidence_truncated": False
        }
        
        return payload

    def _collect_evidence(self, finding_id: str, workspace_id: str, identity_id: str) -> Dict[str, Any]:
        evidence = {"raw": {}}
        for collector in self.collectors:
            try:
                res = collector.collect(finding_id, workspace_id, identity_id)
                evidence.update(res)
            except Exception as e:
                logger.error("Collector {collector.__class__.__name__} failed: %s", e)
        return evidence
        
    def _perform_reasoning(self, evidence: Dict[str, Any], identity_id: str, workspace_id: str) -> Dict[str, Any]:
        return self.reasoner.analyze_identity_context(identity_id, workspace_id)
        
    def _evaluate_risk_factors(self, evidence: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.risk_registry.evaluate_all(evidence, metrics)
        
    def _compute_confidence(self, evidence: Dict[str, Any], metrics: Dict[str, Any], risk_factors: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.confidence_engine.compute_confidence(evidence, metrics, risk_factors)
