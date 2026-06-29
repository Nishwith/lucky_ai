import time
import subprocess
from pydantic import BaseModel
from backend.brain.config_loader import WORKSPACE_ROOT
from backend.tools.registry import tool
from backend.tools.schemas import ToolResult

class CommandInput(BaseModel):
    command: str
    timeout: float = 30.0

@tool("run_command", "Executes a shell command inside the workspace root.", "CONFIRM", CommandInput)
def run_command(command: str, timeout: float = 30.0) -> ToolResult:
    # Ensure workspace directory exists
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    try:
        # Use shell=True for windows command compatibility (cmd.exe or powershell)
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE_ROOT.resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        duration_ms = (time.time() - start_time) * 1000
        
        success = proc.returncode == 0
        output_data = proc.stdout if success else proc.stderr or proc.stdout
        
        meta = {
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "stdout": proc.stdout,
            "stderr": proc.stderr
        }
        
        return ToolResult(
            success=success,
            output=output_data,
            error=proc.stderr if not success else None,
            meta=meta
        )
    except subprocess.TimeoutExpired:
        duration_ms = (time.time() - start_time) * 1000
        return ToolResult(
            success=False,
            error=f"Command timed out after {timeout} seconds.",
            meta={"exit_code": -1, "duration_ms": duration_ms, "stdout": "", "stderr": "TimeoutExpired"}
        )
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return ToolResult(
            success=False,
            error=str(e),
            meta={"exit_code": -1, "duration_ms": duration_ms, "stdout": "", "stderr": str(e)}
        )
