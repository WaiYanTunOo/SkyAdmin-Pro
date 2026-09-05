"""Dashboard layout: detail trees are not inside a page scroll container."""

from pathlib import Path


def test_dashboard_detail_trees_not_in_canvas_scroll():
    text = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "dashboard.py").read_text(
        encoding="utf-8"
    )
    # Header is fixed above scroll; detail is inside CanvasScrollFrame to avoid clipping on 1080p
    assert "CanvasScrollFrame" in text
    assert "self._detail_scroll = CanvasScrollFrame(self.body" in text
    assert "self._detail = ctk.CTkFrame(self._detail_scroll.content" in text
    assert "self._header = ctk.CTkFrame(self.body" in text
