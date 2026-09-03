"""
Main entry point for the Suricata Forwarder.
Orchestrates Watcher, Parser, Normalizer, and Sender.
"""
import logging
import sys

from config import EVE_JSON_PATH, LOG_LEVEL, DESTINATION_URL
from watcher import FileWatcher
from parser import EventParser
from normalizer import EventNormalizer
from sender import EventSender

def setup_logging():
    """Configures the root logger."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main():
    """Main execution loop for the forwarder."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Suricata Forwarder...")
    
    watcher = FileWatcher(file_path=EVE_JSON_PATH)
    parser = EventParser()
    normalizer = EventNormalizer()
    sender = EventSender(target_url=DESTINATION_URL)
    
    try:
        for raw_line in watcher.watch():
            # 1. Parse
            parsed_event = parser.parse_line(raw_line)
            if not parsed_event:
                continue
                
            # 2. Normalize
            normalized_event = normalizer.normalize(parsed_event)
            if not normalized_event:
                continue
                
            # 3. Send
            sender.send(normalized_event)
            
    except KeyboardInterrupt:
        logger.info("Suricata Forwarder stopped by user.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
