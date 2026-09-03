from abc import ABC, abstractmethod
from typing import Any, Dict, List

from app.schemas.security_event import SecurityEvent


class BaseConnector(ABC):
    """
    Abstract base class for all Enterprise Data Ingestion Connectors.
    Provides a standardized contract for fetching and normalizing security events.
    """

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the external data source.
        Returns True if successful, False otherwise.
        """

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the external data source.
        Returns True if authenticated, False otherwise.
        """

    @abstractmethod
    def fetch_events(self, **kwargs) -> List[SecurityEvent]:
        """
        Fetch events from the external source and normalize them into SecurityEvent objects.
        Returns a list of standardized SecurityEvent models.
        """

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health and operational status of the connector.
        Returns a dictionary containing health metrics or status info.
        """

    @abstractmethod
    def disconnect(self) -> bool:
        """
        Gracefully disconnect from the data source and clean up resources.
        Returns True if successfully disconnected.
        """
