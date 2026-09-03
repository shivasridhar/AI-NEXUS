import logging
import uuid
from typing import Any, Dict, List, Optional

from botocore.exceptions import BotoCoreError, ClientError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.schemas.security_event import SecurityEvent
from app.services.aws.session_provider import AwsSessionProvider
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry
from app.utils.parsers import parse_timestamp

logger = logging.getLogger(__name__)


def _is_throttling_error(exception: Exception) -> bool:
    """Helper to determine if a ClientError is a throttling exception that should be retried."""
    if isinstance(exception, ClientError):
        error_code = exception.response.get("Error", {}).get("Code", "Unknown")
        return error_code in (
            "ThrottlingException",
            "RequestLimitExceeded",
            "ProvisionedThroughputExceededException",
        )
    return False


@ConnectorRegistry.register("aws_securityhub")
class AwsSecurityHubConnector(BaseConnector):
    """
    AWS Security Hub Connector for fetching ASFF findings.
    Reuses the centralized AwsSessionProvider for authentication.
    """

    def __init__(
        self,
        account_id: str,
        region: str,
        auth_method: str,
        role_arn: Optional[str] = None,
        external_id: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ):
        self.account_id = account_id
        self.region = region
        self.auth_method = auth_method
        self.role_arn = role_arn
        self.external_id = external_id
        self.access_key = access_key
        self.secret_key = secret_key

        # Security Hub specific filtering criteria passed from configuration
        self.filters = filters or {}

        self.session = None
        self.sh_client = None

    def connect(self) -> bool:
        """
        Initializes the AWS Session and Security Hub client using shared infrastructure.
        """
        try:
            self.session = AwsSessionProvider.get_session(
                auth_method=self.auth_method,
                region=self.region,
                access_key=self.access_key,
                secret_key=self.secret_key,
                role_arn=self.role_arn,
                external_id=self.external_id,
                session_name="SentinelAI_SecurityHub_Connector",
            )
            self.sh_client = self.session.client("securityhub")
            return True
        except Exception as e:
            logger.error("[AwsSecurityHubConnector] Connection failed: %s", str(e))
            return False

    def authenticate(self) -> bool:
        """
        Verifies the authentication state by making a lightweight STS call.
        """
        if not self.session:
            return False
        try:
            sts = self.session.client("sts")
            sts.get_caller_identity()
            return True
        except ClientError as e:
            logger.error("[AwsSecurityHubConnector] Authentication verification failed: %s", str(e))
            return False

    @retry(
        retry=retry_if_exception_type(ClientError) | retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _execute_fetch_page(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single fetch request, handling API Throttling with exponential backoff.
        The @retry decorator will only trigger on matching exceptions.
        """
        try:
            return self.sh_client.get_findings(**kwargs)
        except ClientError as e:
            if _is_throttling_error(e):
                logger.warning("[AwsSecurityHubConnector] API Throttled. Retrying...")
                raise e  # Will be caught by @retry
            # For non-throttling ClientErrors (e.g. ExpiredToken, AccessDenied), raise immediately
            logger.error("[AwsSecurityHubConnector] ClientError during fetch: %s", str(e))
            raise e

    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Fetches ASFF findings from Security Hub using pagination and config-driven filters.
        """
        events = []
        if not self.sh_client:
            raise ValueError(
                "Security Hub Client is not initialized. Call connect() first."
            )

        fetch_kwargs = {}
        if self.filters:
            fetch_kwargs["Filters"] = self.filters

        try:
            next_token = None
            while True:
                if next_token:
                    fetch_kwargs["NextToken"] = next_token

                response = self._execute_fetch_page(fetch_kwargs)

                findings = response.get("Findings", [])
                for finding in findings:
                    events.append(self._build_event(finding))

                next_token = response.get("NextToken")
                if not next_token:
                    break

            if not events:
                logger.info(
                    "[AwsSecurityHubConnector] Fetch completed successfully, but zero findings matched filters."
                )

        except ClientError as e:
            # Handle terminal Auth/Access errors properly
            logger.error("[AwsSecurityHubConnector] Fetch failed due to client error: %s", str(e))
            raise e
        except BotoCoreError as e:
            logger.error("[AwsSecurityHubConnector] Fetch failed due to BotoCore error: %s", str(e))
            raise e
        except Exception as e:
            logger.error("[AwsSecurityHubConnector] Fetch failed: %s", str(e))
            raise e

        return events

    def _build_event(self, asff: Dict[str, Any]) -> SecurityEvent:
        """
        Standardize the ASFF format into a SentinelAI SecurityEvent.
        """
        event_id = asff.get("Id", f"aws-sh-{uuid.uuid4().hex}")

        # ASFF allows multiple types; extract the first/primary one
        types = asff.get("Types", ["Unknown"])
        event_type = types[0] if types else "Unknown"

        # Extract Severity
        severity_obj = asff.get("Severity", {})
        severity = severity_obj.get("Label", "INFO")

        # Extract Timestamp
        timestamp_str = asff.get("UpdatedAt") or asff.get("CreatedAt")
        timestamp = parse_timestamp(timestamp_str)

        # Extract Asset (First Resource ARN)
        resources = asff.get("Resources", [])
        asset = resources[0].get("Id") if resources else self.account_id

        # Identity (Only if Principal/IAM is referenced)
        identity = None
        for res in resources:
            if (
                "iam" in res.get("Id", "")
                or res.get("Type") == "AwsIamUser"
                or res.get("Type") == "AwsIamRole"
            ):
                identity = res.get("Id")
                break

        # Preserve specific ASFF metadata
        metadata = {
            "Compliance": asff.get("Compliance", {}).get("Status"),
            "WorkflowState": asff.get("Workflow", {}).get("Status"),
            "RecordState": asff.get("RecordState"),
            "GeneratorId": asff.get("GeneratorId"),
            "Title": asff.get("Title"),
        }

        return SecurityEvent(
            event_id=event_id,
            source="security_hub",
            vendor="AWS",
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            asset=asset,
            identity=identity,
            raw_payload=asff,
            metadata={k: v for k, v in metadata.items() if v is not None},
        )

    def health_check(self) -> Dict[str, Any]:
        """Validates Security Hub API connectivity."""
        if not self.sh_client:
            raise ValueError("Connector not connected")

        # Lightweight check: get 1 finding
        self.sh_client.get_findings(MaxResults=1)
        return {"status": "ok", "service": "securityhub", "account_id": self.account_id}

    def disconnect(self) -> bool:
        """Cleans up the boto3 session and client."""
        self.session = None
        self.sh_client = None
        return True
