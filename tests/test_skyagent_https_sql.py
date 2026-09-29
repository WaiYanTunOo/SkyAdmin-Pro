"""Tests for optional HTTPS LLM and SQL validator hardening."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from skyadmin_pro.services.skyagent._https_llm import HttpsLLMProvider, try_https_llm_from_env
from skyadmin_pro.services.skyagent._sql_validator import validate_select_only
from skyadmin_pro.services.skyagent.exceptions import DatabaseReadOnlyError, LLMProviderError


class TestSqlHardening:
    @pytest.mark.parametrize(
        "sql",
        [
            "INSERT INTO clients (name) VALUES ('x')",
            "UPDATE clients SET name='x'",
            "DELETE FROM clients",
            "DROP TABLE clients",
            "ATTACH DATABASE 'x.db' AS other",
            "PRAGMA table_info(clients)",
            "SELECT * INTO new_table FROM clients",
            "SELECT * FROM clients; DELETE FROM clients",
        ],
    )
    def test_rejects_mutating(self, sql):
        if ";" in sql:
            from skyadmin_pro.services.skyagent._sql_validator import validate_no_multiple_statements

            with pytest.raises((DatabaseReadOnlyError, ValueError)):
                validate_select_only(sql)
                validate_no_multiple_statements(sql)
        else:
            with pytest.raises(DatabaseReadOnlyError):
                validate_select_only(sql)

    def test_allows_plain_select(self):
        validate_select_only("SELECT id, name FROM clients WHERE deleted_at IS NULL")


class TestHttpsLLM:
    def test_from_env_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("SKYAGENT_LLM_URL", raising=False)
        assert try_https_llm_from_env() is None

    def test_from_env_rejects_non_https(self, monkeypatch):
        monkeypatch.setenv("SKYAGENT_LLM_URL", "http://localhost:11434/v1")
        assert try_https_llm_from_env() is None

    def test_from_env_rejects_loopback(self, monkeypatch):
        monkeypatch.setenv("SKYAGENT_LLM_URL", "https://127.0.0.1/v1")
        assert try_https_llm_from_env() is None

    def test_provider_rejects_loopback_url(self):
        with pytest.raises(LLMProviderError, match="failed"):
            HttpsLLMProvider("https://127.0.0.1/v1")

    def test_from_env_builds_https(self, monkeypatch):
        monkeypatch.setenv("SKYAGENT_LLM_URL", "https://api.example.com/v1")
        monkeypatch.setenv("SKYAGENT_LLM_API_KEY", "sk-test")
        p = try_https_llm_from_env()
        assert p is not None
        assert p.health_check() is True

    def test_product_llm_none_without_env(self, monkeypatch):
        monkeypatch.delenv("SKYAGENT_LLM_URL", raising=False)
        provider = try_https_llm_from_env()
        from skyadmin_pro.services.skyagent.llm_interface import SkyAgentLLM

        llm = SkyAgentLLM(provider) if provider is not None else None
        assert llm is None

    def test_query_parses_openai_payload(self):
        payload = {"choices": [{"message": {"content": "  hello  "}}]}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        opener = MagicMock()
        opener.open.return_value = mock_resp
        with (
            patch("skyadmin_pro.services.skyagent._https_llm.assert_public_https_url", side_effect=lambda u, **k: u),
            patch("urllib.request.build_opener", return_value=opener),
        ):
            p = HttpsLLMProvider("https://api.example.com/v1", api_key="sk-secret")
            assert p.query("hi", system="sys") == "hello"
            req = opener.open.call_args[0][0]
            assert "Authorization" in req.headers
            assert "sk-secret" in req.headers["Authorization"]

    def test_query_fail_closed(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError("t")
        with (
            patch("skyadmin_pro.services.skyagent._https_llm.assert_public_https_url", side_effect=lambda u, **k: u),
            patch("urllib.request.build_opener", return_value=opener),
        ):
            p = HttpsLLMProvider("https://api.example.com/v1")
            with pytest.raises(LLMProviderError, match="failed"):
                p.query("hi")
