import psutil
import shutil
import subprocess
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from backend.brain.config_loader import PROVIDER, MODEL, API_BASE, USER_NAME
from backend.core.state import system_state
from backend.core.startup import STARTUP_REPORT, run_startup_validation

router = APIRouter()

class ModelSwitchRequest(BaseModel):
    provider: Optional[str] = None
    model: str

def get_gpu_metrics() -> Optional[Dict[str, float]]:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        # Run nvidia-smi command to query GPU utilization and memory info
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.total,memory.used", "--format=csv,noheader,nounits"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1
        )
        if res.returncode == 0:
            parts = res.stdout.strip().split(",")
            if len(parts) >= 3:
                return {
                    "gpu_util": float(parts[0].strip()),
                    "vram_total": float(parts[1].strip()) * 1024 * 1024,  # convert MB to Bytes
                    "vram_used": float(parts[2].strip()) * 1024 * 1024
                }
    except Exception:
        pass
    return None

async def list_models_internal() -> List[Dict[str, Any]]:
    from backend.brain.config_loader import PROVIDER, MODEL, API_BASE
    if PROVIDER != "ollama":
        return [{"name": MODEL, "details": {"parameter_size": "N/A"}}]
    
    url = f"{API_BASE or 'http://localhost:11434'}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json().get("models", [])
    except Exception:
        pass
    return []

@router.get("/system/metrics")
async def get_system_metrics():
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "ram": {
            "total": ram.total,
            "used": ram.used,
            "percent": ram.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "percent": disk.percent
        },
        "gpu": get_gpu_metrics()
    }

@router.get("/system/status")
async def get_system_status():
    from backend.brain.config_loader import PROVIDER, MODEL
    return {
        "status": "degraded" if STARTUP_REPORT["degraded_mode"] else "online",
        "system_state": system_state.current_state,
        "provider": PROVIDER,
        "model": MODEL,
        "startup_report": STARTUP_REPORT
    }

@router.get("/system/models")
async def get_installed_models():
    models = await list_models_internal()
    return {"models": models}

@router.post("/system/model")
async def switch_model(req: ModelSwitchRequest):
    from backend.brain.config_loader import _manager
    
    # Update active config dynamically
    if req.provider:
        _manager.set("provider", req.provider)
    _manager.set("model", req.model)
    
    # Re-validate new model and service availability
    report = await run_startup_validation()
    
    from backend.core.state import SystemState
    if report["degraded_mode"]:
        system_state.transition_to(SystemState.ERROR, f"Switched to model {req.model} (degraded mode)")
    else:
        system_state.transition_to(SystemState.READY, f"Switched to model {req.model}")
        
    return {
        "success": True,
        "active_provider": _manager.get("provider"),
        "active_model": _manager.get("model"),
        "startup_report": report
    }
