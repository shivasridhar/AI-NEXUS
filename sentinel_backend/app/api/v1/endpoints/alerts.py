import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory storage for Stage 1 simulation
mock_alerts_db: List[Dict[str, Any]] = []

class SimulatedAlert(BaseModel):
    source: str = Field(..., description="E.g., wazuh, suricata, openvas")
    type: str = Field(..., description="E.g., brute_force, port_scan")
    target_ip: str = Field(..., description="The IP address being targeted")
    details: str = Field(..., description="Additional details about the alert")

@router.post("")
async def receive_simulated_alert(alert: SimulatedAlert):
    """
    Stage 1 Simulation Endpoint.
    Receives an alert, stores it in memory, and correlates it with recent alerts.
    """
    now = datetime.now(timezone.utc)
    
    # Store the alert
    new_alert = {
        "timestamp": now.isoformat(),
        "data": alert.model_dump()
    }
    mock_alerts_db.append(new_alert)
    
    # Basic correlation logic (Stage 1 requirements)
    # If 2+ alerts arrive for the same target_ip within a short time window (e.g. 5 mins)
    recent_threshold = now - timedelta(minutes=5)
    
    recent_alerts_for_ip = [
        a for a in mock_alerts_db 
        if a["data"]["target_ip"] == alert.target_ip and datetime.fromisoformat(a["timestamp"]) >= recent_threshold
    ]
    
    response = {
        "message": "Alert received successfully",
        "stored_alert": alert.model_dump()
    }
    
    if len(recent_alerts_for_ip) >= 2:
        logger.warning(f"🚨 HIGH RISK INCIDENT: Multiple alerts detected for IP {alert.target_ip}!")
        response["correlation"] = {
            "status": "High Risk Incident",
            "reason": f"Detected {len(recent_alerts_for_ip)} alerts for {alert.target_ip} within 5 minutes.",
            "related_sources": list(set(a["data"]["source"] for a in recent_alerts_for_ip))
        }
        
    return response

@router.get("")
async def get_simulated_alerts():
    """View all received simulation alerts."""
    return {"total": len(mock_alerts_db), "alerts": mock_alerts_db}
