"""UI structural tests — verify widget hierarchy and layout properties."""

from __future__ import annotations

import pytest

pytest.importorskip("customtkinter")


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


def test_sidebar_has_all_nav_buttons(app):
    """Sidebar has a button for each navigation item."""
    from skyadmin_pro.config import NAV_ITEMS

    assert len(app._nav_buttons) == len(NAV_ITEMS)
    for key, _label in NAV_ITEMS:
        assert key in app._nav_buttons


def test_sidebar_toggle_changes_width(app):
    """Toggle sidebar collapses and expands."""
    original_width = app.sidebar.cget("width")
    app._toggle_sidebar()
    app.update()
    collapsed_width = app.sidebar.cget("width")
    assert collapsed_width < original_width
    app._toggle_sidebar()
    app.update()
    assert app.sidebar.cget("width") == original_width


def test_all_views_registered(app):
    """All navigation views are lazily loaded — only dashboard is eager."""
    from skyadmin_pro.config import NAV_ITEMS

    # Dashboard is loaded eagerly on startup
    assert "dashboard" in app._views
    # Other views load lazily on first show
    for key, _label in NAV_ITEMS:
        if key == "dashboard":
            continue
        # Trigger lazy load
        app.show_view(key)
        app.update()
        assert key in app._views, f"View {key} failed to lazy-load"


def test_dashboard_view_has_widgets(app):
    """Dashboard view contains stat cards and treeviews."""
    app.show_view("dashboard")
    app.update()
    view = app._views.get("dashboard")
    assert view is not None
    children = view.winfo_children()
    assert len(children) > 0


def test_settings_view_has_appearance_menu(app):
    """Settings view has appearance mode selector."""
    app.show_view("settings")
    app.update()
    view = app._views.get("settings")
    assert view is not None
    assert hasattr(view, "appearance_menu")


def test_database_tasks_view_has_tabs(app):
    """Database & Tasks view has tab container."""
    app.show_view("database_tasks")
    app.update()
    view = app._views.get("database_tasks")
    assert view is not None
    assert hasattr(view, "tabs")


def test_status_bar_exists(app):
    """Status bar is present at the bottom."""
    assert hasattr(app, "status_bar")
    assert hasattr(app, "status_label")


def test_theme_toggle_switches_mode(app):
    """Ctrl+D toggles between dark and light mode."""
    import customtkinter as ctk

    original = ctk.get_appearance_mode()
    app._toggle_dark_light()
    app.update()
    new_mode = ctk.get_appearance_mode()
    assert new_mode != original
    # Toggle back
    app._toggle_dark_light()
    app.update()
    assert ctk.get_appearance_mode() == original


def test_global_search_shortcut_bound(app):
    """Ctrl+F shortcut is bound (dialog creation needs full theme context)."""
    # Verify the shortcut binding exists
    assert app.bind("<Control-f>") is not None
    assert app.bind("<Control-F>") is not None


def test_keyboard_shortcuts_bound(app):
    """Live keyboard shortcuts are bound (including Ctrl+S save)."""
    assert app.bind("<Control-f>") is not None
    assert app.bind("<Control-d>") is not None
    assert app.bind("<Control-e>") is not None
    assert app.bind("<Control-n>") is not None
    assert app.bind("<Control-z>") is not None
    assert app.bind("<Control-s>") is not None
    assert app.bind("<Control-S>") is not None
    assert callable(getattr(app, "_shortcut_save", None))
    assert callable(getattr(app, "_shortcut_new", None))
    assert callable(getattr(app, "open_global_search", None))
    # Backup remains Settings-only — no Ctrl+B.
    assert app.bind("<Control-b>") in (None, "")


def test_shortcut_save_noop_status(app):
    """Ctrl+S on a view without save reports Nothing to save."""
    statuses: list[str] = []
    app.set_status = statuses.append  # type: ignore[method-assign]
    app.show_view("dashboard")
    app.update()
    app._shortcut_save()
    assert statuses and statuses[-1] == "Nothing to save"


def test_shortcut_dispatch_reaches_clients_panel(app, monkeypatch):
    """Ctrl+Z / Ctrl+N forward to the clients panel (no AttributeError)."""
    app.show_view("database_tasks")
    app.update()
    view = app.get_view("database_tasks")
    assert view is not None
    view._ensure_lazy_panel("Clients & Expiry")
    panel = view.clients_panel
    assert panel is not None

    undo_calls: list[str] = []
    new_calls: list[str] = []
    monkeypatch.setattr(panel, "_undo_last", lambda: undo_calls.append("undo"))
    monkeypatch.setattr(panel, "_open_client_dialog", lambda: new_calls.append("new"))

    view._on_shortcut_undo()
    view._on_shortcut_new()
    assert undo_calls == ["undo"]
    assert new_calls == ["new"]


def test_shortcut_new_from_dashboard_navigates(app, monkeypatch):
    """Ctrl+N from Dashboard navigates to Database & Tasks and opens new client."""
    app.show_view("dashboard")
    app.update()
    opened: list[str] = []

    # Pre-create the view and stub the dialog before the shortcut runs.
    tasks = app._ensure_view("database_tasks")
    assert tasks is not None
    tasks._ensure_lazy_panel("Clients & Expiry")
    monkeypatch.setattr(
        tasks.clients_panel,
        "_open_client_dialog",
        lambda: opened.append("new"),
    )

    app._shortcut_new()
    app.update()
    assert app._active_key == "database_tasks"
    assert opened == ["new"]


def test_audit_log_dialog_loads_without_crash(app):
    """AuditLogDialog renders via set_rows (empty state or data rows)."""
    from skyadmin_pro.ui.views.audit_log import AuditLogDialog

    dlg = AuditLogDialog(app)
    app.update()
    try:
        assert dlg.tree.tree.get_children(), "expected empty-message row or data"
    finally:
        try:
            dlg.destroy()
        except Exception:
            pass
