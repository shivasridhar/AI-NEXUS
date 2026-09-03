from typing import Dict, Any
from app.schemas.risk_evidence import (
    RiskEvidence,
    IdentityEvidence,
    RiskScoreEvidence,
    ActivityEvidence,
    AttackPathEvidence
)

def adapt_to_risk_evidence(raw_evidence: Dict[str, Any]) -> RiskEvidence:
    """
    Adapts the raw dictionary evidence collected by EvidenceCollector
    into the typed Pydantic RiskEvidence schema.
    """
    if "error" in raw_evidence:
        raise ValueError(f"Cannot adapt error evidence: {raw_evidence['error']}")

    identity = IdentityEvidence(
        arn=raw_evidence["identity"]["arn"],
        type=raw_evidence["identity"]["type"],
        first_seen=raw_evidence["identity"].get("first_seen"),
        last_seen=raw_evidence["identity"].get("last_seen"),
        total_events=raw_evidence["identity"].get("total_events", 0)
    )

    risk = RiskScoreEvidence(
        score=raw_evidence["risk"]["score"],
        severity=raw_evidence["risk"]["severity"],
        reasons=raw_evidence["risk"]["reasons"]
    )

    recent_activity = [
        ActivityEvidence(
            event_name=act["event_name"],
            event_source=act["event_source"],
            time=act["time"],
            resource=act.get("resource"),
            source_ip=act.get("source_ip")
        )
        for act in raw_evidence.get("recent_activity", [])
    ]

    attack_path = AttackPathEvidence(
        nodes_count=raw_evidence["attack_path"]["nodes_count"],
        edges_count=raw_evidence["attack_path"]["edges_count"],
        traversal_summary=raw_evidence["attack_path"]["traversal_summary"],
        edges=raw_evidence["attack_path"]["edges"]
    )

    return RiskEvidence(
        identity=identity,
        risk=risk,
        recent_activity=recent_activity,
        attack_path=attack_path,
        relationship_counts=raw_evidence.get("relationship_counts", {}),
        sensitive_resource_access_summary=raw_evidence.get("sensitive_resource_access_summary", {})
    )
