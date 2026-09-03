import logging
import time
from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel, Field

from app.schemas.security_event import SecurityEvent

logger = logging.getLogger(__name__)


class PublishFailureDetail(BaseModel):
    event_id: str
    reason: str


class PublishSummary(BaseModel):
    published_count: int
    failed_count: int
    failures: List[PublishFailureDetail] = Field(default_factory=list)
    duration_ms: float


class SecurityEventPublisher(ABC):
    """
    Abstract interface for publishing processed SecurityEvents to a downstream sink.
    Decoupled from transport mechanism (e.g. In-memory, Kafka, RabbitMQ, Redis Streams).
    """

    @abstractmethod
    def publish(self, events: List[SecurityEvent]) -> PublishSummary:
        """
        Publishes the events to the configured sink.
        Returns a PublishSummary detail.
        """


class InMemorySecurityEventPublisher(SecurityEventPublisher):
    """
    Stage 1 default implementation of SecurityEventPublisher.
    Maintains a bounded list of published events in RAM.
    """

    def __init__(self):
        from app.core.config import settings

        self.max_size = settings.PUBLISHER_MAX_SIZE
        self._published_events: List[SecurityEvent] = []

    def publish(self, events: List[SecurityEvent]) -> PublishSummary:
        start_time = time.time()
        failures: List[PublishFailureDetail] = []
        success_count = 0

        logger.info(f"[InMemoryPublisher] Starting publishing of {len(events)} events.")

        for event in events:
            try:
                if not event.event_id or not event.vendor or not event.source:
                    raise ValueError(
                        "Event is missing critical fields (event_id, vendor, source)."
                    )

                # Bounded FIFO eviction
                if len(self._published_events) >= self.max_size:
                    self._published_events.pop(0)

                self._published_events.append(event)
                success_count += 1
            except Exception as e:
                # Capture event_id if present and non-empty, otherwise default to "unknown"
                raw_ev_id = getattr(event, "event_id", None)
                ev_id = raw_ev_id if raw_ev_id else "unknown"
                logger.error("[InMemoryPublisher] Event publish failed for ID={ev_id}: %s", e)
                failures.append(PublishFailureDetail(event_id=ev_id, reason=str(e)))

        duration_ms = (time.time() - start_time) * 1000.0

        summary = PublishSummary(
            published_count=success_count,
            failed_count=len(failures),
            failures=failures,
            duration_ms=round(duration_ms, 3),
        )

        logger.info(
            f"[InMemoryPublisher] Publishing completed. "
            f"Success: {success_count}, Failed: {len(failures)}, Duration: {summary.duration_ms:.2f}ms"
        )
        return summary

    def get_published_events(self) -> List[SecurityEvent]:
        """Utility method to inspect published events (e.g. for simulations, API responses, testing)."""
        return self._published_events


class SecurityEventPublisherFactory:
    """
    Factory to construct SecurityEventPublisher instances dynamically based on configuration.
    """

    @staticmethod
    def create(publisher_type: str = "in_memory") -> SecurityEventPublisher:
        if publisher_type.lower() == "in_memory":
            return InMemorySecurityEventPublisher()
        # Future transports can easily be wired here:
        # elif publisher_type.lower() == "kafka":
        #     return KafkaSecurityEventPublisher()
        else:
            raise ValueError(f"Unknown publisher type: {publisher_type}")
