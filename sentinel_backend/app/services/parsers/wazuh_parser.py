import logging
from typing import List, Any
import uuid
from pydantic import ValidationError

from app.schemas.canonical_event import CanonicalEventSchema
from app.services.parsers.base import BaseEventParser
from app.services.utils.time_utils import normalize_timestamp_utc
from app.services.utils.entity_resolution import resolve_actor_identifier
from app.services.severity_normalization import normalize_wazuh_severity

logger = logging.getLogger(__name__)

class WazuhParser(BaseEventParser):
    def parse(self, data: Any, workspace_id: uuid.UUID) -> List[CanonicalEventSchema]:
        """
        Parses Wazuh alert data into CanonicalEvent representations.
        """
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                raise ValueError("Expected list or dict for Wazuh data")
                
        canonical_events = []
        for idx, record in enumerate(data):
            if not isinstance(record, dict):
                logger.warning(f"Wazuh record at index {idx} is not a valid JSON object. Skipping.")
                continue
                
            try:
                # Extract fields with defaults/fallbacks
                timestamp_raw = record.get("timestamp")
                if not timestamp_raw:
                    logger.warning(f"Missing timestamp in Wazuh record index {idx}. Skipping.")
                    continue
                    
                timestamp_utc = normalize_timestamp_utc(timestamp_raw)
                
                # Rule extraction
                rule = record.get("rule", {})
                severity_raw = str(rule.get("level", 0))
                severity_normalized = normalize_wazuh_severity(rule.get("level", 0))
                
                # Actor extraction (e.g., from agent or data)
                agent = record.get("agent", {})
                raw_actor = agent.get("name") or agent.get("ip") or record.get("data", {}).get("srcip")
                actor_identifier = resolve_actor_identifier(raw_actor, "wazuh")
                
                # Asset extraction
                asset_identifier = agent.get("id")
                
                event = CanonicalEventSchema(
                    source_tool="wazuh",
                    event_type=rule.get("description", "Unknown Wazuh Event"),
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
                logger.warning(f"Validation failed for Wazuh event index {idx}: {str(e)}. Skipping.")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error parsing Wazuh event index {idx}: {str(e)}. Skipping.")
                continue
                
        return canonical_events
