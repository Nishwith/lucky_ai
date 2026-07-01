import py_compile
from pathlib import Path
from backend.brain.config_loader import WORKSPACE_ROOT
from backend.core.logger import logger

async def verify_tool_execution(tool_name: str, params: dict, success: bool, output: any, error: str) -> tuple[bool, str]:
    """
    Verifies the success and correctness of a tool execution.
    Returns: (is_verified: bool, message: str)
    """
    if not success:
        return False, f"Execution failed: {error}"
        
    try:
        if tool_name == "create_file":
            path = params.get("path", "")
            file_path = (WORKSPACE_ROOT / path).resolve()
            if not file_path.exists():
                return False, f"File '{path}' does not exist on disk."
            if file_path.stat().st_size == 0:
                return False, f"File '{path}' is empty."
            # Python syntax check
            if file_path.suffix == ".py":
                try:
                    py_compile.compile(str(file_path), doraise=True)
                except Exception as compile_err:
                    return False, f"Python syntax error in '{path}': {compile_err}"
            return True, f"File '{path}' created and syntax-verified."
            
        elif tool_name == "edit_file":
            path = params.get("path", "")
            file_path = (WORKSPACE_ROOT / path).resolve()
            if not file_path.exists():
                return False, f"File '{path}' does not exist after edit."
            # Python syntax check
            if file_path.suffix == ".py":
                try:
                    py_compile.compile(str(file_path), doraise=True)
                except Exception as compile_err:
                    return False, f"Python syntax error after edit in '{path}': {compile_err}"
            return True, f"File '{path}' edited and syntax-verified."
            
        elif tool_name == "scaffold_project":
            proj_name = params.get("project_name", "")
            proj_path = (WORKSPACE_ROOT / proj_name).resolve()
            if not proj_path.exists() or not proj_path.is_dir():
                return False, f"Project directory '{proj_name}' was not created."
            return True, f"Project '{proj_name}' scaffolded successfully."
            
        elif tool_name == "run_command":
            # Command execution tool returns success=True if subprocess completed
            return True, "Command executed."
            
        # Default verification for other tools
        return True, "Tool completed successfully."
        
    except Exception as e:
        logger.error(f"Verification engine error: {e}", exc_info=True)
        return False, f"Verification error: {str(e)}"
