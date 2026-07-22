import os

from .base import LLMProvider, ProviderNotReady


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self) -> None:
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
        self._client = None

    def _get_client(self):
        # Import lazily so the default Ollama path never needs the anthropic
        # package installed or an API key present.
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def check_ready(self) -> None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ProviderNotReady(
                "ANTHROPIC_API_KEY is not set. Export it or switch back with "
                "LLM_PROVIDER=ollama"
            )
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise ProviderNotReady(
                "The anthropic package is missing. Run: pip install anthropic"
            ) from exc

    def complete(self, system: str, user: str) -> str:
        resp = self._get_client().messages.create(
            model=self.model,
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")
