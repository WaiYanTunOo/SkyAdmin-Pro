"""async_ui helper tests."""

from unittest.mock import MagicMock

from skyadmin_pro.ui.async_ui import run_background, run_on_main


def test_run_on_main_surfaces_callback_errors():
    widget = MagicMock()
    widget.winfo_exists.return_value = True
    feedback = MagicMock()
    widget.feedback = feedback

    def boom() -> None:
        raise RuntimeError("ui broke")

    run_on_main(widget, boom)
    callback = widget.after.call_args[0][1]
    callback()
    feedback.error.assert_called_once_with("ui broke")


def test_run_background_reports_worker_errors(monkeypatch):
    widget = MagicMock()
    widget.winfo_exists.return_value = True
    errors: list[str] = []

    class _ImmediateThread:
        def __init__(self, target, daemon=True):
            self._target = target

        def start(self):
            self._target()

    monkeypatch.setattr("skyadmin_pro.ui.async_ui.threading.Thread", _ImmediateThread)

    run_background(
        widget,
        work=lambda: (_ for _ in ()).throw(ValueError("worker failed")),
        on_error=errors.append,
    )
    callback = widget.after.call_args[0][1]
    callback()
    assert errors == ["worker failed"]
