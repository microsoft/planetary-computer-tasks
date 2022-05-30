from typing import Any, Dict, Optional

from pydantic import BaseModel


class OrchSignal(BaseModel):
    instance_id: str
    event_name: str
    event_data: Optional[Dict[str, Any]] = None
