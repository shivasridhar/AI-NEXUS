from typing import List, Dict, Any
from app.schemas.risk_evidence import RiskEvidence
from app.schemas.verified_response import VerificationResult
from app.schemas.claims import Citation, CitationReference

class CitationEngine:
    """
    Generates structured citations for verified statements based on RiskEvidence.
    """
    
    def generate_citations(self, results: List[VerificationResult], evidence: RiskEvidence) -> List[Citation]:
        citations = []
        citation_id = 1
        
        for result in results:
            if not result.is_verified:
                continue
                
            refs = []
            
            # Match Identity
            if evidence.identity and evidence.identity.arn and evidence.identity.arn in result.claim:
                refs.append(CitationReference(type="Identity", ref=evidence.identity.arn))
                
            # Match Recent Activity
            for act in evidence.recent_activity:
                if act.event_name in result.claim:
                    refs.append(CitationReference(type="Event Timestamp", ref=act.event_name, time=act.time))
                if act.source_ip and act.source_ip in result.claim:
                    refs.append(CitationReference(type="Source IP", ref=act.source_ip))
                if act.resource and act.resource in result.claim:
                    refs.append(CitationReference(type="Database Record", ref=act.resource))
                    
            # Match Attack Path
            if evidence.attack_path and evidence.attack_path.edges:
                for edge in evidence.attack_path.edges:
                    if edge in result.claim:
                        refs.append(CitationReference(type="Graph Path", ref=edge))
                        
            # Match Risk Score
            if evidence.risk and str(evidence.risk.score) in result.claim:
                refs.append(CitationReference(type="Risk Score", ref=str(evidence.risk.score)))
                
            if refs:
                # Deduplicate refs by string representation
                unique_refs = []
                seen = set()
                for r in refs:
                    key = f"{r.type}:{r.ref}:{r.time}"
                    if key not in seen:
                        seen.add(key)
                        unique_refs.append(r)
                        
                citations.append(Citation(
                    citation_id=f"cite_{citation_id}",
                    claim=result.claim,
                    references=unique_refs
                ))
                citation_id += 1
                
        return citations
