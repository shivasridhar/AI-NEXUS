import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Declarative Mappings ---
CVSS_RANGES = [
    (0.0, "INFO"),
    (4.0, "LOW"),
    (7.0, "MEDIUM"),
    (9.0, "HIGH"),
    (10.0, "CRITICAL")
]

def parse_timestamp(timestamp_str: Optional[str]) -> datetime:
    """
    Consistently parses ISO timestamps.
    Falls back to current UTC time if no timestamp is provided or if parsing fails.
    """
    if timestamp_str:
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning(f"[Parser] Failed to parse timestamp: {timestamp_str}. Using current UTC.")
            pass
    return datetime.now(timezone.utc)

def filter_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively removes None values from a dictionary."""
    return {
        k: (filter_none_values(v) if isinstance(v, dict) else v)
        for k, v in data.items()
        if v is not None
    }

def map_cvss_score(score: float) -> str:
    """Maps CVSS base score to SecurityEvent severity string band."""
    for bound, label in CVSS_RANGES:
        # We assume bounds are the UPPER exclusive limit for ranges,
        # Except 10.0 which includes 10.0 and above.
        if bound == 10.0 or score < bound:
            return label
    return "CRITICAL"
