import pytest
import json
from app.schemas.ai_response import AIResponse, Finding, Recommendation
from app.schemas.risk_evidence import RiskEvidence, IdentityEvidence, RiskScoreEvidence, ActivityEvidence, AttackPathEvidence
from app.schemas.verified_response import VerifiedResponse, VerificationResult
from app.schemas.claims import Claim, ClaimEntity
from app.services.verification.claim_extractor import ClaimExtractor
from app.services.verification.verifier import Verifier
from app.services.verification.confidence_engine import ConfidenceEngine
from app.services.verification.citation_engine import CitationEngine
from app.services.langgraph.state import WorkflowState
from app.services.langgraph.nodes import extract_claims, verify_claims, calculate_confidence, attach_citations, build_verified_response

@pytest.fixture
def sample_ai_response():
    return AIResponse(
        executive_summary="The identity arn:aws:iam::123456789012:user/admin performed dangerous actions. Source IP 192.168.1.1 was used.",
        risk_assessment="High risk due to ConsoleLogin and AssumeRole.",
        attack_path_analysis="Attacker can traverse from Admin to S3.",
        findings=[
            Finding(title="Exposed Credentials", description="AssumeRole event detected without MFA.", severity="High")
        ],
        recommendations=[
            Recommendation(action="Rotate keys", rationale="Compromised", effort="Low")
        ]
    )

@pytest.fixture
def sample_risk_evidence():
    return RiskEvidence(
        identity=IdentityEvidence(arn="arn:aws:iam::123456789012:user/admin", type="IAMUser"),
        risk=RiskScoreEvidence(score=85.0, severity="High"),
        recent_activity=[
            ActivityEvidence(event_name="ConsoleLogin", event_source="signin.amazonaws.com", time="2023-01-01T00:00:00Z", source_ip="192.168.1.1"),
            ActivityEvidence(event_name="AssumeRole", event_source="sts.amazonaws.com", time="2023-01-01T01:00:00Z")
        ],
        attack_path=AttackPathEvidence(nodes_count=2, edges_count=1, traversal_summary="Path exists", edges=["Assumes"])
    )

def test_claim_extractor(sample_ai_response):
    extractor = ClaimExtractor()
    claims = extractor.extract(sample_ai_response)
    
    assert len(claims) > 0
    
    has_arn = False
    has_ip = False
    has_event = False
    
    for c in claims:
        if c.entities.arns:
            has_arn = True
        if c.entities.ips:
            has_ip = True
        if c.entities.events:
            has_event = True
            
    assert has_arn, "Should extract ARNs"
    assert has_ip, "Should extract IPs"
    assert has_event, "Should extract events"

def test_verifier_happy_path(sample_risk_evidence):
    claims = [
        Claim(
            claim_id="1",
            claim_text="The identity arn:aws:iam::123456789012:user/admin performed an action.",
            section="test",
            entities=ClaimEntity(arns=["arn:aws:iam::123456789012:user/admin"])
        ),
        Claim(
            claim_id="2",
            claim_text="From IP 192.168.1.1",
            section="test",
            entities=ClaimEntity(ips=["192.168.1.1"])
        )
    ]
    
    verifier = Verifier()
    results = verifier.verify(claims, sample_risk_evidence)
    
    assert len(results) == 2
    assert results[0].is_verified is True
    assert results[1].is_verified is True

def test_verifier_unsupported_claim(sample_risk_evidence):
    claims = [
        Claim(
            claim_id="1",
            claim_text="The identity arn:aws:iam::999999999999:user/hacker logged in.",
            section="test",
            entities=ClaimEntity(arns=["arn:aws:iam::999999999999:user/hacker"])
        )
    ]
    
    verifier = Verifier()
    results = verifier.verify(claims, sample_risk_evidence)
    
    assert len(results) == 1
    assert results[0].is_verified is False
    assert "Removed unsupported claim referencing arn:aws:iam::999999999999:user/hacker" in results[0].correction

def test_confidence_engine(sample_risk_evidence):
    engine = ConfidenceEngine()
    
    results = [
        VerificationResult(claim="valid", is_verified=True, evidence_reference="Match"),
        VerificationResult(claim="invalid", is_verified=False, correction="Removed")
    ]
    
    score = engine.calculate(results, sample_risk_evidence)
    assert 0.0 < score <= 1.0

def test_citation_engine(sample_risk_evidence):
    engine = CitationEngine()
    results = [
        VerificationResult(claim="User arn:aws:iam::123456789012:user/admin did a ConsoleLogin", is_verified=True)
    ]
    
    citations = engine.generate_citations(results, sample_risk_evidence)
    assert len(citations) == 1
    refs = citations[0].references
    
    assert len(refs) >= 2
    types = [r.type for r in refs]
    assert "Identity" in types
    assert "Event Timestamp" in types

def test_verification_nodes(sample_ai_response, sample_risk_evidence):
    state = WorkflowState(
        request_id="test_req",
        identity_id="test_id",
        workspace_id="test_ws",
        ai_draft=sample_ai_response,
        evidence=sample_risk_evidence
    )
    
    state = extract_claims(state)
    assert len(state.extracted_claims) > 0
    
    state = verify_claims(state)
    assert len(state.verification_results) > 0
    
    state = calculate_confidence(state)
    assert state.confidence_score > 0
    
    state = attach_citations(state)
    assert len(state.citations) > 0
    
    state = build_verified_response(state)
    assert state.final_response is not None
    assert state.final_response.is_fully_verified
    assert state.final_response.confidence_score == state.confidence_score
