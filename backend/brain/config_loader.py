"""
Lucky AI — Config Loader
Reads config.json once. Everything imports from here.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # lucky-ai/

def load_config() -> dict:
    cfg_path = ROOT / "config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"config.json not found at {cfg_path}")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)

CFG = load_config()

# Quick access
PROVIDER   = CFG["provider"]
MODEL      = CFG["model"]
API_BASE   = CFG.get("api_base", "")
API_KEY    = CFG.get("api_key", "")
USER_NAME  = CFG["lucky"]["user_name"]
LUCKY_NAME = CFG["lucky"]["name"]
LANGUAGE   = CFG["lucky"]["language"]
DB_PATH    = ROOT / CFG["memory"]["db_path"]
VEC_PATH   = ROOT / CFG["memory"]["vector_path"]
MAX_HIST   = CFG["memory"]["max_history"]
HOST       = CFG["server"]["host"]
PORT       = CFG["server"]["port"]
