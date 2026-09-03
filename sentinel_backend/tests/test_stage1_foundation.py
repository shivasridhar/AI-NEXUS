import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from typing import List, Dict, Any

from app.schemas.security_event import SecurityEvent
from app.services.connectors.base_connector import BaseConnector

def test_security_event_valid_creation():
    """Test that a SecurityEvent can be successfully created with valid data."""
    now = datetime.now(timezone.utc)
    event = SecurityEvent(
        event_id="evt-12345",
        source="wazuh-manager",
        vendor="Wazuh",
        event_type="FileIntegrity",
        timestamp=now,
        severity="HIGH",
        asset="10.0.0.5",
        raw_payload={"rule": "550", "description": "File integrity checksum changed"}
    )
    
    assert event.event_id == "evt-12345"
    assert event.vendor == "Wazuh"
    assert event.severity == "HIGH"
    assert event.asset == "10.0.0.5"
    assert "rule" in event.raw_payload

def test_security_event_missing_required_fields():
    """Test that SecurityEvent raises ValidationError when missing required fields."""
    with pytest.raises(ValidationError):
        # Missing 'source' and 'vendor' which are required
        SecurityEvent(
            event_id="evt-67890",
            event_type="Authentication",
            timestamp=datetime.now(timezone.utc),
            severity="LOW"
        )

def test_base_connector_is_abstract():
    """Test that BaseConnector cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseConnector()

def test_concrete_connector_implementation():
    """Test that a concrete implementation of BaseConnector works as expected."""
    class MockConnector(BaseConnector):
        def connect(self) -> bool:
            return True
            
        def authenticate(self) -> bool:
            return True
            
        def fetch_events(self, **kwargs) -> List[SecurityEvent]:
            return []
            
        def health_check(self) -> Dict[str, Any]:
            return {"status": "healthy"}
            
        def disconnect(self) -> bool:
            return True

    connector = MockConnector()
    assert connector.connect() is True
    assert connector.authenticate() is True
    assert isinstance(connector.fetch_events(), list)
    assert connector.health_check()["status"] == "healthy"
    assert connector.disconnect() is True
