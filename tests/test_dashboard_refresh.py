"""Dashboard deferred tree refresh lifecycle and fingerprint skip tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytest.importorskip("customtkinter")

from skyadmin_pro.ui.views.dashboard import DashboardView, snap_fingerprint


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    import customtkinter as ctk

    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.main_window import MainWindow

    tmp = tmp_path_factory.mktemp("dashboard_refresh")
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


def test_snap_fingerprint_stable_for_same_snapshot(db):
    snap = db.dashboard_snapshot()
    assert snap_fingerprint(snap) == snap_fingerprint(snap)


def test_snap_fingerprint_changes_when_counts_change(db):
    client_id = db.get_or_create_client("Acme Corp")
    before = snap_fingerprint(db.dashboard_snapshot())
    with db.connection() as conn:
        conn.execute(
            "INSERT INTO tasks (client_id, title, status, due_date) VALUES (?, ?, ?, ?)",
            (client_id, "Follow up", "pending", "2099-01-01"),
        )
    after = snap_fingerprint(db.dashboard_snapshot())
    assert before != after


def test_dashboard_cancels_deferred_refresh_on_hide():
    view = DashboardView.__new__(DashboardView)
    view._visible = True
    view._tree_refresh_after = "tree-1"
    view._detail_trees_after = "detail-1"
    view._timeline_after = "timeline-1"
    view.after_cancel = MagicMock()

    view.on_hide()

    assert view._visible is False
    assert view._tree_refresh_after is None
    assert view._detail_trees_after is None
    assert view._timeline_after is None
    assert view.after_cancel.call_count == 3


def test_dashboard_skips_deferred_trees_when_fingerprint_unchanged(monkeypatch, app):
    app.show_view("dashboard")
    view = app._views["dashboard"]
    snap = app.db.dashboard_snapshot()
    view._snap_fingerprint = snap_fingerprint(snap)
    view._trees_ready = True

    scheduled: list[tuple[int, object]] = []
    real_after = view.after

    def track_after(ms, fn):
        scheduled.append((ms, fn))
        return real_after(ms, fn)

    monkeypatch.setattr(view, "after", track_after)
    report_calls: list[int] = []
    orig_report = view._refresh_report

    def counting_report():
        report_calls.append(1)
        return orig_report()

    monkeypatch.setattr(view, "_refresh_report", counting_report)
    month_calls: list[int] = []
    orig_month = view.month_panel.refresh

    def counting_month():
        month_calls.append(1)
        return orig_month()

    monkeypatch.setattr(view.month_panel, "refresh", counting_month)

    view.on_show()
    # on_show() is now async (snapshot off thread): pump Tk + wait for worker.
    # NOTE: no time.sleep in the main thread — background run_on_main needs
    # the main thread inside Tcl (update/mainloop) to schedule its callback.
    import time as _time

    deadline = _time.time() + 10.0
    while _time.time() < deadline:
        app.update()
        if month_calls:
            break
    app.update()

    assert month_calls == [1]
    assert report_calls == []
    # Pumps (after 0/50ms queue drains) are expected with async refresh;
    # only tree rebuilds (100/80/120ms) must be skipped when unchanged.
    assert [ms for ms, _ in scheduled if ms in (100, 80, 120)] == []


def test_dashboard_mark_stale_forces_tree_rebuild(monkeypatch, app):
    app.show_view("dashboard")
    view = app._views["dashboard"]
    # Invalidate any in-flight async on_show snapshot so it can't schedule
    # trees after we install tracking (would duplicate [100,80,120]).
    view._snap_seq = int(getattr(view, "_snap_seq", 0)) + 1
    view._cancel_deferred_refresh()
    app.update()
    snap = app.db.dashboard_snapshot()
    view._snap_fingerprint = snap_fingerprint(snap)
    view._trees_ready = True

    scheduled: list[int] = []
    real_after = view.after

    def track_after(ms, fn):
        scheduled.append(ms)
        return real_after(0, fn)

    monkeypatch.setattr(view, "after", track_after)
    view.mark_stale()
    view.refresh()
    app.update()

    # Filter queue-pump afters (0/50ms); only tree rebuilds matter here.
    assert [ms for ms in scheduled if ms in (100, 80, 120)] == [100, 80, 120]


def test_dashboard_settings_round_trip_skips_priority_trees(monkeypatch, app):
    from skyadmin_pro.config import NAV_DASHBOARD, NAV_SETTINGS

    app.show_view(NAV_DASHBOARD)
    view = app._views[NAV_DASHBOARD]
    real_after = view.after

    def immediate_after(ms, fn):
        return real_after(0, fn)

    monkeypatch.setattr(view, "after", immediate_after)
    view.refresh(force=True)
    app.update()
    assert view._trees_ready

    priority_calls: list[int] = []
    orig_priority = view._refresh_priority_trees

    def spy_priority(snap):
        priority_calls.append(1)
        return orig_priority(snap)

    monkeypatch.setattr(view, "_refresh_priority_trees", spy_priority)

    def passthrough_after(ms, fn):
        return real_after(ms, fn)

    monkeypatch.setattr(view, "after", passthrough_after)

    app.show_view(NAV_SETTINGS)
    app.update()
    app.show_view(NAV_DASHBOARD)
    app.update()

    assert priority_calls == []


def test_dashboard_deferred_trees_skip_when_hidden_before_callback(app):
    app.show_view("dashboard")
    view = app._views["dashboard"]
    view._visible = False
    view._trees_ready = False
    snap = app.db.dashboard_snapshot()

    view._refresh_priority_trees(snap)
    view._refresh_detail_trees(snap)
    view._draw_timeline_deferred(snap)

    assert view._trees_ready is False


def test_dashboard_force_refresh_schedules_trees(monkeypatch, app):
    app.show_view("dashboard")
    view = app._views["dashboard"]
    view._snap_seq = int(getattr(view, "_snap_seq", 0)) + 1
    view._cancel_deferred_refresh()
    app.update()
    snap = app.db.dashboard_snapshot()
    view._snap_fingerprint = snap_fingerprint(snap)
    view._trees_ready = True

    scheduled: list[int] = []
    real_after = view.after

    def track_after(ms, fn):
        scheduled.append(ms)
        return real_after(0, fn)

    monkeypatch.setattr(view, "after", track_after)

    view.refresh(force=True)
    app.update()

    assert [ms for ms in scheduled if ms in (100, 80, 120)] == [100, 80, 120]
    assert view._trees_ready is True
