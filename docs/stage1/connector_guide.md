# Connector Developer Guide

This guide explains how to add new data source integrations to the SentinelAI Stage 1 Ingestion Engine. The architecture relies heavily on Object-Oriented polymorphism and a Metaclass Registry to ensure you never have to modify core routing logic to add a connector.

## How to Add a New Connector

### 1. Implement `BaseConnector`
Create a new file in `app/services/connectors/` (e.g., `my_custom_connector.py`).
Import `BaseConnector` and `ConnectorRegistry`. 

Your class must implement the `BaseConnector` abstract methods.

```python
import logging
from typing import List, Dict, Any
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry
from app.schemas.security_event import SecurityEvent

logger = logging.getLogger(__name__)

class MyCustomConnector(BaseConnector, metaclass=ConnectorRegistry):
    """
    Connector for Custom Source.
    The metaclass automatically registers this class under the name returned by `get_name()`.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Extract necessary fields from config (passed from UI)
        self.api_key = config.get("api_key")
        self.endpoint = config.get("endpoint")

    @classmethod
    def get_name(cls) -> str:
        # This exact string must match the `connector_name` passed from the UI
        return "custom_source"

    def connect(self) -> None:
        logger.info(f"Connecting to {self.endpoint}...")
        # Initialization logic (e.g., setting up requests session)

    def authenticate(self) -> bool:
        logger.info("Authenticating...")
        # Verify credentials
        # Raise PermissionError if invalid.
        if not self.api_key:
            raise PermissionError("Missing API Key")
        return True

    def fetch_events(self) -> List[SecurityEvent]:
        # Connect to remote source, fetch data
        # Map raw data to the `SecurityEvent` schema
        raw_data = {"id": "123", "msg": "Suspicious login"}
        
        event = SecurityEvent(
            event_id="123",
            timestamp=datetime.now(timezone.utc),
            source=self.get_name(),
            event_type="login",
            severity=5.0,
            action="login",
            status="failed",
            raw_data=raw_data
        )
        return [event]

    def disconnect(self) -> None:
        logger.info("Disconnecting...")
        # Clean up resources
```

### 2. Update Frontend Configuration
Because the frontend UI is strictly data-driven, you **DO NOT** need to create new React components or new layout files to support this connector. *(Re-verified: even after the removal of UI mocks in the telemetry pass, this zero-frontend-changes claim remains true; the frontend dynamically builds the connector configuration form directly from the `/api/v1/integrations` schema.)*

Simply ensure the backend `/api/v1/integrations` endpoint includes your new connector schema in its payload:
```json
{
  "provider": "custom_source",
  "name": "My Custom Source",
  "status": "available",
  "config_schema": [
    {
      "name": "endpoint",
      "label": "API URL",
      "type": "text",
      "required": true
    },
    {
      "name": "api_key",
      "label": "API Key",
      "type": "password",
      "required": true
    }
  ]
}
```
The UI in `/integrations` will automatically parse this schema and generate the form for users to configure the integration.

### 3. Verify Isolation
Do not import other connectors into your new connector file.
Do not import pipeline logic (Validation/Enrichment) into your connector. 
Your connector has exactly one job: yield a list of `SecurityEvent` objects. The pipeline will handle the rest.
