"""
Configuration module for Suricata Forwarder.
"""
import logging

EVE_JSON_PATH = "/var/log/suricata/eve.json"
LOG_LEVEL = logging.INFO

# Target URL for the sender (to be implemented later)
DESTINATION_URL = "http://localhost:8000/api/v1/ingestion/suricata"
