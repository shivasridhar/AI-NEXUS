"""
Watcher module for monitoring the Suricata eve.json log file.
"""
import os
import time
import logging
from typing import Iterator

logger = logging.getLogger(__name__)

class FileWatcher:
    """Monitors a file and yields new lines as they are appended (like tail -f)."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path

    def watch(self) -> Iterator[str]:
        """
        Yields new lines from the monitored file.
        Starts reading from the end of the file.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"File not found: {self.file_path}")
            # Wait for file to exist
            while not os.path.exists(self.file_path):
                time.sleep(1)
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            # Seek to the end of the file
            f.seek(0, os.SEEK_END)
            logger.info(f"Started monitoring {self.file_path} from the end of file.")
            
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                yield line
