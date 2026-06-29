"""
Lucky AI — SQLite Memory (Structured)
=======================================
Stores: projects, tasks, personal info, chat history, reminders.
This is Lucky's factual, structured memory.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import Optional
from ..brain.config_loader import DB_PATH


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables on first run."""
    conn = get_conn()
    c = conn.cursor()

    # ── Personal info ─────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS personal_info (
        key        TEXT PRIMARY KEY,
        value      TEXT NOT NULL,
        category   TEXT DEFAULT 'general',
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Projects ─────────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS projects (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        description TEXT,
        status      TEXT DEFAULT 'active',
        priority    TEXT DEFAULT 'medium',
        deadline    TEXT,
        progress    INTEGER DEFAULT 0,
        stack       TEXT,
        notes       TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Tasks ─────────────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        title      TEXT NOT NULL,
        status     TEXT DEFAULT 'pending',
        priority   TEXT DEFAULT 'medium',
        due_date   TEXT,
        notes      TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )""")

    # ── Chat history ──────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role       TEXT NOT NULL,
        content    TEXT NOT NULL,
        agent      TEXT DEFAULT 'brain',
        timestamp  TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Reminders ─────────────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        title      TEXT NOT NULL,
        remind_at  TEXT NOT NULL,
        repeat     TEXT DEFAULT 'none',
        done       INTEGER DEFAULT 0
    )""")

    # ── Memory log (what Lucky learned) ──────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS memory_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        content    TEXT NOT NULL,
        approved   INTEGER DEFAULT 0,
        category   TEXT DEFAULT 'general',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # ── Permission Rules ─────────────────────────────────────────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS permission_rules (
        tool_name  TEXT PRIMARY KEY,
        rule       TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
    from backend.core.logger import logger
    logger.info("SQLite initialized successfully.")


# ── Personal Info ─────────────────────────────────────────────────────────────
def save_personal_info(key: str, value: str, category: str = "general"):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO personal_info (key, value, category, updated_at) VALUES (?,?,?,?)",
        (key, value, category, datetime.datetime.now().isoformat())
    )
    conn.commit(); conn.close()


def get_all_personal_info() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT key, value, category FROM personal_info").fetchall()
    conn.close()
    return {r["key"]: {"value": r["value"], "category": r["category"]} for r in rows}


# ── Projects ──────────────────────────────────────────────────────────────────
def save_project(name: str, description: str = "", deadline: str = "",
                 priority: str = "medium", stack: str = "", notes: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO projects (name, description, deadline, priority, stack, notes) VALUES (?,?,?,?,?,?)",
        (name, description, deadline, priority, stack, notes)
    )
    pid = cur.lastrowid
    conn.commit(); conn.close()
    return pid


def get_active_projects() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM projects WHERE status='active' ORDER BY deadline ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_overdue_projects() -> list:
    today = datetime.date.today().isoformat()
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT name, deadline, priority FROM projects WHERE deadline < ? AND status='active'",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_project_progress(project_id: int, progress: int):
    conn = get_conn()
    conn.execute("UPDATE projects SET progress=?, updated_at=? WHERE id=?",
                 (progress, datetime.datetime.now().isoformat(), project_id))
    conn.commit(); conn.close()


# ── Tasks ─────────────────────────────────────────────────────────────────────
def save_task(title: str, project_id: int = None, due_date: str = "",
              priority: str = "medium", notes: str = "") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tasks (title, project_id, due_date, priority, notes) VALUES (?,?,?,?,?)",
        (title, project_id, due_date, priority, notes)
    )
    tid = cur.lastrowid
    conn.commit(); conn.close()
    return tid


def get_pending_tasks() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT t.*, p.name as project_name FROM tasks t "
        "LEFT JOIN projects p ON t.project_id=p.id "
        "WHERE t.status='pending' ORDER BY t.due_date ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def complete_task(task_id: int):
    conn = get_conn()
    conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
    conn.commit(); conn.close()


# ── Chat History ──────────────────────────────────────────────────────────────
def save_message(session_id: str, role: str, content: str, agent: str = "brain"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO chat_history (session_id, role, content, agent) VALUES (?,?,?,?)",
        (session_id, role, content[:4000], agent)
    )
    conn.commit(); conn.close()


def get_recent_history(session_id: str, limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM chat_history WHERE session_id=? "
        "ORDER BY timestamp DESC LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ── Memory Log ────────────────────────────────────────────────────────────────
def propose_memory(content: str, category: str = "general") -> int:
    """Lucky suggests saving something — user approves in UI."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO memory_log (content, category) VALUES (?,?)",
        (content, category)
    )
    mid = cur.lastrowid
    conn.commit(); conn.close()
    return mid


def approve_memory(memory_id: int):
    conn = get_conn()
    conn.execute("UPDATE memory_log SET approved=1 WHERE id=?", (memory_id,))
    conn.commit(); conn.close()


def get_pending_memory_approvals() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM memory_log WHERE approved=0 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Context builder for prompts ───────────────────────────────────────────────
def build_memory_context() -> str:
    """Build a text summary of everything Lucky knows — injected into every prompt."""
    info     = get_all_personal_info()
    projects = get_active_projects()
    tasks    = get_pending_tasks()
    overdue  = get_overdue_projects()

    parts = []

    if info:
        info_str = "\n".join(f"- {k}: {v['value']}" for k, v in list(info.items())[:15])
        parts.append(f"Personal info:\n{info_str}")

    if projects:
        proj_str = "\n".join(
            f"- {p['name']} (deadline: {p['deadline'] or 'TBD'}, priority: {p['priority']}, {p['progress']}% done)"
            for p in projects[:8]
        )
        parts.append(f"Active projects:\n{proj_str}")

    if overdue:
        over_str = "\n".join(f"- {p['name']} was due {p['deadline']}!" for p in overdue)
        parts.append(f"⚠️ OVERDUE:\n{over_str}")

    if tasks:
        task_str = "\n".join(
            f"- {t['title']} (due: {t['due_date'] or 'TBD'}, priority: {t['priority']})"
            for t in tasks[:8]
        )
        parts.append(f"Pending tasks:\n{task_str}")

    return "\n\n".join(parts) if parts else ""


# ── Permission Rules Helpers ──────────────────────────────────────────────────
def get_permission_rule(tool_name: str) -> Optional[str]:
    conn = get_conn()
    row = conn.execute("SELECT rule FROM permission_rules WHERE tool_name = ?", (tool_name,)).fetchone()
    conn.close()
    return row["rule"] if row else None


def set_permission_rule(tool_name: str, rule: str):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO permission_rules (tool_name, rule, updated_at) VALUES (?, ?, ?)",
        (tool_name, rule, datetime.datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
