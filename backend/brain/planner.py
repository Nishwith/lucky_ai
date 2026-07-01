import json
import re
import time
from typing import Optional, AsyncGenerator, Dict, Any, List

# Word-boundary pattern compiled once at import time
_TOOL_KEYWORDS = [
    "run", "execute", "command", "terminal", "python", "pip", "npm", "git", "node",
    "create", "delete", "write", "edit", "remove", "save", "list", "read", "folder",
    "directory", "scaffold", "template", "file", "make", "version", "install", "shell",
    "check", "show", "open", "output", "print", "start", "stop", "test", "build",
    "deploy", "mkdir", "touch", "cat", "ls", "dir", "pwd", "cd"
]
_TOOL_KEYWORD_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(k) for k in _TOOL_KEYWORDS) + r')\b',
    re.IGNORECASE
)
from backend.brain.universal_brain import brain
from backend.tools.registry import tool_registry
from backend.tools.schemas import ToolResult
from backend.core.logger import logger
from backend.core.state import system_state, SystemState

def build_planner_prompt(tools: List[Dict[str, Any]]) -> str:
    tools_str = ""
    for t in tools:
        tools_str += f"- Tool: '{t['name']}'\n  Description: {t['description']}\n  Parameters Schema: {t['input_schema']}\n\n"
        
    return f"""You are the Planning and Routing Coordinator for LUCKY AI OS.
Your job is to analyze the user's request and determine if it requires executing a system tool.

Available tools in the OS:
{tools_str}

Analyze the user request:
- If a registered tool is needed to fulfill the request, output EXACTLY a JSON object with:
  {{
    "need_tool": true,
    "tool_name": "<name of selected tool>",
    "params": {{<parameters matching the schema>}}
  }}
- If the request is conversational, general knowledge, or can be answered without tools, output EXACTLY a JSON object with:
  {{
    "need_tool": false
  }}

CRITICAL RULES:
1. Only select from the available tools list above. Do not invent tools.
2. ONLY select a tool if the user explicitly requests a real-world action (e.g., write/create a file, delete a file, run a shell command, run python code, list directory, scaffold a project).
3. If they are asking you to "write code", "explain a concept", "how to write a FastAPI app", or general questions, set "need_tool" to false. Do NOT write a file or run a command for conversational code questions unless they explicitly say "create file X" or "save to file".
4. If the user asks to run a command or script (e.g., git, pip, python version, node version), select 'run_command'.
5. Extract parameters carefully from the user request matching the schema.
6. Output ONLY valid JSON. Do not include markdown code block backticks (```json), comments, or any extra text.
"""

def clean_json_response(response: str) -> dict:
    # Strip markdown code blocks if present
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
    if match:
        response = match.group(1)
    response = response.strip()
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Regex search for first { and last }
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(response[start:end+1])
            except Exception:
                pass
    return {"need_tool": False}

def matches_tool_keywords(message: str) -> bool:
    """Pre-filtering using word-boundary regex to avoid false positives like 'running' matching 'run'."""
    return bool(_TOOL_KEYWORD_PATTERN.search(message))

def get_deterministic_decision(message: str) -> Optional[dict]:
    """Deterministically route common system commands without LLM overhead."""
    # Check deterministic run command pattern
    # e.g. "run python --version" -> run_command
    # E.g. "execute git status" -> run_command
    match_run = re.match(r"^\s*(?:run|execute)\s+([^\n\r]+)$", message, re.IGNORECASE)
    if match_run:
        cmd = match_run.group(1).strip()
        return {
            "need_tool": True,
            "tool_name": "run_command",
            "params": {"command": cmd}
        }

    # Check deterministic list files pattern
    # e.g. "list files", "list workspace files", "list directory", "ls", "dir"
    match_list = re.match(r"^\s*(?:list\s+files|list\s+workspace\s+files|list\s+directory|ls|dir)\s*$", message, re.IGNORECASE)
    if match_list:
        return {
            "need_tool": True,
            "tool_name": "list_files",
            "params": {"path": "."}
        }

    return None

async def plan_and_execute_stream(
    message: str,
    system_prompt: str,
    history: list
) -> Optional[AsyncGenerator[str, None]]:
    """
    Checks if a message requires tool execution. If yes, runs the tool and returns 
    a generator that streams progress updates, tool output, and final formatted LLM response.
    Returns None if no tool execution is required.
    """
    if not matches_tool_keywords(message):
        logger.debug(f"Planner bypass: message '{message}' contains no execution keywords.")
        return None

    decision = get_deterministic_decision(message)
    if decision is None:
        tools = tool_registry.list_all()
        if not tools:
            return None

        planner_prompt = build_planner_prompt(tools)
        
        logger.info("Planner: Checking tool intent via LLM...")
        try:
            # Run standard LLM complete call with temperature=0 for exact extraction
            classification_raw = await brain.think(
                prompt=message,
                system=planner_prompt,
                temperature=0.0
            )
            decision = clean_json_response(classification_raw)
        except Exception as e:
            logger.error(f"Planner classification failed: {e}")
            # C3 fix: Do NOT fall through to hallucination. Return an error generator.
            async def _error_gen():
                yield f"\u26a0\ufe0f Planner classification failed: {e}. Please try again."
            return _error_gen()

    if not decision.get("need_tool"):
        return None

    tool_name = decision.get("tool_name")
    params = decision.get("params", {})
    
    logger.info(f"Planner selected tool '{tool_name}' with parameters {params}")
    
    async def generator():
        yield f"⚙️ Planning execution for tool '{tool_name}'...\n"
        
        system_state.transition_to(SystemState.EXECUTING, f"Executing tool {tool_name}")
        yield f"⏳ Running tool '{tool_name}'...\n"
        
        start_time = time.time()
        res = await tool_registry.execute(tool_name, params)
        duration = time.time() - start_time
        
        logger.info(f"Tool '{tool_name}' finished in {duration:.2f}s. Success={res.success}")
        
        yield "📥 Collecting output and formatting response...\n\n"
        
        system_state.transition_to(SystemState.THINKING, "Formatting tool output response")
        
        # Feed actual tool result back to the LLM to format the response
        summary_prompt = f"""The user asked: "{message}"
Tool '{tool_name}' was executed.

Execution Result:
Success: {res.success}
Output: {res.output}
Error: {res.error}
Metadata: {res.meta}

Please explain or summarize this result to the user naturally. Do not invent any execution output.
"""
        async for token in brain.think_stream(
            prompt=summary_prompt,
            system=system_prompt,
            history=history,
            temperature=0.5
        ):
            yield token
            
    return generator()

async def plan_and_execute(
    message: str,
    system_prompt: str,
    history: list
) -> Optional[str]:
    """
    Non-streaming version of planner. Checks, executes, and returns formatted reply.
    """
    if not matches_tool_keywords(message):
        logger.debug(f"Planner bypass (non-stream): message '{message}' contains no execution keywords.")
        return None

    decision = get_deterministic_decision(message)
    if decision is None:
        tools = tool_registry.list_all()
        if not tools:
            return None

        planner_prompt = build_planner_prompt(tools)
        
        try:
            classification_raw = await brain.think(
                prompt=message,
                system=planner_prompt,
                temperature=0.0
            )
            decision = clean_json_response(classification_raw)
        except Exception as e:
            logger.error(f"Planner classification failed: {e}")
            # C3 fix: Return error string instead of falling through to hallucination
            return f"\u26a0\ufe0f Planner classification failed: {e}. Please try again."

    if not decision.get("need_tool"):
        return None

    tool_name = decision.get("tool_name")
    params = decision.get("params", {})
    
    logger.info(f"Planner selected tool '{tool_name}' (non-stream) with parameters {params}")
    
    system_state.transition_to(SystemState.EXECUTING, f"Executing tool {tool_name}")
    res = await tool_registry.execute(tool_name, params)
    
    system_state.transition_to(SystemState.THINKING, "Formatting tool output response")
    
    summary_prompt = f"""The user asked: "{message}"
Tool '{tool_name}' was executed.

Execution Result:
Success: {res.success}
Output: {res.output}
Error: {res.error}
Metadata: {res.meta}

Please explain or summarize this result to the user naturally. Do not invent any execution output.
"""
    reply = await brain.think(
        prompt=summary_prompt,
        system=system_prompt,
        history=history,
        temperature=0.5
    )
    return reply
