import unittest
from unittest.mock import patch, MagicMock
from app.services.langgraph.state import WorkflowState
from app.services.langgraph.nodes import generate_ai_draft, TransientAIError
from app.schemas.risk_evidence import RiskEvidence, IdentityEvidence, RiskScoreEvidence, AttackPathEvidence

class TestGenerateAIDraft(unittest.TestCase):
    def setUp(self):
        self.evidence = RiskEvidence(
            identity=IdentityEvidence(arn="arn:aws:iam::123:user/test", type="IAMUser", total_events=10),
            risk=RiskScoreEvidence(score=8.0, severity="High", reasons=["Risk 1"]),
            attack_path=AttackPathEvidence(nodes_count=2, edges_count=1, traversal_summary="test", edges=[])
        )
        self.state = WorkflowState(
            request_id="req-123",
            identity_id="arn:aws:iam::123:user/test",
            workspace_id="ws-456",
            evidence=self.evidence
        )

    @patch('app.services.langgraph.nodes.AIAnalystService')
    @patch('app.services.langgraph.nodes.PromptManager')
    def test_successful_ai_generation(self, MockPromptManager, MockAnalyst):
        mock_analyst = MockAnalyst.return_value
        mock_analyst.call_llm.return_value = {
            "success": True,
            "executive_summary": "Test Summary",
            "risk_assessment": "Test Risk",
            "attack_path_analysis": "Test Path",
            "findings": [{"title": "F1", "description": "D1", "severity": "High"}],
            "recommendations": [{"action": "A1", "rationale": "R1", "effort": "Low"}]
        }
        
        mock_manager = MockPromptManager.return_value
        mock_manager.get_system_prompt.return_value = "System prompt"
        
        updated_state = generate_ai_draft(self.state)
        
        self.assertIn("generate_ai_draft", updated_state.node_history)
        self.assertIsNotNone(updated_state.ai_draft)
        self.assertEqual(updated_state.ai_draft.executive_summary, "Test Summary")
        self.assertEqual(updated_state.provider_name, "google")
        self.assertIsNotNone(updated_state.latency_ms)

    def test_missing_risk_evidence(self):
        self.state.evidence = None
        with self.assertRaisesRegex(ValueError, "RiskEvidence is missing"):
            generate_ai_draft(self.state)

    @patch('app.services.langgraph.nodes.AIAnalystService')
    def test_invalid_ai_json_response(self, MockAnalyst):
        # AI Analyst handles JSON parsing, but if it returns success=False for json error:
        mock_analyst = MockAnalyst.return_value
        mock_analyst.call_llm.return_value = {
            "success": False,
            "code": "AI_RESPONSE_INVALID",
            "message": "JSON error"
        }
        state = generate_ai_draft(self.state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Non-transient AI failure", state.error_message)

    @patch('app.services.langgraph.nodes.AIAnalystService')
    def test_schema_validation_failure(self, MockAnalyst):
        mock_analyst = MockAnalyst.return_value
        mock_analyst.call_llm.return_value = {
            "success": True,
            "executive_summary": "Test Summary"
            # Missing required fields to trigger schema error
        }
        state = generate_ai_draft(self.state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Schema validation failed", state.error_message)

    @patch('app.services.langgraph.nodes._invoke_ai_with_retry')
    def test_provider_timeout_exhaustion(self, mock_invoke):
        mock_invoke.side_effect = TransientAIError("Timeout")
        
        # Should raise TransientAIError after 3 attempts because reraise=True
        state = generate_ai_draft(self.state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Timeout", state.error_message)
        
        self.assertEqual(mock_invoke.call_count, 3)

    @patch('app.services.langgraph.nodes.AIAnalystService')
    def test_provider_exception(self, MockAnalyst):
        mock_analyst = MockAnalyst.return_value
        # Simulated unexpected exception inside call_llm
        mock_analyst.call_llm.side_effect = Exception("Fatal failure")
        state = generate_ai_draft(self.state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Fatal failure", state.error_message)

    @patch('app.services.langgraph.nodes._invoke_ai_with_retry')
    @patch('app.services.langgraph.nodes.PromptManager')
    def test_retry_success(self, MockPromptManager, mock_invoke):
        # Fail twice with transient error, succeed on third
        mock_invoke.side_effect = [
            TransientAIError("Timeout 1"),
            TransientAIError("Timeout 2"),
            {
                "success": True,
                "executive_summary": "Test Summary",
                "risk_assessment": "Test Risk",
                "attack_path_analysis": "Test Path",
                "findings": [],
                "recommendations": []
            }
        ]
        
        updated_state = generate_ai_draft(self.state)
        self.assertEqual(mock_invoke.call_count, 3)
        self.assertIsNotNone(updated_state.ai_draft)

if __name__ == '__main__':
    unittest.main()
