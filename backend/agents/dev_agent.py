import json
import re
from typing import List, Dict, Any, AsyncGenerator, Optional

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

    async def run_stream(self, user_request: str, context: AgentContext, history: list) -> AsyncGenerator[str, None]:
        """
        Autonomous execution stream for the DevAgent.
        Plans a task graph, executes tools immediately, generates code on-demand,
        verifies each file, and reports progress live.
        """
        tools = tool_registry.list_all()
        tools_str = ""
        for t in tools:
            tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"

        system_prompt = f"""You are the Developer Planning Specialist for LUCKY AI OS.
Your job is to analyze the user request and generate a complete step-by-step Execution Plan to run in the workspace to fulfill the user request.

Available execution tools:
{tools_str}

Output a JSON array containing the ordered list of tasks:
[
  {{
    "task_id": "1",
    "name": "<short descriptive name of this task>",
    "tool_name": "<name of selected tool>",
    "params": {{<parameters matching schema>}}
  }}
]

CRITICAL RULES:
1. ONLY select from the available tools list. Do not invent tools.
2. For any file creation or editing task (like `create_file` or `edit_file`), do NOT generate the actual code content. Instead, set the parameter `"content": "__GENERATE__"`.
3. Plan the complete list of files and commands required to build a fully functional, production-ready project. For example, if generating a project, plan the requirements.txt, Dockerfile, CRUD, schemas, database, config, README, and verification commands.
4. Output ONLY valid JSON array. Do not include markdown code block backticks (```json), comments, or any extra text.
"""
        logger.info("DevAgent: Compiling task-graph plan...")
        yield "⚙️ Dev Agent is compiling workspace execution plan...\n\n"
        
        try:
            from backend.brain.model_router import get_model_for_agent
            plan_raw = await brain.think_with(
                model=get_model_for_agent("coding"),
                prompt=user_request,
                system=system_prompt
            )
            steps = parse_plan_json(plan_raw)
        except Exception as e:
            logger.error(f"DevAgent planning failed: {e}")
            steps = []

        if not steps:
            # Fall back to standard conversational response stream
            yield "📝 No tool operations needed. Answering conversational request...\n\n"
            async for token in brain.think_stream(
                prompt=user_request,
                system="You are the default developer agent system context.",
                history=history,
                temperature=0.5
            ):
                yield token
            return

        # Format and display the execution plan
        plan_md = "### 📋 Prepared Autonomous Execution Plan:\n"
        for s in steps:
            plan_md += f"- **Task {s.get('task_id')}**: {s.get('name')} (`{s.get('tool_name')}`)\n"
        plan_md += "\n**Execution Plan Prepared. Starting queue execution...**\n\n---\n\n"
        yield plan_md

        # Execute queue
        executed_steps = []
        import time
        start_time = time.time()
        
        for idx, step in enumerate(steps):
            task_id = step.get("task_id", str(idx + 1))
            name = step.get("name", "Unnamed Task")
            tool_name = step.get("tool_name")
            params = step.get("params", {})
            
            yield f"⏳ **Running Task {task_id}/{len(steps)}**: {name}...\n"
            
            # Check for on-demand code generation
            if tool_name in ("create_file", "edit_file") and params.get("content") == "__GENERATE__":
                path = params.get("path", "file.txt")
                yield f"   🧠 Generating source code content for `{path}`...\n"
                
                # Assemble previous files context
                prev_files_context = ""
                for prev in executed_steps:
                    if prev["tool_name"] == "create_file" and prev.get("success"):
                        p_path = prev["params"].get("path")
                        p_content = prev["params"].get("content", "")
                        prev_files_context += f"### File: {p_path}\n```python\n{p_content}\n```\n\n"
                
                generator_prompt = f"""You are generating the content for `{path}`.
User's Overall Goal: "{user_request}"
Complete Project Plan:
{json.dumps(steps, indent=2)}

Previously written files in workspace:
{prev_files_context}

Generate the COMPLETE, production-ready code content for `{path}`.
CRITICAL: Do NOT write markdown code blocks (```python ... ```) or any explanations. Output ONLY the raw contents of the file.
"""
                try:
                    file_content = await brain.think_with(
                        model=get_model_for_agent("coding"),
                        prompt=generator_prompt,
                        system="You are a code generator. Output raw file content only. No markdown ticks, no conversational text."
                    )
                    # Clean potential markdown ticks if LLM hallucinated them
                    file_content = file_content.strip()
                    if file_content.startswith("```"):
                        lines = file_content.splitlines()
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        file_content = "\n".join(lines)
                    params["content"] = file_content
                except Exception as gen_err:
                    yield f"   ❌ **Generation Error** for `{path}`: {gen_err}\n\n"
                    break
            
            # Execute tool call
            try:
                res = await tool_registry.execute(tool_name, params)
                success = res.success
                output = res.output
                error = res.error
            except Exception as exec_err:
                success = False
                output = None
                error = str(exec_err)
                
            executed_steps.append({
                "tool_name": tool_name,
                "params": params,
                "success": success,
                "output": output,
                "error": error
            })
            
            if not success:
                yield f"   ❌ **Failed**: {name} - {error}\n\n"
                break
                
            # Perform Verification
            yield "   🔍 Verifying execution step...\n"
            try:
                from backend.brain.config_loader import WORKSPACE_ROOT
                if tool_name == "create_file":
                    file_path = WORKSPACE_ROOT / params.get("path", "")
                    if not file_path.exists():
                        raise AssertionError(f"File '{params.get('path')}' does not exist on disk.")
                    if file_path.stat().st_size == 0:
                        raise AssertionError(f"File '{params.get('path')}' is empty.")
                    # Compile python checks
                    if file_path.suffix == ".py":
                        import py_compile
                        py_compile.compile(str(file_path), doraise=True)
                yield f"   ✓ **Verified**: {name} succeeded.\n\n"
            except Exception as ver_err:
                yield f"   ❌ **Verification Failed** for {name}: {ver_err}\n\n"
                break
        
        # Check if all steps completed successfully
        all_ok = len(executed_steps) == len(steps) and all(s["success"] for s in executed_steps)
        duration = time.time() - start_time
        
        if all_ok:
            yield f"---\n\n🏁 **Execution completed successfully.**\n"
            yield f"Execution time: {duration:.1f} seconds.\n\n"
        else:
            yield f"---\n\n⚠️ **Execution halted prematurely due to a step failure.**\n\n"
            
        # Final Summary Report Think Stream
        yield "### 📝 Summary Report:\n"
        summary_prompt = f"""The user requested: "{user_request}"
We executed the following steps:
{json.dumps(executed_steps, indent=2)}

Please provide a concise final summary report for the user. Mention files that were created, commands that were run, and next steps. Keep it brief.
"""
        async for token in brain.think_stream(
            prompt=summary_prompt,
            system="You are the system coordinator. Synthesize the completed tasks status.",
            temperature=0.5
        ):
            yield token
