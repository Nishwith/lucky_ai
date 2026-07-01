import json
from typing import List, Dict, Any

from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext
from backend.brain.universal_brain import brain
from backend.core.logger import logger

class PAAgent(BaseAgent):
    def __init__(self):
        super().__init__("Personal Assistant Agent")

    async def plan(self, user_request: str, context: AgentContext) -> List[Dict[str, Any]]:
        # Personal Assistant operates primarily on memory context, so no tool steps are planned today
        return []

    async def execute(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"step_results": []}

    async def report(self, results: Dict[str, Any], user_request: str, context: AgentContext) -> tuple:
        summary_prompt = f"""The user asked: "{user_request}"

Please provide a helpful personal assistant briefing or agenda.
Make it concise, alert the user of active/overdue projects, and organize immediate task items.
"""
        logger.info("PAAgent: Building report prompts...")
        from backend.brain.prompt_builder import pa_agent_system
        system_prompt = pa_agent_system(memory=context.relevant_memories)
        return summary_prompt, system_prompt
