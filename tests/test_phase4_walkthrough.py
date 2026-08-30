"""Automated Phase 4 walkthrough — offscreen checks mirroring docs/PHASE4_WALKTHROUGH.md."""

from __future__ import annotations

import customtkinter as ctk
import pytest

pytest.importorskip("customtkinter")

pytestmark = pytest.mark.walkthrough

SIDEBAR_VIEWS = ("dashboard", "document_hub", "database_tasks", "office_hub", "utilities", "settings")
DB_TABS = (
    "Tasks",
    "Courier Tracker",
    "Clients & Expiry",
    "Monthly Tax Status",
    "Company Details",
    "Renewals",
    "Service Pipeline",
    "Suppliers & AP",
)
DOC_TABS = (
    "Smart Renamer",
    "Image to PDF",
    "Agent Bundle",
    "Portal Upload",
    "Archive & Clean",
    "Financial Docs",
)


def _find_unthemed_entries(widget, path: str = "") -> list[str]:
    """CTkEntry widgets missing themed border (border_width=1)."""
    bad: list[str] = []
    for child in widget.winfo_children():
        name = f"{path}/{type(child).__name__}"
        if isinstance(child, ctk.CTkEntry):
            try:
                if int(child.cget("border_width")) != 1:
                    bad.append(name)
            except Exception:
                bad.append(name)
        bad.extend(_find_unthemed_entries(child, name))
    return bad


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.main_window import MainWindow

    tmp = tmp_path_factory.mktemp("phase4")
    db = Database(tmp / "test.db")
    paths = WorkspacePaths(tmp / "workspace")
    paths.ensure()
    client_id = db.get_or_create_client("Walkthrough Co")
    db.get_or_create_client("Second Co")
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO documents (client_id, document_type, expiry_date) VALUES (?, ?, ?)",
            (client_id, "Visa", "2027-01-01"),
        )
    ctk.set_appearance_mode("dark")
    window = MainWindow(db=db, paths=paths)
    window.geometry("1100x700")
    window.update()
    yield window
    try:
        window.destroy()
    except Exception:
        pass


def test_phase4_all_sidebar_views_load(app):
    failures: list[str] = []
    for key in SIDEBAR_VIEWS:
        app.show_view(key)
        app.update()
        view = app._views.get(key)
        if view is None:
            failures.append(f"{key}: view not loaded")
            continue
        if view.winfo_width() <= 0 or view.winfo_height() <= 0:
            failures.append(f"{key}: zero geometry")
        unthemed = _find_unthemed_entries(view)
        if unthemed:
            failures.append(f"{key}: unthemed entries {unthemed[:3]}")
    assert not failures, ";\n".join(failures)


def test_phase4_database_tasks_tabs(app):
    app.show_view("database_tasks")
    app.update()
    view = app._views["database_tasks"]
    failures: list[str] = []
    for tab in DB_TABS:
        view.tabs.set(tab)
        app.update()
        if view.tabs.get() != tab:
            failures.append(f"tab not selected: {tab}")
        panel = view.tabs.tab(tab)
        unthemed = _find_unthemed_entries(panel)
        if unthemed:
            failures.append(f"{tab}: unthemed entries {unthemed[:3]}")
    assert not failures, ";\n".join(failures)


def test_phase4_document_hub_tabs(app):
    app.show_view("document_hub")
    app.update()
    view = app._views["document_hub"]
    for tab in DOC_TABS:
        view.tabs.set(tab)
        app.update()
        assert view.tabs.get() == tab


def test_phase4_theme_toggle_refreshes_views(app):
    for mode in ("Light", "Dark"):
        ctk.set_appearance_mode(mode)
        app.show_view("settings")
        app.update()
        settings = app._views["settings"]
        settings.appearance_menu.set(mode)
        settings._on_appearance_change(mode)
        app.update()
        unthemed = _find_unthemed_entries(settings)
        assert not unthemed, f"settings unthemed after {mode}: {unthemed[:5]}"


def test_phase4_settings_phase3_controls(app):
    app.show_view("settings")
    app.update()
    settings = app._views["settings"]
    assert hasattr(settings, "data_sync_label")
    settings._refresh_license_label()
    app.update()
    assert "sync" in settings.data_sync_label.cget("text").lower()
    assert settings.app.db.quick_check() is True


def test_phase5_settings_sync_conflicts_button(app):
    app.show_view("settings")
    app.update()
    settings = app._views["settings"]
    assert hasattr(settings, "conflicts_btn")
    with app.db.connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_conflicts (table_name, global_id, direction, local_updated_at, remote_updated_at)
            VALUES ('clients', 'test-gid', 'pull', '2026-02-01', '2026-01-01')
            """
        )
    settings._refresh_license_label()
    app.update()
    assert settings.conflicts_btn.cget("state") == "normal"
    assert "1" in settings.conflicts_btn.cget("text")
    rows = app.db.list_sync_conflicts()
    assert len(rows) == 1
    app.db.clear_sync_conflicts()


def test_phase4_company_details_vo_fields(app):
    app.show_view("database_tasks")
    app.update()
    view = app._views["database_tasks"]
    view.tabs.set("Company Details")
    app.update()
    view._ensure_lazy_panel("Company Details")
    app.update()
    panel = view.company_panel
    assert hasattr(panel, "vo_address_var")
    assert hasattr(panel, "shareholder_var")


def test_phase5_activation_dialog_offscreen(monkeypatch, fake_app_dir):
    """Activation dialog builds and accepts a valid dev-signed key offline."""
    import time

    import skyadmin_pro.paths as paths_mod
    from skyadmin_pro.services.license_authoring import generate_ed25519_license
    from skyadmin_pro.ui.activation import ActivationDialog

    monkeypatch.setattr(paths_mod, "app_data_dir", lambda: fake_app_dir)
    mid = "ABCD1234EFGH5678"
    saved: list[str] = []

    monkeypatch.setattr("skyadmin_pro.services.license.get_machine_id", lambda: mid)
    monkeypatch.setattr("skyadmin_pro.services.license.requires_online_check", lambda: False)
    monkeypatch.setattr(
        "skyadmin_pro.services.license.save_license_file",
        lambda content: saved.append(content),
    )

    app = ctk.CTk()
    app.withdraw()
    dialog = ActivationDialog(app, allow_quit=False)
    dialog.geometry("620x740")
    dialog.update()

    assert dialog.activate_btn.winfo_exists()
    assert "Activate Now" in dialog.activate_btn.cget("text")

    key = generate_ed25519_license(mid, days_valid=7, package_days=7)
    dialog.key_box.insert("1.0", key)
    dialog._activate()
    for _ in range(80):
        dialog.update()
        if saved:
            break
        time.sleep(0.05)
    status_text = dialog.status.cget("text")

    dialog.destroy()
    app.destroy()

    assert saved, "activation should save license when online check disabled"
    assert "Activation complete" in status_text
