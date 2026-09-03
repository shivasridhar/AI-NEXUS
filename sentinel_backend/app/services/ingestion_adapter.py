from dataclasses import dataclass
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class UnifiedEvent:
    event_id: str
    workspace_id: str
    timestamp: str
    source_tool: str
    severity: int
    mitre_technique: str
    actor_id: str
    actor_type: str  # 'Identity', 'Host', 'IPAddress'
    asset_id: Optional[str]
    asset_type: Optional[str]  # 'Resource', 'Host', 'IPAddress'
    original_record: Any  # Keep reference for further processing if needed

# Minimal MITRE static tagging map
MITRE_MAP = {
    "AssumeRole": "T1078.004",  # Cloud Accounts
    "ConsoleLogin": "T1078",     # Valid Accounts
    "CreateUser": "T1136.003",   # Create Account: Cloud
    "wazuh:syscheck": "T1492",   # Stored Data Manipulation
    "wazuh:authentication_failed": "T1110", # Brute Force
    "suricata:alert": "T1190"    # Exploit Public-Facing Application
}

def get_mitre_technique(source_tool: str, event_type: str) -> str:
    key = f"{source_tool}:{event_type}"
    if key in MITRE_MAP:
        return MITRE_MAP[key]
    if event_type in MITRE_MAP:
        return MITRE_MAP[event_type]
    return "Unknown"

class IngestionAdapter:
    
    @staticmethod
    def from_access_log(log) -> Optional[UnifiedEvent]:
        if not log.identity_arn or log.identity_arn == "unknown":
            return None
            
        mitre_tech = get_mitre_technique("aws", log.event_name)
        
        asset_id = None
        asset_type = None
        if log.resource_arn:
            asset_id = log.resource_arn
            asset_type = "Resource"
        elif log.source_ip:
            asset_id = log.source_ip
            asset_type = "IPAddress"
            
        return UnifiedEvent(
            event_id=str(log.id),
            workspace_id=str(log.workspace_id),
            timestamp=log.event_time.isoformat(),
            source_tool="aws_cloudtrail",
            severity=50,
            mitre_technique=mitre_tech,
            actor_id=log.identity_arn,
            actor_type="Identity",
            asset_id=asset_id,
            asset_type=asset_type,
            original_record=log
        )
        
    @staticmethod
    def from_canonical_event(event) -> Optional[UnifiedEvent]:
        if not event.actor_identifier:
            return None
            
        mitre_tech = get_mitre_technique(event.source_tool, event.event_type)
        
        actor_type = "Host"
        if event.source_tool == "suricata":
            actor_type = "IPAddress"
            
        asset_type = None
        if event.asset_identifier:
            asset_type = "Host" # Default assumption for Wazuh/Suricata targets for now
            if event.source_tool == "suricata" and "." in event.asset_identifier:
                asset_type = "IPAddress"
                
        return UnifiedEvent(
            event_id=str(event.id),
            workspace_id=str(event.workspace_id),
            timestamp=event.timestamp_utc.isoformat(),
            source_tool=event.source_tool,
            severity=event.severity_normalized or 50,
            mitre_technique=mitre_tech,
            actor_id=event.actor_identifier,
            actor_type=actor_type,
            asset_id=event.asset_identifier,
            asset_type=asset_type,
            original_record=event
        )
