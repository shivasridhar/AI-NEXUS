from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IngestionSource(ABC):
    """
    Abstract base class for all ingestion sources (e.g., FileUpload, AwsCloudTrail).
    """

    @abstractmethod
    def fetch_events(self) -> Dict[str, Any]:
        """
        Fetches events from the source and returns them as a RawEventBatch
        (typically a dictionary matching the CloudTrail JSON structure).
        """

    @abstractmethod
    def get_source_metadata(self) -> Dict[str, Any]:
        """
        Returns metadata about the ingestion source, such as the source type and identifier.
        """
