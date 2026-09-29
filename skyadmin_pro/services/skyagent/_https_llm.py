"""Optional OpenAI-compatible HTTPS LLM (stdlib urllib only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .exceptions import LLMProviderError
from .llm_interface import LLMProvider

_DEFAULT_TIMEOUT = 20.0
_ENV_URL = "SKYAGENT_LLM_URL"
_ENV_KEY = "SKYAGENT_LLM_API_KEY"
_ENV_MODEL = "SKYAGENT_LLM_MODEL"


class HttpsLLMProvider(LLMProvider):
    """Chat Completions client; fail-closed; never logs secrets."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._url = base_url.rstrip("/")
        if not self._url.endswith("/chat/completions"):
            self._url = f"{self._url}/chat/completions"
        self._api_key = (api_key or "").strip() or None
        self._model = model
        self._timeout = timeout

    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        user = prompt if not context else f"Context:\n{context}\n\n{prompt}"
        messages.append({"role": "user", "content": user})
        body = json.dumps({"model": self._model, "messages": messages}).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise LLMProviderError("HTTPS LLM request failed") from e
        return _extract_content(raw)

    def health_check(self) -> bool:
        """True when configured for HTTPS; network probed only on query."""
        return self._url.lower().startswith("https://")


def try_https_llm_from_env() -> HttpsLLMProvider | None:
    """Construct provider only when SKYAGENT_LLM_URL is https; else None."""
    url = (os.environ.get(_ENV_URL) or "").strip()
    if not url or not url.lower().startswith("https://"):
        return None
    key = (os.environ.get(_ENV_KEY) or "").strip() or None
    model = (os.environ.get(_ENV_MODEL) or "gpt-4o-mini").strip() or "gpt-4o-mini"
    return HttpsLLMProvider(url, api_key=key, model=model)


def _extract_content(raw: Any) -> str:
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMProviderError("HTTPS LLM returned unexpected payload") from e
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError("HTTPS LLM returned empty content")
    return content.strip()
