from typing import List, Dict, Any
from app.schemas.cloudtrail import CloudTrailEvent, CloudTrailLogFile
from pydantic import ValidationError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CloudTrailParser:
    @staticmethod
    def normalize_json(json_data: Any) -> Dict[str, Any]:
        """
        Normalizes various CloudTrail log structures into the standard {"Records": [...]} wrapper.
        """
        # 1. Array of events
        if isinstance(json_data, list):
            return {"Records": json_data}

        if not isinstance(json_data, dict):
            raise ValueError("Unsupported CloudTrail format. Expected JSON object or list.")

        # Case-insensitive check for wrapper keys like Records, records, Events, events
        keys_lower = {k.lower(): k for k in json_data.keys()}
        
        for wrapper in ["records", "events"]:
            if wrapper in keys_lower:
                original_key = keys_lower[wrapper]
                records_list = json_data[original_key]
                if not isinstance(records_list, list):
                    raise ValueError(f"Unsupported CloudTrail format. Expected a list under key '{original_key}'.")
                return {"Records": records_list}

        # 2. Single Event History JSON
        # Detect if it contains typical CloudTrail keys directly at the root
        if "eventID" in json_data or "eventTime" in json_data or "eventName" in json_data:
            return {"Records": [json_data]}

        raise ValueError("Unsupported CloudTrail format. Expected CloudTrail event or Records array.")

    @staticmethod
    def parse_log_file(json_data: Dict[str, Any]) -> List[CloudTrailEvent]:
        """Parses a complete normalized CloudTrail log file JSON into Pydantic models."""
        normalized = CloudTrailParser.normalize_json(json_data)
        
        records = normalized.get("Records", [])

        validated_events = []
        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                logger.warning(f"Record at index {idx} is not a valid JSON object. Skipping.")
                continue
            if "eventID" not in record or not record["eventID"]:
                logger.warning("Missing eventID in record. Skipping.")
                continue
            if "eventTime" not in record or not record["eventTime"]:
                logger.warning("Missing eventTime in record. Skipping.")
                continue
            
            # Verify timestamp format
            try:
                from app.services.utils.time_utils import normalize_timestamp_utc
                normalize_timestamp_utc(record["eventTime"])
            except Exception:
                logger.warning(f"Invalid timestamp in record: {record['eventTime']}. Skipping.")
                continue

            try:
                event_model = CloudTrailEvent(**record)
                validated_events.append(event_model)
            except ValidationError as e:
                # Map standard validation errors to user-friendly messages
                logger.warning(f"Validation failed for event {record.get('eventID')}: {str(e)}. Skipping.")
                continue

        if not validated_events and records:
            raise ValueError("Unsupported CloudTrail format. All records failed validation.")

        return validated_events

    @staticmethod
    def extract_access_log_data(event: CloudTrailEvent) -> Dict[str, Any]:
        """Extracts the specific fields required for the AccessLog model."""
        # Extract resource ARN safely
        resource_arn = None
        if event.resources and len(event.resources) > 0:
            resource_arn = event.resources[0].ARN
        elif hasattr(event, "requestParameters") and event.requestParameters:
            params = event.requestParameters
            if isinstance(params, dict):
                # Try to extract common ARN fields for IAM and other resources
                resource_arn = params.get("policyArn") or params.get("roleArn") or params.get("resourceArn")
                if not resource_arn and params.get("roleName"):
                    # Mock an ARN if only roleName is provided
                    account = (
                                event.recipientAccountId
                                or event.userIdentity.accountId
                                or "unknown"
                            )
                    resource_arn = f"arn:aws:iam::{account}:role/{params.get('roleName')}"
            
        # Generate synthetic ARN if missing (common for AWS service-generated events)
        identity_arn = "unknown"
        if event.userIdentity and event.userIdentity.arn:
            identity_arn = event.userIdentity.arn
        elif event.userIdentity and event.userIdentity.invokedBy:
            account = (
                        event.recipientAccountId
                        or event.userIdentity.accountId
                        or "unknown"
                    )
            identity_arn = f"arn:aws:iam::{account}:service/{event.userIdentity.invokedBy}"
            
        return {
            "event_id": event.eventID,
            "event_time": event.eventTime,
            "event_name": event.eventName,
            "event_source": event.eventSource,
            "aws_region": event.awsRegion,
            "source_ip": event.sourceIPAddress,
            "identity_arn": identity_arn,
            "resource_arn": resource_arn,
            "account_id": (
                            event.recipientAccountId
                            or event.userIdentity.accountId
                            or "unknown"
                            ),    
            "raw_event_json": event.model_dump(mode='json')
        }
