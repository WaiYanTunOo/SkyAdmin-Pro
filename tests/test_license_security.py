"""License core: unique keys, tamper resistance, one-time use, self-heal."""

import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

import skyadmin_pro.services.license as lic
from skyadmin_pro.services.license_authoring import (
    _dev_private_key,
    _ed25519_sig_b64url,
    build_control_envelope_v2,
    generate_ed25519_license,
    generate_ed25519_passcode,
    generate_license as legacy_hmac_license,
    generate_passcode as legacy_hmac_passcode,
)
from skyadmin_pro.services.license_crypto import license_payload_string
from skyadmin_pro.services.license_public import LICENSE_SIGNATURE_ALGORITHM


@pytest.fixture
def mid():
    return lic.get_machine_id()


def _wrap(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign_license_obj(mid: str, exp: str | None, iat: str, nonce: str, pkg: str) -> dict:
    payload = license_payload_string(mid, exp, iat, nonce, pkg)
    return {
        "mid": mid,
        "exp": exp,
        "sig": _ed25519_sig_b64url(_dev_private_key(), payload),
        "iat": iat,
        "n": nonce,
        "pkg": pkg,
        "alg": LICENSE_SIGNATURE_ALGORITHM,
    }


# --- uniqueness -----------------------------------------------------------


def test_keys_unique_for_identical_params(mid):
    keys = {generate_ed25519_license(mid, 14, package_days=14) for _ in range(3)}
    assert len(keys) == 3


def test_key_verifies_and_reports_package(mid):
    key = generate_ed25519_license(mid, days_valid=7, package_days=7)
    ok, msg, nonce = lic.check_activation_usable(key)
    assert ok
    assert "7-day package" in msg.lower()
    assert nonce


def test_ed25519_passcode_verifies(mid):
    code = generate_ed25519_passcode(mid, days_valid=7)
    ok, msg = lic.verify_key_text(code)
    assert ok, msg
    assert "passcode" in msg.lower()


def test_legacy_hmac_license_rejected(mid):
    key = legacy_hmac_license(mid, days_valid=7, package_days=7)
    ok, msg, _nonce = lic.check_activation_usable(key)
    assert not ok
    assert "retired" in msg.lower()


def test_legacy_hmac_passcode_rejected(mid):
    code = legacy_hmac_passcode(mid)
    ok, msg = lic.verify_key_text(code)
    assert not ok
    assert "retired" in msg.lower()


# --- tamper resistance ----------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("exp", "2099-01-01T00:00:00Z"),
        ("pkg", "365"),
        ("n", "deadbeefdead"),
        ("iat", "2020-01-01T00:00"),
    ],
)
def test_tampered_field_rejected(mid, field, value):
    key = generate_ed25519_license(mid, days_valid=30, package_days=30)
    b64 = "".join(key.split())
    b64 += "=" * (-len(b64) % 4)
    obj = json.loads(base64.urlsafe_b64decode(b64))
    obj[field] = value
    tampered = base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode().rstrip("=")
    ok, _msg = lic.verify_key_text(tampered)
    assert not ok


def test_wrong_machine_rejected(mid):
    other = generate_ed25519_license("0123456789ABCDEF", 30, package_days=30)
    ok, msg, _n = lic.check_activation_usable(other)
    assert not ok and "machine" in msg.lower()


def test_expired_rejected(mid):
    exp = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    obj = _sign_license_obj(mid, exp, "x", "x", "1")
    ok, msg, _n = lic.check_activation_usable(_wrap(obj))
    assert not ok and "expire" in msg.lower()


def test_utc_expiry_parses_full_duration(mid):
    exp = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    obj = _sign_license_obj(mid, exp, "x", "nonceutc01", "1")
    ok, _msg, _n = lic.check_activation_usable(_wrap(obj))
    assert ok
    parsed = lic._parse_expiry(exp)
    assert parsed > datetime.now()


def test_never_expire_key_has_no_exp(mid):
    obj = _sign_license_obj(mid, None, "x", "noncenever01", "")
    ok, msg, _n = lic.check_activation_usable(_wrap(obj))
    assert ok
    assert "never" in msg.lower()


# --- one-time use ---------------------------------------------------------


def test_burn_blocks_redemption(mid, fake_app_dir, monkeypatch):
    (fake_app_dir / "hardware.id").write_text(mid, encoding="utf-8")
    import skyadmin_pro.paths as pm

    monkeypatch.setattr(pm, "app_data_dir", lambda: fake_app_dir)

    key = generate_ed25519_license(mid, days_valid=7, package_days=7)
    payload = lic._payload_of(key)
    nonce = payload["n"]

    ok, msg, _ = lic.check_activation_usable(key)
    assert ok, f"pre-burn failed: {msg}"
    lic.mark_used(nonce)

    lic.save_license_file(key)
    ok, _, _ = lic.check_activation_usable(key)
    assert ok

    monkeypatch.setattr(
        lic,
        "_read_license_payload",
        lambda: {"mid": mid, "exp": payload["exp"], "n": "other-nonce-xyz"},
    )
    ok, msg, _ = lic.check_activation_usable(key)
    assert not ok and "already been used" in msg.lower()


# --- machine ban covers passcode ------------------------------------------


def test_machine_ban_blocks_key_and_passcode(mid, fake_app_dir):
    hw = fake_app_dir / "hardware.id"
    hw.write_text(mid, encoding="utf-8")
    banned = fake_app_dir / "banned.txt"
    banned.write_text(mid + "\n", encoding="utf-8")

    ok, msg = lic.verify_key_text(generate_ed25519_license(mid, 30, package_days=30))
    assert not ok and "blocked" in msg.lower()
    ok, msg = lic.verify_key_text(generate_ed25519_passcode(mid))
    assert not ok and "blocked" in msg.lower()

    banned.unlink()
    hw.unlink()


# --- SKYCTRL2 signed control list -----------------------------------------


class FakeResp:
    def __init__(self, content):
        self._b = __import__("io").BytesIO(content.encode())

    def read(self, n=-1):
        if n == -1:
            return self._b.read()
        return self._b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_control_list_apply_and_replace(mid, fake_app_dir, monkeypatch):
    import urllib.request

    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")
    envelope = build_control_envelope_v2(
        "\n".join([f"REVOKE n{mid[:6]}", f"BAN {mid}", "USED u123"]) + "\n",
    )
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: FakeResp(envelope),
    )
    ok, msg = lic.fetch_revocations(timeout=1)
    assert ok, msg
    assert (fake_app_dir / "revoked.txt").read_text().strip() == f"n{mid[:6]}"
    assert (fake_app_dir / "banned.txt").read_text().strip() == mid
    assert "u123" in lic.used_nonces()

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: FakeResp(build_control_envelope_v2("")),
    )
    ok, msg = lic.fetch_revocations(timeout=1)
    assert ok
    assert not (fake_app_dir / "revoked.txt").exists()
    assert not (fake_app_dir / "banned.txt").exists()


def test_control_list_tamper_refused(mid, fake_app_dir, monkeypatch):
    import urllib.request
    from io import BytesIO

    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")

    good = build_control_envelope_v2(f"REVOKE n{mid[:6]}\n")
    wrapped = good[len("SKYCTRL2:") :]
    wrapped += "=" * (-len(wrapped) % 4)
    obj = json.loads(base64.urlsafe_b64decode(wrapped.encode()))
    pt = base64.b64decode(obj["payload"] + "==").decode().replace("REVOKE", "BAN   ")
    obj["payload"] = base64.urlsafe_b64encode(pt.encode()).decode().rstrip("=")
    evil = "SKYCTRL2:" + base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    class FakeResp(BytesIO):
        def __init__(self, content):
            if isinstance(content, str):
                content = content.encode()
            super().__init__(content)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: FakeResp(evil))
    ok, msg = lic.fetch_revocations(timeout=1)
    assert not ok and "signature" in msg.lower()
    assert not (fake_app_dir / "banned.txt").exists()


def test_legacy_skyctrl1_refused(mid, fake_app_dir, monkeypatch):
    import urllib.request

    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod
    from skyadmin_pro.services.license_authoring import hmac_hex

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")

    plaintext = f"REVOKE n{mid[:6]}\n"
    obj = {
        "v": 1,
        "alg": "HMAC-SHA256",
        "sig": hmac_hex(plaintext),
        "payload": base64.urlsafe_b64encode(plaintext.encode()).decode().rstrip("="),
    }
    legacy = "SKYCTRL1:" + base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: FakeResp(legacy))
    ok, msg = lic.fetch_revocations(timeout=1)
    assert not ok and "skyctrl2" in msg.lower()


# --- update checker -------------------------------------------------------


def test_control_list_writes_latest_update(mid, fake_app_dir, monkeypatch):
    import urllib.request

    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")
    envelope = build_control_envelope_v2("LATEST 0.9.9 https://cdn.example/SkyAdminPro.exe\n")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: FakeResp(envelope),
    )
    ok, msg = lic.fetch_revocations(timeout=1)
    assert ok, msg
    info = lic.read_update_info()
    assert info is not None
    assert info["version"] == "0.9.9"
    assert info["url"] == "https://cdn.example/SkyAdminPro.exe"


def test_check_for_updates_returns_info(mid, fake_app_dir, monkeypatch):
    import urllib.request

    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")
    envelope = build_control_envelope_v2("LATEST 99.0.0 https://cdn.example/new.exe\n")
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: FakeResp(envelope),
    )
    ok, msg, info = lic.check_for_updates(timeout=1)
    assert ok, msg
    assert info is not None
    assert info["version"] == "99.0.0"


def test_update_info_roundtrip_and_compare(fake_app_dir):
    from skyadmin_pro.config import APP_VERSION
    from skyadmin_pro.services.license import is_newer_version, read_update_info

    assert read_update_info() is None or isinstance(read_update_info(), dict)
    assert is_newer_version("0.2.1", "0.2.0")
    assert not is_newer_version("0.2.0", "0.2.0")
    assert not is_newer_version("0.1.9", "0.2.0")
    assert APP_VERSION


def test_requires_online_check_respects_config(monkeypatch):
    import skyadmin_pro.config as config
    from skyadmin_pro.services.license import requires_online_check

    monkeypatch.setattr(config, "API_BASE_URL", "")
    monkeypatch.setattr(config, "REVOCATION_URL", "")
    assert requires_online_check() is False

    monkeypatch.setattr(config, "API_BASE_URL", "https://example.test")
    assert requires_online_check() is True


def test_report_activation_claim_skips_without_api(monkeypatch):
    import skyadmin_pro.config as config

    monkeypatch.setattr(config, "API_BASE_URL", "")
    ok, msg = lic.report_activation_claim("dummy")
    assert ok
    assert "no api" in msg.lower()


def test_report_activation_claim_posts_code(mid, monkeypatch):
    import json
    import urllib.request

    import skyadmin_pro.config as config

    monkeypatch.setattr(config, "API_BASE_URL", "https://worker.test")
    key = generate_ed25519_license(mid, days_valid=7, package_days=7)

    captured: dict[str, object] = {}

    class FakeResp:
        def read(self, n=-1):
            return json.dumps({"ok": True, "message": "claimed", "already_used": False}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    ok, msg = lic.report_activation_claim(key)
    assert ok, msg
    assert captured["url"] == "https://worker.test/api/claim"
    assert captured["body"]["code"] == key

