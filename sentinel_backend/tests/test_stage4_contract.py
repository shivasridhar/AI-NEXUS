import pytest
from pydantic import ValidationError
from app.schemas.risk_evidence import RiskEvidence, IncidentDetail, AttackPath

def test_risk_evidence_valid():
    data = {
        "score": 85,
        "severity": "Critical",
        "incidents": [
            {
                "finding_type": "Privilege Escalation",
                "description": "Path to admin",
                "attack_paths": [
                    {"path_nodes": ["node_a", "node_b"], "criticality": 5}
                ]
            }
        ]
    }
    obj = RiskEvidence(**data)
    assert obj.score == 85
    assert obj.severity == "Critical"
    assert len(obj.incidents) == 1

def test_score_bounds():
    with pytest.raises(ValidationError):
        RiskEvidence(score=-1, severity="Low", incidents=[])
    
    with pytest.raises(ValidationError):
        RiskEvidence(score=101, severity="Critical", incidents=[])

def test_severity_mismatch():
    # Score 85 should be Critical, High should fail validation
    with pytest.raises(ValidationError) as exc:
        RiskEvidence(score=85, severity="High", incidents=[])
    assert "Expected 'Critical'" in str(exc.value)

    # Score 50 should be Medium
    with pytest.raises(ValidationError):
        RiskEvidence(score=50, severity="Low", incidents=[])

def test_invalid_severity_enum():
    with pytest.raises(ValidationError):
        RiskEvidence(score=90, severity="SuperCritical", incidents=[])
