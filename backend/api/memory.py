"""
Lucky AI — Memory API
Endpoints to save and retrieve everything Lucky knows about you.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..memory.sqlite_db import (
    save_personal_info, get_all_personal_info,
    save_project, get_active_projects, get_overdue_projects,
    save_task, get_pending_tasks, complete_task,
    approve_memory, get_pending_memory_approvals,
    build_memory_context,
)
from ..memory.vector_db import (
    remember, recall, save_style, get_all_styles,
    build_semantic_context,
)

router = APIRouter()


# ── Personal Info ─────────────────────────────────────────────────────────────
class InfoIn(BaseModel):
    key:      str
    value:    str
    category: str = "general"

@router.post("/memory/info")
async def add_info(data: InfoIn):
    save_personal_info(data.key, data.value, data.category)
    return {"status": "saved", "key": data.key}

@router.get("/memory/info")
async def get_info():
    return get_all_personal_info()


# ── Projects ──────────────────────────────────────────────────────────────────
class ProjectIn(BaseModel):
    name:        str
    description: str = ""
    deadline:    str = ""
    priority:    str = "medium"
    stack:       str = ""
    notes:       str = ""

@router.post("/memory/project")
async def add_project(data: ProjectIn):
    pid = save_project(data.name, data.description, data.deadline,
                       data.priority, data.stack, data.notes)
    remember(f"Project: {data.name} — {data.description}. Deadline: {data.deadline}",
             category="project")
    return {"status": "saved", "id": pid}

@router.get("/memory/projects")
async def get_projects():
    return {
        "active":  get_active_projects(),
        "overdue": get_overdue_projects(),
    }


# ── Tasks ─────────────────────────────────────────────────────────────────────
class TaskIn(BaseModel):
    title:      str
    project_id: Optional[int] = None
    due_date:   str = ""
    priority:   str = "medium"
    notes:      str = ""

@router.post("/memory/task")
async def add_task(data: TaskIn):
    tid = save_task(data.title, data.project_id, data.due_date, data.priority, data.notes)
    return {"status": "saved", "id": tid}

@router.get("/memory/tasks")
async def get_tasks():
    return get_pending_tasks()

@router.post("/memory/task/{task_id}/complete")
async def finish_task(task_id: int):
    complete_task(task_id)
    return {"status": "completed"}


# ── Style ─────────────────────────────────────────────────────────────────────
class StyleIn(BaseModel):
    domain:      str
    description: str

@router.post("/memory/style")
async def add_style(data: StyleIn):
    save_style(data.domain, data.description)
    return {"status": "saved", "domain": data.domain}

@router.get("/memory/styles")
async def get_styles():
    return get_all_styles()


# ── Recall ────────────────────────────────────────────────────────────────────
@router.get("/memory/recall")
async def recall_memory(query: str, n: int = 5):
    results = recall(query, n)
    return {"results": results, "query": query}


# ── Full Context ──────────────────────────────────────────────────────────────
@router.get("/memory/context")
async def get_full_context(query: str = "general overview"):
    return {
        "structured": build_memory_context(),
        "semantic":   build_semantic_context(query),
    }


# ── Memory Approvals ──────────────────────────────────────────────────────────
@router.get("/memory/pending")
async def pending_approvals():
    return get_pending_memory_approvals()

@router.post("/memory/approve/{memory_id}")
async def approve(memory_id: int):
    approve_memory(memory_id)
    return {"status": "approved"}
