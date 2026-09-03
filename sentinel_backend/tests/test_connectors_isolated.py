import pytest
import json
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import io

# Mock botocore before importing anything that uses it
sys.modules['botocore'] = MagicMock()
sys.modules['botocore.exceptions'] = MagicMock()
sys.modules['boto3'] = MagicMock()

from app.schemas.security_event import SecurityEvent
from app.services.connectors.wazuh_connector import WazuhConnector, WazuhAuthError
from app.services.connectors.suricata_connector import SuricataConnector
from app.services.connectors.openvas_connector import OpenVASConnector, GMPConnectionError
from app.services.connectors.aws_securityhub_connector import AwsSecurityHubConnector
from app.services.connectors.aws_iam_connector import AwsIamConnector

# ----------------------------------------
# WAZUH CONNECTOR TESTS
# ----------------------------------------

@patch("app.services.connectors.wazuh_connector.requests.Session.get")
@patch("app.services.connectors.wazuh_connector.requests.Session.post")
def test_wazuh_fetch_success(mock_post, mock_get):
    connector = WazuhConnector("wazuh", "test", "http://test", "user", "pass")
    
    # Mock auth response
    mock_post.return_value.status_code = 200
    mock_post.return_value.text = '{"data": {"token": "fake_token"}}'
    
    # Mock events response
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.side_effect = [
        {
            "data": {
                "affected_items": [
                    {
                        "id": "1",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "rule": {"level": 5, "description": "Auth Failed", "id": "100"},
                        "agent": {"id": "001", "name": "webserver"}
                    }
                ]
            }
        },
        {"data": {"affected_items": []}} # Empty to terminate pagination
    ]
    
    events = connector.fetch_events()
    assert len(events) == 1
    assert events[0].vendor == "Wazuh" # Case matches BaseConnector assignment or WazuhConnector
    assert events[0].severity == "LOW"  # level 5 -> normalize to 33 -> LOW
    assert events[0].asset == "001"
    assert events[0].event_type == "Auth Failed"

@patch("app.services.connectors.wazuh_connector.requests.Session.post")
def test_wazuh_auth_failure(mock_post):
    connector = WazuhConnector("wazuh", "test", "http://test", "user", "pass")
    mock_post.return_value.status_code = 401
    mock_post.return_value.text = 'Unauthorized'
    
    with pytest.raises(WazuhAuthError):
        connector.fetch_events()

# ----------------------------------------
# SURICATA CONNECTOR TESTS
# ----------------------------------------

@patch("app.services.connectors.suricata_connector.LocalStorageProvider")
@patch("os.access")
@patch("app.services.connectors.suricata_connector.Path.exists")
@patch("app.services.connectors.suricata_connector.open")
def test_suricata_fetch_success(mock_open, mock_exists, mock_access, mock_storage):
    connector = SuricataConnector("/var/log/suricata/eve.json")
    connector.vendor = "suricata"
    connector.source = "test"
    mock_exists.return_value = True
    mock_access.return_value = True
    
    connector.source = "test"
    mock_exists.return_value = True
    mock_access.return_value = True
    
    # Mock JSON payload for alert
    alert_payload = {
        "timestamp": "2024-01-01T12:00:00.000000+0000",
        "event_type": "alert",
        "src_ip": "1.2.3.4",
        "dest_ip": "5.6.7.8",
        "alert": {
            "severity": 1,
            "signature": "ET EXPLOIT",
            "action": "allowed"
        }
    }
    
    file_content = json.dumps(alert_payload) + "\n"
    mock_open.return_value.__enter__.return_value = io.StringIO(file_content)
    
    connector.vendor = "suricata"
    connector.source = "test"
    
    with patch("os.stat") as mock_stat:
        import os
        # Mock stat result to pretend the file exists and has a size
        mock_stat_result = os.stat_result((33188, 12345, 0, 1, 0, 0, 1000, 0, 0, 0))
        mock_stat.return_value = mock_stat_result
        
        connector.connect()
        events = connector.fetch_events()
        
    assert len(events) == 1
    assert events[0].vendor == "suricata"
    assert events[0].severity == "CRITICAL" # severity 1 -> CRITICAL
    assert events[0].asset == "1.2.3.4 -> 5.6.7.8"
    assert events[0].metadata["action"] == "allowed"


# ----------------------------------------
# OPENVAS CONNECTOR TESTS
# ----------------------------------------

@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_auth_failure(mock_socket_class):
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    
    connector = OpenVASConnector("openvas", "test", "127.0.0.1", 9390, "u", "p")
    connector.connect()
    
    # Mock authenticate failure
    class MockStream:
        def __init__(self):
            self.read_called = False
            
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<authenticate_response status="401" status_text="Unauthorized"/>'
            return b''
            
        def write(self, *args, **kwargs):
            pass
            
    with patch("app.services.connectors.openvas_connector.SocketStreamWrapper") as MockWrapper:
        MockWrapper.return_value = MockStream()
        assert connector.authenticate() is False

# ----------------------------------------
# AWS SECURITY HUB CONNECTOR TESTS
# ----------------------------------------

@patch("app.services.connectors.aws_securityhub_connector.AwsSessionProvider.get_session")
def test_security_hub_fetch(mock_get_session):
    mock_boto_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_boto_client
    mock_get_session.return_value = mock_session
    
    mock_boto_client.get_findings.return_value = {
        "Findings": [
            {
                "Id": "test-finding-1",
                "Types": ["Software and Configuration Checks/Vulnerabilities/CVE"],
                "Severity": {"Label": "HIGH"},
                "UpdatedAt": "2024-01-01T12:00:00Z",
                "Resources": [{"Id": "arn:aws:ec2:region:account:instance/i-123456"}]
            }
        ]
    }
    
    connector = AwsSecurityHubConnector("sh", "test", "env")
    connector.connect()
    events = connector.fetch_events()
    
    assert len(events) == 1
    assert events[0].vendor == "AWS"
    assert events[0].severity == "HIGH"
    assert events[0].asset == "arn:aws:ec2:region:account:instance/i-123456"
    assert "CVE" in events[0].event_type

# ----------------------------------------
# AWS IAM CONNECTOR TESTS
# ----------------------------------------

@patch("app.services.connectors.aws_iam_connector.AwsSessionProvider.get_session")
def test_iam_fetch(mock_get_session):
    mock_boto_client = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = mock_boto_client
    mock_get_session.return_value = mock_session

    mock_paginator_users = MagicMock()
    mock_paginator_users.paginate.return_value = [{"Users": [{"UserName": "testuser", "Arn": "arn:aws:iam::123:user/testuser"}]}]
    
    mock_paginator_roles = MagicMock()
    mock_paginator_roles.paginate.return_value = [{"Roles": []}]

    def mock_get_paginator(operation):
        if operation == 'list_users': return mock_paginator_users
        if operation == 'list_roles': return mock_paginator_roles
        
    mock_boto_client.get_paginator.side_effect = mock_get_paginator
    mock_boto_client.list_attached_user_policies.return_value = {"AttachedPolicies": []}
    
    connector = AwsIamConnector("iam", "test", "env")
    connector.connect()
    events = connector.fetch_events()

    assert len(events) == 1
    assert events[0].vendor == "AWS"
    assert events[0].event_type == "IAMUserDiscovery"
    assert events[0].severity == "INFO"
    assert events[0].identity == "arn:aws:iam::123:user/testuser"
