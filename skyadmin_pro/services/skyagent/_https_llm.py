"""Optional OpenAI-compatible HTTPS LLM (stdlib urllib only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin

from skyadmin_pro.services.net import assert_public_https_url

from .exceptions import LLMProviderError
from .llm_interface import LLMProvider

_DEFAULT_TIMEOUT = 20.0
_ENV_URL = "SKYAGENT_LLM_URL"
_ENV_KEY = "SKYAGENT_LLM_API_KEY"
_ENV_MODEL = "SKYAGENT_LLM_MODEL"


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        try:
            assert_public_https_url(urljoin(req.full_url, newurl))
        except ValueError as exc:
            raise urllib.error.URLError("redirect blocked") from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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
        try:
            url = assert_public_https_url(base_url, resolve=False)
        except ValueError as exc:
            raise LLMProviderError("HTTPS LLM request failed") from exc
        self._url = url.rstrip("/")
        if not self._url.endswith("/chat/completions"):
            self._url = f"{self._url}/chat/completions"
        self._api_key = (api_key or "").strip() or None
        self._model = model
        self._timeout = timeout

    def query(self, prompt: str, *, context: str | None = None, system: str | None = None) -> str:
        try:
            assert_public_https_url(self._url)
        except ValueError as exc:
            raise LLMProviderError("HTTPS LLM request failed") from exc
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
        opener = urllib.request.build_opener(_SafeRedirectHandler)
        try:
            with opener.open(req, timeout=self._timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            raise LLMProviderError("HTTPS LLM request failed") from e
        return _extract_content(raw)

    def health_check(self) -> bool:
        return self._url.lower().startswith("https://")


def try_https_llm_from_env() -> HttpsLLMProvider | None:
    """Construct provider only when SKYAGENT_LLM_URL is public https; else None."""
    url = (os.environ.get(_ENV_URL) or "").strip()
    if not url:
        return None
    try:
        assert_public_https_url(url, resolve=False)
    except ValueError:
        return None
    key = (os.environ.get(_ENV_KEY) or "").strip() or None
    model = (os.environ.get(_ENV_MODEL) or "gpt-4o-mini").strip() or "gpt-4o-mini"
    try:
        return HttpsLLMProvider(url, api_key=key, model=model)
    except LLMProviderError:
        return None


def _extract_content(raw: Any) -> str:
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMProviderError("HTTPS LLM returned unexpected payload") from e
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError("HTTPS LLM returned empty content")
    return content.strip()
