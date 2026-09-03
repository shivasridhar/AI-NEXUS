import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas.security_event import SecurityEvent
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry
from app.services.storage.storage_provider import LocalStorageProvider
from app.utils.parsers import parse_timestamp

logger = logging.getLogger(__name__)

SURICATA_SEVERITY_MAP = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM"}

logger = logging.getLogger(__name__)

# --- Event-Type Specific Mapping Implementations ---


def _map_alert(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    alert = payload.get("alert", {})
    severity_val = alert.get("severity", 3)

    # Declarative severity mapping
    severity = SURICATA_SEVERITY_MAP.get(severity_val, "LOW")

    metadata = {
        "signature": alert.get("signature"),
        "signature_id": alert.get("signature_id"),
        "category": alert.get("category"),
        "action": alert.get("action"),
    }

    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="Alert",
        timestamp=timestamp,
        severity=severity,
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_dns(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    dns = payload.get("dns", {})
    metadata = {
        "query_type": dns.get("type"),
        "rrname": dns.get("rrname"),
        "rrtype": dns.get("rrtype"),
        "rcode": dns.get("rcode"),
    }
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="DNS",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_http(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    http = payload.get("http", {})
    metadata = {
        "hostname": http.get("hostname"),
        "url": http.get("url"),
        "http_user_agent": http.get("http_user_agent"),
        "http_method": http.get("http_method"),
        "status": http.get("status"),
    }

    # Try to extract credentials/identity if present in headers (e.g. Authorization basic/bearer)
    identity = None
    # (Checking raw HTTP fields is possible, but we don't fabricate)

    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="HTTP",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        identity=identity,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_tls(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    tls = payload.get("tls", {})
    metadata = {
        "subject": tls.get("subject"),
        "issuerdn": tls.get("issuerdn"),
        "sni": tls.get("sni"),
        "version": tls.get("version"),
    }
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="TLS",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_ssh(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    ssh = payload.get("ssh", {})
    metadata = {
        "client_proto": ssh.get("client", {}).get("proto_version"),
        "client_software": ssh.get("client", {}).get("software_version"),
        "server_proto": ssh.get("server", {}).get("proto_version"),
        "server_software": ssh.get("server", {}).get("software_version"),
    }
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="SSH",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_flow(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    flow = payload.get("flow", {})
    metadata = {
        "pkts_toserver": flow.get("pkts_toserver"),
        "pkts_toclient": flow.get("pkts_toclient"),
        "bytes_toserver": flow.get("bytes_toserver"),
        "bytes_toclient": flow.get("bytes_toclient"),
        "reason": flow.get("reason"),
        "age": flow.get("age"),
    }
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="Flow",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_file(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    fileinfo = payload.get("fileinfo", {})
    metadata = {
        "filename": fileinfo.get("filename"),
        "gaps": fileinfo.get("gaps"),
        "state": fileinfo.get("state"),
        "size": fileinfo.get("size"),
        "tx_id": fileinfo.get("tx_id"),
    }
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="File",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_smb(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    smb = payload.get("smb", {})
    metadata = {
        "command": smb.get("command"),
        "filename": smb.get("filename"),
        "share": smb.get("share"),
        "dialect": smb.get("dialect"),
    }

    # Map identity if domain/username is present in SMB headers
    identity = None
    domain = smb.get("domain")
    username = smb.get("username")
    if username:
        identity = f"{domain}\\{username}" if domain else username

    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type="SMB",
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        identity=identity,
        raw_payload=payload,
        metadata=metadata,
    )


def _map_fallback(
    payload: Dict[str, Any], event_id: str, timestamp: datetime, asset: str
) -> SecurityEvent:
    """Fallback mapper for any unexpected event types."""
    event_type = payload.get("event_type", "generic").upper()
    return SecurityEvent(
        event_id=event_id,
        source="suricata_eve",
        vendor="suricata",
        event_type=event_type,
        timestamp=timestamp,
        severity="INFO",
        asset=asset,
        raw_payload=payload,
        metadata={},
    )


# Dynamic dispatch registry for Suricata event types
_MAPPER_REGISTRY = {
    "alert": _map_alert,
    "dns": _map_dns,
    "http": _map_http,
    "tls": _map_tls,
    "ssh": _map_ssh,
    "flow": _map_flow,
    "fileinfo": _map_file,
    "smb": _map_smb,
}


@ConnectorRegistry.register("suricata")
class SuricataConnector(BaseConnector):
    """
    Suricata EVE JSON file connector.
    Tails eve.json incrementally, handles log rotation natively,
    and dispatches parsed JSON lines through a dynamic event mapper registry.
    """

    def __init__(
        self,
        file_path: str,
        max_bytes_per_poll: int = 10 * 1024 * 1024,  # Default to 10MB per fetch loop
        fresh_start: bool = False,
    ):
        self.file_path = file_path
        self.max_bytes_per_poll = max_bytes_per_poll
        self.fresh_start = fresh_start

        self.storage = LocalStorageProvider()
        self.state_file_path = (
            f"connectors/suricata/{hashlib.md5(file_path.encode()).hexdigest()}.json"
        )

        self.offset = 0
        self.inode = 0
        self._is_ready = False

        # Validate configuration early
        if not self.file_path:
            raise ValueError("[SuricataConnector] File path is required in config.")

    def connect(self) -> bool:
        """
        Init/validation step. Verifies the log file exists and is readable.
        """
        path = Path(self.file_path)
        if not path.exists():
            logger.error("[SuricataConnector] Log file does not exist: %s", self.file_path)
            return False
        if not os.access(self.file_path, os.R_OK):
            logger.error("[SuricataConnector] Log file exists but is not readable: %s", self.file_path)
            return False

        self._is_ready = True
        self._load_cursor()
        return True

    def authenticate(self) -> bool:
        """
        Secondary validation step. Checks file permissions and reads a byte to confirm access.
        """
        if not self._is_ready:
            return False
        try:
            with open(self.file_path, "rb") as f:
                f.read(1)
            return True
        except IOError as e:
            logger.error("[SuricataConnector] Accessibility validation failed: %s", str(e))
            return False

    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Main incremental log poll.
        Checks for log rotation, handles truncation, processes up to max_bytes_per_poll,
        and saves updated cursor offset.
        """
        if not self._is_ready:
            raise ValueError("Connector is not connected. Call connect() first.")

        events: List[SecurityEvent] = []

        try:
            stat = os.stat(self.file_path)
        except OSError as e:
            logger.error("[SuricataConnector] Failed to access stat on file {self.file_path}: %s", str(e))
            raise e

        current_size = stat.st_size
        current_inode = stat.st_ino

        # Detect log rotation or truncation
        if current_inode != self.inode:
            logger.warning(
                f"[SuricataConnector] Log rotation detected! Inode changed from {self.inode} to {current_inode}. Resetting offset."
            )
            self.offset = 0
            self.inode = current_inode
        elif current_size < self.offset:
            logger.warning(
                f"[SuricataConnector] Log file truncation detected! Size ({current_size}) is smaller than offset ({self.offset}). Resetting offset."
            )
            self.offset = 0

        # Calculate bytes to read in this chunk
        bytes_to_read = min(current_size - self.offset, self.max_bytes_per_poll)
        if bytes_to_read <= 0:
            return events

        bytes_read = 0
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.offset)

                # Stream lines
                while bytes_read < bytes_to_read:
                    line = f.readline()
                    if not line:
                        break  # EOF reached early

                    bytes_read += len(line.encode("utf-8"))

                    # Ensure we don't process a trailing partial line at EOF
                    if (
                        not line.endswith("\n")
                        and (self.offset + bytes_read) == current_size
                    ):
                        # Revert the offset addition of this line so we read it next poll cycle
                        bytes_read -= len(line.encode("utf-8"))
                        break

                    parsed_event = self._parse_line(line)
                    if parsed_event:
                        events.append(parsed_event)
                        logger.info(
                            f"[SuricataConnector] Parsed event_id={parsed_event.event_id} "
                            f"vendor={parsed_event.vendor} source={parsed_event.source}"
                        )

            # Update offset and persist state
            self.offset += bytes_read
            self._save_cursor()

            logger.info(
                f"[SuricataConnector] Successfully read {bytes_read} bytes. Processed {len(events)} events."
            )

        except Exception as e:
            logger.error("[SuricataConnector] Failed during event read loop: %s", str(e))
            raise e

        return events

    def _parse_line(self, line: str) -> Optional[SecurityEvent]:
        """
        Parses a single JSON line and dispatches it to the correct mapper.
        Returns None on corrupted lines or parse failures.
        """
        stripped = line.strip()
        if not stripped:
            return None

        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            logger.warning("[SuricataConnector] Corrupted JSON line skipped.")
            return None

        # Standard baseline values
        event_id = payload.get("flow_id")
        if event_id:
            event_id = f"suricata-{event_id}"
        else:
            event_id = f"suricata-{uuid.uuid4().hex}"

        try:
            timestamp_str = payload.get("timestamp")
            timestamp = parse_timestamp(timestamp_str)
        except (ValueError, TypeError):
            timestamp = datetime.now(timezone.utc)

        # Asset is src/dest IP + ports in metadata
        src_ip = payload.get("src_ip", "0.0.0.0")
        dest_ip = payload.get("dest_ip", "0.0.0.0")
        asset = f"{src_ip} -> {dest_ip}"

        # Resolve mapper dynamically using the dispatch registry
        event_type = payload.get("event_type", "generic").lower()
        mapper = _MAPPER_REGISTRY.get(event_type, _map_fallback)

        try:
            event = mapper(payload, event_id, timestamp, asset)

            # Enrich common metadata
            event.metadata["proto"] = payload.get("proto")
            event.metadata["src_port"] = payload.get("src_port")
            event.metadata["dest_port"] = payload.get("dest_port")
            event.metadata["flow_id"] = payload.get("flow_id")
            event.metadata["in_iface"] = payload.get("in_iface")

            return event
        except Exception as e:
            logger.warning("[SuricataConnector] Failed mapping event type '{event_type}': %s", str(e))
            return None

    def health_check(self) -> Dict[str, Any]:
        """
        Checks log path visibility and size.
        """
        path = Path(self.file_path)
        if not path.exists():
            return {"status": "error", "message": "Log file path does not exist."}
        if not os.access(self.file_path, os.R_OK):
            return {
                "status": "error",
                "message": "Log file exists but is not readable.",
            }

        return {
            "status": "ok",
            "file": self.file_path,
            "size_bytes": path.stat().st_size,
            "current_offset": self.offset,
        }

    def disconnect(self) -> bool:
        """Cleanup handler."""
        self._is_ready = False
        return True

    # --- Cursor Persistence Functions ---

    def _load_cursor(self):
        """Loads cursor state from persistent LocalStorageProvider."""
        if self.fresh_start:
            logger.info(
                "[SuricataConnector] Fresh start requested. Ignoring persisted cursor."
            )
            self.offset = 0
            try:
                stat = os.stat(self.file_path)
                self.inode = stat.st_ino
            except OSError:
                self.inode = 0
            return

        try:
            content = self.storage.get(self.state_file_path)
            state = json.loads(content.decode("utf-8"))
            self.offset = state.get("offset", 0)
            self.inode = state.get("inode", 0)
            logger.info(
                f"[SuricataConnector] Loaded cursor state: Inode={self.inode}, Offset={self.offset}"
            )
        except FileNotFoundError:
            # First time initialized
            logger.info(
                "[SuricataConnector] No persisted cursor found. Initializing cursor from 0."
            )
            self.offset = 0
            try:
                stat = os.stat(self.file_path)
                self.inode = stat.st_ino
            except OSError:
                self.inode = 0
        except Exception as e:
            logger.error(
                f"[SuricataConnector] Failed to load cursor state: {str(e)}. Defaulting to offset 0."
            )
            self.offset = 0
            self.inode = 0

    def _save_cursor(self):
        """Saves cursor state to persistent LocalStorageProvider."""
        state = {
            "offset": self.offset,
            "inode": self.inode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.storage.save(self.state_file_path, json.dumps(state))
        except Exception as e:
            logger.error("[SuricataConnector] Failed to save cursor state: %s", str(e))
