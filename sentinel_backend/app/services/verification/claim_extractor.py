import re
from typing import List, Dict, Any
from app.schemas.ai_response import AIResponse
from app.schemas.claims import Claim, ClaimEntity
from app.services.verification.entity_normalizer import EntityNormalizer

class ClaimExtractor:
    """
    Extracts structured claims from an AIResponse deterministically.
    """
    
    def extract(self, ai_response: AIResponse) -> List[Claim]:
        claims = []
        claim_id_counter = 1
        
        def process_text(text: str, section: str):
            nonlocal claim_id_counter
            if not text:
                return
            
            # Split by periods, newlines, or bullets
            sentences = re.split(r'(?<=[.!?])\s+|\n+|- ', text)
            for sentence in sentences:
                s = sentence.strip()
                if not s or len(s) < 10:
                    continue
                    
                claims.append(Claim(
                    claim_id=f"claim_{claim_id_counter}",
                    claim_text=s,
                    section=section,
                    entities=self._extract_entities(s)
                ))
                claim_id_counter += 1
                
        process_text(ai_response.executive_summary, "executive_summary")
        process_text(ai_response.risk_assessment, "risk_assessment")
        process_text(ai_response.attack_path_analysis, "attack_path_analysis")
        
        for idx, finding in enumerate(ai_response.findings):
            process_text(finding.description, f"finding_{idx+1}")
            
        return claims
        
    def _extract_entities(self, text: str) -> ClaimEntity:
        """
        Extracts known entity patterns from text for deterministic verification.
        """
        entities = ClaimEntity()
        
        # Extract ARNs
        arn_pattern = r'arn:aws:[a-z0-9-]*:[a-z0-9-]*:\d{12}:[a-zA-Z0-9-/_]+'
        raw_arns = re.findall(arn_pattern, text)
        entities.arns = [EntityNormalizer.normalize_arn(a) for a in raw_arns]
        
        # Extract IPs
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        raw_ips = re.findall(ip_pattern, text)
        entities.ips = [EntityNormalizer.normalize_ip(ip) for ip in raw_ips]
        
        # Extract explicit CloudTrail/AWS events (heuristic)
        event_pattern = r'\b[A-Z][a-zA-Z0-9]+(?:API|Action|Event)\b|\b(?:AssumeRole|CreateUser|AttachRolePolicy|PutObject|GetObject|ConsoleLogin)\b'
        raw_events = [e for e in re.findall(event_pattern, text) if len(e) > 5]
        entities.events = [EntityNormalizer.normalize_event(e) for e in raw_events]
        
        # Remove duplicates
        entities.arns = list(set(entities.arns))
        entities.ips = list(set(entities.ips))
        entities.events = list(set(entities.events))
        
        return entities
