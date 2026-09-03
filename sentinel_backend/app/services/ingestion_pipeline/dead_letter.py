import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DeadLetterPublisher(ABC):
    """
    Interface for handling rejected, duplicate, or failed events.
    """

    @abstractmethod
    def publish_dead_letter(
        self, payload: Dict[str, Any], reason: str, event_id: str
    ) -> None:
        """Publishes the raw payload and rejection reason to a dead letter queue."""


class InMemoryDeadLetterPublisher(DeadLetterPublisher):
    """
    In-memory bounded dead-letter publisher for Stage 1.
    Prevents silent data loss without requiring external infrastructure.
    """

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._dead_letters = []

    def publish_dead_letter(
        self, payload: Dict[str, Any], reason: str, event_id: str
    ) -> None:
        dlq_event = {"event_id": event_id, "reason": reason, "raw_payload": payload}

        # FIFO eviction if bounded size is exceeded
        if len(self._dead_letters) >= self.max_size:
            self._dead_letters.pop(0)

        self._dead_letters.append(dlq_event)
        logger.debug(f"[DLQ] Event {event_id} captured. Reason: {reason}")

    def get_dead_letters(self) -> list:
        return self._dead_letters
