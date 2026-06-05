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


# ── Request / Response models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message:    str
    session_id: str  = ""
    stream:     bool = True


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
    fn = mapping.get(agent, build_system_prompt)
    return fn(memory=memory_ctx) if agent in mapping else fn(memory_context=memory_ctx)


# ── Streaming chat ─────────────────────────────────────────────────────────────
@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    Streaming endpoint — tokens appear in real time.
    Use this for the UI chat interface.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # 1. Route to best agent + model
    agent, model = route(req.message)

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
        full_response = []
        yield f"data: {{\"agent\": \"{agent}\", \"model\": \"{model}\", \"session_id\": \"{session_id}\"}}\n\n"

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

        # Store in semantic memory
        remember(
            f"User asked: {req.message[:200]} | Lucky replied: {complete[:300]}",
            category=agent
        )

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Non-streaming chat ─────────────────────────────────────────────────────────
@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Non-streaming endpoint — full response at once.
    Use this for agents, automation, testing.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # Route + build context
    agent, model = route(req.message)
    sql_ctx      = build_memory_context()
    semantic_ctx = build_semantic_context(req.message)
    memory_ctx   = "\n\n".join(filter(None, [sql_ctx, semantic_ctx]))
    system       = get_system_for_agent(agent, memory_ctx)
    history      = get_recent_history(session_id, limit=20)

    # Save user message
    save_message(session_id, "user", req.message, agent)

    # Get response
    reply = await brain.think_with(
        model=model,
        prompt=req.message,
        system=system,
        history=history,
    )

    # Save + store in memory
    save_message(session_id, "assistant", reply, agent)
    remember(
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
