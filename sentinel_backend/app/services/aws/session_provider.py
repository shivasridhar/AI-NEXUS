import boto3
import logging
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AwsSessionProvider:
    """
    Centralized AWS authentication and session provider.
    Reused by all AWS-based connectors (CloudTrail, IAM, Security Hub) to prevent logic duplication.
    """
    @staticmethod
    def get_session(
        auth_method: str,
        region: str,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        role_arn: Optional[str] = None,
        external_id: Optional[str] = None,
        session_name: str = "SentinelAI_Session"
    ) -> boto3.Session:
        try:
            if auth_method == "access_key":
                if not access_key or not secret_key:
                    raise ValueError("Access Key ID and Secret Access Key must be provided for 'access_key' auth method.")
                return boto3.Session(
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key
                )
            elif auth_method == "role_arn":
                if not role_arn:
                    raise ValueError("Role ARN must be provided for 'role_arn' auth method.")
                
                sts_client = boto3.client('sts', region_name=region)
                assume_kwargs = {
                    "RoleArn": role_arn,
                    "RoleSessionName": session_name
                }
                # Add External ID if provided — prevents confused deputy attacks
                if external_id:
                    assume_kwargs["ExternalId"] = external_id
                
                assumed_role = sts_client.assume_role(**assume_kwargs)
                credentials = assumed_role['Credentials']
                
                return boto3.Session(
                    region_name=region,
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
            else:
                raise ValueError(f"Unsupported auth_method: {auth_method}")
        except ClientError as e:
            logger.error("Failed to create AWS Session: %s", str(e))
            raise ValueError(f"AWS Authentication failed: {str(e)}") from e
