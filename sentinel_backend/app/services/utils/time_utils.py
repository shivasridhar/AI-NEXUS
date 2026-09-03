from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def normalize_timestamp_utc(time_str: str) -> datetime:
    """
    Normalizes a timestamp string to a UTC datetime object.
    Handles 'Z' suffixes and standard ISO 8601 formats.
    """
    try:
        if isinstance(time_str, str):
            # Replace 'Z' with UTC offset to parse correctly
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        elif isinstance(time_str, datetime):
            return time_str
    except ValueError as e:
        logger.warning("Invalid timestamp format: %s", time_str)
        raise ValueError(f"Invalid timestamp format: {time_str}") from e
    
    raise TypeError(f"Expected string or datetime, got {type(time_str)}")
