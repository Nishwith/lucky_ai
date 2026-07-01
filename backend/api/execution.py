from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from backend.tools.registry import tool_registry
from backend.tools.permissions import respond_to_permission
from backend.tools.schemas import ToolResult

router = APIRouter()

class PermissionResponse(BaseModel):
    approved: bool
    remember_rule: Optional[str] = None  # 'allow' | 'deny' | None

@router.get("/tools")
async def list_tools():
    """List all registered system tools and parameter schemas."""
    return {"tools": tool_registry.list_all()}

@router.post("/tools/{tool_name}", response_model=ToolResult)
async def execute_tool(tool_name: str, params: Dict[str, Any]):
    """Execute a system tool asynchronously."""
    # This blocks if the tool prompts for CONFIRM, and resumes on user response
    result = await tool_registry.execute(tool_name, params)
    return result

@router.post("/permissions/respond/{request_id}")
async def resolve_permission(request_id: str, req: PermissionResponse):
    """Fulfills a pending permission dialog confirmation."""
    success = respond_to_permission(request_id, req.approved, req.remember_rule)
    if not success:
        raise HTTPException(status_code=404, detail="Permission request ID not found or already resolved.")
    return {"success": True}

@router.get("/permissions/pending")
async def list_pending_permissions():
    """List all currently pending permission requests and system state."""
    from backend.tools.permissions import PENDING_CONFIRMATIONS
    from backend.core.state import system_state
    from backend.core.startup import STARTUP_REPORT
    from backend.brain.config_loader import PROVIDER, MODEL
    
    return {
        "pending": [
            {
                "request_id": rid,
                "tool_name": info["tool_name"],
                "params": info["params"]
            }
            for rid, info in list(PENDING_CONFIRMATIONS.items())
            if info.get("approved") is None
        ],
        "system_state": system_state.current_state,
        "status": "degraded" if STARTUP_REPORT.get("degraded_mode", False) else "online",
        "model": MODEL,
        "provider": PROVIDER
    }
