from typing import List
from app.schemas.risk_evidence import RiskEvidence
from app.schemas.verified_response import VerificationResult

class ConfidenceEngine:
    """
    Calculates a multi-dimensional confidence score for the verification pipeline.
    
    Algorithm Weights (Max 100 points):
    - Verification Coverage (40%): The percentage of extracted claims that are fully verified against evidence.
    - Evidence Completeness (25%): The presence of key evidence dimensions (Identity, Activity, Attack Path).
    - Citation Completeness (20%): Penalty for verified claims that lack specific reference links.
    - Graph Consistency (15%): Consistency between the pre-calculated risk score and graph traversal depth.
    """
    
    def calculate(self, results: List[VerificationResult], evidence: RiskEvidence) -> float:
        if not results:
            return 0.0
            
        score = 0.0
        
        # 1. Verification Coverage (Max 40 points)
        verified_count = sum(1 for r in results if r.is_verified)
        success_ratio = verified_count / len(results)
        score += success_ratio * 40.0
        
        # 2. Evidence Completeness (Max 25 points)
        if evidence.identity and evidence.identity.arn:
            score += 10.0
        if evidence.recent_activity:
            score += 10.0
        if evidence.attack_path and evidence.attack_path.nodes_count > 0:
            score += 5.0
            
        # 3. Citation Completeness (Max 20 points)
        # Base 20 points, subtract 5 for every verified claim missing a reference.
        missing_refs = sum(1 for r in results if r.is_verified and not r.evidence_reference)
        penalty = min(20.0, missing_refs * 5.0)
        score += (20.0 - penalty)
        
        # 4. Graph Consistency (Max 15 points)
        # Full points by default, subtract if high risk but no graph path.
        graph_consistency_score = 15.0
        if evidence.risk and evidence.risk.score > 70 and (not evidence.attack_path or evidence.attack_path.nodes_count == 0):
            graph_consistency_score -= 10.0
        score += graph_consistency_score
            
        # Normalize to 0.0 - 1.0 range
        final_score = max(0.0, min(100.0, score))
        return final_score / 100.0
