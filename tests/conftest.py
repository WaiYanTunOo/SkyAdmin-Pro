"""Shared fixtures: sandboxed app-data dir so tests never touch real data."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Phase 1 (SQLCipher): the suite uses throwaway DB files, so pin a constant
# test-only cipher salt. Production never sets this and derives the salt
# from the machine ID instead (see skyadmin_pro/db/cipher.py).
os.environ.setdefault("SKYADMIN_CIPHER_SALT", "SkyAdminTestCipherSalt-v1")

from skyadmin_pro.database import Database  # noqa: E402


@pytest.fixture
def fake_app_dir(tmp_path, monkeypatch):
    """Redirect app_data_dir() to a temp folder for the duration of a test."""
    import skyadmin_pro.paths as paths_mod

    base = tmp_path / ".skyadmin_pro"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: base)
    return base


@pytest.fixture
def real_app_dir():
    from skyadmin_pro.paths import app_data_dir

    return app_data_dir()


@pytest.fixture(autouse=True)
def _license_test_sandbox(request, tmp_path, monkeypatch):
    """Keep license tests off the developer's real ~/.skyadmin_pro (bans, rate limits)."""
    mod = getattr(request.module, "__name__", "")
    if mod not in (
        "test_license_ed25519",
        "test_license_security",
        "test_activation_dialog",
        "tests.test_license_ed25519",
        "tests.test_license_security",
        "tests.test_activation_dialog",
    ):
        return
    import skyadmin_pro.paths as paths_mod

    base = tmp_path / "skyadmin_license_test"
    base.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: base)
    return base


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(tmp_path / "test.db")
