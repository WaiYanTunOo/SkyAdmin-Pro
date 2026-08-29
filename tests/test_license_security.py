"""License core: unique keys, tamper resistance, one-time use, self-heal."""

import base64
import json
from datetime import datetime, timedelta

import pytest

import skyadmin_pro.services.license as lic


@pytest.fixture
def mid():
    return lic.get_machine_id()


def _sign(payload: str) -> str:
    return lic._hmac(payload)


def _wrap(obj: dict) -> str:
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


# --- uniqueness -----------------------------------------------------------

def test_keys_unique_for_identical_params(mid):
    keys = {lic.generate_license(mid, 14, package_days=14) for _ in range(3)}
    assert len(keys) == 3


def test_key_verifies_and_reports_package(mid):
    key = lic.generate_license(mid, days_valid=7, package_days=7)
    ok, msg, nonce = lic.check_activation_usable(key)
    assert ok
    assert "7-day package" in msg.lower()
    assert nonce


# --- tamper resistance ----------------------------------------------------

@pytest.mark.parametrize("field,value", [
    ("exp", "2099-01-01T00:00:00"),
    ("pkg", "365"),
    ("n", "deadbeefdead"),
    ("iat", "2020-01-01T00:00"),
])
def test_tampered_field_rejected(mid, field, value):
    key = lic.generate_license(mid, days_valid=30, package_days=30)
    b64 = "".join(key.split())
    b64 += "=" * (-len(b64) % 4)
    obj = json.loads(base64.urlsafe_b64decode(b64))
    obj[field] = value
    tampered = base64.urlsafe_b64encode(
        json.dumps(obj, separators=(",", ":")).encode()
    ).decode().rstrip("=")
    ok, _msg = lic.verify_key_text(tampered)
    assert not ok


def test_wrong_machine_rejected(mid):
    other = lic.generate_license("0123456789ABCDEF", 30, package_days=30)
    ok, msg, _n = lic.check_activation_usable(other)
    assert not ok and "machine" in msg.lower()


def test_expired_rejected(mid):
    exp = (datetime.now() - timedelta(days=1)).replace(microsecond=0).isoformat(timespec="seconds")
    payload = f"{mid}|{exp}|x|x|1"
    obj = {"mid": mid, "exp": exp, "sig": _sign(payload), "iat": "x", "n": "x", "pkg": "1"}
    ok, msg, _n = lic.check_activation_usable(_wrap(obj))
    assert not ok and "expire" in msg.lower()


# --- one-time use ---------------------------------------------------------

def test_burn_blocks_redemption(mid, fake_app_dir, monkeypatch):
    (fake_app_dir / "hardware.id").write_text(mid, encoding="utf-8")
    import skyadmin_pro.paths as pm

    monkeypatch.setattr(pm, "app_data_dir", lambda: fake_app_dir)

    key = lic.generate_license(mid, days_valid=7, package_days=7)
    payload = lic._payload_of(key)
    nonce = payload["n"]

    # Not burned yet → redeemable; then burn.
    ok, msg, _ = lic.check_activation_usable(key)
    assert ok, f"pre-burn failed: {msg}"
    lic.mark_used(nonce)

    # Same code re-pasted while still saved = repair case → allowed.
    lic.save_license_file(key)
    ok, _, _ = lic.check_activation_usable(key)
    assert ok

    # A DIFFERENT machine's saved license (different nonce) → blocked.
    monkeypatch.setattr(
        lic, "_read_license_payload",
        lambda: {"mid": mid, "exp": payload["exp"], "n": "other-nonce-xyz"},
    )
    ok, msg, _ = lic.check_activation_usable(key)
    assert not ok and "already been used" in msg.lower()


# --- machine ban covers passcode ------------------------------------------

def test_machine_ban_blocks_key_and_passcode(mid, fake_app_dir):
    # Seed hardware.id so get_machine_id() returns the same value
    hw = fake_app_dir / "hardware.id"
    hw.write_text(mid, encoding="utf-8")
    banned = fake_app_dir / "banned.txt"
    banned.write_text(mid + "\n", encoding="utf-8")

    ok, msg = lic.verify_key_text(lic.generate_license(mid, 30, package_days=30))
    assert not ok and "blocked" in msg.lower()
    ok, msg = lic.verify_key_text(lic.generate_passcode(mid))
    assert not ok and "blocked" in msg.lower()

    banned.unlink()
    hw.unlink()


# --- SKYCTRL1 signed control list -----------------------------------------

def _ctrl_wrap(lines):
    plaintext = "\n".join(lines) + "\n"
    obj = {
        "v": 1,
        "alg": "HMAC-SHA256",
        "sig": _sign(plaintext),
        "payload": base64.urlsafe_b64encode(plaintext.encode()).decode().rstrip("="),
    }
    wrapped = base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")
    return "SKYCTRL1:" + wrapped


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
    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod
    import urllib.request

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")  # use Gist path for this test
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: FakeResp(
            _ctrl_wrap([f"REVOKE n{mid[:6]}", f"BAN {mid}", "USED u123"])
        )
    )
    ok, msg = lic.fetch_revocations(timeout=1)
    assert ok, msg
    assert (fake_app_dir / "revoked.txt").read_text().strip() == f"n{mid[:6]}"
    assert (fake_app_dir / "banned.txt").read_text().strip() == mid
    assert "u123" in lic.used_nonces()

    # Owner clears everything → local state replaced (empty).
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: FakeResp(_ctrl_wrap([]))
    )
    ok, msg = lic.fetch_revocations(timeout=1)
    assert ok
    assert not (fake_app_dir / "revoked.txt").exists()
    assert not (fake_app_dir / "banned.txt").exists()


def test_control_list_tamper_refused(mid, fake_app_dir, monkeypatch):
    import skyadmin_pro.config as cfg
    import skyadmin_pro.paths as paths_mod
    import urllib.request
    from io import BytesIO

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    monkeypatch.setattr(cfg, "REVOCATION_URL", "https://x/raw/c.txt")
    monkeypatch.setattr(cfg, "API_BASE_URL", "")  # use Gist path for this test

    good = _ctrl_wrap([f"REVOKE n{mid[:6]}"])
    wrapped = good.split(":", 1)[1]
    wrapped += "=" * (-len(wrapped) % 4)
    obj = json.loads(base64.urlsafe_b64decode(wrapped.encode()))
    pt = base64.b64decode(obj["payload"]).decode().replace("REVOKE", "BAN   ")
    obj["payload"] = base64.b64encode(pt.encode()).decode().rstrip("=")
    evil = "SKYCTRL1:" + base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

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


# --- update checker -------------------------------------------------------

def test_update_info_roundtrip_and_compare(fake_app_dir):
    from skyadmin_pro.config import APP_VERSION
    from skyadmin_pro.services.license import is_newer_version, read_update_info

    assert read_update_info() is None or isinstance(read_update_info(), dict)
    assert is_newer_version("0.2.1", "0.2.0")
    assert not is_newer_version("0.2.0", "0.2.0")
    assert not is_newer_version("0.1.9", "0.2.0")
    assert APP_VERSION  # sanity
