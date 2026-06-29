import os
import sys
import uuid
import subprocess
from pydantic import BaseModel
from backend.brain.config_loader import WORKSPACE_ROOT
from backend.tools.registry import tool
from backend.tools.schemas import ToolResult

class PythonInput(BaseModel):
    code: str
    timeout: float = 30.0

@tool("run_python", "Executes an arbitrary Python code block using the current Python environment.", "CONFIRM", PythonInput)
def run_python(code: str, timeout: float = 30.0) -> ToolResult:
    # Ensure workspace root exists
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Create a unique temp file inside the workspace
    filename = f"tmp_run_{uuid.uuid4().hex}.py"
    temp_file = WORKSPACE_ROOT / filename
    
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Execute using system python executable to preserve loaded packages
        python_exe = sys.executable
        
        proc = subprocess.run(
            [python_exe, filename],
            cwd=str(WORKSPACE_ROOT.resolve()),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        
        success = proc.returncode == 0
        output_data = proc.stdout if success else proc.stderr or proc.stdout
        
        return ToolResult(
            success=success,
            output=output_data,
            error=proc.stderr if not success else None,
            meta={"exit_code": proc.returncode, "stderr": proc.stderr}
        )
    except subprocess.TimeoutExpired:
        return ToolResult(
            success=False,
            error=f"Python execution timed out after {timeout} seconds."
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=str(e)
        )
    finally:
        # Guarantee cleanup of temporary file
        if temp_file.exists():
            try:
                os.remove(temp_file)
            except Exception:
                pass
