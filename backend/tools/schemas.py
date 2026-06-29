from pydantic import BaseModel
from typing import Optional, Any, Dict

class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
