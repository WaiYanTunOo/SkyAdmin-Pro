"""Document Hub polling lifecycle tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from skyadmin_pro.ui.views.document_hub.view import DocumentHubView


def test_document_hub_build_defers_all_panels(monkeypatch):
    """Document Hub shell should not construct tool panels until first visit."""
    built: list[str] = []
    tabs_mock = MagicMock()
    tabs_mock.tab.return_value = MagicMock()

    def _add(name: str) -> None:
        built.append(name)

    tabs_mock.add = _add
    monkeypatch.setattr(
        "skyadmin_pro.ui.views.document_hub.view.themed_tabview",
        lambda *_args, **_kwargs: tabs_mock,
    )

    view = DocumentHubView.__new__(DocumentHubView)
    view.body = MagicMock()
    view.app = MagicMock()
    DocumentHubView.build(view)

    assert built == [
        "Smart Renamer",
        "Image to PDF",
        "Agent Bundle",
        "Portal Upload",
        "Archive & Clean",
        "Financial Docs",
    ]
    assert view.renamer is None
    assert view.converter is None
    assert view._lazy_panels == {}


def test_document_hub_stops_polling_on_hide():
    view = DocumentHubView.__new__(DocumentHubView)
    view._polling = True
    view._poll_after = "poll-1"
    view.after_cancel = MagicMock()
    view.winfo_exists = MagicMock(return_value=True)

    view.on_hide()

    assert view._polling is False
    assert view._poll_after is None
    view.after_cancel.assert_called_once_with("poll-1")


def test_document_hub_cancel_poll_is_idempotent():
    view = DocumentHubView.__new__(DocumentHubView)
    view._poll_after = None
    view.after_cancel = MagicMock()

    view._cancel_poll()

    view.after_cancel.assert_not_called()
