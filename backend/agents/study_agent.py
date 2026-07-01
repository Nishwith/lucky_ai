import json
from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext
from backend.tools.registry import tool_registry
from backend.brain.universal_brain import brain
from backend.core.logger import logger
from backend.agents.dev_agent import parse_plan_json

class StudyAgent(BaseAgent):
    def __init__(self):
        super().__init__("Study Agent")

    async def plan(self, user_request: str, context: AgentContext) -> List[Dict[str, Any]]:
        tools = tool_registry.list_all()
        tools_str = ""
        for t in tools:
            # Study agent only uses file writing tools or read tools
            if t["name"] in ("create_file", "edit_file", "read_file"):
                tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"

        if not tools_str:
            return []

        system = f"""You are the Study Agent Planning Specialist for LUCKY AI OS.
Your job is to analyze the user study request and decide if we need to write/save notes or read files.

Available study tools:
{tools_str}

If the user wants to save study notes or a summary to a file, output a JSON array containing the file creation call:
[
  {{
    "tool_name": "create_file",
    "params": {{"path": "<filename.md>", "content": "<notes markdown content>"}}
  }}
]
Otherwise, return an empty array `[]`. Only write to files if they explicitly requested saving.
Output ONLY valid JSON.
"""
        logger.info("StudyAgent: Checking note-saving plans...")
        try:
            plan_raw = await brain.think(
                prompt=user_request,
                system=system,
                temperature=0.0
            )
            return parse_plan_json(plan_raw)
        except Exception as e:
            logger.error(f"StudyAgent planning failed: {e}")
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
        summary_prompt = f"""The user asked: "{user_request}"
Study Agent execution results: {json.dumps(results.get("step_results", []), indent=2)}

Please explain the study topic in detail. Use real-world analogies, examples, and structured note headings.
If notes were saved to a file, state the file path clearly at the end.
"""
        logger.info("StudyAgent: Building report prompts...")
        from backend.brain.prompt_builder import study_agent_system
        system_prompt = study_agent_system(memory=context.relevant_memories)
        return summary_prompt, system_prompt
