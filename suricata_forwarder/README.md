# Suricata Forwarder

The Suricata Forwarder is a lightweight agent built using Python to monitor, parse, normalize, and dispatch security events from Suricata's `eve.json` log file.

## Architecture

This project strictly adheres to clean architecture, separating responsibilities into dedicated modules:

- **`config.py`**: Centralized configuration management.
- **`watcher.py`**: Handles file I/O safely. Emulates `tail -f` behavior, ensuring only newly appended lines are read.
- **`parser.py`**: Safely translates raw text lines into JSON objects, completely ignoring malformed entries without crashing.
- **`normalizer.py`**: Converts raw JSON structures into a standard, unified internal dictionary. It currently extracts vital fields from `alert`, `anomaly`, `dns`, and `flow` events.
- **`sender.py`**: The dispatch layer. It is currently a stub that prints normalized data to standard output, engineered for easy future integration with an HTTP POST (e.g., via `requests`).
- **`main.py`**: The orchestrator that integrates the pipeline: `watcher -> parser -> normalizer -> sender`.

## Requirements
- Python 3.8+
- Suricata generating `eve.json` at `/var/log/suricata/eve.json`.

## How to Run Locally

1. **Start the Forwarder**:
   ```bash
   python main.py
   ```
   *Note: If you don't have `/var/log/suricata/eve.json` on your local machine, you will need to create a dummy file for testing, or run this as `sudo` on a machine where Suricata is actively writing logs.*

2. **Testing with a Dummy File (Optional)**:
   - Edit `config.py` and change `EVE_JSON_PATH = "test_eve.json"`.
   - Create `test_eve.json`.
   - Start the forwarder: `python main.py`.
   - In another terminal, append a JSON line to the file:
     ```bash
     echo '{"timestamp": "2026-07-18T10:00:00Z", "event_type": "alert", "src_ip": "192.168.1.10", "dest_ip": "10.0.0.5", "proto": "TCP", "in_iface": "eth0", "alert": {"signature": "Test Alert", "severity": 1}}' >> test_eve.json
     ```
   - Verify the event appears beautifully printed in the terminal running `main.py`.
