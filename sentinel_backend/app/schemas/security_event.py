from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional
from datetime import datetime

class SecurityEvent(BaseModel):
    """
    Universal SecurityEvent contract for Stage 1 Data Ingestion Engine.
    Represents normalized security events from disparate sources (AWS, Wazuh, OpenVAS, Suricata, etc.).
    """
    event_id: str = Field(..., description="Unique identifier for the event")
    source: str = Field(..., description="The system or component that generated the event (e.g., 'wazuh-agent', 'cloudtrail', 'suricata')")
    vendor: str = Field(..., description="The vendor of the security product (e.g., 'AWS', 'Wazuh', 'OpenVAS')")
    event_type: str = Field(..., description="Categorization of the event (e.g., 'Authentication', 'FileIntegrity', 'Vulnerability')")
    timestamp: datetime = Field(..., description="When the event occurred (ISO-8601 format preferred)")
    severity: str = Field(..., description="Normalized severity level (e.g., 'INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')")
    
    asset: Optional[str] = Field(None, description="The primary asset involved (e.g., IP address, hostname, AWS ARN)")
    identity: Optional[str] = Field(None, description="The user, IAM role, or machine identity involved")
    
    raw_payload: Dict[str, Any] = Field(default_factory=dict, description="The original raw event data for forensic auditing")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional enriched or normalized metadata")

    model_config = ConfigDict(extra="allow")
