import inspect
from typing import Callable, Dict, Any, Type, Optional, List
from pydantic import BaseModel
from backend.tools.schemas import ToolResult
from backend.tools.permissions import check_permission
from backend.core.logger import logger

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, permission_level: str = "CONFIRM", input_model: Optional[Type[BaseModel]] = None):
        """Decorator to register a function as a system tool."""
        def decorator(func: Callable):
            self._tools[name] = {
                "func": func,
                "name": name,
                "description": description,
                "permission_level": permission_level,
                "input_model": input_model
            }
            logger.debug(f"Registered tool: {name} (Permission: {permission_level})")
            return func
        return decorator

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all tools with metadata and schema for client discovery."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "permission_level": t["permission_level"],
                "input_schema": t["input_model"].schema() if t["input_model"] else {}
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, params: dict) -> ToolResult:
        """Executes a tool with parameters after checking permission levels."""
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{name}' not found.")

        # 1. Parameter Validation
        input_model = tool["input_model"]
        if input_model:
            try:
                validated_params = input_model(**params)
                params_dict = validated_params.dict()
            except Exception as e:
                logger.warning(f"Parameter validation failed for tool '{name}': {e}")
                return ToolResult(success=False, error=f"Invalid arguments: {str(e)}")
        else:
            params_dict = params

        # 2. Gated Permission Check (Blocks async if level is CONFIRM)
        try:
            await check_permission(name, params_dict, tool["permission_level"])
        except PermissionError as e:
            return ToolResult(success=False, error=str(e))
        except Exception as e:
            return ToolResult(success=False, error=f"Security manager error: {str(e)}")

        # 3. Execution
        func = tool["func"]
        try:
            logger.info(f"Executing tool '{name}' with args: {params_dict}")
            if inspect.iscoroutinefunction(func):
                result = await func(**params_dict)
            else:
                result = func(**params_dict)

            # Normalize output
            if isinstance(result, ToolResult):
                return result
            return ToolResult(success=True, output=result)
        except Exception as e:
            logger.error(f"Error occurred during execution of '{name}': {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

# Global singleton tool registry
tool_registry = ToolRegistry()

# Decorator export shortcut
tool = tool_registry.register
