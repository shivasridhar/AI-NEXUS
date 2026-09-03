import logging
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.schemas.security_event import SecurityEvent
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry
from app.services.severity_normalization import normalize_wazuh_severity
from app.utils.parsers import parse_timestamp

logger = logging.getLogger(__name__)


def _map_wazuh_severity_to_label(level: int) -> str:
    """
    Takes the raw Wazuh rule level, passes it through the existing normalizer (0-100),
    and converts it into the string enum expected by SecurityEvent.
    """
    normalized_score = normalize_wazuh_severity(level)
    if normalized_score < 20:
        return "INFO"
    elif normalized_score < 40:
        return "LOW"
    elif normalized_score < 60:
        return "MEDIUM"
    elif normalized_score < 80:
        return "HIGH"
    return "CRITICAL"


class WazuhAuthError(Exception):
    """Raised when authentication against Wazuh fails."""


class WazuhAPIError(Exception):
    """Raised when the Wazuh API returns a non-2xx or explicit error."""


@ConnectorRegistry.register("wazuh")
class WazuhConnector(BaseConnector):
    """
    Wazuh REST API Connector.
    Uses dynamic JWT authentication, explicit cursor-based incremental polling,
    and automatic pagination.
    """

    def __init__(
        self,
        base_url: str,
        user: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
        filters: Optional[Dict[str, Any]] = None,
    ):
        # Configuration
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        # Filtering and state
        self.filters = filters or {}
        self.last_timestamp: Optional[str] = self.filters.get("since_timestamp")

        # Client state
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.token: Optional[str] = None

    def connect(self) -> bool:
        """
        Prepares the session. Actual connection validation occurs in authenticate().
        """
        return self.authenticate()

    def authenticate(self) -> bool:
        """
        Authenticates against Wazuh using Basic Auth to obtain a JWT.
        """
        auth_url = urljoin(self.base_url, "/security/user/authenticate")
        try:
            # Wazuh typically uses Basic Auth for the auth endpoint to return a Bearer token
            response = self.session.post(
                auth_url, auth=(self.user, self.password), timeout=self.timeout
            )

            if response.status_code == 401:
                logger.error(
                    "[WazuhConnector] Authentication failed: Invalid credentials."
                )
                raise WazuhAuthError("Invalid Wazuh credentials.")

            response.raise_for_status()

            data = response.json()
            token = data.get("data", {}).get("token")

            if not token:
                logger.error(
                    "[WazuhConnector] Authentication succeeded but no token returned."
                )
                return False

            self.token = token
            # Inject token for all future requests in this session
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            logger.info(
                "[WazuhConnector] Successfully authenticated and obtained token."
            )
            return True

        except requests.exceptions.RequestException as e:
            logger.error("[WazuhConnector] Network error during authentication: %s", str(e))
            return False
        except ValueError as e:
            logger.error("[WazuhConnector] Failed to parse authentication response: %s", str(e))
            return False

    @retry(
        retry=retry_if_exception_type(
            (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                WazuhAPIError,
            )
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _execute_api_call(
        self, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes an API call with automatic token refresh and exponential backoff on network/rate-limit errors.
        """
        url = urljoin(self.base_url, endpoint)

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            # Handle Token Expiry
            if response.status_code == 401:
                logger.warning(
                    "[WazuhConnector] Token expired mid-session. Re-authenticating..."
                )
                if self.authenticate():
                    # Retry the request with the new token
                    response = self.session.get(
                        url, params=params, timeout=self.timeout
                    )
                else:
                    raise WazuhAuthError(
                        "Failed to re-authenticate after token expiry."
                    )

            # Respect potential Rate Limits
            if response.status_code == 429:
                logger.warning(
                    "[WazuhConnector] Rate limited by Wazuh API. Backing off..."
                )
                raise WazuhAPIError("Rate Limited")  # Will trigger @retry

            response.raise_for_status()

            json_data = response.json()
            # Wazuh API returns its own 'error' code in the envelope
            if json_data.get("error", 0) != 0:
                err_msg = json_data.get("message", "Unknown Wazuh API Error")
                raise WazuhAPIError(
                    f"Wazuh API Error {json_data.get('error')}: {err_msg}"
                )

            return json_data

        except requests.exceptions.RequestException as e:
            logger.error("[WazuhConnector] Request failed: %s", str(e))
            raise e  # Triggers @retry if it's a ConnectionError/Timeout

    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Fetches Wazuh alerts incrementally with real API pagination.
        """
        if not self.token:
            if not self.authenticate():
                raise WazuhAuthError("Cannot fetch events: Authentication failed.")

        events = []
        limit = min(500, settings.MAX_RESULTS_PER_POLL)
        offset = 0

        # Build query string based on filters and incremental state
        query_parts = []
        if self.last_timestamp:
            # Assuming last_timestamp is ISO-8601, e.g. "2024-01-01T00:00:00Z"
            # Wazuh filter param: timestamp>2024-01-01T00:00:00Z
            query_parts.append(f"timestamp>{self.last_timestamp}")

        for k, v in self.filters.items():
            if k == "since_timestamp":
                continue  # handled above
            query_parts.append(f"{k}={v}")

        params = {
            "limit": limit,
            "sort": "+timestamp",  # Ascending order to safely track high-water mark
        }
        if query_parts:
            params["q"] = ";".join(query_parts)

        latest_fetched_timestamp = self.last_timestamp

        try:
            while True:
                params["offset"] = offset
                response_data = self._execute_api_call(
                    (
                        "/security/alerts"
                        if "security/alerts" in self.base_url
                        else "/alerts"
                    ),
                    params,
                )

                data_envelope = response_data.get("data", {})
                affected_items = data_envelope.get("affected_items", [])

                if not affected_items:
                    break

                for alert in affected_items:
                    events.append(self._build_event(alert))
                    # Track high-water mark
                    alert_time = alert.get("timestamp")
                    if alert_time:
                        latest_fetched_timestamp = alert_time

                # Check if we have exhausted all items
                total_affected = data_envelope.get("total_affected_items", 0)
                offset += len(affected_items)

                if offset >= total_affected:
                    break

            if not events:
                logger.info(
                    "[WazuhConnector] Fetch completed successfully, but zero new alerts matched filters."
                )
            else:
                logger.info(
                    f"[WazuhConnector] Successfully fetched {len(events)} alerts."
                )
                # Update the cursor state across polls
                if latest_fetched_timestamp:
                    self.last_timestamp = latest_fetched_timestamp

        except Exception as e:
            logger.error("[WazuhConnector] Event fetch workflow failed: %s", str(e))
            raise e

        return events

    def _build_event(self, alert: Dict[str, Any]) -> SecurityEvent:
        """
        Standardize the Wazuh alert format into a SentinelAI SecurityEvent.
        """
        event_id = alert.get("id", f"wazuh-{uuid.uuid4().hex}")

        rule = alert.get("rule", {})
        groups = rule.get("groups", [])

        event_type = (
            groups[0] if groups else rule.get("description", "Unknown Wazuh Alert")
        )

        # Severity mapped via shared normalizer
        raw_level = rule.get("level", 0)
        severity = _map_wazuh_severity_to_label(raw_level)

        # Timestamp parsing
        timestamp_str = alert.get("timestamp")
        timestamp = parse_timestamp(timestamp_str)

        # Asset Mapping
        agent = alert.get("agent", {})
        asset = agent.get("id") or agent.get("name") or agent.get("ip")

        # Identity Mapping
        data_block = alert.get("data", {})
        identity = data_block.get("srcuser") or data_block.get("dstuser")

        # Metadata
        metadata = {
            "rule_id": rule.get("id"),
            "rule_groups": groups,
            "manager_name": alert.get("manager", {}).get("name"),
            "location": alert.get("location"),
            "decoder_name": alert.get("decoder", {}).get("name"),
        }

        return SecurityEvent(
            event_id=event_id,
            source="wazuh_alerts",
            vendor="Wazuh",
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            asset=asset,
            identity=identity,
            raw_payload=alert,
            metadata={k: v for k, v in metadata.items() if v is not None},
        )

    def health_check(self) -> Dict[str, Any]:
        """Validates Wazuh API connectivity via a lightweight call."""
        if not self.token:
            is_auth = self.authenticate()
            if not is_auth:
                raise WazuhAuthError("Failed to authenticate during health check.")

        try:
            # Lightweight call to the manager info endpoint
            info = self._execute_api_call("/manager/info", {})
            manager_name = (
                info.get("data", {})
                .get("affected_items", [{}])[0]
                .get("name", "Unknown")
            )
            return {"status": "ok", "service": "wazuh", "manager": manager_name}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect(self) -> bool:
        """Cleans up the requests session."""
        self.session.close()
        self.token = None
        return True
