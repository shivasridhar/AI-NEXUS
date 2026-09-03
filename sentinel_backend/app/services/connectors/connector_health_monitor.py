import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.services.connectors.base_connector import BaseConnector

logger = logging.getLogger(__name__)


class ConnectorStatus(str, Enum):
    """Normalized health status representations for any connector."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    UNKNOWN = "UNKNOWN"


class HealthReport:
    """
    Serializable status report for a connector instance.
    Decouples raw health state from API/Dashboard consumers.
    """

    def __init__(
        self,
        name: str,
        status: ConnectorStatus,
        last_poll: Optional[datetime],
        failure_count: int,
        last_error: Optional[str],
    ):
        self.name = name
        self.status = status
        self.last_poll = last_poll
        self.failure_count = failure_count
        self.last_error = last_error

    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a dictionary for API/JSON serialization."""
        return {
            "name": self.name,
            "status": self.status.value,
            "last_poll": self.last_poll.isoformat() if self.last_poll else None,
            "failure_count": self.failure_count,
            "last_error": self.last_error,
        }


class ConnectorHealthMonitor:
    """
    Tracks and executes health checks for active connector instances.
    Contains zero connector-specific checking logic; relies entirely on the BaseConnector interface.
    """

    def __init__(self):
        # Maps connector name (instance ID) to its health state
        self._status: Dict[str, ConnectorStatus] = {}
        self._last_poll: Dict[str, Optional[datetime]] = {}
        self._failures: Dict[str, int] = {}
        self._last_errors: Dict[str, Optional[str]] = {}

    def register_instance(self, name: str):
        """Register a new connector instance for tracking."""
        if name not in self._status:
            self._status[name] = ConnectorStatus.UNKNOWN
            self._last_poll[name] = None
            self._failures[name] = 0
            self._last_errors[name] = None

    def check_health(self, name: str, connector: BaseConnector) -> HealthReport:
        """
        Execute a health check on the given connector instance and update tracking state.
        Errors are safely caught to prevent crashing the monitor.
        """
        self.register_instance(name)

        try:
            # Delegate entirely to the standard interface method
            connector.health_check()

            self._status[name] = ConnectorStatus.HEALTHY
            self._last_poll[name] = datetime.now(timezone.utc)
            self._failures[name] = 0
            self._last_errors[name] = None

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.error("[Connector: {name}] Health check failed: %s", error_msg)

            self._failures[name] += 1
            self._last_errors[name] = error_msg

            # Simple thresholding logic: >3 consecutive failures = DOWN, otherwise DEGRADED
            if self._failures[name] > 3:
                self._status[name] = ConnectorStatus.DOWN
            else:
                self._status[name] = ConnectorStatus.DEGRADED

        return self.get_report(name)

    def get_report(self, name: str) -> HealthReport:
        """Retrieve the current health report for a tracked connector."""
        return HealthReport(
            name=name,
            status=self._status.get(name, ConnectorStatus.UNKNOWN),
            last_poll=self._last_poll.get(name),
            failure_count=self._failures.get(name, 0),
            last_error=self._last_errors.get(name),
        )
