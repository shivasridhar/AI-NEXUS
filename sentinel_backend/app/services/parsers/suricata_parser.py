import logging
from typing import List, Any
import uuid
from pydantic import ValidationError

from app.schemas.canonical_event import CanonicalEventSchema
from app.services.parsers.base import BaseEventParser
from app.services.utils.time_utils import normalize_timestamp_utc
from app.services.utils.entity_resolution import resolve_actor_identifier

logger = logging.getLogger(__name__)

class SuricataParser(BaseEventParser):
    def parse(self, data: Any, workspace_id: uuid.UUID) -> List[CanonicalEventSchema]:
        """
        Parses Suricata EVE JSON data into CanonicalEvent representations.
        """
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                raise ValueError("Expected list or dict for Suricata data")
                
        canonical_events = []
        for idx, record in enumerate(data):
            if not isinstance(record, dict):
                logger.warning(f"Suricata record at index {idx} is not a dict. Skipping.")
                continue
                
            try:
                timestamp_raw = record.get("timestamp")
                if not timestamp_raw:
                    logger.warning(f"Missing timestamp in Suricata record index {idx}. Skipping.")
                    continue
                    
                timestamp_utc = normalize_timestamp_utc(timestamp_raw)
                
                # Suricata severity is typically 1 (High) to 4 (Low) in alert.severity
                alert = record.get("alert", {})
                severity_raw = str(alert.get("severity", ""))
                
                # Map 1-4 to 0-100 (1=High -> 90, 2=Medium -> 60, 3=Low -> 30, 4=Info -> 10)
                severity_normalized = 0
                if severity_raw == "1":
                    severity_normalized = 90
                elif severity_raw == "2":
                    severity_normalized = 60
                elif severity_raw == "3":
                    severity_normalized = 30
                elif severity_raw == "4":
                    severity_normalized = 10
                
                raw_actor = record.get("src_ip")
                actor_identifier = resolve_actor_identifier(raw_actor, "suricata") if raw_actor else None
                
                asset_identifier = record.get("dest_ip")
                     
                event = CanonicalEventSchema(
                    source_tool="suricata",
                    event_type=alert.get("signature", record.get("event_type", "Suricata Alert")),
                    severity_raw=severity_raw,
                    severity_normalized=severity_normalized,
                    timestamp_utc=timestamp_utc,
                    actor_identifier=actor_identifier,
                    asset_identifier=asset_identifier,
                    raw_event_json=record,
                    workspace_id=workspace_id,
                    linked_access_log_id=None
                )
                canonical_events.append(event)
            except ValidationError as e:
                logger.warning(f"Validation failed for Suricata event index {idx}: {str(e)}. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error parsing Suricata event index {idx}: {str(e)}. Skipping.")
                continue
                
        return canonical_events
