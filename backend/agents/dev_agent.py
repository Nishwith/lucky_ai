import json
import re
import asyncio
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
    "params": {{...}},
    "dependencies": []
  }}
]

CRITICAL RULES:
1. ONLY select from the available tools list. Do not invent tools.
2. For any file creation or editing task (like `create_file` or `edit_file`), do NOT generate the actual code content. Instead, set the parameter `"content": "__GENERATE__"`.
3. Plan the complete list of files and commands required to build a fully functional, production-ready project. For example, if generating a project, plan the requirements.txt, Dockerfile, CRUD, schemas, database, config, README, and verification commands.
4. Define the `"dependencies"` array containing the task_id strings of other tasks that MUST complete before this task can run (e.g., models.py depends on database.py). If a task has no dependencies, set it to `[]`. Tasks without dependencies will execute concurrently.
5. Output ONLY valid JSON array. Do not include markdown code block backticks (```json), comments, or any extra text.
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
            deps_str = f" (Depends on: {', '.join(s.get('dependencies', []))})" if s.get('dependencies') else ""
            plan_md += f"- **Task {s.get('task_id')}**: {s.get('name')} (`{s.get('tool_name')}`){deps_str}\n"
        plan_md += "\n**Execution Plan Prepared. Starting queue execution...**\n\n---\n\n"
        yield plan_md

        # Execute queue with Dependency Graph scheduling
        import time
        
        completed_tasks = {}  # task_id -> success_bool
        task_outputs = {}  # task_id -> {"tool_name": str, "params": dict}
        running_tasks = set()
        active_producers = []
        token_queue = asyncio.Queue()
        
        async def run_single_task(step):
            tid = step.get("task_id", str(len(completed_tasks) + 1))
            name = step.get("name", "Unnamed Task")
            tool_name = step.get("tool_name")
            params = step.get("params", {})
            
            yield f"⏳ **Running (Task {tid})**: {name}...\n"
            
            # Check for code generation
            if tool_name in ("create_file", "edit_file") and params.get("content") == "__GENERATE__":
                path = params.get("path", "file.txt")
                yield f"   🧠 Generating source code content for `{path}` (Task {tid})...\n"
                
                # Compile context of dependency files only
                deps = step.get("dependencies", [])
                dep_files_context = ""
                for dep_id in deps:
                    dep_info = task_outputs.get(dep_id)
                    if dep_info and dep_info["tool_name"] == "create_file":
                        p_path = dep_info["params"].get("path")
                        p_content = dep_info["params"].get("content", "")
                        dep_files_context += f"### Dependency File: {p_path}\n```python\n{p_content}\n```\n\n"
                
                generator_prompt = f"""You are generating the content for `{path}`.
User's Overall Goal: "{user_request}"
Complete Project Plan:
{json.dumps(steps, indent=2)}

Dependency files in workspace that this file depends on:
{dep_files_context}

Generate the COMPLETE, production-ready code content for `{path}`.
CRITICAL: Do NOT write markdown code blocks (```python ... ```) or any explanations. Output ONLY the raw contents of the file.
"""
                try:
                    file_content = await brain.think_with(
                        model=get_model_for_agent("coding"),
                        prompt=generator_prompt,
                        system="You are a code generator. Output raw file content only. No markdown ticks, no conversational text."
                    )
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
                    yield f"   ❌ **Generation Error** for `{path}` (Task {tid}): {gen_err}\n\n"
                    completed_tasks[tid] = False
                    return
            
            # Execute tool call with Retry Policy (up to 2 retries)
            max_retries = 2
            success = False
            error = ""
            res = None
            
            for attempt in range(max_retries + 1):
                if attempt > 0:
                    yield f"   🔄 **Retrying (Task {tid})** (Attempt {attempt}/{max_retries})...\n"
                    await asyncio.sleep(1.0)
                try:
                    res = await tool_registry.execute(tool_name, params)
                    success = res.success
                    error = res.error
                except Exception as exec_err:
                    success = False
                    error = str(exec_err)
                    
                if success:
                    # Verification check
                    yield f"   🔍 Verifying (Task {tid})...\n"
                    from backend.tools.verification import verify_tool_execution
                    verified, ver_msg = await verify_tool_execution(tool_name, params, success, res.output, error)
                    if verified:
                        yield f"   ✓ **Verified (Task {tid})**: {ver_msg}\n\n"
                        completed_tasks[tid] = True
                        task_outputs[tid] = {"tool_name": tool_name, "params": params}
                        break
                    else:
                        yield f"   ❌ **Verification Attempt Failed (Task {tid})**: {ver_msg}\n"
                        error = ver_msg
                else:
                    yield f"   ❌ **Execution Attempt Failed (Task {tid})**: {error}\n"
            
            if not completed_tasks.get(tid):
                completed_tasks[tid] = False

        async def queue_producer(step):
            tid = step.get("task_id")
            try:
                async for token in run_single_task(step):
                    await token_queue.put(token)
            except Exception as pe:
                await token_queue.put(f"⚠️ Task wrapper error for Task {tid}: {pe}\n\n")
            finally:
                running_tasks.remove(tid)

        # Scheduler execution loop
        start_time = time.time()
        while len(completed_tasks) < len(steps):
            # Check if any step failed. If a step fails, we halt execution.
            if any(val is False for val in completed_tasks.values()):
                break
                
            # Find ready steps
            ready_steps = []
            for s in steps:
                tid = s.get("task_id")
                if tid in completed_tasks or tid in running_tasks:
                    continue
                deps = s.get("dependencies", [])
                if all(completed_tasks.get(dep_id) is True for dep_id in deps):
                    ready_steps.append(s)
            
            # Start ready steps
            for step in ready_steps:
                running_tasks.add(step.get("task_id"))
                t = asyncio.create_task(queue_producer(step))
                active_producers.append(t)
            
            # Yield any currently buffered tokens from queue
            while not token_queue.empty():
                yield await token_queue.get()
                
            if running_tasks:
                try:
                    # Bounded wait for a token to avoid spinning CPU
                    token = await asyncio.wait_for(token_queue.get(), timeout=0.2)
                    yield token
                except asyncio.TimeoutError:
                    pass
            else:
                # No tasks are running and no new tasks are ready
                break
                
        # Clean up any leftover tasks
        for t in active_producers:
            if not t.done():
                t.cancel()
        
        # Pull any final tokens remaining in the queue
        while not token_queue.empty():
            yield await token_queue.get()
            
        all_ok = len(completed_tasks) == len(steps) and all(completed_tasks.values())
        duration = time.time() - start_time
        
        if all_ok:
            yield f"---\n\n🏁 **Execution completed successfully.**\n"
            yield f"Execution time: {duration:.1f} seconds.\n\n"
        else:
            yield f"---\n\n⚠️ **Execution halted prematurely due to a step failure.**\n\n"
            
        # Final Summary Report Think Stream
        yield "### 📝 Summary Report:\n"
        
        # Format list of results for summary LLM
        summary_results = [
            {"task_id": tid, "name": s.get("name"), "success": completed_tasks.get(tid, False)}
            for tid, s in [(s.get("task_id"), s) for s in steps]
        ]
        
        summary_prompt = f"""The user requested: "{user_request}"
We executed the following steps:
{json.dumps(summary_results, indent=2)}

Please provide a concise final summary report for the user. Mention files that were created, commands that were run, and next steps. Keep it brief.
"""
        async for token in brain.think_stream(
            prompt=summary_prompt,
            system="You are the system coordinator. Synthesize the completed tasks status.",
            temperature=0.5
        ):
            yield token
