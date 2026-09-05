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


def test_dashboard_build_defers_header_extras():
    text = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "dashboard.py").read_text(
        encoding="utf-8"
    )
    build_src = text.split("def build(self)")[1].split("def _build_header_extras")[0]
    assert "self.next_tree" not in build_src
    assert "timeline_canvas" not in build_src
    assert "_build_header_extras" in text
    on_show = text.split("def on_show")[1].split("def on_hide")[0]
    assert "self._build_header_extras()" in on_show
    assert "self._schedule_detail_trees_progressive()" in on_show
    assert "self._build_detail_trees()" not in on_show
    assert "def _build_detail_trees_priority" in text
    assert "def _build_detail_trees_secondary" in text
    assert "def _build_detail_trees_heavy" in text