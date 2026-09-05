"""Outbound HTTPS policy — fail closed on downgrade."""

from __future__ import annotations

import pytest

from skyadmin_pro.services.net import require_https_api_url


class TestRequireHttpsApiUrl:
    def test_https_accepted(self):
        url = "https://skyadmin-worker.example.workers.dev/"
        assert require_https_api_url(url) == url

    def test_empty_rejected(self):
        with pytest.raises(RuntimeError, match="not configured"):
            require_https_api_url("")

    def test_plain_http_rejected(self):
        with pytest.raises(RuntimeError, match="must use https"):
            require_https_api_url("http://evil.example/sync")

    def test_bare_host_defaults_to_https(self):
        assert require_https_api_url("example.workers.dev") == "example.workers.dev"

    def test_localhost_allowed(self):
        assert require_https_api_url("http://localhost:8787/").startswith("http://localhost")

    def test_escape_hatch_opt_in(self, monkeypatch):
        monkeypatch.setenv("SKYADMIN_ALLOW_HTTP_API", "1")
        assert require_https_api_url("http://192.168.1.9:8787/").startswith("http://")

    def test_no_hatch_by_default(self, monkeypatch):
        monkeypatch.delenv("SKYADMIN_ALLOW_HTTP_API", raising=False)
        with pytest.raises(RuntimeError, match="must use https"):
            require_https_api_url("http://192.168.1.9:8787/")


class TestSyncRefusesInsecureUrl:
    def test_register_refuses_http(self, monkeypatch):
        import skyadmin_pro.services.data_sync as sync_mod

        monkeypatch.setattr(sync_mod, "API_BASE_URL", "http://evil.example/")
        ok, message = sync_mod.register_sync_device(timeout=0.1)
        assert ok is False
        assert "https" in message

    def test_sync_request_refuses_http(self, monkeypatch):
        import skyadmin_pro.services.data_sync as sync_mod

        monkeypatch.setattr(sync_mod, "API_BASE_URL", "http://evil.example/")
        ok, message = sync_mod._sync_request("GET", "/api/sync/schema", machine_id="M", token="T")
        assert ok is False
        assert "https" in message
