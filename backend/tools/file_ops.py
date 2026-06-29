import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from backend.brain.config_loader import WORKSPACE_ROOT
from backend.tools.registry import tool
from backend.tools.schemas import ToolResult

# ── Path Resolution Helper (With Traversal Protection) ───────────────────────
def resolve_path(relative_path: str) -> Path:
    """Resolves path relative to the workspace, defending against traversal attacks."""
    # Ensure the root exists
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    
    safe_root = WORKSPACE_ROOT.resolve()
    
    # Handle absolute paths if passed incorrectly by translating them relative to root
    if Path(relative_path).is_absolute():
        # Strip drive letter and leading slashes
        pure_path = Path(relative_path).relative_to(Path(relative_path).anchor)
        target_path = Path(safe_root / pure_path).resolve()
    else:
        target_path = Path(safe_root / relative_path).resolve()
        
    # Boundary check
    if not str(target_path).startswith(str(safe_root)):
        raise PermissionError(f"Security error: path '{relative_path}' traverses outside workspace directory.")
        
    return target_path

# ── Pydantic Inputs ───────────────────────────────────────────────────────────
class PathInput(BaseModel):
    path: str

class CreateFileInput(BaseModel):
    path: str
    content: str

class EditFileInput(BaseModel):
    path: str
    target_content: str
    replacement_content: str

class ListFilesInput(BaseModel):
    path: str = "."

# ── Tools Registration ────────────────────────────────────────────────────────
@tool("list_files", "Lists all files and subdirectories inside a directory.", "AUTO", ListFilesInput)
def list_files(path: str = ".") -> ToolResult:
    try:
        target = resolve_path(path)
        if not target.exists():
            return ToolResult(success=False, error=f"Directory '{path}' does not exist.")
        if not target.is_dir():
            return ToolResult(success=False, error=f"Path '{path}' is not a directory.")
            
        items = []
        for entry in os.scandir(target):
            # Compute relative path for cleaner output
            rel = os.path.relpath(entry.path, WORKSPACE_ROOT)
            items.append({
                "name": entry.name,
                "path": rel.replace("\\", "/"),
                "is_dir": entry.is_dir(),
                "size": entry.stat().st_size if entry.is_file() else None
            })
        return ToolResult(success=True, output=items)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool("read_file", "Reads the textual content of a file from the workspace.", "AUTO", PathInput)
def read_file(path: str) -> ToolResult:
    try:
        target = resolve_path(path)
        if not target.exists():
            return ToolResult(success=False, error=f"File '{path}' does not exist.")
        if not target.is_file():
            return ToolResult(success=False, error=f"Path '{path}' is not a file.")
            
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool("create_file", "Creates a new file with specified content.", "CONFIRM", CreateFileInput)
def create_file(path: str, content: str) -> ToolResult:
    try:
        target = resolve_path(path)
        # Ensure parent directories exist
        target.parent.mkdir(parents=True, exist_ok=True)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return ToolResult(success=True, output=f"File created successfully at: {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool("edit_file", "Modifies an existing file by finding and replacing a block of text.", "CONFIRM", EditFileInput)
def edit_file(path: str, target_content: str, replacement_content: str) -> ToolResult:
    try:
        target = resolve_path(path)
        if not target.exists():
            return ToolResult(success=False, error=f"File '{path}' does not exist.")
            
        with open(target, "r", encoding="utf-8") as f:
            content = f.read()
            
        if target_content not in content:
            return ToolResult(success=False, error="Target content block to replace was not found in the file.")
            
        # Perform single exact replace
        new_content = content.replace(target_content, replacement_content, 1)
        
        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)
        return ToolResult(success=True, output=f"File '{path}' updated successfully.")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool("delete_file", "Permanently deletes a file from the workspace.", "CONFIRM", PathInput)
def delete_file(path: str) -> ToolResult:
    try:
        target = resolve_path(path)
        if not target.exists():
            return ToolResult(success=False, error=f"Path '{path}' does not exist.")
        if target.is_dir():
            return ToolResult(success=False, error="Target is a directory. Use delete_folder tools or verify paths.")
            
        os.remove(target)
        return ToolResult(success=True, output=f"File '{path}' deleted successfully.")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


@tool("create_folder", "Creates a directory tree structure in the workspace.", "CONFIRM", PathInput)
def create_folder(path: str) -> ToolResult:
    try:
        target = resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, output=f"Directory created successfully at: {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
