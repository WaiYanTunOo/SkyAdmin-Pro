"""Tests for workspace paths and normalization."""

from __future__ import annotations

import sys

from skyadmin_pro.config import APP_NAME, SETTING_WORKSPACE_ROOT
from skyadmin_pro.database import Database
from skyadmin_pro.paths import WorkspacePaths, default_workspace_root


def test_default_workspace_root_windows_unfrozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    root = default_workspace_root()
    expected = tmp_path / "Programs" / APP_NAME / "Workspace"
    assert root == expected


def test_default_workspace_root_frozen(monkeypatch, tmp_path):
    fake_exe = tmp_path / "bin" / "SkyAdminPro.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    root = default_workspace_root()
    assert root == fake_exe.parent / "Workspace"


def test_workspace_paths_structure(tmp_path):
    root = tmp_path / "custom_workspace"
    wp = WorkspacePaths(root)
    assert wp.root == root
    assert wp.staging == root / "00_Staging_Area"
    assert wp.ready_to_upload == root / "02_Ready_to_Upload"
    assert wp.archive == root / "Z_Archive_Backup"
    assert wp.clients == root / "Clients"
    assert wp.suppliers == root / "Suppliers"

    wp.ensure()
    assert wp.staging.is_dir()
    assert wp.ready_to_upload.is_dir()
    assert wp.archive.is_dir()
    assert wp.clients.is_dir()
    assert wp.suppliers.is_dir()


def test_normalize_workspace_migrates_and_cleans_empty_legacy(tmp_path, monkeypatch):
    from main import _normalize_workspace

    desired_dir = tmp_path / "Programs" / APP_NAME / "Workspace"
    legacy_dir = tmp_path / "OneDrive" / "Documents" / APP_NAME
    legacy_sub = legacy_dir / "00_Staging_Area"
    legacy_sub.mkdir(parents=True, exist_ok=True)

    db_file = tmp_path / "test.db"
    db = Database(db_file)
    db.set_setting(SETTING_WORKSPACE_ROOT, str(legacy_dir))

    monkeypatch.setattr("skyadmin_pro.paths.default_workspace_root", lambda: desired_dir)

    _normalize_workspace(db)

    assert db.get_setting(SETTING_WORKSPACE_ROOT) == str(desired_dir)
    assert desired_dir.is_dir()
    assert not legacy_dir.exists()
