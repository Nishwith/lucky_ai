import asyncio
import uuid
from typing import Dict, Any, Optional
from backend.core.logger import logger
from backend.core.events import event_bus
from backend.memory.sqlite_db import get_permission_rule, set_permission_rule

# Global store for in-flight permission requests waiting for user input
# Structure: { request_id: { "event": asyncio.Event, "approved": Optional[bool], "tool_name": str, "params": dict } }
PENDING_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}

async def check_permission(tool_name: str, params: dict, permission_level: str = "CONFIRM") -> bool:
    """
    Verifies if a tool execution is authorized.
    Levels:
      - AUTO: always allow
      - DENY: block immediately
      - CONFIRM: wait asynchronously for user response
    """
    # 1. First, check persistent SQLite rules
    db_rule = get_permission_rule(tool_name)
    if db_rule == "allow":
        logger.info(f"Permission check: Tool '{tool_name}' allowed by persistent rule.")
        return True
    elif db_rule == "deny":
        logger.warning(f"Permission check: Tool '{tool_name}' blocked by persistent rule.")
        raise PermissionError(f"Permission denied by persistent rules for tool '{tool_name}'")

    # 2. Check the default permission level configured for the tool
    if tool_name == "run_command":
        cmd = params.get("command", "")
        from backend.brain.config_loader import COMMAND_ALLOWLIST
        if cmd.strip() in COMMAND_ALLOWLIST or any(cmd.strip().startswith(a) for a in COMMAND_ALLOWLIST):
            logger.info(f"Command '{cmd}' is in allowlist. Auto-allowing.")
            return True

    if permission_level == "AUTO":
        return True
    elif permission_level == "DENY":
        raise PermissionError(f"Permission permanently denied by security policy for tool '{tool_name}'")
    
    # 3. Handle CONFIRM (Interactive Prompt)
    request_id = str(uuid.uuid4())
    event = asyncio.Event()
    
    pending_info = {
        "event": event,
        "approved": None,
        "tool_name": tool_name,
        "params": params
    }
    PENDING_CONFIRMATIONS[request_id] = pending_info
    
    logger.info(f"Permission required for '{tool_name}'. Request ID: {request_id}. Emitting event.")
    
    # Emit permission request to Event Bus (to be pushed to UI via SSE/WebSocket later)
    await event_bus.emit("permission.requested", {
        "request_id": request_id,
        "tool_name": tool_name,
        "params": params
    })
    
    # Wait for user input with a 60-second timeout to prevent task leaks
    try:
        await asyncio.wait_for(event.wait(), timeout=60.0)
    except asyncio.TimeoutError:
        PENDING_CONFIRMATIONS.pop(request_id, None)
        logger.warning(f"Permission request {request_id} for tool '{tool_name}' timed out.")
        raise PermissionError(f"Permission confirmation timed out (60s) for tool '{tool_name}'")
        
    # Get user response details
    user_response = PENDING_CONFIRMATIONS.pop(request_id, None)
    if user_response and user_response["approved"] is True:
        logger.info(f"Permission request {request_id} for tool '{tool_name}' approved by user.")
        return True
    else:
        logger.warning(f"Permission request {request_id} for tool '{tool_name}' denied by user.")
        raise PermissionError(f"User denied permission to execute tool '{tool_name}'")


def respond_to_permission(request_id: str, approved: bool, remember_rule: Optional[str] = None):
    """
    Called by API endpoint to fulfill a pending permission check.
    If remember_rule is 'allow' or 'deny', saves it in SQLite.
    """
    if request_id not in PENDING_CONFIRMATIONS:
        logger.warning(f"Response received for invalid/timed out permission request: {request_id}")
        return False
        
    pending = PENDING_CONFIRMATIONS[request_id]
    pending["approved"] = approved
    
    if remember_rule in ("allow", "deny"):
        tool_name = pending["tool_name"]
        set_permission_rule(tool_name, remember_rule)
        logger.info(f"Persisted permission rule '{remember_rule}' for tool '{tool_name}'.")
        
    # Signal the event to resume execution
    pending["event"].set()
    return True
