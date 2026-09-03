import logging
from typing import List, Any
import uuid
from pydantic import ValidationError

from app.schemas.canonical_event import CanonicalEventSchema
from app.services.parsers.base import BaseEventParser
from app.services.utils.time_utils import normalize_timestamp_utc
from app.services.severity_normalization import normalize_openvas_severity

logger = logging.getLogger(__name__)

class OpenVASParser(BaseEventParser):
    def parse(self, data: Any, workspace_id: uuid.UUID) -> List[CanonicalEventSchema]:
        """
        Parses OpenVAS report data into CanonicalEvent representations.
        """
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                raise ValueError("Expected list or dict for OpenVAS data")
                
        canonical_events = []
        for idx, record in enumerate(data):
            if not isinstance(record, dict):
                logger.warning(f"OpenVAS record at index {idx} is not a dict. Skipping.")
                continue
                
            try:
                timestamp_raw = record.get("creation_time") or record.get("timestamp")
                if not timestamp_raw:
                    logger.warning(f"Missing timestamp in OpenVAS record index {idx}. Skipping.")
                    continue
                    
                timestamp_utc = normalize_timestamp_utc(timestamp_raw)
                
                severity_raw = record.get("threat", "Log")
                severity_normalized = normalize_openvas_severity(severity_raw)
                
                # Vulnerability scanners don't have actors in the traditional sense,
                # but they target assets.
                host = record.get("host", {})
                asset_identifier = host.get("asset_id") or host.get("ip") or record.get("host")
                if isinstance(asset_identifier, dict):
                     asset_identifier = str(asset_identifier)
                     
                event = CanonicalEventSchema(
                    source_tool="openvas",
                    event_type=record.get("name", "Vulnerability Finding"),
                    severity_raw=severity_raw,
                    severity_normalized=severity_normalized,
                    timestamp_utc=timestamp_utc,
                    actor_identifier=None, # OpenVAS doesn't identify malicious actors, it identifies vulnerabilities
                    asset_identifier=asset_identifier if isinstance(asset_identifier, str) else str(asset_identifier),
                    raw_event_json=record,
                    workspace_id=workspace_id,
                    linked_access_log_id=None
                )
                canonical_events.append(event)
            except ValidationError as e:
                logger.warning(f"Validation failed for OpenVAS event index {idx}: {str(e)}. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error parsing OpenVAS event index {idx}: {str(e)}. Skipping.")
                continue
                
        return canonical_events
