import pytest
import time
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout, ConnectionError
from botocore.exceptions import ClientError
from app.services.connectors.wazuh_connector import WazuhConnector, WazuhAuthError, WazuhAPIError
from app.services.connectors.aws_iam_connector import AwsIamConnector
from app.services.connectors.aws_securityhub_connector import AwsSecurityHubConnector
from app.services.connectors.suricata_connector import SuricataConnector
from app.services.connectors.openvas_connector import OpenVASConnector, GMPConnectionError, GMPProtocolError

# --- WAZUH NEGATIVE TESTS ---

def test_wazuh_auth_failure_no_leak(caplog):
    """
    Test that Wazuh authentication failure raises WazuhAuthError 
    and does not leak credentials in the exception or logs.
    """
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="SUPER_SECRET_PASSWORD"
    )
    
    with patch("requests.Session.post") as mock_post:
        # Simulate 401 Unauthorized
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp
        
        with pytest.raises(WazuhAuthError) as exc_info:
            connector.fetch_events()
            
        assert "SUPER_SECRET_PASSWORD" not in str(exc_info.value)
        assert "SUPER_SECRET_PASSWORD" not in caplog.text

@patch("tenacity.nap.time.sleep")
def test_wazuh_retry_exponential_backoff(mock_sleep, caplog):
    """
    Test that Wazuh correctly retries on 429 Too Many Requests,
    using exponential backoff bounds, and eventually fails.
    """
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="password"
    )
    connector.token = "fake-token" # Skip auth
    
    with patch("requests.Session.get") as mock_get:
        # Simulate rate limit 429 constantly
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_get.return_value = mock_resp
        
        with pytest.raises(WazuhAPIError) as exc_info:
            connector.fetch_events()
            
        assert "Rate Limited" in str(exc_info.value)
        # Should attempt 5 times (initial + 4 retries) based on stop_after_attempt(5)
        assert mock_get.call_count == 5
        # Ensure sleep was called (we mocked it so it runs instantly)
        assert mock_sleep.call_count >= 1

def test_wazuh_partial_batch_failure():
    """
    Test behavior when one event is valid and another is malformed.
    Currently, _build_event might crash the entire batch.
    We assert the exact current behavior (as-is).
    """
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="password"
    )
    connector.token = "fake-token"
    
    valid_alert = {
        "id": "alert-1",
        "timestamp": "2024-01-01T00:00:00Z",
        "rule": {"level": 5, "description": "Test rule"}
    }
    
    # Missing ID generates a random UUID, invalid timestamp falls back to UTC.
    # Let's pass an invalid type for level to trigger TypeError in normalize_wazuh_severity
    invalid_alert = {
        "id": "alert-2",
        "timestamp": "2024-01-01T00:00:00Z",
        "rule": {"level": "NOT_AN_INT", "description": "Test rule"}
    }
    
    with patch("requests.Session.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "error": 0,
            "data": {
                "affected_items": [valid_alert, invalid_alert],
                "total_affected_items": 2
            }
        }
        mock_get.return_value = mock_resp
        
        # Currently, if _build_event raises an exception (like TypeError for string in int comparison),
        # the entire fetch_events loop catches it and raises it, crashing the batch.
        with pytest.raises(TypeError):
            connector.fetch_events()

def test_wazuh_timeout():
    """Test Wazuh handles requests.exceptions.Timeout."""
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="password"
    )
    connector.token = "fake-token"
    
    with patch("requests.Session.get") as mock_get:
        mock_get.side_effect = Timeout("Connection timed out")
        with pytest.raises(Timeout):
            connector.fetch_events()

def test_wazuh_network_failure():
    """Test Wazuh handles requests.exceptions.ConnectionError."""
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="password"
    )
    connector.token = "fake-token"
    
    with patch("requests.Session.get") as mock_get:
        mock_get.side_effect = ConnectionError("Connection refused")
        with pytest.raises(ConnectionError):
            connector.fetch_events()

def test_wazuh_empty_response():
    """Test Wazuh handles an empty response gracefully."""
    connector = WazuhConnector(
        base_url="https://fake-wazuh",
        user="admin",
        password="password"
    )
    connector.token = "fake-token"
    
    with patch("requests.Session.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "error": 0,
            "data": {
                "affected_items": [],
                "total_affected_items": 0
            }
        }
        mock_get.return_value = mock_resp
        
        events = connector.fetch_events()
        assert events == []

# --- AWS IAM NEGATIVE TESTS ---

def test_aws_iam_client_error_no_leak(caplog):
    """
    Test that AWS IAM handles botocore ClientErrors gracefully
    and does not leak AWS credentials.
    """
    connector = AwsIamConnector(
        account_id="123456789012",
        region="us-east-1",
        auth_method="static",
        access_key="AKIAFAKE",
        secret_key="SUPER_SECRET_AWS_KEY"
    )
    
    # Mock botocore client
    connector.iam_client = MagicMock()
    # Simulate AccessDenied
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
    connector.iam_client.get_paginator.side_effect = ClientError(error_response, 'ListUsers')
    
    with pytest.raises(ClientError) as exc_info:
        connector.fetch_events()
        
    assert "SUPER_SECRET_AWS_KEY" not in str(exc_info.value)
    assert "SUPER_SECRET_AWS_KEY" not in caplog.text

from botocore.exceptions import ReadTimeoutError, EndpointConnectionError

def test_aws_iam_timeout():
    """Test AWS IAM handles botocore.exceptions.ReadTimeoutError."""
    connector = AwsIamConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.iam_client = MagicMock()
    connector.iam_client.get_paginator.side_effect = ReadTimeoutError(endpoint_url="https://iam.amazonaws.com")
    
    with pytest.raises(ReadTimeoutError):
        connector.fetch_events()

def test_aws_iam_network_failure():
    """Test AWS IAM handles botocore.exceptions.EndpointConnectionError."""
    connector = AwsIamConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.iam_client = MagicMock()
    connector.iam_client.get_paginator.side_effect = EndpointConnectionError(endpoint_url="https://iam.amazonaws.com")
    
    with pytest.raises(EndpointConnectionError):
        connector.fetch_events()

def test_aws_iam_empty_response():
    """Test AWS IAM handles an empty response gracefully."""
    connector = AwsIamConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.iam_client = MagicMock()
    mock_paginator_users = MagicMock()
    mock_paginator_users.paginate.return_value = [{"Users": []}]
    mock_paginator_roles = MagicMock()
    mock_paginator_roles.paginate.return_value = [{"Roles": []}]
    
    def mock_get_paginator(operation):
        if operation == 'list_users': return mock_paginator_users
        if operation == 'list_roles': return mock_paginator_roles
        
    connector.iam_client.get_paginator.side_effect = mock_get_paginator
    
    events = connector.fetch_events()
    assert events == []

def test_aws_iam_invalid_payload():
    """Test AWS IAM partial batch failure handling (or current crash behavior).
    Currently, a missing 'Arn' triggers a KeyError in fetch_events.
    """
    connector = AwsIamConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.iam_client = MagicMock()
    mock_paginator_users = MagicMock()
    # Missing 'Arn' for user
    mock_paginator_users.paginate.return_value = [{"Users": [{"UserName": "test"}]}]
    
    def mock_get_paginator(operation):
        if operation == 'list_users': return mock_paginator_users
        
    connector.iam_client.get_paginator.side_effect = mock_get_paginator
    connector.iam_client.list_attached_user_policies.return_value = {"AttachedPolicies": []}
    
    # Assert current behavior: crashes the fetch loop
    with pytest.raises(KeyError):
        connector.fetch_events()

def test_aws_iam_retry():
    """Test AWS IAM botocore Throttling propagation."""
    connector = AwsIamConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.iam_client = MagicMock()
    error_response = {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}}
    connector.iam_client.get_paginator.side_effect = ClientError(error_response, 'ListUsers')
    
    with pytest.raises(ClientError) as exc_info:
        connector.fetch_events()
    assert "Throttling" in str(exc_info.value)

# --- AWS SECURITY HUB NEGATIVE TESTS ---

def test_aws_securityhub_client_error(caplog):
    """
    Test that AWS Security Hub handles ClientErrors without leaking credentials.
    """
    connector = AwsSecurityHubConnector(
        account_id="123456789012",
        region="us-east-1",
        auth_method="static",
        access_key="AKIAFAKE",
        secret_key="SUPER_SECRET_AWS_KEY"
    )
    
    connector.sh_client = MagicMock()
    error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
    connector.sh_client.get_paginator.side_effect = ClientError(error_response, 'GetFindings')
    
    with pytest.raises(ClientError) as exc_info:
        connector.fetch_events()
        
    assert "SUPER_SECRET_AWS_KEY" not in str(exc_info.value)
    assert "SUPER_SECRET_AWS_KEY" not in caplog.text

def test_aws_securityhub_timeout():
    """Test AWS Security Hub handles botocore.exceptions.ReadTimeoutError."""
    connector = AwsSecurityHubConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.sh_client = MagicMock()
    connector.sh_client.get_findings.side_effect = ReadTimeoutError(endpoint_url="https://securityhub.amazonaws.com")
    
    with pytest.raises(ReadTimeoutError):
        connector.fetch_events()

def test_aws_securityhub_network_failure():
    """Test AWS Security Hub handles botocore.exceptions.EndpointConnectionError."""
    connector = AwsSecurityHubConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.sh_client = MagicMock()
    connector.sh_client.get_findings.side_effect = EndpointConnectionError(endpoint_url="https://securityhub.amazonaws.com")
    
    with pytest.raises(EndpointConnectionError):
        connector.fetch_events()

def test_aws_securityhub_empty_response():
    """Test AWS Security Hub handles an empty response gracefully."""
    connector = AwsSecurityHubConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.sh_client = MagicMock()
    connector.sh_client.get_findings.return_value = {"Findings": []}
    
    events = connector.fetch_events()
    assert events == []

def test_aws_securityhub_invalid_payload():
    """Test AWS Security Hub partial batch failure handling.
    Currently, _build_event handles missing keys somewhat gracefully, but a missing timestamp might crash or default.
    """
    connector = AwsSecurityHubConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.sh_client = MagicMock()
    # Missing all necessary fields
    connector.sh_client.get_findings.return_value = {"Findings": [{}]}
    
    # Assert current behavior: _build_event handles empty gracefully by defaulting fields,
    # or raises TypeError from parse_timestamp if it can't handle None
    # Assuming parse_timestamp(None) returns None and SecurityEvent raises ValidationError, or it crashes.
    # Let's catch Exception generally or see what it raises.
    # Actually, parse_timestamp raises ValueError for None or invalid.
    with pytest.raises(Exception):
        connector.fetch_events()

@patch("tenacity.nap.time.sleep")
def test_aws_securityhub_retry_exponential_backoff(mock_sleep):
    """Test AWS Security Hub retry logic for ThrottlingException."""
    connector = AwsSecurityHubConnector(
        account_id="123456789012", region="us-east-1", auth_method="static",
        access_key="AKIAFAKE", secret_key="password"
    )
    connector.sh_client = MagicMock()
    error_response = {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}}
    connector.sh_client.get_findings.side_effect = ClientError(error_response, 'GetFindings')
    
    with pytest.raises(ClientError) as exc_info:
        connector.fetch_events()
    
    assert "ThrottlingException" in str(exc_info.value)
    # Should attempt 5 times
    assert connector.sh_client.get_findings.call_count == 5
    assert mock_sleep.call_count >= 1

# --- SURICATA NEGATIVE TESTS ---

def test_suricata_network_failure(caplog):
    """
    Test Suricata network failure handling (e.g., unreachable file/socket if local, or HTTP if remote)
    """
    # Suricata connector reads from eve.json file path
    connector = SuricataConnector(eve_json_path="/fake/path/eve.json")
    
    with patch("builtins.open") as mock_open:
        mock_open.side_effect = FileNotFoundError("No such file or directory")
        
        with pytest.raises(FileNotFoundError):
            connector.fetch_events()
            
def test_suricata_invalid_payload():
    """
    Test Suricata skipping malformed JSON lines in eve.json.
    """
    connector = SuricataConnector(eve_json_path="/fake/path/eve.json")
    
    mock_file_content = [
        '{"timestamp": "2024-01-01T00:00:00.000000+0000", "event_type": "alert", "alert": {"severity": 1, "signature": "Test"}}',
        'THIS IS NOT JSON',
        '{"timestamp": "2024-01-01T00:00:01.000000+0000", "event_type": "alert", "alert": {"severity": 2, "signature": "Test 2"}}'
    ]
    
    with patch("builtins.open", MagicMock()) as mock_open:
        # Mock file iteration
        mock_open.return_value.__enter__.return_value = mock_file_content
        
        events = connector.fetch_events()
        
        # Valid records make it through, malformed is skipped
        assert len(events) == 2

def test_suricata_empty_response():
    """Test Suricata handles an empty file gracefully."""
    connector = SuricataConnector(eve_json_path="/fake/path/eve.json")
    with patch("builtins.open", MagicMock()) as mock_open:
        mock_open.return_value.__enter__.return_value = []
        events = connector.fetch_events()
        assert events == []
        
# --- OPENVAS NEGATIVE TESTS ---

import socket

def test_openvas_auth_failure_no_leak(caplog):
    """
    Test OpenVAS auth failure raises GMPProtocolError and does not leak password.
    """
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="OPENVAS_SECRET_PASSWORD")
    
    class MockStream:
        def __init__(self):
            self.read_called = False
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<authenticate_response status="401" status_text="Unauthorized"/>'
            return b''
            
    with patch("app.services.connectors.openvas_connector.socket.socket"), \
         patch("app.services.connectors.openvas_connector.SocketStreamWrapper") as MockWrapper:
        MockWrapper.return_value = MockStream()
        
        with pytest.raises(GMPProtocolError) as exc_info:
            connector.fetch_events()
            
        assert "OPENVAS_SECRET_PASSWORD" not in str(exc_info.value)
        assert "OPENVAS_SECRET_PASSWORD" not in caplog.text

@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_timeout(mock_socket_class):
    """Test OpenVAS handles socket timeouts."""
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="password")
    
    mock_sock.connect.side_effect = socket.timeout("Connection timed out")
    
    with pytest.raises(GMPConnectionError):
        connector.fetch_events()

@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_network_failure(mock_socket_class):
    """Test OpenVAS handles network failures."""
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="password")
    
    mock_sock.connect.side_effect = ConnectionError("Connection refused")
    
    with pytest.raises(GMPConnectionError):
        connector.fetch_events()

@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_empty_response(mock_socket_class):
    """Test OpenVAS handles an empty response gracefully."""
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="password")
    
    class MockStreamAuth:
        def __init__(self):
            self.read_called = False
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<authenticate_response status="200" status_text="OK"/>'
            return b''

    class MockStreamResults:
        def __init__(self):
            self.read_called = False
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<get_results_response status="200" status_text="OK"></get_results_response>'
            return b''

    with patch("app.services.connectors.openvas_connector.SocketStreamWrapper") as MockWrapper:
        MockWrapper.side_effect = [MockStreamAuth(), MockStreamResults()]
        events = connector.fetch_events()
        assert events == []

@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_invalid_payload(mock_socket_class):
    """Test OpenVAS handling of malformed XML."""
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="password")
    
    class MockStreamAuth:
        def __init__(self):
            self.read_called = False
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<authenticate_response status="200" status_text="OK"/>'
            return b''

    class MockStreamResults:
        def __init__(self):
            self.read_called = False
        def read(self, size=-1):
            if not self.read_called:
                self.read_called = True
                return b'<get_results_response status="200"><result id="1"><host>127.0.0.1</host></result><result>UNCLOSED TAG'
            return b''

    with patch("app.services.connectors.openvas_connector.SocketStreamWrapper") as MockWrapper:
        MockWrapper.side_effect = [MockStreamAuth(), MockStreamResults()]
        
        # Expect the XML parser to crash the loop
        with pytest.raises(Exception):
            connector.fetch_events()

@patch("tenacity.nap.time.sleep")
@patch("app.services.connectors.openvas_connector.socket.socket")
def test_openvas_retry(mock_socket_class, mock_sleep):
    """Test OpenVAS exponential backoff via health_check retry logic."""
    mock_sock = MagicMock()
    mock_socket_class.return_value = mock_sock
    connector = OpenVASConnector(host="127.0.0.1", port=9390, user="admin", password="password")
    
    with patch("app.services.connectors.openvas_connector.GMPTransport.send_command") as mock_send:
        mock_send.side_effect = GMPConnectionError("Socket disconnected")
        
        # Health check returns a dict on error rather than raising, but it consumes the retries inside _execute_with_retry
        # Wait, if _execute_with_retry fails completely, health_check catches it and returns {"status": "error"}
        # So we shouldn't assert raises here, we should just assert the return value and the call counts.
        res = connector.health_check()
        assert res["status"] == "error"
        assert mock_send.call_count == 5
        assert mock_sleep.call_count >= 1
