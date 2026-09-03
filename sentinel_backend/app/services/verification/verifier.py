from typing import List, Dict, Any
from app.schemas.risk_evidence import RiskEvidence
from app.schemas.verified_response import VerificationResult
from app.schemas.claims import Claim
from app.services.verification.entity_normalizer import EntityNormalizer

class Verifier:
    """
    Verifies claims deterministically against RiskEvidence using normalized entities.
    """
    
    def verify(self, claims: List[Claim], evidence: RiskEvidence) -> List[VerificationResult]:
        results = []
        
        # Build normalized evidence lookup index
        evidence_index = {
            "arns": set(),
            "ips": set(),
            "events": set(),
        }
        
        if evidence.identity and evidence.identity.arn:
            evidence_index["arns"].add(EntityNormalizer.normalize_arn(evidence.identity.arn))
            
        for act in evidence.recent_activity:
            evidence_index["events"].add(EntityNormalizer.normalize_event(act.event_name))
            if act.source_ip:
                evidence_index["ips"].add(EntityNormalizer.normalize_ip(act.source_ip))
            if act.resource:
                evidence_index["arns"].add(EntityNormalizer.normalize_arn(act.resource))
                
        if evidence.attack_path:
            for edge in evidence.attack_path.edges:
                evidence_index["events"].add(EntityNormalizer.normalize_event(edge))
                
        for claim in claims:
            entities = claim.entities
            claim_text = claim.claim_text
            
            has_entities = bool(entities.arns or entities.ips or entities.events)
            
            if has_entities:
                matched = True
                failed_entity = None
                
                for arn in entities.arns:
                    if arn not in evidence_index["arns"]:
                        matched = False
                        failed_entity = arn
                        break
                        
                if matched:
                    for ip in entities.ips:
                        if ip not in evidence_index["ips"]:
                            matched = False
                            failed_entity = ip
                            break
                            
                if matched:
                    for event in entities.events:
                        event_matched = any(event in e or e in event for e in evidence_index["events"])
                        if not event_matched:
                            matched = False
                            failed_entity = event
                            break
                            
                is_verified = matched
                
                if matched:
                    evidence_ref = "Matches Evidence Entities"
                    correction = None
                else:
                    evidence_ref = None
                    correction = f"Removed unsupported claim referencing {failed_entity}"
            else:
                is_verified = True
                evidence_ref = None
                correction = None
                
            results.append(VerificationResult(
                claim=claim_text,
                is_verified=is_verified,
                evidence_reference=evidence_ref,
                correction=correction
            ))
            
        return results
