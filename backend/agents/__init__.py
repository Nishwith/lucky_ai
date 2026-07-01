from backend.agents.base_agent import BaseAgent
from backend.agents.context import AgentContext, build_agent_context
from backend.agents.dev_agent import DevAgent
from backend.agents.study_agent import StudyAgent
from backend.agents.content_agent import ContentAgent
from backend.agents.business_agent import BusinessAgent
from backend.agents.pa_agent import PAAgent

AGENT_REGISTRY = {
    "coding": DevAgent(),
    "study": StudyAgent(),
    "content": ContentAgent(),
    "business": BusinessAgent(),
    "pa": PAAgent()
}

def get_agent_executor(agent_key: str):
    """Retrieve the class instance executor matching an agent key."""
    return AGENT_REGISTRY.get(agent_key)
