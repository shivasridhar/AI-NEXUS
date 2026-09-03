import logging
import time
from typing import Dict, List, Optional, Tuple

from app.schemas.security_event import SecurityEvent
from app.services.ingestion_pipeline.dead_letter import DeadLetterPublisher
from app.services.ingestion_pipeline.duplicate_detector import DeduplicationStrategy
from app.services.ingestion_pipeline.metadata_enrichment import MetadataEnricher
from app.services.ingestion_pipeline.validator import EventValidator

logger = logging.getLogger(__name__)


class EventPipeline:
    """
    Orchestrates the sequential processing of SecurityEvent payloads.
    Stages:
      1. Validation: Rejects invalid schemas/timestamps/vendors.
      2. Duplicate Detection: Deduplicates based on ID or content hash.
      3. Metadata Enrichment: Stamps processing metrics under "ingestion".

    Uses constructor dependency injection for testability and structural decoupling.
    """

    def __init__(
        self,
        validator: EventValidator,
        duplicate_detector: DeduplicationStrategy,
        enricher: MetadataEnricher,
        dlq_publisher: Optional[DeadLetterPublisher] = None,
    ):
        self.validator = validator
        self.duplicate_detector = duplicate_detector
        self.enricher = enricher
        self.dlq_publisher = dlq_publisher

    def process_event(
        self, event: SecurityEvent
    ) -> Tuple[Optional[SecurityEvent], Optional[str], Optional[str]]:
        """
        Processes a single SecurityEvent.
        Returns (enriched_event, None, None) if successful.
        Returns (None, error_type, error_reason) if failed.
        error_type is one of: "validation", "duplicate", "error".
        """
        start_time = time.time()

        # 1. Validation
        is_valid, errors = self.validator.validate(event)
        if not is_valid:
            # Rejections are logged at WARNING level for alerting visibility
            logger.warning(
                f"[EventPipeline] Rejecting invalid event ID={event.event_id} from source={event.source}. "
                f"Validation errors: {errors}"
            )
            # In a production context, quarantine/dead-letter logic would trigger here
            return None, "validation", f"Validation failed: {errors}"

        # 2. Duplicate Detection
        if self.duplicate_detector.is_duplicate(event):
            logger.info(
                f"[EventPipeline] Skipping duplicate event ID={event.event_id} from source={event.source}"
            )
            return None, "duplicate", "Duplicate event skipped"

        # 3. Metadata Enrichment
        enriched_event = self.enricher.enrich(event, start_time)
        return enriched_event, None, None

    def process(
        self, events: List[SecurityEvent]
    ) -> Tuple[List[SecurityEvent], List[Dict[str, str]]]:
        """
        Processes a batch of SecurityEvents.
        Filters out invalid or duplicate events, returning only successfully processed logs and a list of failures.
        """
        processed_events: List[SecurityEvent] = []
        failures: List[Dict[str, str]] = []

        for event in events:
            try:
                processed, err_type, err_reason = self.process_event(event)
                if processed:
                    processed_events.append(processed)
                else:
                    failure_reason = f"{err_type}: {err_reason}"
                    failures.append(
                        {
                            "event_id": getattr(event, "event_id", "unknown"),
                            "type": err_type,
                            "reason": err_reason,
                        }
                    )
                    if self.dlq_publisher:
                        raw = getattr(event, "raw_payload", {})
                        if not raw:
                            # If raw_payload is missing or empty, dump the event model
                            raw = event.model_dump(mode="json")
                        self.dlq_publisher.publish_dead_letter(
                            payload=raw,
                            reason=failure_reason,
                            event_id=getattr(event, "event_id", "unknown"),
                        )
            except Exception as e:
                # Error isolation: failure in one event does not crash processing of the batch
                logger.error(
                    f"[EventPipeline] Unexpected exception processing event ID={event.event_id}: "
                    f"{type(e).__name__} - {str(e)}"
                )
                failures.append(
                    {
                        "event_id": getattr(event, "event_id", "unknown"),
                        "type": "error",
                        "reason": f"Pipeline failure: {str(e)}",
                    }
                )

        return processed_events, failures
