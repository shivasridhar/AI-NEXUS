import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from app.schemas.security_event import SecurityEvent
from app.services.aws.session_provider import AwsSessionProvider
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry

logger = logging.getLogger(__name__)


@ConnectorRegistry.register("aws_iam")
class AwsIamConnector(BaseConnector):
    """
    AWS IAM Connector for fetching IAM users, roles, policies, and trust relationships.
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
    ):
        self.account_id = account_id
        self.region = region
        self.auth_method = auth_method
        self.role_arn = role_arn
        self.external_id = external_id
        self.access_key = access_key
        self.secret_key = secret_key

        self.session = None
        self.iam_client = None

    def connect(self) -> bool:
        """
        Initializes the AWS Session and IAM client.
        """
        try:
            self.session = AwsSessionProvider.get_session(
                auth_method=self.auth_method,
                region=self.region,
                access_key=self.access_key,
                secret_key=self.secret_key,
                role_arn=self.role_arn,
                external_id=self.external_id,
                session_name="SentinelAI_IAM_Connector",
            )
            self.iam_client = self.session.client("iam")
            return True
        except Exception as e:
            logger.error("[AwsIamConnector] Connection failed: %s", str(e))
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
            logger.error("[AwsIamConnector] Authentication verification failed: %s", str(e))
            return False

    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Discovers IAM Users, Roles, attached policies, permission boundaries,
        and trust relationships, and maps them to SecurityEvent objects.
        """
        events = []
        if not self.iam_client:
            raise ValueError("IAM Client is not initialized. Call connect() first.")

        try:
            # 1. Discover IAM Users
            user_paginator = self.iam_client.get_paginator("list_users")
            for page in user_paginator.paginate():
                for user in page.get("Users", []):
                    policies = self._get_user_policies(user["UserName"])
                    boundary = self._get_user_boundary(user)

                    events.append(
                        self._build_event(
                            event_type="IAMUserDiscovery",
                            raw_item=user,
                            extra_metadata={
                                "AttachedPolicies": policies,
                                "PermissionsBoundary": boundary,
                            },
                            identity=user["Arn"],
                        )
                    )

            # 2. Discover IAM Roles
            role_paginator = self.iam_client.get_paginator("list_roles")
            for page in role_paginator.paginate():
                for role in page.get("Roles", []):
                    # Reduce noise by optionally skipping AWS service-linked roles
                    if "aws-service-role" in role.get("Arn", ""):
                        continue

                    policies = self._get_role_policies(role["RoleName"])
                    boundary = self._get_role_boundary(role)
                    trust_policy = role.get("AssumeRolePolicyDocument", {})

                    events.append(
                        self._build_event(
                            event_type="IAMRoleDiscovery",
                            raw_item=role,
                            extra_metadata={
                                "AttachedPolicies": policies,
                                "PermissionsBoundary": boundary,
                                "TrustRelationship": trust_policy,
                            },
                            identity=role["Arn"],
                        )
                    )

        except Exception as e:
            logger.error("[AwsIamConnector] Fetch failed: %s", str(e))
            raise

        return events

    def _get_user_policies(self, user_name: str) -> List[str]:
        """Fetch attached managed policies for a specific user."""
        try:
            resp = self.iam_client.list_attached_user_policies(UserName=user_name)
            return [p["PolicyArn"] for p in resp.get("AttachedPolicies", [])]
        except ClientError as e:
            logger.warning("Could not fetch policies for user {user_name}: %s", str(e))
            return []

    def _get_user_boundary(self, user: Dict[str, Any]) -> Optional[str]:
        """Extract the permissions boundary ARN if it exists."""
        return user.get("PermissionsBoundary", {}).get("PermissionsBoundaryArn")

    def _get_role_policies(self, role_name: str) -> List[str]:
        """Fetch attached managed policies for a specific role."""
        try:
            resp = self.iam_client.list_attached_role_policies(RoleName=role_name)
            return [p["PolicyArn"] for p in resp.get("AttachedPolicies", [])]
        except ClientError as e:
            logger.warning("Could not fetch policies for role {role_name}: %s", str(e))
            return []

    def _get_role_boundary(self, role: Dict[str, Any]) -> Optional[str]:
        """Extract the permissions boundary ARN if it exists."""
        return role.get("PermissionsBoundary", {}).get("PermissionsBoundaryArn")

    def _build_event(
        self, event_type: str, raw_item: dict, extra_metadata: dict, identity: str
    ) -> SecurityEvent:
        """Standardize the AWS IAM entity into a SentinelAI SecurityEvent."""
        return SecurityEvent(
            event_id=f"aws-iam-{uuid.uuid4().hex}",
            source="aws-iam-api",
            vendor="AWS",
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            severity="INFO",  # Discovery events are INFO; the Risk Engine will escalate if necessary
            asset=self.account_id,
            identity=identity,
            raw_payload=raw_item,
            metadata=extra_metadata,
        )

    def health_check(self) -> Dict[str, Any]:
        """Validates IAM API connectivity via a lightweight call."""
        if not self.iam_client:
            raise ValueError("Connector not connected")
        self.iam_client.get_account_authorization_details(Filter=["User"], MaxItems=1)
        return {"status": "ok", "service": "iam", "account_id": self.account_id}

    def disconnect(self) -> bool:
        """Cleans up the boto3 session and client."""
        self.session = None
        self.iam_client = None
        return True
