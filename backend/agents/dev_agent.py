import json
import re
from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext
from backend.tools.registry import tool_registry
from backend.brain.universal_brain import brain
from backend.core.logger import logger

def parse_plan_json(response: str) -> list:
    # Strip markdown backticks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if match:
        response = match.group(1)
    response = response.strip()
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return data
    except Exception:
        start = response.find("[")
        end = response.rfind("]")
        if start != -1 and end != -1:
            try:
                data = json.loads(response[start:end+1])
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []

class DevAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dev Agent")

    async def plan(self, user_request: str, context: AgentContext) -> List[Dict[str, Any]]:
        tools = tool_registry.list_all()
        tools_str = ""
        for t in tools:
            tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"

        system = f"""You are the Developer Planning Specialist for LUCKY AI OS.
Your job is to analyze the user request and generate a step-by-step list of tool execution tasks to run in the workspace.

Available execution tools:
{tools_str}

Output a JSON array containing the ordered list of tool calls:
[
  {{
    "tool_name": "<name of selected tool>",
    "params": {{<parameters matching schema>}}
  }}
]

CRITICAL RULES:
1. ONLY select from the available tools list. Do not invent tools.
2. If the request does not require modifying the workspace (e.g., explaining code, syntax questions, or design discussions), return an empty array `[]`.
3. Output ONLY valid JSON. Do not include markdown code block backticks (```json), comments, or any extra text.
"""
        logger.info("DevAgent: Planning steps...")
        try:
            from backend.brain.model_router import get_model_for_agent
            plan_raw = await brain.think_with(
                model=get_model_for_agent("coding"),
                prompt=user_request,
                system=system
            )
            return parse_plan_json(plan_raw)
        except Exception as e:
            logger.error(f"DevAgent planning failed: {e}")
            return []

    async def execute(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for step in steps:
            tool_name = step.get("tool_name")
            params = step.get("params", {})
            logger.info(f"DevAgent: Executing '{tool_name}' with {params}")
            res = await tool_registry.execute(tool_name, params)
            results.append({
                "tool_name": tool_name,
                "params": params,
                "success": res.success,
                "output": res.output,
                "error": res.error
            })
            if not res.success:
                logger.warning(f"DevAgent execution halted at step '{tool_name}' due to failure.")
                break
        return {"step_results": results}

    async def report(self, results: Dict[str, Any], user_request: str, context: AgentContext) -> tuple:
        summary_prompt = f"""The user requested: "{user_request}"
The Dev Agent executed the following steps:
{json.dumps(results.get("step_results", []), indent=2)}

Please summarize the outcome to the user.
- Explain clearly what was accomplished.
- State file locations or command outputs.
- If any step failed or timed out, report the error detail clearly.
"""
        logger.info("DevAgent: Building report prompts...")
        from backend.brain.prompt_builder import dev_agent_system
        system_prompt = dev_agent_system(memory=context.relevant_memories)
        return summary_prompt, system_prompt
