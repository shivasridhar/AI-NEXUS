import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from app.schemas.security_event import SecurityEvent
from app.services.connectors.connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


class EventValidationError(Exception):
    """Raised when an event fails logical validation checks."""

    def __init__(self, errors: Dict[str, str]):
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class EventValidator:
    """
    Handles technical validation rules for SecurityEvent payloads before downstream ingestion.
    """

    def __init__(
        self,
        max_age_days: int = 30,
        max_future_skew_minutes: int = 60,
        allowed_vendors: Optional[List[str]] = None,
    ):
        self.max_age_days = max_age_days
        self.max_future_skew_minutes = max_future_skew_minutes
        self._allowed_vendors = allowed_vendors

    def _get_allowed_vendors(self) -> List[str]:
        """Dynamically pulls active connector registry names to avoid synchronization drift."""
        if self._allowed_vendors is not None:
            return self._allowed_vendors
        # Fetch directly from the runtime registry and ensure standard vendors like 'aws' are included
        registry_names = ConnectorRegistry.list_registered()
        vendors = set(registry_names)
        if any(name.startswith("aws") for name in registry_names):
            vendors.add("aws")
        return list(vendors)

    def validate(self, event: SecurityEvent) -> Tuple[bool, Dict[str, str]]:
        """
        Validates logical rules on a SecurityEvent.
        Returns a tuple of (is_valid, errors_dictionary).
        """
        errors: Dict[str, str] = {}

        # 1. Pydantic baseline validation (Implicitly done by model type safety, but check structure)
        if not isinstance(event, SecurityEvent):
            errors["type"] = "Object is not an instance of SecurityEvent"
            return False, errors

        # 2. Check vendor registry alignment
        allowed_vendors = self._get_allowed_vendors()
        # Normalise check to lowercase to prevent minor casing mismatches
        vendor_lower = event.vendor.lower()
        allowed_vendors_lower = [v.lower() for v in allowed_vendors]

        if vendor_lower not in allowed_vendors_lower:
            errors["vendor"] = (
                f"Vendor '{event.vendor}' is not registered in the ConnectorRegistry. Allowed: {allowed_vendors}"
            )

        # 3. Check raw payload presence and integrity
        if not event.raw_payload:
            errors["raw_payload"] = (
                "Raw payload is missing or empty. Audit trail cannot be verified."
            )

        # 4. Check timestamp sanity limits
        now = datetime.now(timezone.utc)

        # Ensure timezone-aware
        ts = event.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        # Max Age Check
        min_allowed_time = now - timedelta(days=self.max_age_days)
        if ts < min_allowed_time:
            errors["timestamp"] = (
                f"Event timestamp {ts.isoformat()} is too old (max age: {self.max_age_days} days)."
            )

        # Future Skew Check
        max_allowed_time = now + timedelta(minutes=self.max_future_skew_minutes)
        if ts > max_allowed_time:
            errors["timestamp"] = (
                f"Event timestamp {ts.isoformat()} is too far in the future (skew limit: {self.max_future_skew_minutes} minutes)."
            )

        # 5. Check Severity bounds
        allowed_severities = {"INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if event.severity.upper() not in allowed_severities:
            errors["severity"] = (
                f"Severity '{event.severity}' is invalid. Allowed: {allowed_severities}"
            )

        # 6. Event Type validation
        if not event.event_type or not event.event_type.strip():
            errors["event_type"] = "Event type cannot be empty."

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning(
                f"[EventValidator] Event validation failed for ID={event.event_id}, source={event.source}. "
                f"Errors: {errors}. Event quarantined."
            )

        return is_valid, errors
