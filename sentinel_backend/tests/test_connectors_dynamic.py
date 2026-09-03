import pytest
from typing import List, Dict, Any
from app.services.connectors.connector_registry import ConnectorRegistry, ConnectorNotFoundError
from app.services.connectors.connector_factory import ConnectorFactory
from app.services.connectors.connector_manager import ConnectorManager
from app.schemas.security_event import SecurityEvent

def test_connector_registration():
    """Verify that all implemented connectors are dynamically registered on module load."""
    # Force import of connectors to trigger decorators
    import app.services.connectors.aws_iam_connector
    import app.services.connectors.aws_securityhub_connector
    import app.services.connectors.wazuh_connector
    import app.services.connectors.suricata_connector
    import app.services.connectors.openvas_connector

    registered = ConnectorRegistry.list_registered()
    assert "aws_iam" in registered
    assert "aws_securityhub" in registered
    assert "wazuh" in registered
    assert "suricata" in registered
    assert "openvas" in registered

def test_connector_factory_resolution():
    """Verify that the factory correctly retrieves and creates classes dynamically."""
    # We can pass dummy structures that pass initialization checks
    wazuh_config = {
        "base_url": "https://localhost:55000",
        "user": "foo",
        "password": "bar"
    }
    connector = ConnectorFactory.create("wazuh", wazuh_config)
    assert connector.__class__.__name__ == "WazuhConnector"

    suricata_config = {
        "file_path": "/tmp/non_existent_eve.json" # config passes __init__
    }
    connector = ConnectorFactory.create("suricata", suricata_config)
    assert connector.__class__.__name__ == "SuricataConnector"

def test_connector_factory_invalid_name():
    """Verify that the factory raises ConnectorNotFoundError for unknown plugins."""
    with pytest.raises(ConnectorNotFoundError):
        ConnectorFactory.create("unknown_plugin", {})
