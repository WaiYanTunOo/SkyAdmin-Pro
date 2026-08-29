"""Shared fixtures: sandboxed app-data dir so tests never touch real data."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skyadmin_pro.database import Database


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


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(tmp_path / "test.db")
