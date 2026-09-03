import unittest
from unittest.mock import patch
from app.services.langgraph.state import WorkflowState
from app.services.langgraph.nodes import retrieve_evidence

class TestRetrieveEvidence(unittest.TestCase):
    @patch('app.services.langgraph.nodes.neo4j_manager')
    @patch('app.services.langgraph.nodes.SessionLocal')
    @patch('app.services.langgraph.nodes.EvidenceCollector')
    def test_retrieve_evidence_success(self, MockCollector, mock_db, mock_graph):
        state = WorkflowState(
            request_id="req-123",
            identity_id="arn:aws:iam::123:user/test",
            workspace_id="ws-456"
        )
        
        mock_instance = MockCollector.return_value
        mock_instance.collect_evidence.return_value = {
            "identity": {
                "arn": "arn:aws:iam::123:user/test",
                "type": "IAMUser",
                "total_events": 100
            },
            "risk": {
                "score": 8.5,
                "severity": "High",
                "reasons": ["Risk 1"]
            },
            "recent_activity": [],
            "attack_path": {
                "nodes_count": 5,
                "edges_count": 4,
                "traversal_summary": "Graph shows 4 relationships.",
                "edges": ["ACCESSED"]
            }
        }
        
        updated_state = retrieve_evidence(state)
        
        self.assertIn("retrieve_evidence", updated_state.node_history)
        self.assertIsNotNone(updated_state.evidence)
        self.assertEqual(updated_state.evidence.identity.arn, "arn:aws:iam::123:user/test")
        self.assertEqual(updated_state.evidence.risk.score, 8.5)

    @patch('app.services.langgraph.nodes.neo4j_manager')
    @patch('app.services.langgraph.nodes.SessionLocal')
    @patch('app.services.langgraph.nodes.EvidenceCollector')
    def test_retrieve_evidence_missing_identity(self, MockCollector, mock_db, mock_graph):
        state = WorkflowState(
            request_id="req-123",
            identity_id="unknown",
            workspace_id="ws-456"
        )
        
        mock_instance = MockCollector.return_value
        mock_instance.collect_evidence.return_value = {
            "error": "Identity 'unknown' not found."
        }
        
        state = retrieve_evidence(state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Identity 'unknown' not found", state.error_message)
            


    @patch('app.services.langgraph.nodes.neo4j_manager')
    @patch('app.services.langgraph.nodes.SessionLocal')
    @patch('app.services.langgraph.nodes.EvidenceCollector')
    def test_retrieve_evidence_exception_handling(self, MockCollector, mock_db, mock_graph):
        state = WorkflowState(
            request_id="req-123",
            identity_id="arn:aws:iam::123:user/test",
            workspace_id="ws-456"
        )
        
        mock_instance = MockCollector.return_value
        mock_instance.collect_evidence.side_effect = Exception("Database timeout")
        
        state = retrieve_evidence(state)
        self.assertIsNotNone(state.error_message)
        self.assertIn("Database timeout", state.error_message)
            


if __name__ == '__main__':
    unittest.main()
