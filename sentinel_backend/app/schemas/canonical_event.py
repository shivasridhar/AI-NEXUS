from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class CanonicalEventSchema(BaseModel):
    model_config = ConfigDict(extra='ignore')
    
    source_tool: str
    event_type: str
    
    severity_raw: Optional[str] = None
    severity_normalized: Optional[int] = Field(None, ge=0, le=100)
    
    timestamp_utc: datetime
    
    actor_identifier: Optional[str] = None
    asset_identifier: Optional[str] = None
    
    raw_event_json: Dict[str, Any]
    
    workspace_id: uuid.UUID
    linked_access_log_id: Optional[uuid.UUID] = None
