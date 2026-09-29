"""SkyAgent chat must not grab the root — DatePicker stays usable while open."""

from pathlib import Path


def _src(*parts: str) -> str:
    return (Path(__file__).resolve().parents[1].joinpath(*parts)).read_text(encoding="utf-8")


def test_skyagent_ui_has_no_grab_set() -> None:
    """Chat construction must not call grab_set / make_modal (no grab fight)."""
    package = Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "skyagent"
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "grab_set" not in text, f"{path.name} must not call grab_set"
        assert "make_modal" not in text, f"{path.name} must not use make_modal"


def test_skyagent_destroy_has_no_leftover_grab() -> None:
    """destroy() only cancels the async pump; no grab_release needed without grab."""
    mixin = _src("skyadmin_pro", "ui", "views", "skyagent", "chat_mixin.py")
    assert "def destroy(self)" in mixin
    assert "cancel_pump" in mixin
    assert "grab_release" not in mixin
    assert "grab_set" not in mixin


def test_open_skyagent_shortcut_and_singleton_lift() -> None:
    """Ctrl+Shift+A opens SkyAgent; second invoke lifts existing toplevel."""
    main = _src("skyadmin_pro", "ui", "main_window.py")
    assert 'bind("<Control-Shift-a>"' in main
    assert 'bind("<Control-Shift-A>"' in main
    assert "open_skyagent" in main
    assert "self._skyagent_chat.lift()" in main
    assert "SkyAgentChat(self)" in main
