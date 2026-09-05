"""A4 — measure Dashboard first on_show progressive paint (automated)."""

from __future__ import annotations

import os
import time

import pytest

pytest.importorskip("customtkinter")


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    import customtkinter as ctk

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.main_window import MainWindow

    tmp = tmp_path_factory.mktemp("dash_paint")
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


def _pump(app, view, rounds: int = 40) -> None:
    for _ in range(rounds):
        try:
            app.update()
            view.update_idletasks()
        except Exception:
            break


def test_dashboard_progressive_on_show_completes_and_is_timed(app, capsys):
    """Time first Dashboard on_show through progressive tree stages."""
    # Fresh dashboard instance path: show_view builds if needed
    t0 = time.perf_counter()
    app.show_view("dashboard")
    view = app._views["dashboard"]
    _pump(app, view)
    # Force remaining stages if any after() still pending
    if not getattr(view, "_detail_built", False):
        view._build_detail_trees()
        _pump(app, view, 10)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert getattr(view, "_detail_built", False) or getattr(view, "_detail_stage", 0) >= 1
    # Soft budget for CI/offscreen — not a hard SLA; log for Wave A notes.
    assert elapsed_ms < 30_000, f"Dashboard first show took {elapsed_ms:.0f}ms"

    if os.environ.get("SKYADMIN_DASHBOARD_PAINT") == "1":
        print(f"DASHBOARD_FIRST_ON_SHOW_MS={elapsed_ms:.1f}")
