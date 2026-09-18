"""Dashboard layout: Today scrolls; Incentive report_tree is outside CanvasScrollFrame."""

from pathlib import Path


def _src(*parts: str) -> str:
    return (Path(__file__).resolve().parents[1].joinpath(*parts)).read_text(encoding="utf-8")


def _pkg(*parts: str) -> str:
    root = Path(__file__).resolve().parents[1].joinpath(*parts)
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))


def test_dashboard_detail_trees_not_in_canvas_scroll():
    shell = _src("skyadmin_pro", "ui", "views", "dashboard", "dashboardViewMixin0.py")
    tabs = _src("skyadmin_pro", "ui", "views", "dashboard", "tabs.py")
    heavy = _src("skyadmin_pro", "ui", "views", "dashboard", "dashboardViewMixin13.py")
    assert "self._detail = ctk.CTkFrame(self.body" in shell
    assert "self._detail_scroll = CanvasScrollFrame(self.body" not in shell
    assert "view._detail_scroll = CanvasScrollFrame(today_tab)" in tabs
    assert "view._today = view._detail_scroll.content" in tabs
    assert "ThemedTreeview(" in heavy
    assert "self._incentive" in heavy


def test_dashboard_build_defers_header_extras():
    shell = _src("skyadmin_pro", "ui", "views", "dashboard", "dashboardViewMixin0.py")
    build_src = shell.split("def build(self)")[1].split("def _build_header_extras")[0]
    assert "self.next_tree" not in build_src
    assert "timeline_canvas" not in build_src
    assert "_build_header_extras" in shell
    on_show = _src("skyadmin_pro", "ui", "views", "dashboard", "dashboardViewMixin1.py").split("def on_show")[1]
    if "\n    def " in on_show:
        on_show = on_show.split("\n    def ")[0]
    assert "self._build_header_extras()" in on_show
    assert "self._schedule_detail_trees_progressive()" in on_show
    assert "self._build_detail_trees()" not in on_show
    text = _pkg("skyadmin_pro", "ui", "views", "dashboard")
    assert "def _build_detail_trees_priority" in text
    assert "def _build_detail_trees_secondary" in text
    assert "def _build_detail_trees_heavy" in text
