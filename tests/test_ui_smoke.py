"""Offscreen UI smoke: main window builds, sidebar, settings, data flows."""

import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("customtkinter")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    import customtkinter as ctk

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.main_window import MainWindow

    tmp = tmp_path_factory.mktemp("ui")
    db = Database(tmp / "test.db")

    # Copy the developer's real DB when present so data-dependent asserts run.
    real_db = Path.home() / ".skyadmin_pro" / "skyadmin_pro.db"
    if real_db.exists():
        db.shutdown()
        shutil.copy2(real_db, tmp / "test.db")
        db = Database(tmp / "test.db")

    paths = WorkspacePaths(tmp / "workspace")
    paths.ensure()
    ctk.set_appearance_mode("dark")
    window = MainWindow(db=db, paths=paths)
    window.update()
    yield window
    try:
        window.destroy()
    except Exception:
        pass


def test_sidebar_has_six_nav_buttons(app):
    assert len(app._nav_buttons) == 6
    for key, btn in app._nav_buttons.items():
        assert btn.cget("text").strip()


def test_views_lazy_loaded(app):
    assert len(app._views) == 1
    assert "dashboard" in app._views
    for key in ("document_hub", "database_tasks", "office_hub", "utilities", "settings"):
        assert key not in app._views
        app.show_view(key)
        app.update()
        assert key in app._views


def test_settings_license_controls(app):
    app.show_view("settings")
    app.update()
    settings = app._views["settings"]
    texts = []
    def walk(w):
        for c in w.winfo_children():
            if isinstance(c, __import__("customtkinter").CTkButton):
                texts.append(str(c.cget("text")))
            walk(c)
    walk(settings)
    assert sum("Activate / Manage" in t for t in texts) == 1
    assert any("Disclaimer" in t for t in texts)
