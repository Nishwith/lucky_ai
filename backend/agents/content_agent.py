import json
from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext
from backend.tools.registry import tool_registry
from backend.brain.universal_brain import brain
from backend.core.logger import logger
from backend.agents.dev_agent import parse_plan_json

class ContentAgent(BaseAgent):
    def __init__(self):
        super().__init__("Content Agent")

    async def plan(self, user_request: str, context: AgentContext) -> List[Dict[str, Any]]:
        tools = tool_registry.list_all()
        tools_str = ""
        for t in tools:
            if t["name"] in ("create_file", "edit_file"):
                tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"

        system = f"""You are the Content Agent Planning Specialist for LUCKY AI OS.
Your job is to analyze the request and decide if we need to write/save generated content to a file.

Available tools:
{tools_str}

If the user wants to save a script, article, post, or draft to a file, output a JSON array containing the file creation call:
[
  {{
    "tool_name": "create_file",
    "params": {{"path": "<filename.md>", "content": "<markdown content>"}}
  }}
]
Otherwise, return an empty array `[]`. Output ONLY valid JSON.
"""
        logger.info("ContentAgent: Checking file plan...")
        try:
            plan_raw = await brain.think(
                prompt=user_request,
                system=system,
                temperature=0.0
            )
            return parse_plan_json(plan_raw)
        except Exception as e:
            logger.error(f"ContentAgent planning failed: {e}")
            return []

    async def execute(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for step in steps:
            tool_name = step.get("tool_name")
            params = step.get("params", {})
            res = await tool_registry.execute(tool_name, params)
            results.append({
                "tool_name": tool_name,
                "params": params,
                "success": res.success,
                "output": res.output,
                "error": res.error
            })
        return {"step_results": results}

    async def report(self, results: Dict[str, Any], user_request: str, context: AgentContext) -> tuple:
        summary_prompt = f"""The user requested: "{user_request}"
Content Agent execution details: {json.dumps(results.get("step_results", []), indent=2)}

Please write the script, post, hook, or article according to the user request.
If any file was successfully saved, mention the path clearly.
"""
        logger.info("ContentAgent: Building report prompts...")
        from backend.brain.prompt_builder import content_agent_system
        system_prompt = content_agent_system(memory=context.relevant_memories)
        return summary_prompt, system_prompt
