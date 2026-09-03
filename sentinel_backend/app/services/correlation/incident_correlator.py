"""
Multi-Source Incident Correlation Service (Dynamic SOC Engine)

Correlates events from different security tools into unified Incidents 
using dynamic, configuration-driven time-window and grouping key analysis.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Load Dynamic SOC Configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "core", "soc_config.json")

def load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load dynamic correlation config: {e}")
        # Safe fallback
        return {
            "correlation": {
                "time_window_minutes": 5,
                "grouping_keys": ["actor", "asset", "source_ip"],
                "min_events_for_incident": 2,
                "severity_mapping": {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
            }
        }

class CorrelatedIncident:
    """Represents a dynamically correlated security incident."""

    def __init__(self, config: dict, incident_id: Optional[str] = None):
        self.id: str = incident_id or str(uuid4())
        self.events: List[Dict[str, Any]] = []
        self.sources: set = set()
        self.actors: set = set()
        self.assets: set = set()
        self.severity: str = "Low"
        self.mitre_techniques: List[Dict[str, str]] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.description: str = ""
        self.config = config.get("correlation", {})

    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        self.sources.add(event.get("source", "unknown"))

        actor = event.get("identity") or event.get("actor")
        if actor:
            self.actors.add(actor)

        asset = event.get("asset")
        if asset:
            self.assets.add(asset)

        # Update time window
        event_time = event.get("timestamp")
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                event_time = None

        if event_time:
            if self.start_time is None or event_time < self.start_time:
                self.start_time = event_time
            if self.end_time is None or event_time > self.end_time:
                self.end_time = event_time

        # Escalate severity using dynamic mapping
        event_severity = str(event.get("severity", "INFO")).upper()
        self.severity = self._max_severity(self.severity, event_severity)

    def _max_severity(self, current: str, incoming: str) -> str:
        order = self.config.get("severity_mapping", {})
        current_val = order.get(current.upper(), 0)
        incoming_val = order.get(incoming.upper(), 0)
        if incoming_val > current_val:
            return incoming.capitalize()
        return current.capitalize()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_count": len(self.events),
            "sources": list(self.sources),
            "actors": list(self.actors),
            "assets": list(self.assets),
            "severity": self.severity,
            "mitre_techniques": self.mitre_techniques,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "description": self.description,
            "events": self.events[:50],  # Cap payload
        }


class IncidentCorrelator:
    """
    Correlates security events from multiple sources into unified incidents
    using dynamic logic loaded from soc_config.json.
    """

    def __init__(self):
        self.config = load_config()
        self.corr_config = self.config.get("correlation", {})
        self.time_window = timedelta(minutes=self.corr_config.get("time_window_minutes", 5))
        self.grouping_keys = self.corr_config.get("grouping_keys", [])

    def correlate(self, events: List[Dict[str, Any]]) -> List[CorrelatedIncident]:
        """
        Takes a list of normalized events and groups them using dynamic rules.
        """
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: e.get("timestamp", ""))
        incidents: List[CorrelatedIncident] = []
        assigned: set = set()

        for i, event in enumerate(sorted_events):
            if i in assigned:
                continue

            incident = CorrelatedIncident(self.config)
            incident.add_event(event)
            assigned.add(i)

            for j, candidate in enumerate(sorted_events):
                if j in assigned or j == i:
                    continue

                if self._should_correlate(event, candidate, incident):
                    incident.add_event(candidate)
                    assigned.add(j)

            incident.description = self._generate_description(incident)
            incidents.append(incident)

        # Dynamic filtering threshold
        min_events = self.corr_config.get("min_events_for_incident", 2)
        multi_source = self.corr_config.get("multi_source_escalation", True)

        significant_incidents = []
        for inc in incidents:
            if len(inc.events) >= min_events or (multi_source and len(inc.sources) > 1):
                significant_incidents.append(inc)

        # Sort dynamically by severity
        order = self.corr_config.get("severity_mapping", {})
        significant_incidents.sort(
            key=lambda i: (order.get(i.severity.upper(), 0), len(i.events)),
            reverse=True
        )

        return significant_incidents

    def _should_correlate(self, event_a: Dict, event_b: Dict, incident: CorrelatedIncident) -> bool:
        """Dynamically evaluates if two events should be correlated."""
        
        # 1. Time proximity check
        time_a = event_a.get("timestamp", "")
        time_b = event_b.get("timestamp", "")
        if time_a and time_b:
            try:
                dt_a = datetime.fromisoformat(str(time_a).replace("Z", "+00:00"))
                dt_b = datetime.fromisoformat(str(time_b).replace("Z", "+00:00"))
                if abs(dt_b - dt_a) > self.time_window:
                    return False
            except (ValueError, TypeError):
                pass

        # 2. Dynamic Grouping Keys
        for key in self.grouping_keys:
            if key in ["actor", "identity"]:
                val_a = event_a.get("identity") or event_a.get("actor")
                val_b = event_b.get("identity") or event_b.get("actor")
                if val_a and val_b and val_a == val_b:
                    return True
                if val_b and val_b in incident.actors:
                    return True
            elif key == "asset":
                val_a = event_a.get("asset")
                val_b = event_b.get("asset")
                if val_a and val_b and val_a == val_b:
                    return True
                if val_b and val_b in incident.assets:
                    return True
            else:
                # Arbitrary metadata keys (e.g. source_ip)
                val_a = event_a.get("metadata", {}).get(key) or event_a.get(key)
                val_b = event_b.get("metadata", {}).get(key) or event_b.get(key)
                if val_a and val_b and val_a == val_b:
                    return True

        return False

    def _generate_description(self, incident: CorrelatedIncident) -> str:
        parts = []
        if len(incident.sources) > 1:
            parts.append(f"Cross-source incident detected across {', '.join(incident.sources)}")
        else:
            source = list(incident.sources)[0] if incident.sources else "unknown"
            parts.append(f"Correlated incident from {source}")

        parts.append(f"involving {len(incident.events)} events")

        if incident.actors:
            parts.append(f"by {', '.join(list(incident.actors)[:3])}")

        if incident.assets:
            parts.append(f"targeting {', '.join(list(incident.assets)[:3])}")

        if incident.start_time and incident.end_time:
            duration = incident.end_time - incident.start_time
            if duration.total_seconds() > 0:
                parts.append(f"over {int(duration.total_seconds())}s window")

        return " ".join(parts) + "."
