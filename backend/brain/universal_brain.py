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
from .config_loader import PROVIDER, MODEL, API_BASE, API_KEY

# Suppress litellm noise
litellm.suppress_debug_info = True
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# ── Build the model string LiteLLM expects ────────────────────────────────────
def _build_model_string() -> str:
    """
    LiteLLM uses different prefixes per provider:
    ollama/qwen3:8b | groq/llama-3.3-70b | gpt-4o-mini | claude-... | gemini/...
    """
    if PROVIDER == "ollama":
        return f"ollama/{MODEL}"
    if PROVIDER == "openai":
        return MODEL                        # OpenAI needs no prefix
    if PROVIDER == "anthropic":
        return MODEL                        # Anthropic needs no prefix
    if PROVIDER in ("groq", "deepseek", "openrouter", "gemini"):
        return f"{PROVIDER}/{MODEL}"
    return MODEL                            # Fallback — pass as-is


MODEL_STRING = _build_model_string()


# ── Extra kwargs per provider ─────────────────────────────────────────────────
def _provider_kwargs() -> dict:
    kwargs = {}
    if API_KEY:
        kwargs["api_key"] = API_KEY
    if API_BASE and PROVIDER == "ollama":
        kwargs["api_base"] = API_BASE
    if PROVIDER == "openrouter":
        kwargs["api_base"] = "https://openrouter.ai/api/v1"
    return kwargs


EXTRA_KW = _provider_kwargs()


# ── Universal Brain ───────────────────────────────────────────────────────────
class UniversalBrain:
    """
    Single interface for all AI providers.
    All agents use this — they never touch LiteLLM or Ollama directly.
    """

    def __init__(self):
        self.model  = MODEL_STRING
        self.kwargs = EXTRA_KW
        print(f"[Lucky AI Brain] Provider: {PROVIDER} | Model: {MODEL}")

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
