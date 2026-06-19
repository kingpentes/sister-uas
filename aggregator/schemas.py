from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class EventSchema(BaseModel):
    topic: str
    event_id: str
    timestamp: datetime
    source: str
    payload: Dict[str, Any]

class StatsResponse(BaseModel):
    received: int
    unique_processed: int
    duplicate_dropped: int
    uptime_seconds: float
    topics: int
