from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any

# --- HEAD (Stage 5 AI Layer) Schemas ---
class IdentityEvidence(BaseModel):
    arn: str = Field(..., description="The AWS ARN of the identity.")
    type: str = Field(..., description="The type of the machine identity (e.g. IAMUser, IAMRole).")
    first_seen: Optional[str] = Field(None, description="ISO timestamp of when the identity was first seen.")
    last_seen: Optional[str] = Field(None, description="ISO timestamp of when the identity was last seen.")
    total_events: int = Field(default=0, description="Total number of logged events for this identity.")

class RiskScoreEvidence(BaseModel):
    score: float = Field(..., description="The calculated risk score.")
    severity: str = Field(..., description="Risk severity level (e.g., Low, Medium, High, Critical).")
    reasons: List[str] = Field(default_factory=list, description="List of reasons contributing to the risk score.")

class ActivityEvidence(BaseModel):
    event_name: str = Field(..., description="The name of the CloudTrail event.")
    event_source: str = Field(..., description="The AWS service source of the event.")
    time: str = Field(..., description="ISO timestamp of the event.")
    resource: Optional[str] = Field(None, description="The ARN of the resource accessed.")
    source_ip: Optional[str] = Field(None, description="The source IP address of the request.")

class AttackPathEvidence(BaseModel):
    nodes_count: int = Field(default=0, description="Number of nodes in the attack path graph.")
    edges_count: int = Field(default=0, description="Number of edges in the attack path graph.")
    traversal_summary: str = Field(..., description="Summary string of the graph traversal.")
    edges: List[str] = Field(default_factory=list, description="Unique relationship types found in the path.")

# --- origin/main Schemas ---
class AttackPath(BaseModel):
    path_nodes: List[str] = Field(description="Sequence of node ARNs/IDs forming the attack path")
    criticality: Optional[int] = Field(default=None, description="Criticality of the target node, if known")

class IncidentDetail(BaseModel):
    finding_type: str = Field(description="The type of risk finding")
    description: str = Field(description="Description of the risk finding")
    attack_paths: Optional[List[AttackPath]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

class RiskEvidence(BaseModel):
    """
    Enterprise contract for evidence collected during an AI investigation.
    Combines relational telemetry, graph relationships, and pre-calculated risk metrics.
    """
    # HEAD fields
    identity: Optional[IdentityEvidence] = None
    risk: Optional[RiskScoreEvidence] = None
    recent_activity: List[ActivityEvidence] = Field(default_factory=list)
    attack_path: Optional[AttackPathEvidence] = None
    relationship_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Dictionary of relationship counts (e.g. accessed_resource_count, assumed_role_count)."
    )
    sensitive_resource_access_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of sensitive API actions grouped by service."
    )
    
    # origin/main fields
    score: Optional[int] = Field(default=None, ge=0, le=100, description="Overall risk score from 0 to 100")
    severity: Optional[Literal["Critical", "High", "Medium", "Low"]] = Field(default=None, description="Risk severity level")
    incidents: List[IncidentDetail] = Field(default_factory=list, description="Nested incident/path detail")

    # Stage 3/4 — MITRE ATT&CK mapping
    mitre_techniques: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of MITRE ATT&CK techniques mapped to this identity's activity"
    )

    # Stage 4 — Blast Radius
    blast_radius: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Blast radius analysis: reachable nodes, affected resources, blast score"
    )

    # Stage 4 — Compliance Mapping
    compliance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Compliance posture: per-framework scores and violated controls"
    )
    
    @field_validator('severity')
    @classmethod
    def validate_severity_bounds(cls, v: Optional[str], info) -> Optional[str]:
        if v is None:
            return v
        score = info.data.get('score')
        if score is None:
            return v
        
        expected_severity = "Low"
        if score >= 80:
            expected_severity = "Critical"
        elif score >= 60:
            expected_severity = "High"
        elif score >= 40:
            expected_severity = "Medium"
            
        if v != expected_severity:
            raise ValueError(f"Severity '{v}' does not match score {score}. Expected '{expected_severity}'")
        return v
