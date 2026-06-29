"""
Lucky AI — Universal Brain Interface
=====================================
The ONE file that makes Lucky AI work with any AI provider.
Agents never call Ollama/OpenAI/Groq directly.
They always call UniversalBrain.think() — provider doesn't matter.

To switch provider: change config.json. Zero code changes.
"""

import litellm
import logging
from typing import AsyncGenerator

# Suppress litellm noise
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


class UniversalBrain:
    """
    Single interface for all AI providers.
    All agents use this — they never touch LiteLLM or Ollama directly.
    """

    def __init__(self):
        # UniversalBrain uses dynamic properties to fetch current model/kwargs
        pass

    @property
    def model(self) -> str:
        from . import config_loader as cl
        if cl.PROVIDER == "ollama":
            return f"ollama/{cl.MODEL}"
        if cl.PROVIDER in ("openai", "anthropic"):
            return cl.MODEL
        if cl.PROVIDER in ("groq", "deepseek", "openrouter", "gemini"):
            return f"{cl.PROVIDER}/{cl.MODEL}"
        return cl.MODEL

    @property
    def kwargs(self) -> dict:
        from . import config_loader as cl
        kwargs = {}
        if cl.API_KEY:
            kwargs["api_key"] = cl.API_KEY
        if cl.API_BASE and cl.PROVIDER == "ollama":
            kwargs["api_base"] = cl.API_BASE
        if cl.PROVIDER == "openrouter":
            kwargs["api_base"] = "https://openrouter.ai/api/v1"
        return kwargs

    # ── Normal (non-streaming) ────────────────────────────────────────────────
    async def think(
        self,
        prompt:      str,
        system:      str  = "",
        history:     list = None,
        temperature: float = 0.7,
        max_tokens:  int   = 2048,
    ) -> str:
        """
        Send a prompt and get a full response back.
        Use this for agents, PA tasks, code generation etc.
        """
        messages = self._build_messages(prompt, system, history or [])
        try:
            response = await litellm.acompletion(
                model       = self.model,
                messages    = messages,
                temperature = temperature,
                max_tokens  = max_tokens,
                **self.kwargs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Lucky AI Error] Brain failed: {str(e)}"

    # ── Streaming ─────────────────────────────────────────────────────────────
    async def think_stream(
        self,
        prompt:  str,
        system:  str  = "",
        history: list = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the response token by token.
        Use this for chat UI — shows text appearing in real time.
        """
        messages = self._build_messages(prompt, system, history or [])
        try:
            response = await litellm.acompletion(
                model       = self.model,
                messages    = messages,
                temperature = temperature,
                stream      = True,
                **self.kwargs,
            )
            async for chunk in response:
                token = chunk.choices[0].delta.content
                if token:
                    yield token
        except Exception as e:
            yield f"[Lucky AI Error] {str(e)}"

    # ── Route to specialist model ─────────────────────────────────────────────
    async def think_with(
        self,
        model:   str,
        prompt:  str,
        system:  str  = "",
        history: list = None,
    ) -> str:
        """
        Use a different model for a specific task.
        e.g. think_with("ollama/qwen2.5-coder:7b", "Write this FastAPI route...")
        """
        messages = self._build_messages(prompt, system, history or [])
        try:
            response = await litellm.acompletion(
                model    = model,
                messages = messages,
                **self.kwargs,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Lucky AI Error] Specialist brain failed: {str(e)}"

    # ── Internal ──────────────────────────────────────────────────────────────
    @staticmethod
    def _build_messages(prompt: str, system: str, history: list) -> list:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages


# ── Singleton ─────────────────────────────────────────────────────────────────
brain = UniversalBrain()
