"""Automated release-build gates (Phase 5A)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "SkyAdminPro.exe"
MIN_EXE_BYTES = 10 * 1024 * 1024


@pytest.mark.release
def test_exe_exists_and_reasonable_size():
    if not EXE.is_file():
        pytest.skip("dist/SkyAdminPro.exe not built — run pyinstaller SkyAdminPro.spec")
    assert EXE.stat().st_size >= MIN_EXE_BYTES


@pytest.mark.release
def test_exe_excludes_license_authoring():
    if not EXE.is_file():
        pytest.skip("dist/SkyAdminPro.exe not built")
    data = EXE.read_bytes()
    assert b"skyadmin_pro.services.license_authoring" not in data
    assert b"generate_ed25519_license" not in data


@pytest.mark.release
def test_embedded_public_key_constant():
    text = (ROOT / "skyadmin_pro" / "services" / "license_public.py").read_text(encoding="utf-8")
    assert "b9bc4ee341f806f7cdfe698c048fc4b212e8b5ef6ebffcb63bc4d527d136b501" in text


@pytest.mark.release
def test_worker_signing_key_matches_desktop():
    from skyadmin_pro.config import API_BASE_URL

    api_url = (API_BASE_URL or "").strip()
    if not api_url:
        pytest.skip("API_BASE_URL not configured")

    url = api_url.rstrip("/") + "/api/signing/public-key"
    req = urllib.request.Request(url, headers={"User-Agent": "SkyAdminPro"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read(8192))
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"Worker unreachable: {exc}")

    assert payload.get("ok") is True, payload.get("error")
    assert payload.get("matches_desktop") is True


@pytest.mark.release
def test_worker_pricing_endpoint():
    from skyadmin_pro.config import API_BASE_URL

    api_url = (API_BASE_URL or "").strip()
    if not api_url:
        pytest.skip("API_BASE_URL not configured")

    url = api_url.rstrip("/") + "/api/pricing"
    req = urllib.request.Request(url, headers={"User-Agent": "SkyAdminPro"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = json.loads(resp.read(16384))
    assert payload.get("ok") is True
    assert len(payload.get("packages") or []) >= 1
