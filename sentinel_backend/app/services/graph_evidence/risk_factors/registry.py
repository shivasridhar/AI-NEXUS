from abc import ABC, abstractmethod
from typing import Dict, Any, List

class RiskFactorEvaluator(ABC):
    @abstractmethod
    def evaluate(self, evidence: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a specific risk factor. Returns None if not applicable,
        or a dict with details if the risk factor is present.
        """

class HighPrivilegeEvaluator(RiskFactorEvaluator):
    def evaluate(self, evidence: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        identity = evidence.get("identity", {})
        if identity.get("is_admin") or identity.get("risk_score", 0) > 80:
            return {"factor": "High Privilege", "severity": "HIGH", "description": "Identity has high privileges."}
        return None

class CriticalAssetEvaluator(RiskFactorEvaluator):
    def evaluate(self, evidence: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        if metrics.get("reachable_critical_assets", 0) > 0:
            return {"factor": "Critical Asset Access", "severity": "CRITICAL", "description": "Can reach critical assets."}
        return None

class RiskFactorRegistry:
    def __init__(self):
        self.evaluators: List[RiskFactorEvaluator] = [
            HighPrivilegeEvaluator(),
            CriticalAssetEvaluator()
        ]
        
    def evaluate_all(self, evidence: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        factors = []
        for evaluator in self.evaluators:
            res = evaluator.evaluate(evidence, metrics)
            if res:
                factors.append(res)
        return factors
