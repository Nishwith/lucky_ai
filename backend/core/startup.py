import json
import sqlite3
import httpx
from pathlib import Path
from backend.brain.config_loader import ROOT, PROVIDER, MODEL, API_BASE, DB_PATH, VEC_PATH
from backend.core.logger import logger

# Global state to hold the validation report
STARTUP_REPORT = {
    "config_ok": False,
    "sqlite_ok": False,
    "chroma_ok": False,
    "ollama_ok": False,
    "model_ok": False,
    "degraded_mode": False,
    "errors": []
}

async def run_startup_validation() -> dict:
    global STARTUP_REPORT
    logger.info("Running startup validation...")
    
    # 1. Config check
    try:
        cfg_path = ROOT / "config.json"
        if cfg_path.exists():
            STARTUP_REPORT["config_ok"] = True
        else:
            STARTUP_REPORT["errors"].append("config.json missing")
    except Exception as e:
        STARTUP_REPORT["errors"].append(f"Config read error: {str(e)}")

    # 2. SQLite check
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        # Create a temp table to verify write
        conn.execute("CREATE TABLE IF NOT EXISTS startup_ping (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()
        STARTUP_REPORT["sqlite_ok"] = True
    except Exception as e:
        STARTUP_REPORT["errors"].append(f"SQLite write error: {str(e)}")

    # 3. ChromaDB check
    try:
        VEC_PATH.mkdir(parents=True, exist_ok=True)
        # Verify import is possible
        import chromadb
        STARTUP_REPORT["chroma_ok"] = True
    except Exception as e:
        STARTUP_REPORT["errors"].append(f"ChromaDB check error: {str(e)}")

    # 4. Provider / Model check
    if PROVIDER == "ollama":
        url = f"{API_BASE or 'http://localhost:11434'}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    STARTUP_REPORT["ollama_ok"] = True
                    data = resp.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    # Check exact match or base name match (e.g. qwen3:8b matches qwen3:8b)
                    if MODEL in models or f"{MODEL}:latest" in models or any(m.startswith(MODEL) for m in models):
                        STARTUP_REPORT["model_ok"] = True
                    else:
                        STARTUP_REPORT["errors"].append(f"Model '{MODEL}' not found in Ollama installed models: {models}")
                else:
                    STARTUP_REPORT["errors"].append(f"Ollama returned status {resp.status_code}")
        except Exception as e:
            STARTUP_REPORT["errors"].append(f"Ollama unreachable: {str(e)}")
            STARTUP_REPORT["degraded_mode"] = True
    else:
        # For non-local, assume basic ok but validate API key presence
        STARTUP_REPORT["ollama_ok"] = True
        STARTUP_REPORT["model_ok"] = True
        from backend.brain.config_loader import API_KEY
        if not API_KEY and PROVIDER in ["openai", "anthropic", "groq", "gemini", "deepseek"]:
            STARTUP_REPORT["errors"].append(f"API key missing for provider '{PROVIDER}'")
            STARTUP_REPORT["degraded_mode"] = True

    # Critical errors cause degraded mode
    if not STARTUP_REPORT["sqlite_ok"] or not STARTUP_REPORT["chroma_ok"]:
        STARTUP_REPORT["degraded_mode"] = True

    if STARTUP_REPORT["errors"]:
        logger.warning(f"Startup validated with warnings/errors: {STARTUP_REPORT['errors']}")
    else:
        logger.info("Startup validation passed successfully.")

    return STARTUP_REPORT
