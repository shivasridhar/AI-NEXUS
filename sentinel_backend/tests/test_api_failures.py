import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.api.dependencies import get_db

@pytest.fixture
def client(postgres_db):
    app.dependency_overrides[get_db] = lambda: postgres_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def assert_error_envelope(response_json):
    assert "error" in response_json, f"Missing 'error' envelope in {response_json}"
    error = response_json["error"]
    assert "code" in error, f"Missing 'code' in {error}"
    assert "message" in error, f"Missing 'message' in {error}"
    assert "details" in error, f"Missing 'details' in {error}"

def test_authentication_failure(client):
    response = client.get("/api/v1/organizations/me")
    assert response.status_code == 401
    assert_error_envelope(response.json())

def test_authorization_failure(client):
    # Missing role or similar. We can mock a token with wrong permissions or invalid workspace
    response = client.get("/api/v1/organizations/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
    assert_error_envelope(response.json())

def test_invalid_request_missing_payload(client):
    from app.api.dependencies import get_current_workspace
    from app.models.tenant import Workspace
    import uuid
    def _mock_ws():
        ws = Workspace()
        ws.id = uuid.uuid4()
        return ws
    app.dependency_overrides[get_current_workspace] = _mock_ws
    try:
        response = client.post("/api/v1/integrations/aws", json={})
        assert response.status_code in [400, 422]
        assert_error_envelope(response.json())
    finally:
        app.dependency_overrides.pop(get_current_workspace, None)

def test_connector_failure(client):
    # Trigger a ClientError by mocking boto3.client
    from botocore.exceptions import ClientError
    from app.api.dependencies import get_current_workspace
    from app.models.tenant import Workspace
    import uuid
    
    def _mock_ws():
        ws = Workspace()
        ws.id = uuid.uuid4()
        return ws
    app.dependency_overrides[get_current_workspace] = _mock_ws
    with patch("boto3.client") as mock_boto:
        mock_boto.side_effect = ClientError({"Error": {"Code": "AccessDenied", "Message": "Connection refused"}}, "AssumeRole")
        
        try:
            response = client.post("/api/v1/integrations/aws", json={
                "account_id": "123456789012",
                "region": "us-east-1",
                "auth_method": "access_key",
                "access_key": "AKIA",
                "secret_key": "SECRET"
            })
            assert response.status_code >= 400
            assert_error_envelope(response.json())
        finally:
            app.dependency_overrides.pop(get_current_workspace, None)

@pytest.mark.parametrize("endpoint, method, kwargs", [
    ("/api/v1/organizations/me", "get", {}),
    ("/api/v1/integrations/aws", "post", {"json": {"account_id": "123456789012", "region": "us-east-1", "auth_method": "access_key", "access_key": "A", "secret_key": "S"}, "headers": {"x-workspace-id": "123e4567-e89b-12d3-a456-426614174000"}}),
])
def test_internal_server_error_no_leak(client, endpoint, method, kwargs):
    # We monkeypatch the endpoint's dependency or internal function to raise a raw Exception
    from app.api.dependencies import get_current_active_user
    
    def mock_get_current_user_exception():
        raise Exception("SUPER_SECRET_INTERNAL_EXCEPTION_TEXT")
        
    app.dependency_overrides[get_current_active_user] = mock_get_current_user_exception
    try:
        from fastapi.testclient import TestClient
        from app.main import app as main_app
        # Create a specific client that doesn't raise server exceptions, allowing us to see the 500 response
        local_client = TestClient(main_app, raise_server_exceptions=False)
        response = getattr(local_client, method)(endpoint, **kwargs)
        
        assert response.status_code == 500
        # If it returns JSON (e.g. through a global exception handler), check that the secret text is NOT leaked
        try:
            resp_json = response.json()
            assert_error_envelope(resp_json)
            assert "SUPER_SECRET_INTERNAL_EXCEPTION_TEXT" not in str(resp_json)
        except ValueError:
            # If it returns raw text instead of JSON
            assert "SUPER_SECRET_INTERNAL_EXCEPTION_TEXT" not in response.text
    finally:
        app.dependency_overrides.pop(get_current_active_user, None)
