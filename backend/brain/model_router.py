"""
Lucky AI — Model Router
========================
Detects what kind of task is being asked and routes to the best model.
User never sees this — it just works automatically.
"""

import re
from .config_loader import PROVIDER

# ── Specialist models (only used when PROVIDER is ollama) ─────────────────────
SPECIALIST = {
    "coding":  "ollama/qwen2.5-coder:7b",
    # "ai_dev":  "ollama/deepseek-r1:7b",
    # "vision":  "ollama/gemma4:e4b",
    "default": f"ollama/qwen3:8b",
}

# ── Trigger keywords per domain ───────────────────────────────────────────────
ROUTING_RULES = {
    "coding": [
        "code", "build", "website", "debug", "html", "css", "javascript",
        "typescript", "python", "fastapi", "react", "nextjs", "function",
        "class", "error", "fix", "script", "component", "api", "backend",
        "frontend", "database", "sql", "docker", "deploy", "git", "npm",
        "pip", "install", "import", "async", "refactor", "test", "unittest"
    ],
    # "ai_dev": [
    #     "pytorch", "tensorflow", "huggingface", "transformers", "fine-tune",
    #     "finetune", "train", "model", "dataset", "embedding", "vector",
    #     "langchain", "langgraph", "crewai", "autogen", "rag", "agent",
    #     "inference", "onnx", "lora", "qlora", "loss function", "epoch",
    #     "neural", "ai model", "ml model", "machine learning"
    # ],
    # "vision": [
    #     "screen", "look at", "see my", "what's on", "image", "screenshot",
    #     "ui design", "visual", "design review", "what do you see"
    # ],
}


def detect_agent(message: str) -> str:
    """
    Detect which agent should handle this message.
    Returns: 'coding' | 'ai_dev' | 'vision' | 'content' | 'pa' | 'study' | 'business' | 'brain'
    """
    msg = message.lower()

    # Content agent
    content_kw = ["script", "youtube", "caption", "hook", "blog", "article",
                  "seo", "keyword", "thumbnail", "content", "post", "write"]
    if any(k in msg for k in content_kw) and not any(k in msg for k in ["code", "build"]):
        return "content"

    # PA agent
    pa_kw = ["project", "deadline", "task", "remind", "briefing", "plan my",
             "what do i have", "schedule", "overdue", "this week"]
    if any(k in msg for k in pa_kw):
        return "pa"

    # Study agent
    study_kw = ["explain", "summarise", "summarize", "notes", "revision",
                "what is", "how does", "study", "learn", "understand", "concept"]
    if any(k in msg for k in study_kw):
        return "study"

    # Business agent
    biz_kw = ["email", "proposal", "client", "cold", "outreach", "pitch",
              "invoice", "contract", "business", "sales"]
    if any(k in msg for k in biz_kw):
        return "business"

    # Coding or AI dev
    for agent, keywords in ROUTING_RULES.items():
        if any(k in msg for k in keywords):
            return agent

    return "brain"  # Default — main Qwen3 brain


def get_model_for_agent(agent: str) -> str:
    """
    Get the best model for a given agent.
    If using cloud providers, always uses the configured model (no local specialists).
    """
    if PROVIDER != "ollama":
        # Cloud providers: use configured model for everything
        # They're powerful enough (GPT-4o, Claude, Llama 70B via Groq etc.)
        from .config_loader import MODEL, PROVIDER as P
        return f"{P}/{MODEL}" if P not in ("openai", "anthropic") else MODEL

    # Local Ollama: route to specialist models
    return SPECIALIST.get(agent, SPECIALIST["default"])


def route(message: str) -> tuple[str, str]:
    """
    Main routing function.
    Returns: (agent_name, model_to_use)
    """
    agent = detect_agent(message)
    model = get_model_for_agent(agent)
    return agent, model
