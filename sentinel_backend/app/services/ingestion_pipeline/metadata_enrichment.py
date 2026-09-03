import os
import socket
import time
from datetime import datetime, timezone
from typing import Optional

from app.schemas.security_event import SecurityEvent


class MetadataEnricher:
    """
    Enriches validated SecurityEvents with ingestion metrics, pipeline metadata, and execution telemetry.
    Ensures all metadata is strictly isolated under the metadata['ingestion'] namespace.
    """

    def __init__(
        self,
        pipeline_version: str = "1.0.0",
        environment: Optional[str] = None,
        node_id: Optional[str] = None,
    ):
        self.pipeline_version = pipeline_version

        # Load from config settings or environment defaults
        self.environment = environment or os.getenv("ENV") or "production"
        self.node_id = (
            node_id or os.getenv("HOSTNAME") or socket.gethostname() or "unknown-node"
        )

    def enrich(self, event: SecurityEvent, start_time: float) -> SecurityEvent:
        """
        Enriches the SecurityEvent. Starts with the epoch time of processing start
        to compute the processing duration.
        """
        ingestion_ts = datetime.now(timezone.utc)
        duration_ms = (time.time() - start_time) * 1000.0

        # Maintain absolute namespacing isolation to prevent key collision
        ingestion_metadata = {
            "ingested_at": ingestion_ts.isoformat(),
            "connector": event.source,
            "processing_duration_ms": round(duration_ms, 3),
            "node_id": self.node_id,
            "pipeline_version": self.pipeline_version,
            "environment": self.environment,
        }

        # Initialize dictionary if not present
        if event.metadata is None:
            event.metadata = {}

        # Safely nest enrichment under the namespaced ingestion dictionary
        event.metadata["ingestion"] = ingestion_metadata

        return event
