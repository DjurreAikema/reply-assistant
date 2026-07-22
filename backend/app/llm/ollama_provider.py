import os

import requests

from .base import LLMProvider, ProviderNotReady


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
        self.model = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

    def check_ready(self) -> None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise ProviderNotReady(
                f"Ollama is not reachable at {self.base_url}. "
                f"Start it first: ollama serve"
            ) from exc

        installed = [m.get("name", "") for m in resp.json().get("models", [])]
        # Ollama reports "llama3.1:8b" but a bare "llama3.1" tag also resolves,
        # so match on the prefix before the colon as well.
        wanted = self.model.split(":")[0]
        if not any(n == self.model or n.split(":")[0] == wanted for n in installed):
            raise ProviderNotReady(
                f"Model {self.model} is not pulled. Run: ollama pull {self.model}"
            )

    def complete(self, system: str, user: str) -> str:
        # format=json makes llama3.1:8b far more reliable at emitting bare
        # JSON. The fence stripping in structured.py stays anyway, as a
        # belt-and-braces for provider differences.
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]
