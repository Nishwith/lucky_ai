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

# ── GLOBAL INITIALIZATION (THE FIX) ────────────────────────────────────────────
# We initialize the database ONCE when the server boots. 
# This prevents the massive lag on every chat message.
VEC_PATH.mkdir(parents=True, exist_ok=True)
_client = chromadb.PersistentClient(
    path=str(VEC_PATH),
    settings=Settings(anonymized_telemetry=False)  # Kills the telemetry spam
)

# Load collections into RAM instantly
_memory_col = _client.get_or_create_collection("lucky_memory")
_style_col  = _client.get_or_create_collection("lucky_style")
_work_col   = _client.get_or_create_collection("lucky_work")

def init_vector_db():
    print("[Lucky AI Memory] ChromaDB initialized ✓")


# ── Core memory operations ─────────────────────────────────────────────────────
def remember(text: str, category: str = "general", metadata: dict = None):
    """Store any piece of information in semantic memory."""
    uid = str(time.time())
    _memory_col.add(
        documents=[text],
        ids=[uid],
        metadatas=[{
            "category": category,
            "time":     datetime.datetime.now().isoformat(),
            **(metadata or {})
        }]
    )

def recall(query: str, n: int = 5, category: str = None) -> list[str]:
    """Find the most relevant memories, filtered by relevance score."""
    try:
        where = {"category": category} if category else None
        
        # We must explicitly ask for 'distances' to measure relevance
        results = _memory_col.query(
            query_texts=[query],
            n_results=min(n, _memory_col.count() or 1),
            where=where,
            include=["documents", "distances"] 
        )
        
        if not results["documents"] or not results["documents"][0]:
            return []
            
        docs = results["documents"][0]
        distances = results["distances"][0]
        
        # ✅ THE FILTER: Only keep memories with a strong mathematical match
        # ChromaDB uses L2 distance by default. Lower is better. 
        # A threshold of 1.25 is an excellent cut-off for "actually relevant".
        relevant_memories = []
        for doc, dist in zip(docs, distances):
            if dist < 1.25:  
                relevant_memories.append(doc)
                
        return relevant_memories
        
    except Exception as e:
        print(f"Memory search error: {e}")
        return []


# ── Style memory (coding style, content tone, preferences) ────────────────────
def save_style(domain: str, description: str):
    """
    Save how the user likes things done in a specific domain.
    """
    try:
        _style_col.delete(where={"domain": domain})
    except Exception:
        pass
        
    _style_col.add(
        documents=[description],
        ids=[f"style_{domain}_{int(time.time())}"],
        metadatas=[{"domain": domain, "updated": datetime.datetime.now().isoformat()}]
    )

def get_style(domain: str) -> str:
    """Retrieve the user's style for a specific domain."""
    try:
        results = _style_col.query(
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
    try:
        results = _style_col.get()
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
    _work_col.add(
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
    try:
        results = _work_col.query(
            query_texts=[query],
            n_results=min(n, _work_col.count() or 1)
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