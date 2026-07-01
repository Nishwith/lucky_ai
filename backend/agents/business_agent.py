import json
from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext
from backend.tools.registry import tool_registry
from backend.brain.universal_brain import brain
from backend.core.logger import logger
from backend.agents.dev_agent import parse_plan_json

class BusinessAgent(BaseAgent):
    def __init__(self):
        super().__init__("Business Agent")

    async def plan(self, user_request: str, context: AgentContext) -> List[Dict[str, Any]]:
        tools = tool_registry.list_all()
        tools_str = ""
        for t in tools:
            if t["name"] in ("create_file", "edit_file"):
                tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"

        system = f"""You are the Business Agent Planning Specialist for LUCKY AI OS.
Your job is to decide if we need to save the business proposal, email, client template, or analysis to a file.

Available tools:
{tools_str}

If the user wants to save a proposal, invoice template, outreach template, or analysis to a file, output a JSON array containing the file creation call:
[
  {{
    "tool_name": "create_file",
    "params": {{"path": "<filename.md>", "content": "<proposal markdown content>"}}
  }}
]
Otherwise, return an empty array `[]`. Output ONLY valid JSON.
"""
        logger.info("BusinessAgent: Checking file plan...")
        try:
            plan_raw = await brain.think(
                prompt=user_request,
                system=system,
                temperature=0.0
            )
            return parse_plan_json(plan_raw)
        except Exception as e:
            logger.error(f"BusinessAgent planning failed: {e}")
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
Business Agent execution details: {json.dumps(results.get("step_results", []), indent=2)}

Please write the client email, sales proposal, or analysis. Use a clear, value-focused, conversational business tone.
If any file was saved, clearly outline the filename.
"""
        logger.info("BusinessAgent: Building report prompts...")
        from backend.brain.prompt_builder import business_agent_system
        system_prompt = business_agent_system(memory=context.relevant_memories)
        return summary_prompt, system_prompt
