from abc import ABC, abstractmethod
from typing import List, Dict, Any
import uuid
from app.schemas.canonical_event import CanonicalEventSchema

class BaseEventParser(ABC):
    """
    Abstract base class for all event parsers mapping source tools to the CanonicalEvent schema.
    """
    
    @abstractmethod
    def parse(self, data: Any, workspace_id: uuid.UUID) -> List[CanonicalEventSchema]:
        """
        Parses raw data into a list of CanonicalEvent schemas.
        Must handle its own error catching per record to avoid failing the whole batch.
        """
        pass
