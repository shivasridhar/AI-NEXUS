from abc import ABC, abstractmethod
from typing import Dict, Any
from sqlalchemy.orm import Session
from neo4j import Session as GraphSession

class BaseCollector(ABC):
    def __init__(self, db: Session, graph: GraphSession):
        self.db = db
        self.graph = graph

    @abstractmethod
    def collect(self, finding_id: str, workspace_id: str, identity_id: str) -> Dict[str, Any]:
        """
        Collect evidence specific to this collector.
        Must return a dictionary of evidence key-values.
        """
