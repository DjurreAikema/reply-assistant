import os

from .base import LLMProvider, ProviderNotReady
from .structured import StructuredOutputError, complete_json

__all__ = [
    "LLMProvider",
    "ProviderNotReady",
    "StructuredOutputError",
    "complete_json",
    "get_provider",
]


def get_provider() -> LLMProvider:
    choice = os.environ.get("LLM_PROVIDER", "ollama").lower()
    if choice == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider()
    if choice == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    raise ValueError(f"Unknown LLM_PROVIDER '{choice}'. Use ollama or anthropic.")
