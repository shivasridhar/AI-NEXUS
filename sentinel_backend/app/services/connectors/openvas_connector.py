import hashlib
import json
import logging
import socket
import ssl
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.schemas.security_event import SecurityEvent
from app.services.connectors.base_connector import BaseConnector
from app.services.connectors.connector_registry import ConnectorRegistry
from app.services.storage.storage_provider import LocalStorageProvider
from app.utils.parsers import map_cvss_score, parse_timestamp

logger = logging.getLogger(__name__)


# --- Standard Severity Normalization band mapping ---
def _cvss_score_to_label(score: float) -> str:
    """Maps CVSS base score directly to SecurityEvent severity string bands."""
    return map_cvss_score(score)


class GMPConnectionError(Exception):
    """Raised when socket or SSL connection fails."""


class GMPProtocolError(Exception):
    """Raised when GVM returns a non-2xx status code or malformed GMP response."""


import io


class SocketStreamWrapper(io.RawIOBase):
    """
    Wraps a socket stream to act as a file-like reader that yields data
    until a specific closing XML tag is matched, indicating EOF for that command.
    Prevents reading the entire command response into memory.
    """

    def __init__(self, sock: socket.socket, closing_tag: bytes):
        self.sock = sock
        self.closing_tag = closing_tag
        self.buffer = b""
        self.eof_reached = False

    def readable(self) -> bool:
        return True

    def readinto(self, b: bytearray) -> int:
        if self.eof_reached:
            return 0

        # Read from socket if buffer doesn't have the closing tag yet
        if self.closing_tag not in self.buffer:
            try:
                data = self.sock.recv(8192)
                if not data:
                    self.eof_reached = True
                    if not self.buffer:
                        return 0
                else:
                    self.buffer += data
            except Exception as e:
                logger.error("[SocketStreamWrapper] Socket read error: %s", str(e))
                self.eof_reached = True
                if not self.buffer:
                    return 0

        # Check if closing tag is now present
        tag_index = self.buffer.find(self.closing_tag)
        if tag_index != -1:
            end_pos = tag_index + len(self.closing_tag)
            chunk = self.buffer[:end_pos]
            self.buffer = self.buffer[end_pos:]
            self.eof_reached = True
        else:
            chunk = self.buffer
            self.buffer = b""

        n = len(chunk)
        b[:n] = chunk
        return n


# --- Internal Seam: Decoupled GMP Transport Layer ---
class GMPTransport:
    """
    Handles raw TCP/TLS or Unix socket communication for Greenbone Management Protocol (GMP).
    Separates network transmission logic from XML parsing and normalization.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 9390,
        socket_path: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.socket_path = socket_path
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def connect(self):
        """Establishes either a TLS TCP socket or a Unix socket."""
        try:
            if self.socket_path:
                # Unix socket connection
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect(self.socket_path)
                logger.info("[GMPTransport] Connected to gvmd via Unix socket: %s", self.socket_path)
            elif self.host:
                # TLS TCP connection
                plain_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                plain_sock.settimeout(self.timeout)

                context = ssl.create_default_context()
                if not self.verify_ssl:
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE

                self.sock = context.wrap_socket(plain_sock, server_hostname=self.host)
                self.sock.connect((self.host, self.port))
                logger.info("[GMPTransport] Connected to gvmd via TLS TCP: {self.host}: %s", self.port)
            else:
                raise ValueError(
                    "Must configure either host or socket_path for OpenVAS GMP connection."
                )
        except Exception as e:
            logger.error("[GMPTransport] Connection setup failed: %s", str(e))
            raise GMPConnectionError(f"Failed to connect to GVM daemon: {str(e)}") from e

    def send_command(self, cmd_name: str, payload: str) -> str:
        """
        Sends an XML payload and reads the response until the closing tag </{cmd_name}_response> is received.
        Should only be used for small commands like 'authenticate' or 'get_version'.
        """
        if not self.sock:
            raise GMPConnectionError("Socket is not connected. Call connect() first.")

        try:
            request = f"<{cmd_name}>{payload}</{cmd_name}>".encode("utf-8")

            # Obfuscate credentials from logs
            if cmd_name == "authenticate":
                logger.debug(
                    "[OpenVASConnector] Sending command: <authenticate><credentials><username>***</username><password>***</password></credentials></authenticate>"
                )
            else:
                logger.debug(f"[OpenVASConnector] Sending command: {cmd_name}")

            self.sock.sendall(request)

            closing_tag = f"</{cmd_name}_response>".encode("utf-8")
            stream = SocketStreamWrapper(self.sock, closing_tag)

            # Read until stream signals EOF
            chunks = []
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    break
                chunks.append(chunk)

            response_str = b"".join(chunks).decode("utf-8", errors="ignore").strip()
            return response_str

        except socket.timeout:
            logger.error("[GMPTransport] Timeout reading command: %s", cmd_name)
            raise TimeoutError(f"GMP command {cmd_name} timed out.")
        except Exception as e:
            logger.error("[GMPTransport] Socket error sending command: %s", str(e))
            raise GMPConnectionError(f"GMP socket transmission error: {str(e)}") from e

    def close(self):
        """Clean closure."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


@ConnectorRegistry.register("openvas")
class OpenVASConnector(BaseConnector):
    """
    OpenVAS GMP (Greenbone Management Protocol) Connector.
    Uses a standard local cursor state, streams large XML reports, and maps vulnerabilities dynamically.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 9390,
        socket_path: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
        max_results_per_poll: int = 500,
        fresh_start: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ):

        self.user = user
        self.password = password
        self.max_results_per_poll = max_results_per_poll
        self.fresh_start = fresh_start
        self.filters = filters or {}

        # Instantiate internal GMP transport seam
        self.transport = GMPTransport(
            host=host,
            port=port,
            socket_path=socket_path,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )

        # Cursor State via LocalStorageProvider
        self.storage = LocalStorageProvider()
        cursor_key = f"{host or ''}:{port}:{socket_path or ''}:{user or ''}"
        self.state_file_path = (
            f"connectors/openvas/{hashlib.md5(cursor_key.encode()).hexdigest()}.json"
        )

        self.last_timestamp: Optional[str] = None
        self._authenticated = False

        # Validate configuration early
        if not self.user or not self.password:
            raise ValueError(
                "[OpenVASConnector] Credentials (user, password) are required in config."
            )

    def connect(self) -> bool:
        """Establish the TCP/TLS or Unix socket connection."""
        try:
            self.transport.connect()
            self._load_cursor()
            return True
        except GMPConnectionError:
            return False

    def authenticate(self) -> bool:
        """Performs raw GMP credentials authentication."""
        if self._authenticated:
            return True

        auth_payload = f"<credentials><username>{self.user}</username><password>{self.password}</password></credentials>"
        try:
            response_xml = self.transport.send_command("authenticate", auth_payload)
            root = ET.fromstring(response_xml)

            status = root.get("status", "500")
            if status != "200":
                status_text = root.get(
                    "status_text", "Unknown GVM Authentication Error"
                )
                logger.error(
                    f"[OpenVASConnector] Authentication rejected: {status} - {status_text}"
                )
                return False

            self._authenticated = True
            logger.info(
                "[OpenVASConnector] Successfully authenticated session with GVM."
            )
            return True
        except ET.ParseError:
            logger.error("[OpenVASConnector] Failed to parse auth XML response.")
            return False
        except Exception as e:
            logger.error("[OpenVASConnector] Authentication failure: %s", str(e))
            return False

    @retry(
        retry=retry_if_exception_type(
            (GMPConnectionError, TimeoutError, GMPProtocolError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _execute_with_retry(self, cmd_name: str, payload: str) -> str:
        """Executes GMP socket command with transparent reconnect and retry logic."""
        try:
            if not self._authenticated:
                self.connect()
                if not self.authenticate():
                    raise GMPProtocolError(
                        "Authentication failed during retry attempt."
                    )

            return self.transport.send_command(cmd_name, payload)
        except GMPConnectionError as e:
            # Force session reset so next try establishes a fresh connection
            self._authenticated = False
            self.transport.close()
            raise e

    def _get_results_stream(
        self, first: int, filter_parts: List[str]
    ) -> SocketStreamWrapper:
        """
        Sends get_results command and returns the streaming wrapper.
        """
        current_filter = f"first={first} rows={self.max_results_per_poll}"
        if filter_parts:
            current_filter += " " + " ".join(filter_parts)

        payload = f"<get_results><filter>{current_filter}</filter></get_results>"

        # Ensure connected and authenticated
        if not self._authenticated:
            self.connect()
            if not self.authenticate():
                raise GMPProtocolError("Authentication failed during scan retrieval.")

        try:
            # Send command directly
            request = payload.encode("utf-8")
            self.transport.sock.sendall(request)

            closing_tag = b"</get_results_response>"
            return SocketStreamWrapper(self.transport.sock, closing_tag)
        except Exception as e:
            self._authenticated = False
            self.transport.close()
            raise GMPConnectionError(
                f"Connection dropped sending get_results request: {str(e)}"
            )

    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Fetches vulnerability findings (results) incrementally via paginated GMP commands.
        """
        if not self._authenticated:
            if not self.authenticate():
                raise GMPProtocolError("Cannot fetch: Authentication failed.")

        events: List[SecurityEvent] = []
        first = 1

        # Build GMP query filter string. Example: modify_time>2026-07-14T10:00:00Z
        filter_parts = []
        if self.last_timestamp:
            filter_parts.append(f"modify_time>{self.last_timestamp}")

        # Merge configuration-driven filters
        for k, v in self.filters.items():
            if k == "since_timestamp":
                continue
            filter_parts.append(f"{k}={v}")

        latest_fetched_timestamp = self.last_timestamp

        try:
            while True:
                # Get the socket stream directly
                stream = self._get_results_stream(first, filter_parts)

                # Stream parse results to avoid loading giant documents into memory
                results_processed = 0

                # iterparse requires a file-like byte stream
                context = ET.iterparse(stream, events=("end",))

                for event, elem in context:
                    if elem.tag == "result":
                        results_processed += 1
                        try:
                            event_obj = self._parse_result_element(elem)
                            if event_obj:
                                events.append(event_obj)

                            # High water mark tracking
                            mod_time = elem.findtext("modification_time")
                            if mod_time:
                                latest_fetched_timestamp = mod_time
                        except Exception as parse_err:
                            # Isolate line failure: one malformed result does not crash the loop
                            logger.warning("[OpenVASConnector] Skipping corrupted result element: %s", str(parse_err))
                        finally:
                            # Clear processed element to free memory
                            elem.clear()

                # Check if we should break pagination
                if results_processed < self.max_results_per_poll:
                    break

                first += self.max_results_per_poll

            if not events:
                logger.info(
                    "[OpenVASConnector] Fetch completed successfully, but zero new results matched filter."
                )
            else:
                logger.info(
                    f"[OpenVASConnector] Successfully fetched and normalized {len(events)} findings."
                )
                # Update the cursor state across polls
                if latest_fetched_timestamp:
                    self.last_timestamp = latest_fetched_timestamp
                    self._save_cursor()

        except Exception as e:
            logger.error("[OpenVASConnector] Fetch workflow failed: %s", str(e))
            raise e

        return events

    def _parse_result_element(self, elem: ET.Element) -> Optional[SecurityEvent]:
        """
        Parses a single <result> XML element and shapes it into a SecurityEvent.
        """
        result_id = elem.get("id")
        if not result_id:
            result_id = f"openvas-{uuid.uuid4().hex}"

        host = elem.findtext("host", "0.0.0.0")
        port_val = elem.findtext("port", "general/tcp")

        # NVT Details
        nvt = elem.find("nvt")
        nvt_oid = nvt.get("oid") if nvt is not None else "Unknown"
        cve_str = nvt.findtext("cve", "") if nvt is not None else ""
        cve_list = [c.strip() for c in cve_str.split(",") if c.strip()]

        # Severity
        cvss_score_str = nvt.findtext("cvss_base", "0.0") if nvt is not None else "0.0"
        try:
            cvss_score = float(cvss_score_str)
        except ValueError:
            cvss_score = 0.0

        severity = _cvss_score_to_label(cvss_score)

        # Parse tags inside NVT to extract base vector if possible
        tags_str = nvt.findtext("tags", "") if nvt is not None else ""
        cvss_vector = "Unknown"
        if "cvss_base_vector=" in tags_str:
            for tag in tags_str.split("|"):
                if tag.startswith("cvss_base_vector="):
                    cvss_vector = tag.split("=")[1]
                    break

        # Timestamp
        mod_time_str = elem.findtext("modification_time")
        timestamp = parse_timestamp(mod_time_str)

        # Metadata envelope
        metadata = {
            "cve": cve_list,
            "cvss_vector": cvss_vector,
            "qod": nvt.findtext("qod/value", "100") if nvt is not None else "100",
            "nvt_oid": nvt_oid,
            "port": port_val,
            "description": elem.findtext("description", ""),
        }

        # Convert back to raw string segment for forensics
        raw_xml_payload = ET.tostring(elem, encoding="utf-8").decode("utf-8")

        return SecurityEvent(
            event_id=result_id,
            source="openvas_findings",
            vendor="openvas",
            event_type="vulnerability_finding",
            timestamp=timestamp,
            severity=severity,
            asset=f"{host}:{port_val}" if port_val else host,
            raw_payload={"xml": raw_xml_payload},
            metadata=metadata,
        )

    def health_check(self) -> Dict[str, Any]:
        """Verify connectivity by making a lightweight get_version roundtrip."""
        try:
            if not self._authenticated:
                self.connect()
                self.authenticate()

            response = self._execute_with_retry("get_version", "")
            root = ET.fromstring(response)
            version = root.findtext("version", "Unknown")
            return {"status": "ok", "service": "openvas", "gvm_version": version}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def disconnect(self) -> bool:
        """Closes GVM session and releases socket."""
        self.transport.close()
        self._authenticated = False
        return True

    # --- Cursor Persistence Functions ---

    def _load_cursor(self):
        """Loads persistent scan timestamp cursor."""
        if self.fresh_start:
            self.last_timestamp = None
            return

        try:
            content = self.storage.get(self.state_file_path)
            state = json.loads(content.decode("utf-8"))
            self.last_timestamp = state.get("last_timestamp")
            logger.info(
                f"[OpenVASConnector] Loaded cursor state: last_timestamp={self.last_timestamp}"
            )
        except FileNotFoundError:
            self.last_timestamp = None
        except Exception as e:
            logger.error("[OpenVASConnector] Failed to load cursor: %s", str(e))
            self.last_timestamp = None

    def _save_cursor(self):
        """Saves cursor state to local storage provider."""
        state = {
            "last_timestamp": self.last_timestamp,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.storage.save(self.state_file_path, json.dumps(state))
        except Exception as e:
            logger.error("[OpenVASConnector] Failed to save cursor: %s", str(e))
