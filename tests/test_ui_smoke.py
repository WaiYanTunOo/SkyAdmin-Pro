"""Offscreen UI smoke: main window builds, sidebar, settings, data flows."""

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


def test_sidebar_toggle_collapses_and_expands(app):
    assert not app._sidebar_collapsed
    app._toggle_sidebar()
    app.update()
    assert app._sidebar_collapsed
    assert app.sidebar.cget("width") == 56
    for btn in app._nav_buttons.values():
        assert "  " not in btn.cget("text")
    app._toggle_sidebar()
    app.update()
    assert not app._sidebar_collapsed


def test_sidebar_has_six_nav_buttons(app):
    assert len(app._nav_buttons) == 6
    for _key, btn in app._nav_buttons.items():
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


def test_document_hub_lazy_tabs(app):
    app.show_view("document_hub")
    app.update()
    view = app._views["document_hub"]
    assert view.title == "Document Hub"
    for tab in (
        "Smart Renamer",
        "Image to PDF",
        "Agent Bundle",
        "Portal Upload",
        "Archive & Clean",
        "Financial Docs",
    ):
        view.tabs.set(tab)
        app.update()
        assert view.tabs.get() == tab


def test_settings_workspace_field(app):
    app.show_view("settings")
    app.update()
    settings = app._views["settings"]
    assert hasattr(settings, "workspace_var")
    assert settings.workspace_var.get().strip()


def test_settings_sync_status_labels(app):
    app.show_view("settings")
    app.update()
    settings = app._views["settings"]
    assert hasattr(settings, "data_sync_label")
    settings._refresh_license_label()
    app.update()
    assert "sync" in settings.data_sync_label.cget("text").lower()


def test_settings_minimum_geometry(app):
    app.geometry("1100x700")
    app.update()
    for key in ("dashboard", "document_hub", "database_tasks", "office_hub", "utilities", "settings"):
        app.show_view(key)
        app.update()
        view = app._views[key]
        assert view.winfo_width() > 0
        assert view.winfo_height() > 0
