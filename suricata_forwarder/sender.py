"""
Sender module for dispatching normalized events.
Currently acts as a stub (prints to stdout).
"""
import logging
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)

class EventSender:
    """Sends normalized events to the configured destination."""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        
    def send(self, event: Dict[str, Any]) -> None:
        """
        Sends the normalized event.
        Currently prints to stdout as a stub.
        Designed for easy addition of HTTP POST in the future.
        """
        # For Phase 2, we just print the event.
        # Future implementation:
        # try:
        #     response = requests.post(self.target_url, json=event)
        #     response.raise_for_status()
        # except requests.RequestException as e:
        #     logger.error(f"Failed to send event: {e}")
        
        logger.info("--- Sending Event ---")
        # Removing the original_event from output to keep it concise on stdout
        output_event = {k: v for k, v in event.items() if k != "original_event"}
        print(json.dumps(output_event, indent=2))
        logger.info("---------------------")
