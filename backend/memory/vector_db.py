"""
Lucky AI — ChromaDB Vector Memory (Semantic)
=============================================
Stores: preferences, style, past work, conversation summaries.
Enables semantic search — Lucky finds relevant context by meaning, not keywords.
"""

import datetime
import time
import chromadb
from chromadb.config import Settings
from ..brain.config_loader import VEC_PATH

# ── Client ─────────────────────────────────────────────────────────────────────
def _get_client() -> chromadb.PersistentClient:
    VEC_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(VEC_PATH),
        settings=Settings(anonymized_telemetry=False)
    )


def init_vector_db():
    client = _get_client()
    client.get_or_create_collection("lucky_memory")
    client.get_or_create_collection("lucky_style")
    client.get_or_create_collection("lucky_work")
    print("[Lucky AI Memory] ChromaDB initialized ✓")


# ── Core memory operations ─────────────────────────────────────────────────────
def remember(text: str, category: str = "general", metadata: dict = None):
    """Store any piece of information in semantic memory."""
    client = _get_client()
    col    = client.get_or_create_collection("lucky_memory")
    uid    = str(time.time())
    col.add(
        documents=[text],
        ids=[uid],
        metadatas=[{
            "category": category,
            "time":     datetime.datetime.now().isoformat(),
            **(metadata or {})
        }]
    )


def recall(query: str, n: int = 5, category: str = None) -> list[str]:
    """Find the most relevant memories for a given query."""
    client = _get_client()
    col    = client.get_or_create_collection("lucky_memory")
    try:
        where = {"category": category} if category else None
        results = col.query(
            query_texts=[query],
            n_results=min(n, col.count() or 1),
            where=where
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


# ── Style memory (coding style, content tone, preferences) ────────────────────
def save_style(domain: str, description: str):
    """
    Save how the user likes things done in a specific domain.
    e.g. save_style("coding", "Prefers async Python, FastAPI, type hints everywhere")
    e.g. save_style("content", "Casual Telugu-English mix, uses 'bro', short sentences")
    """
    client = _get_client()
    col    = client.get_or_create_collection("lucky_style")
    # Upsert — replace existing style for this domain
    try:
        col.delete(where={"domain": domain})
    except Exception:
        pass
    col.add(
        documents=[description],
        ids=[f"style_{domain}_{int(time.time())}"],
        metadatas=[{"domain": domain, "updated": datetime.datetime.now().isoformat()}]
    )


def get_style(domain: str) -> str:
    """Retrieve the user's style for a specific domain."""
    client = _get_client()
    col    = client.get_or_create_collection("lucky_style")
    try:
        results = col.query(
            query_texts=[domain],
            n_results=1,
            where={"domain": domain}
        )
        docs = results["documents"][0] if results["documents"] else []
        return docs[0] if docs else ""
    except Exception:
        return ""


def get_all_styles() -> dict:
    """Get all saved styles."""
    client  = _get_client()
    col     = client.get_or_create_collection("lucky_style")
    try:
        results = col.get()
        styles  = {}
        for doc, meta in zip(results["documents"], results["metadatas"]):
            domain = meta.get("domain", "unknown")
            styles[domain] = doc
        return styles
    except Exception:
        return {}


# ── Work memory (past projects, generated content) ────────────────────────────
def save_work(title: str, content: str, work_type: str = "code"):
    """Save a piece of work Lucky has done for future reference."""
    client = _get_client()
    col    = client.get_or_create_collection("lucky_work")
    col.add(
        documents=[f"{title}\n\n{content[:2000]}"],
        ids=[str(time.time())],
        metadatas=[{
            "title":     title,
            "type":      work_type,
            "timestamp": datetime.datetime.now().isoformat()
        }]
    )


def find_similar_work(query: str, n: int = 3) -> list[str]:
    """Find past work similar to what's being asked."""
    client = _get_client()
    col    = client.get_or_create_collection("lucky_work")
    try:
        results = col.query(
            query_texts=[query],
            n_results=min(n, col.count() or 1)
        )
        return results["documents"][0] if results["documents"] else []
    except Exception:
        return []


# ── Semantic context builder ───────────────────────────────────────────────────
def build_semantic_context(query: str) -> str:
    """
    Pull relevant memories + styles for a given query.
    Gets injected into the prompt so Lucky responds with full context.
    """
    memories = recall(query, n=4)
    styles   = get_all_styles()
    similar  = find_similar_work(query, n=2)

    parts = []

    if memories:
        parts.append("Relevant past context:\n" + "\n".join(f"- {m}" for m in memories))

    if styles:
        style_str = "\n".join(f"- {k}: {v}" for k, v in styles.items())
        parts.append(f"User's style preferences:\n{style_str}")

    if similar:
        parts.append("Similar past work exists — reference it if helpful:\n" +
                     "\n".join(f"- {s[:200]}" for s in similar))

    return "\n\n".join(parts)
