"""
Normalizer module for converting Suricata events into a standard format.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EventNormalizer:
    """Normalizes Suricata JSON events into a unified format."""
    
    SUPPORTED_EVENT_TYPES = {"alert", "anomaly", "dns", "flow"}
    
    def normalize(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalizes a parsed Suricata event.
        Extracts key fields: timestamp, src_ip, dest_ip, protocol, interface, event_type.
        """
        event_type = event.get("event_type")
        
        if event_type not in self.SUPPORTED_EVENT_TYPES:
            logger.debug(f"Ignoring unsupported event type: {event_type}")
            return None
            
        try:
            normalized = {
                "timestamp": event.get("timestamp"),
                "src_ip": event.get("src_ip"),
                "dest_ip": event.get("dest_ip"),
                "protocol": event.get("proto"),
                "interface": event.get("in_iface"),
                "event_type": event_type,
                "original_event": event
            }
            
            # Additional extraction based on specific event type
            if event_type == "alert":
                alert_data = event.get("alert", {})
                normalized["alert_signature"] = alert_data.get("signature")
                normalized["alert_severity"] = alert_data.get("severity")
            elif event_type == "dns":
                dns_data = event.get("dns", {})
                normalized["dns_query"] = dns_data.get("rrname")
                normalized["dns_type"] = dns_data.get("type")
            
            return normalized
        except Exception as e:
            logger.error(f"Error during normalization: {e}")
            return None
