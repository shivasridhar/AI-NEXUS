"""
Parser module for safely converting raw JSON lines into Python dictionaries.
"""
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class EventParser:
    """Parses raw log lines as JSON."""
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Parses a single line of JSON safely.
        Returns the parsed dictionary, or None if the JSON is malformed.
        """
        try:
            # Remove any trailing whitespace/newlines before parsing
            line = line.strip()
            if not line:
                return None
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e} | Line: {line}")
            return None
