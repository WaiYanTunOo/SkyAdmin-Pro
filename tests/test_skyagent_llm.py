"""Tests for SkyAgent LLM interface."""

from __future__ import annotations

import pytest

from skyadmin_pro.services.skyagent.exceptions import LLMProviderError
from skyadmin_pro.services.skyagent.llm_interface import MockProvider, SkyAgentLLM


class SpyProvider:
    """Provider that records calls for assertion."""

    def __init__(self):
        self.calls: list[dict] = []

    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        self.calls.append({"prompt": prompt, "context": context, "system": system})
        return f"Spy response to: {prompt[:50]}..."

    def health_check(self) -> bool:
        return True


class FailingProvider:
    """Provider that raises on query."""

    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        raise ConnectionError("LLM service unavailable")

    def health_check(self) -> bool:
        return False


class TestMockProvider:
    def test_health_check_returns_true(self):
        provider = MockProvider()
        assert provider.health_check() is True

    def test_query_returns_response(self):
        provider = MockProvider()
        result = provider.query("test prompt")
        assert "Mock Response" in result
        assert "11 chars" in result

    def test_query_with_context(self):
        provider = MockProvider()
        result = provider.query("prompt", context="some context")
        assert "Mock Response" in result


class TestSkyAgentLLM:
    def test_init_with_default_provider(self):
        llm = SkyAgentLLM()
        assert llm.is_available is True

    def test_init_with_custom_provider(self):
        provider = MockProvider()
        llm = SkyAgentLLM(provider)
        assert llm._provider is provider

    def test_is_available_false_when_provider_fails(self):
        llm = SkyAgentLLM(FailingProvider())
        assert llm.is_available is False

    def test_draft_reply_constructs_prompt(self):
        spy = SpyProvider()
        llm = SkyAgentLLM(spy)
        llm.draft_reply("I have a billing issue", context="Client ABC", tone="friendly")
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert "billing issue" in call["prompt"]
        assert "Client ABC" in call["prompt"]
        assert "friendly" in call["prompt"]
        assert call["system"] is not None
        assert "SkyAgent" in call["system"]

    def test_extract_entities_includes_schema(self):
        spy = SpyProvider()
        llm = SkyAgentLLM(spy)
        llm.extract_entities("John Doe, john@example.com, order #456")
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert "customerName" in call["prompt"]
        assert "email" in call["prompt"]
        assert "issueCategory" in call["prompt"]
        assert "John Doe" in call["prompt"]

    def test_summarize_includes_question(self):
        spy = SpyProvider()
        llm = SkyAgentLLM(spy)
        llm.summarize("Document about taxes", question="What is the deadline?")
        assert len(spy.calls) == 1
        call = spy.calls[0]
        assert "What is the deadline?" in call["prompt"]
        assert "Document about taxes" in call["prompt"]

    def test_draft_reply_propagates_provider_error(self):
        llm = SkyAgentLLM(FailingProvider())
        with pytest.raises(LLMProviderError, match="LLM query failed"):
            llm.draft_reply("test", context="ctx")

    def test_extract_entities_propagates_provider_error(self):
        llm = SkyAgentLLM(FailingProvider())
        with pytest.raises(LLMProviderError, match="Entity extraction failed"):
            llm.extract_entities("test text")

    def test_summarize_propagates_provider_error(self):
        llm = SkyAgentLLM(FailingProvider())
        with pytest.raises(LLMProviderError, match="Summarization failed"):
            llm.summarize("docs", question="q")
