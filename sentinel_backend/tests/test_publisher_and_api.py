import pytest
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.security_event import SecurityEvent
from app.services.security_event_publisher import (
    SecurityEventPublisherFactory,
    InMemorySecurityEventPublisher,
    PublishFailureDetail,
    PublishSummary
)
from app.api.dependencies import get_current_workspace
from app.models.tenant import Workspace
from app.services.connectors.connector_registry import ConnectorRegistry
from app.services.connectors.base_connector import BaseConnector

# ── Publisher Unit Tests ──────────────────────────────────────────────────────

def test_publisher_factory_and_in_memory():
    # Factory check
    publisher = SecurityEventPublisherFactory.create("in_memory")
    assert isinstance(publisher, InMemorySecurityEventPublisher)
    
    with pytest.raises(ValueError):
        SecurityEventPublisherFactory.create("non_existent_publisher_type")

    # Publishing flow check
    event = SecurityEvent(
        event_id="test-uuid",
        source="wazuh_alerts",
        vendor="wazuh",
        event_type="Authentication",
        timestamp=datetime.now(timezone.utc),
        severity="HIGH",
        asset="127.0.0.1",
        raw_payload={"details": "dummy"}
    )
    
    summary = publisher.publish([event])
    assert summary.published_count == 1
    assert summary.failed_count == 0
    assert len(summary.failures) == 0
    assert len(publisher.get_published_events()) == 1

def test_publisher_partial_failure():
    publisher = InMemorySecurityEventPublisher()
    
    # Create one valid and one invalid event (missing required fields in raw model)
    valid_event = SecurityEvent(
        event_id="valid-id",
        source="wazuh_alerts",
        vendor="wazuh",
        event_type="Auth",
        timestamp=datetime.now(timezone.utc),
        severity="LOW",
        asset="127.0.0.1",
        raw_payload={"key": "val"}
    )
    
    # We will simulate a malformed/missing fields failure by modifying event attributes after instantiation
    bad_event = valid_event.model_copy()
    bad_event.event_id = "" # invalidate event ID
    
    summary = publisher.publish([valid_event, bad_event])
    assert summary.published_count == 1
    assert summary.failed_count == 1
    assert summary.failures[0].event_id == "unknown"
    assert "missing critical fields" in summary.failures[0].reason.lower()


# ── API Route Unit & Mock Integration Tests ────────────────────────────────────

# Create a mock Workspace instance to bypass database dependency check
mock_ws_id = uuid.uuid4()
mock_org_id = uuid.uuid4()
mock_workspace = Workspace(id=mock_ws_id, organization_id=mock_org_id, name="Simulation Workspace")

@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    app.dependency_overrides[get_current_workspace] = lambda: mock_workspace
    yield
    app.dependency_overrides.clear()


def test_api_trigger_ingestion_success(mocker):
    client = TestClient(app)
    
    mock_events = [
        SecurityEvent(
            event_id="event-uuid-1",
            source="wazuh_alerts",
            vendor="mock_wazuh",
            event_type="Authentication",
            timestamp=datetime.now(timezone.utc),
            severity="HIGH",
            asset="10.0.0.1",
            raw_payload={"event": "login_failure"}
        )
    ]

    class MockConnector(BaseConnector):
        def __init__(self, **kwargs):
            pass
        def connect(self): pass
        def authenticate(self): return True
        def fetch_events(self): return mock_events
        def health_check(self): return {"status": "ok"}
        def disconnect(self): pass

    # Register connector and mock create
    ConnectorRegistry.register("mock_wazuh")(MockConnector)
    
    payload = {
        "connector_name": "mock_wazuh",
        "config": {"host": "localhost"}
    }
    
    response = client.post("/api/v1/ingestion/trigger", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["connector"] == "mock_wazuh"
    assert data["status"] == "completed"
    assert data["events_received"] == 1
    assert data["events_published"] == 1
    assert len(data["failures"]) == 0


def test_api_trigger_auth_failure():
    client = TestClient(app)

    # Mock connector that fails auth
    class BadAuthConnector(BaseConnector):
        def __init__(self, **kwargs):
            pass
        def connect(self): pass
        def authenticate(self): return False # Auth failed
        def fetch_events(self): return []
        def health_check(self): return {"status": "ok"}
        def disconnect(self): pass

    ConnectorRegistry.register("bad_auth_conn")(BadAuthConnector)

    payload = {
        "connector_name": "bad_auth_conn",
        "config": {}
    }
    
    response = client.post("/api/v1/ingestion/trigger", json=payload)
    assert response.status_code == 401
    assert "authentication rejected" in response.json()["detail"].lower()


def test_api_trigger_connection_failure():
    client = TestClient(app)

    # Mock connector that throws connection exception
    class ConnectionErrorConnector(BaseConnector):
        def __init__(self, **kwargs):
            pass
        def connect(self): 
            raise ConnectionRefusedError("Connection refused by test")
        def authenticate(self): return True
        def fetch_events(self): return []
        def health_check(self): return {"status": "failed"}
        def disconnect(self): pass

    ConnectorRegistry.register("conn_error_conn")(ConnectionErrorConnector)

    payload = {
        "connector_name": "conn_error_conn",
        "config": {}
    }
    
    response = client.post("/api/v1/ingestion/trigger", json=payload)
    assert response.status_code == 502
    assert "connection failed" in response.json()["detail"].lower()
