from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.brain.config_loader import WORKSPACE_ROOT
from backend.memory.sqlite_db import get_active_projects, get_all_personal_info, get_recent_history
from backend.memory.vector_db import get_all_styles, build_semantic_context

@dataclass
class AgentContext:
    workspace_root: Path
    active_project: Optional[Dict[str, Any]]
    user_preferences: Dict[str, Any]
    relevant_memories: str
    conversation_history: List[Dict[str, Any]]

def build_agent_context(session_id: str, message: str) -> AgentContext:
    """Combines structured and semantic context sources into a unified bundle."""
    # 1. Fetch active projects
    active_projects = get_active_projects()
    active_proj = active_projects[0] if active_projects else None

    # 2. Gather user info preferences and coding styles
    personal_info = get_all_personal_info()
    styles = get_all_styles()
    user_prefs = {
        "personal_info": {k: v["value"] for k, v in personal_info.items()},
        "styles": styles
    }

    # 3. Retrieve relevant vector memory blocks
    semantic_ctx = build_semantic_context(message)

    # 4. Pull session history
    history = get_recent_history(session_id, limit=20) if session_id else []

    return AgentContext(
        workspace_root=WORKSPACE_ROOT,
        active_project=active_proj,
        user_preferences=user_prefs,
        relevant_memories=semantic_ctx,
        conversation_history=history
    )
