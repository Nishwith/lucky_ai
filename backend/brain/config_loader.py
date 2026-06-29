"""
Lucky AI — Config Loader
Reads config.json dynamically.
"""

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent.parent  # lucky-ai/

class ConfigManager:
    def __init__(self):
        self.load()

    def load(self):
        cfg_path = ROOT / "config.json"
        if not cfg_path.exists():
            raise FileNotFoundError(f"config.json not found at {cfg_path}")
        with open(cfg_path, "r", encoding="utf-8") as f:
            self._cfg = json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        if "." in key:
            parts = key.split(".")
            val = self._cfg
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    return default
            return val if val is not None else default
        return self._cfg.get(key, default)

    def set(self, key: str, value: Any):
        cfg_path = ROOT / "config.json"
        
        # Reload current JSON
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if "." in key:
            parts = key.split(".")
            val = data
            for p in parts[:-1]:
                val = val.setdefault(p, {})
            val[parts[-1]] = value
        else:
            data[key] = value
            
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        self.load()

# Instantiate global manager
_manager = ConfigManager()

# Support module level attributes via __getattr__
def __getattr__(name: str) -> Any:
    if name == "ROOT":
        return ROOT
    if name == "CFG":
        return _manager._cfg
    
    # Map constants
    mappings = {
        "PROVIDER": lambda: _manager.get("provider"),
        "MODEL": lambda: _manager.get("model"),
        "API_BASE": lambda: _manager.get("api_base", ""),
        "API_KEY": lambda: _manager.get("api_key", ""),
        "USER_NAME": lambda: _manager.get("lucky.user_name"),
        "LUCKY_NAME": lambda: _manager.get("lucky.name"),
        "LANGUAGE": lambda: _manager.get("lucky.language"),
        "DB_PATH": lambda: ROOT / _manager.get("memory.db_path"),
        "VEC_PATH": lambda: ROOT / _manager.get("memory.vector_path"),
        "MAX_HIST": lambda: _manager.get("memory.max_history"),
        "HOST": lambda: _manager.get("server.host"),
        "PORT": lambda: _manager.get("server.port"),
        "CONTEXT_WINDOW": lambda: _manager.get("context_window", 2048),
        "WORKSPACE_ROOT": lambda: ROOT / _manager.get("execution.workspace_root", "./workspace"),
        "COMMAND_ALLOWLIST": lambda: _manager.get("execution.command_allowlist", [])
    }
    
    if name in mappings:
        return mappings[name]()
        
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
