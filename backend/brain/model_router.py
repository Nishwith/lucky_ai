"""
Lucky AI — Model Router
========================
Detects what kind of task is being asked and routes to the best model.
User never sees this — it just works automatically.
"""

import re
from typing import List, Tuple
from pydantic import BaseModel
from .config_loader import PROVIDER
from backend.core.logger import logger

# ── Specialist models (only used when PROVIDER is ollama) ─────────────────────
SPECIALIST = {
    "coding":  "ollama/qwen2.5-coder:7b",
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
}

# Define keywords for other agents
CONTENT_KEYWORDS = ["script", "youtube", "caption", "hook", "blog", "article",
                    "seo", "keyword", "thumbnail", "content", "post", "write"]

PA_KEYWORDS = ["project", "deadline", "task", "remind", "briefing", "plan my",
               "what do i have", "schedule", "overdue", "this week"]

STUDY_KEYWORDS = ["explain", "summarise", "summarize", "notes", "revision",
                  "study", "learn", "understand", "concept"]

BIZ_KEYWORDS = ["email", "proposal", "client", "cold", "outreach", "pitch",
                "invoice", "contract", "business", "sales"]


class RoutingDecision(BaseModel):
    agent: str
    model: str
    matched_keywords: List[str]
    reasoning: str
    alternatives: List[str]


def detect_agent_with_details(message: str) -> Tuple[str, List[str], str, List[str]]:
    """
    Analyzes message keywords and returns:
    (selected_agent, matched_keywords, reasoning, alternative_agents)
    """
    msg = message.lower()
    
    # Collect all agent matches
    matches = {}
    
    # Check Content
    content_matches = [k for k in CONTENT_KEYWORDS if k in msg]
    if content_matches:
        # Respect logic: and not any(k in msg for k in ["code", "build"])
        if not any(k in msg for k in ["code", "build"]):
            matches["content"] = content_matches
            
    # Check PA
    pa_matches = [k for k in PA_KEYWORDS if k in msg]
    if pa_matches:
        matches["pa"] = pa_matches
        
    # Check Study
    study_matches = [k for k in STUDY_KEYWORDS if k in msg]
    if study_matches:
        matches["study"] = study_matches
        
    # Check Business
    biz_matches = [k for k in BIZ_KEYWORDS if k in msg]
    if biz_matches:
        matches["business"] = biz_matches
        
    # Check Coding
    coding_matches = [k for k in ROUTING_RULES["coding"] if k in msg]
    if coding_matches:
        matches["coding"] = coding_matches

    # Replicate exact fallback order of detect_agent()
    selected_agent = "brain"
    matched_keywords = []
    reasoning = "Default system brain selected (no matching keywords found)"
    alternatives = []

    # Priority order matching detect_agent():
    # 1. Content (if matched and no code/build)
    # 2. PA
    # 3. Study
    # 4. Business
    # 5. Coding
    
    if "content" in matches:
        # If there is also a coding match and the message contains specific technical/coding keywords, prioritize coding
        if "coding" in matches and any(k in msg for k in ["fastapi", "python", "javascript", "typescript", "html", "css", "react", "nextjs", "api", "backend", "frontend", "code", "build"]):
            selected_agent = "coding"
            matched_keywords = matches["coding"]
            reasoning = f"Matched coding keywords (prioritized over content): {matched_keywords}"
        else:
            selected_agent = "content"
            matched_keywords = matches["content"]
            reasoning = f"Matched content keywords: {matched_keywords}"
    elif "pa" in matches:
        selected_agent = "pa"
        matched_keywords = matches["pa"]
        reasoning = f"Matched PA keywords: {matched_keywords}"
    elif "study" in matches:
        selected_agent = "study"
        matched_keywords = matches["study"]
        reasoning = f"Matched study keywords: {matched_keywords}"
    elif "business" in matches:
        selected_agent = "business"
        matched_keywords = matches["business"]
        reasoning = f"Matched business keywords: {matched_keywords}"
    elif "coding" in matches:
        selected_agent = "coding"
        matched_keywords = matches["coding"]
        reasoning = f"Matched coding keywords: {matched_keywords}"

    # Compile alternatives (other agents that had keyword matches)
    alternatives = [a for a in matches.keys() if a != selected_agent]

    return selected_agent, matched_keywords, reasoning, alternatives


def get_model_for_agent(agent: str) -> str:
    """
    Get the best model for a given agent.
    If using cloud providers, always uses the configured model (no local specialists).
    """
    if PROVIDER != "ollama":
        from .config_loader import MODEL, PROVIDER as P
        return f"{P}/{MODEL}" if P not in ("openai", "anthropic") else MODEL

    return SPECIALIST.get(agent, SPECIALIST["default"])


from typing import Optional

def route(message: str, force_agent: Optional[str] = None) -> RoutingDecision:
    """
    Main routing function returning detailed RoutingDecision.
    """
    if force_agent and force_agent != "brain":
        agent = force_agent
        matched_keywords = []
        reasoning = f"Routed forced agent override: '{force_agent}'"
        alternatives = []
    else:
        agent, matched_keywords, reasoning, alternatives = detect_agent_with_details(message)
        
    model = get_model_for_agent(agent)
    
    decision = RoutingDecision(
        agent=agent,
        model=model,
        matched_keywords=matched_keywords,
        reasoning=reasoning,
        alternatives=alternatives
    )
    
    # Log Routing Decision using structured logging format
    logger.info(f"Routing Decision: agent={decision.agent}, model={decision.model}, reasoning='{decision.reasoning}', alternatives={decision.alternatives}")
    
    return decision
