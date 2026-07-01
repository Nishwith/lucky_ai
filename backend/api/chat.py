"""
Lucky AI — Chat API
====================
Main /chat endpoint. Handles streaming, memory, routing.
"""

import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..brain.universal_brain import brain
from ..brain.model_router    import route
from ..brain.prompt_builder  import (
    build_system_prompt,
    dev_agent_system,
    content_agent_system,
    pa_agent_system,
    study_agent_system,
    business_agent_system,
)
from ..memory.sqlite_db import (
    save_message, get_recent_history,
    build_memory_context, propose_memory
)
from ..memory.vector_db import build_semantic_context, remember

router = APIRouter()


from typing import Optional

class ChatRequest(BaseModel):
    message:     str
    session_id:  str  = ""
    stream:      bool = True
    force_agent: Optional[str] = None


class ChatResponse(BaseModel):
    reply:      str
    agent:      str
    model_used: str
    session_id: str


# ── Agent → system prompt mapping ─────────────────────────────────────────────
def get_system_for_agent(agent: str, memory_ctx: str) -> str:
    mapping = {
        "coding":   dev_agent_system,
        "ai_dev":   dev_agent_system,
        "content":  content_agent_system,
        "pa":       pa_agent_system,
        "study":    study_agent_system,
        "business": business_agent_system,
    }
    if agent in mapping:
        return mapping[agent](memory=memory_ctx)
    return build_system_prompt(memory_context=memory_ctx)


# ── Streaming chat ─────────────────────────────────────────────────────────────
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming endpoint — tokens appear in real time.
    Use this for the UI chat interface.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # 1. Route to best agent + model (supporting manual force override)
    decision = route(req.message, req.force_agent)
    agent = decision.agent
    model = decision.model

    from backend.core.state import system_state, SystemState
    system_state.transition_to(SystemState.THINKING, f"Received stream request for agent {agent}")

    # 2. Build memory context
    sql_ctx      = build_memory_context()
    semantic_ctx = build_semantic_context(req.message)
    memory_ctx   = "\n\n".join(filter(None, [sql_ctx, semantic_ctx]))

    # 3. Build system prompt
    system = get_system_for_agent(agent, memory_ctx)

    # 4. Get conversation history
    history = get_recent_history(session_id, limit=20)

    # 5. Save user message
    save_message(session_id, "user", req.message, agent)

    # 6. Stream response
    async def generate():
        try:
            full_response = []
            yield f"data: {{\"agent\": \"{agent}\", \"model\": \"{model}\", \"session_id\": \"{session_id}\"}}\n\n"

            from backend.agents import get_agent_executor, build_agent_context
            executor = get_agent_executor(agent)
            
            if executor:
                # 1. Context compile
                context = build_agent_context(session_id, req.message)
                
                # 2. Planning phase
                yield f"data: ⚙️ {executor.name} is planning workspace steps...\n\n"
                steps = await executor.plan(req.message, context)
                
                # 3. Execution phase
                if steps:
                    step_names = ", ".join(f"'{s.get('tool_name')}'" for s in steps)
                    yield f"data: ⏳ Running {len(steps)} planned operations: {step_names}...\n\n"
                    results = await executor.execute(steps)
                else:
                    yield f"data: 📝 No tool operations needed. Resolving response...\n\n"
                    results = {"step_results": []}
                
                # 4. Reporting summary prompt build
                summary_prompt, system_prompt = await executor.report(results, req.message, context)
                
                # 5. Final report think streaming
                async for token in brain.think_stream(
                    prompt=summary_prompt,
                    system=system_prompt,
                    history=history,
                    temperature=0.5
                ):
                    full_response.append(token)
                    yield f"data: {token}\n\n"
            else:
                from backend.brain.planner import plan_and_execute_stream
                planner_stream = await plan_and_execute_stream(req.message, system, history)
                
                if planner_stream is not None:
                    async for token in planner_stream:
                        full_response.append(token)
                        yield f"data: {token}\n\n"
                else:
                    async for token in brain.think_stream(
                        prompt=req.message,
                        system=system,
                        history=history,
                    ):
                        full_response.append(token)
                        yield f"data: {token}\n\n"

            # Save complete response
            complete = "".join(full_response)
            save_message(session_id, "assistant", complete, agent)

            # Propose to memory log only if semantically dense (>= 40 chars)
            if len(req.message) >= 40:
                propose_memory(
                    f"User asked: {req.message[:200]} | Lucky replied: {complete[:300]}",
                    category=agent
                )

            yield "data: [DONE]\n\n"
        finally:
            system_state.transition_to(SystemState.READY, "Stream response finished")

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Non-streaming chat ─────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Non-streaming endpoint — full response at once.
    Use this for agents, automation, testing.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Route + build context (supporting manual force override)
    decision = route(req.message, req.force_agent)
    agent = decision.agent
    model = decision.model
    
    from backend.core.state import system_state, SystemState
    system_state.transition_to(SystemState.THINKING, f"Received non-stream request for agent {agent}")
    
    sql_ctx      = build_memory_context()
    semantic_ctx = build_semantic_context(req.message)
    memory_ctx   = "\n\n".join(filter(None, [sql_ctx, semantic_ctx]))
    system       = get_system_for_agent(agent, memory_ctx)
    history      = get_recent_history(session_id, limit=20)

    # Save user message
    save_message(session_id, "user", req.message, agent)

    # Get response
    try:
        from backend.agents import get_agent_executor, build_agent_context
        executor = get_agent_executor(agent)
        
        if executor:
            context = build_agent_context(session_id, req.message)
            steps = await executor.plan(req.message, context)
            results = await executor.execute(steps)
            summary_prompt, system_prompt = await executor.report(results, req.message, context)
            reply = await brain.think(
                prompt=summary_prompt,
                system=system_prompt,
                history=history,
                temperature=0.5
            )
        else:
            from backend.brain.planner import plan_and_execute
            reply = await plan_and_execute(req.message, system, history)
            if reply is None:
                reply = await brain.think_with(
                    model=model,
                    prompt=req.message,
                    system=system,
                    history=history,
                )
    finally:
        system_state.transition_to(SystemState.READY, "Non-stream response finished")

    # Save + store in memory
    save_message(session_id, "assistant", reply, agent)
    if len(req.message) >= 40:
        propose_memory(
            f"User asked: {req.message[:200]} | Lucky replied: {reply[:300]}",
            category=agent
        )

    return ChatResponse(
        reply=reply,
        agent=agent,
        model_used=model,
        session_id=session_id,
    )


# ── Chat history ───────────────────────────────────────────────────────────────
@router.get("/chat/history/{session_id}")
async def get_history(session_id: str, limit: int = 50):
    return {"history": get_recent_history(session_id, limit)}
