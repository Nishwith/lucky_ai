from typing import List, Dict, Any

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    async def plan(self, user_request: str, context: Any) -> List[Dict[str, Any]]:
        """
        Analyze request and context, then return a list of tool calls to execute.
        Format: [{"tool_name": str, "params": dict}]
        """
        raise NotImplementedError()

    async def execute(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute planned steps sequentially using the Tool Registry.
        """
        raise NotImplementedError()

    async def report(self, results: Dict[str, Any], user_request: str, context: Any) -> str:
        """
        Format a friendly final response summary explaining what was accomplished.
        """
        raise NotImplementedError()
