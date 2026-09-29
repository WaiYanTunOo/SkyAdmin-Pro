"""LLM interface abstraction for SkyAgent.

Provides a provider-agnostic interface for querying language models.
Includes a mock provider for offline/testing and a future Worker proxy.
"""

from __future__ import annotations

import abc

from .exceptions import LLMProviderError


class LLMProvider(abc.ABC):
    """Abstract base for LLM backends."""

    @abc.abstractmethod
    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        """Send a prompt to the LLM and return the response text."""

    @abc.abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable."""


class MockProvider(LLMProvider):
    """Deterministic mock for tests and offline mode."""

    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        return f"[Mock Response] Received {len(prompt)} chars."

    def health_check(self) -> bool:
        return True


class SkyAgentLLM:
    """Facade that delegates to the configured LLM provider."""

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self._provider = provider or MockProvider()

    def draft_reply(self, customer_message: str, *, context: str, tone: str = "professional") -> str:
        system = (
            "You are SkyAgent, an AI co-pilot for account administrators. " "Be professional, empathetic, and concise."
        )
        prompt = (
            f"Tone: {tone}\n"
            f"Context:\n{context}\n\n"
            f"Customer message:\n{customer_message}\n\n"
            "Draft a clear, empathetic reply."
        )
        try:
            return self._provider.query(prompt, system=system)
        except Exception as e:
            raise LLMProviderError(f"LLM query failed: {e}") from e

    def extract_entities(self, text: str) -> str:
        system = (
            "You are a data extraction assistant. "
            "Extract entities and return ONLY valid JSON matching the schema. "
            "No markdown, no commentary."
        )
        schema_hint = (
            '{"customerName": "string|null", "email": "string|null", '
            '"accountOrOrderId": "string|null", "issueCategory": '
            '"Billing|Technical|Inquiry|Other", "sentiment": '
            '"Positive|Neutral|Frustrated", "summary": "string"}'
        )
        prompt = f"Extract from the following text.\n" f"JSON schema: {schema_hint}\n\n" f"Text:\n{text}"
        try:
            return self._provider.query(prompt, system=system)
        except Exception as e:
            raise LLMProviderError(f"Entity extraction failed: {e}") from e

    def summarize(self, documents: str, *, question: str) -> str:
        system = (
            "You are a document retrieval assistant. "
            "Answer using ONLY the provided context. "
            "Cite sources. If not found, say so explicitly."
        )
        prompt = (
            f"Context:\n{documents}\n\n" f"Question: {question}\n\n" "Provide a concise answer based on the context."
        )
        try:
            return self._provider.query(prompt, system=system)
        except Exception as e:
            raise LLMProviderError(f"Summarization failed: {e}") from e

    @property
    def is_available(self) -> bool:
        return self._provider.health_check()
