import hashlib
import logging
import time
from abc import ABC, abstractmethod
from threading import Lock
from typing import Dict, Optional

from app.schemas.security_event import SecurityEvent

logger = logging.getLogger(__name__)


class DeduplicationStrategy(ABC):
    """
    Abstract interface for swappable duplicate detection strategies.
    Allows changing storage mechanics (e.g. from in-memory cache to Redis/DB)
    without modifying EventPipeline.
    """

    @abstractmethod
    def is_duplicate(self, event: SecurityEvent) -> bool:
        """Returns True if the event is a duplicate, False otherwise."""


class InMemoryWindowedDeduplicationStrategy(DeduplicationStrategy):
    """
    Thread-safe in-memory duplicate detector with a configurable expiration window.
    Uses exact ID comparison first, falling back to a content hash of key semantic fields.

    WARNING (Horizontal Scaling Limitations):
    Because this maintains state in local process RAM (dict/Lock), it is strictly
    single-instance. In a multi-worker (Uvicorn/Gunicorn) or multi-pod Kubernetes
    deployment, duplicates will bleed through because each worker maintains an
    independent cache.

    Future Strategy: A Redis-backed DeduplicationStrategy (using Redis SETEX or ZSET)
    must be implemented before scaling the API horizontally.
    """

    def __init__(self, window_seconds: Optional[int] = None):
        if window_seconds is None:
            from app.core.config import settings

            self.window_seconds = settings.DEDUP_WINDOW_SECONDS
        else:
            self.window_seconds = window_seconds

        # Maps ID/hash to timestamp of insertion
        self._seen_ids: Dict[str, float] = {}
        self._seen_hashes: Dict[str, float] = {}

        self._lock = Lock()

    def _generate_content_hash(self, event: SecurityEvent) -> str:
        """
        Computes a deterministic hash over a defined subset of semantic fields.
        Avoids hashing the raw payload to prevent issues with minor key-ordering or timestamp differences.
        """
        # Hashing: vendor, source, event_type, normalized timestamp string, asset
        ts_str = event.timestamp.isoformat() if event.timestamp else ""
        semantic_data = f"{event.vendor}:{event.source}:{event.event_type}:{ts_str}:{event.asset or ''}"

        return hashlib.md5(semantic_data.encode("utf-8")).hexdigest()

    def _cleanup_expired(self, now: float):
        """Removes entries that have fallen outside the deduplication window."""
        expired_limit = now - self.window_seconds

        # Clean ID cache
        expired_ids = [k for k, v in self._seen_ids.items() if v < expired_limit]
        for k in expired_ids:
            self._seen_ids.pop(k, None)

        # Clean Hash cache
        expired_hashes = [k for k, v in self._seen_hashes.items() if v < expired_limit]
        for k in expired_hashes:
            self._seen_hashes.pop(k, None)

    def is_duplicate(self, event: SecurityEvent) -> bool:
        now = time.time()

        with self._lock:
            # 1. Periodically prune expired items to bound memory consumption
            self._cleanup_expired(now)

            # 2. Check by Event ID (stable vendor IDs like GVM result UUID or Wazuh alert ID)
            if event.event_id:
                if event.event_id in self._seen_ids:
                    logger.info(
                        f"[Deduplicator] Duplicate detected via exact ID match: ID={event.event_id}"
                    )
                    return True
                self._seen_ids[event.event_id] = now

            # 3. Fallback to Content Hashing (catches identical events with regenerated IDs)
            content_hash = self._generate_content_hash(event)
            if content_hash in self._seen_hashes:
                logger.info(
                    f"[Deduplicator] Duplicate detected via semantic content hash match: Hash={content_hash}"
                )
                return True

            self._seen_hashes[content_hash] = now
            return False
