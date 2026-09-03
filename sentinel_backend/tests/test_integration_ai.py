import pytest
import os
import json
from unittest.mock import patch, MagicMock

from app.services.ai.investigation_service import InvestigationService
from app.services.langgraph.state import WorkflowState
from app.schemas.verified_response import VerifiedResponse
from app.schemas.ai_response import AIResponse

# Mock classes for database
class MockDB:
    def close(self): pass
class MockGraph:
    def close(self): pass

@pytest.fixture
def mock_evidence_collector():
    # Patch at the point of use (inside nodes.py) — standard Python mock rule
    with patch('app.services.ai.evidence_collector.EvidenceCollector.collect_evidence') as mock:
        yield mock

@pytest.fixture
def mock_ai_analyst():
    # Patch AIAnalystService where nodes.py looks it up, and stub __init__ so
    # genai.Client() is never instantiated (avoids GEMINI_API_KEY errors).
    with patch('app.services.langgraph.nodes.AIAnalystService') as MockClass:
        instance = MockClass.return_value
        yield instance

def test_integration_happy_path(mock_evidence_collector, mock_ai_analyst):
    # Setup mocks
    mock_evidence_collector.return_value = {
        "identity": {"arn": "arn:aws:iam::123:user/test", "type": "IAMUser"},
        "risk": {"score": 85.0, "severity": "High", "reasons": []},
        "recent_activity": [{"event_name": "ConsoleLogin", "event_source": "aws", "time": "2023-01-01T00:00:00Z"}],
        "attack_path": {"nodes_count": 0, "edges_count": 0, "traversal_summary": "", "edges": []}
    }
    
    mock_ai_analyst.call_llm.return_value = {
        "success": True,
        "executive_summary": "User arn:aws:iam::123:user/test did a ConsoleLogin",
        "risk_assessment": "High risk",
        "attack_path_analysis": "None",
        "findings": [],
        "recommendations": []
    }
    
    service = InvestigationService(MockDB(), MockGraph())
    result = service.investigate("identity_123", "ws_123", "inv_123")
    
    assert result["success"] is True
    assert "User arn:aws:iam::123:user/test did a ConsoleLogin" in result["executive_summary"]
    assert "verified_response" in result
    assert result["verified_response"]["is_fully_verified"] is True
    assert result["verified_response"]["confidence_score"] > 0

def test_integration_missing_identity(mock_evidence_collector):
    # Setup mocks for error
    mock_evidence_collector.return_value = {"error": "Identity not found"}
    
    service = InvestigationService(MockDB(), MockGraph())
    result = service.investigate("identity_123", "ws_123", "inv_123")
    
    assert result["success"] is False
    assert result["code"] == "WORKFLOW_ERROR"
    assert "Identity not found" in result["message"]

def test_integration_ai_failure(mock_evidence_collector, mock_ai_analyst):
    mock_evidence_collector.return_value = {
        "identity": {"arn": "arn:aws:iam::123:user/test", "type": "IAMUser"},
        "risk": {"score": 85.0, "severity": "High", "reasons": []},
        "recent_activity": [],
        "attack_path": {"nodes_count": 0, "edges_count": 0, "traversal_summary": "", "edges": []}
    }
    
    # Non-transient failure — returned by call_llm on the mocked instance
    mock_ai_analyst.call_llm.return_value = {
        "success": False,
        "code": "BAD_REQUEST",
        "message": "Invalid input"
    }
    
    service = InvestigationService(MockDB(), MockGraph())
    result = service.investigate("identity_123", "ws_123", "inv_123")
    
    assert result["success"] is False
    assert result["code"] == "WORKFLOW_ERROR"
    assert "Non-transient AI failure" in result["message"]

