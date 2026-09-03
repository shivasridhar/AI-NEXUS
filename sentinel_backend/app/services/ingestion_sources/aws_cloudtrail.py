import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.services.ingestion_sources.base import IngestionSource

logger = logging.getLogger(__name__)

class AwsCloudTrailSource(IngestionSource):
    """
    Ingestion source for live AWS CloudTrail fetching via API.
    Supports both IAM User (access key) and IAM Role (AssumeRole with optional External ID) authentication.
    """
    def __init__(self, 
                 account_id: str, 
                 region: str, 
                 auth_method: str, 
                 role_arn: Optional[str] = None,
                 external_id: Optional[str] = None,
                 access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None,
                 start_time: Optional[datetime] = None):
        self.account_id = account_id
        self.region = region
        self.auth_method = auth_method
        self.role_arn = role_arn
        self.external_id = external_id
        self.access_key = access_key
        self.secret_key = secret_key
        self.start_time = start_time
        
        self.client = self._create_client()

    def _create_client(self):
        from app.services.aws.session_provider import AwsSessionProvider
        try:
            session = AwsSessionProvider.get_session(
                auth_method=self.auth_method,
                region=self.region,
                access_key=self.access_key,
                secret_key=self.secret_key,
                role_arn=self.role_arn,
                external_id=self.external_id,
                session_name="SentinelAI_CloudTrailSync"
            )
            return session.client('cloudtrail')
        except Exception as e:
            logger.error("Failed to create AWS CloudTrail client: %s", str(e))
            raise ValueError(f"AWS Authentication failed: {str(e)}") from e

    def fetch_events(self) -> Dict[str, Any]:
        """
        Fetches events from CloudTrail LookupEvents API with pagination.
        Returns a normalized {Records: [...]} structure for the ingestion pipeline.
        """
        records = []
        kwargs: Dict[str, Any] = {}
        if self.start_time:
            kwargs['StartTime'] = self.start_time

        try:
            paginator = self.client.get_paginator('lookup_events')
            for page in paginator.paginate(**kwargs):
                for event in page.get('Events', []):
                    cloudtrail_event_str = event.get('CloudTrailEvent')
                    if cloudtrail_event_str:
                        try:
                            event_data = json.loads(cloudtrail_event_str)
                            records.append(event_data)
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse CloudTrailEvent JSON: %s", cloudtrail_event_str[:100])

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ThrottlingException':
                raise ValueError("AWS CloudTrail API is being throttled. Please try again later.")
            raise ValueError(f"AWS API Error during fetch: {str(e)}")
        except Exception as e:
            raise ValueError(f"Unexpected error fetching CloudTrail events: {str(e)}")

        return {"Records": records}

    def get_source_metadata(self) -> Dict[str, Any]:
        return {
            "sourceType": "AwsCloudTrail",
            "identifier": f"{self.account_id}:{self.region}"
        }
