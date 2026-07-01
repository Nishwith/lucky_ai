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
        cmd = params.get("command", "").strip()
        from backend.brain.config_loader import COMMAND_ALLOWLIST
        # Split on shell operators to prevent injection via chained commands
        # e.g. "git status && rm -rf /" must NOT match allowlist entry "git status"
        import re
        parts = re.split(r'[;&|`]|\|\||\&\&', cmd)
        if len(parts) == 1:
            # Only a single command (no chaining) — safe to check allowlist
            if cmd in COMMAND_ALLOWLIST or any(cmd.startswith(a) for a in COMMAND_ALLOWLIST):
                logger.info(f"Command '{cmd}' is in allowlist. Auto-allowing.")
                return True


    if permission_level == "AUTO":
        return True
    elif permission_level == "DENY":
        raise PermissionError(f"Permission permanently denied by security policy for tool '{tool_name}'")
    
    # 3. Handle CONFIRM (Interactive Prompt)
    # Check for an identical active request in progress to avoid UI spam and duplicate waiter races
    existing_rid = None
    for rid, pending in list(PENDING_CONFIRMATIONS.items()):
        if pending.get("tool_name") == tool_name and pending.get("params") == params and pending.get("approved") is None:
            existing_rid = rid
            break

    if existing_rid:
        logger.info(f"Duplicate permission request detected for '{tool_name}'. Joining existing Request ID: {existing_rid}")
        pending_info = PENDING_CONFIRMATIONS[existing_rid]
        pending_info["waiters"] += 1
        event = pending_info["event"]
        
        try:
            await asyncio.wait_for(event.wait(), timeout=60.0)
        except asyncio.TimeoutError:
            logger.warning(f"Shared permission request {existing_rid} for tool '{tool_name}' timed out.")
            raise PermissionError(f"Permission confirmation timed out (60s) for tool '{tool_name}'")
        finally:
            pending_info["waiters"] -= 1
            if pending_info["waiters"] == 0:
                PENDING_CONFIRMATIONS.pop(existing_rid, None)
                
        if pending_info.get("approved") is True:
            return True
        else:
            raise PermissionError(f"User denied permission to execute tool '{tool_name}'")

    request_id = str(uuid.uuid4())
    event = asyncio.Event()
    
    pending_info = {
        "event": event,
        "approved": None,
        "tool_name": tool_name,
        "params": params,
        "waiters": 1
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
        logger.warning(f"Permission request {request_id} for tool '{tool_name}' timed out.")
        raise PermissionError(f"Permission confirmation timed out (60s) for tool '{tool_name}'")
    finally:
        pending_info["waiters"] -= 1
        if pending_info["waiters"] == 0:
            PENDING_CONFIRMATIONS.pop(request_id, None)
        
    if pending_info.get("approved") is True:
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
