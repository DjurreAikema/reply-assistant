from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Single seam for all model access. Phase two and three add features
    behind this same interface, so nothing outside app.llm may talk to a
    model directly."""

    name: str = "unknown"

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Return the raw text of one completion. No parsing here.
        Parsing and retries live in structured.py so they work the same
        for every provider."""
        raise NotImplementedError

    @abstractmethod
    def check_ready(self) -> None:
        """Raise ProviderNotReady with a fix-it command if the provider
        cannot serve requests. Called once at startup, not per request."""
        raise NotImplementedError


class ProviderNotReady(RuntimeError):
    pass
