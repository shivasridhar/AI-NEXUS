import logging
from typing import Any, Dict, List, Optional

from app.schemas.security_event import SecurityEvent
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_factory import ConnectorFactory
from app.services.connectors.connector_health_monitor import (
    ConnectorHealthMonitor,
)

logger = logging.getLogger(__name__)


class ConnectorManager:
    """
    Orchestrates the lifecycle of active connectors (initialization, auth, fetching, shutdown).
    Maintains zero knowledge of concrete connector classes.
    """

    def __init__(self, pipeline: Optional[Any] = None):
        self._active_connectors: Dict[str, BaseConnector] = {}
        self._health_monitor = ConnectorHealthMonitor()
        self.pipeline = pipeline

    def initialize_connectors(self, configurations: List[Dict[str, Any]]):
        """
        Dynamically initializes connectors based on a data-driven configuration list.

        Args:
            configurations: A list of dicts. Example:
                [
                    {"name": "wazuh", "config": {"url": "...", "api_key": "..."}},
                    {"name": "aws_iam", "config": {"access_key": "..."}}
                ]
        """
        for entry in configurations:
            name = entry.get("name")
            config = entry.get("config", {})

            if not name:
                logger.warning(
                    "Skipping invalid connector configuration: missing 'name' field."
                )
                continue

            try:
                # Instantiation delegated to factory
                connector = ConnectorFactory.create(name, config)

                self._active_connectors[name] = connector
                self._health_monitor.register_instance(name)
                logger.info(
                    f"[Connector: {name}] Successfully initialized via factory."
                )

            except Exception as e:
                # Error isolation: A failure here does not crash the manager or stop other connectors
                logger.error(
                    f"[Connector: {name}] Failed to initialize: {type(e).__name__} - {str(e)}"
                )

    def authenticate_all(self):
        """Iterates through active connectors and triggers their standard authentication process."""
        for name, connector in self._active_connectors.items():
            try:
                # Delegate to the standard abstraction lifecycle
                connector.connect()
                if connector.authenticate():
                    logger.info(f"[Connector: {name}] Authenticated successfully.")
                else:
                    logger.warning(
                        f"[Connector: {name}] Authentication method returned False."
                    )
            except Exception as e:
                # Error isolation
                logger.error(
                    f"[Connector: {name}] Authentication exception: {type(e).__name__} - {str(e)}"
                )

    def fetch_all_events(self) -> List[SecurityEvent]:
        """
        Fetches events from all active connectors.
        Failure in one connector's fetch process is isolated and does not break the pipeline.

        Returns:
            A consolidated list of standard SecurityEvent objects.
        """
        all_events: List[SecurityEvent] = []
        for name, connector in self._active_connectors.items():
            try:
                events = connector.fetch_events()
                all_events.extend(events)
                logger.info(f"[Connector: {name}] Fetched {len(events)} events.")
            except Exception as e:
                # Error isolation
                logger.error(
                    f"[Connector: {name}] Fetch failed: {type(e).__name__} - {str(e)}"
                )

        # Run consolidated events through validation, duplicate detection, and metadata enrichment pipeline
        if self.pipeline:
            all_events = self.pipeline.process(all_events)

        return all_events

    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Executes health checks on all active connectors and returns a serialized status map.
        """
        reports = {}
        for name, connector in self._active_connectors.items():
            report = self._health_monitor.check_health(name, connector)
            reports[name] = report.to_dict()
        return reports

    def shutdown(self):
        """Gracefully disconnects and cleans up all active connectors."""
        for name, connector in self._active_connectors.items():
            try:
                connector.disconnect()
                logger.info(f"[Connector: {name}] Disconnected successfully.")
            except Exception as e:
                logger.error(
                    f"[Connector: {name}] Shutdown exception: {type(e).__name__} - {str(e)}"
                )
