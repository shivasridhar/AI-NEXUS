import math
from typing import List
from app.schemas.risk_evidence import AttackPath

class VectorCalculator:
    def calculate_score(self, attack_paths: List[AttackPath]) -> int:
        if not attack_paths:
            return 0
            
        # Calculate raw score for each path
        path_scores = []
        for path in attack_paths:
            # Criticality is the primary driver (0-100 scale).
            # If not provided, fallback to a low base risk of 10.
            path_score = 10
            if path.criticality is not None:
                path_score = path.criticality
            path_scores.append(path_score)
            
        # Sort so highest risk paths contribute the most
        path_scores.sort(reverse=True)
        
        total_score = 10.0  # Base score if any paths exist
        
        # Apply rank-based decay (1/sqrt(rank)) so 20th path contributes much less than the 2nd
        for i, score in enumerate(path_scores):
            decay_factor = 1.0 / math.sqrt(i + 1)
            total_score += score * decay_factor
            
        return min(max(int(total_score), 0), 100)
        
    def calculate_severity(self, score: int) -> str:
        if score >= 80:
            return "Critical"
        elif score >= 60:
            return "High"
        elif score >= 40:
            return "Medium"
        return "Low"
