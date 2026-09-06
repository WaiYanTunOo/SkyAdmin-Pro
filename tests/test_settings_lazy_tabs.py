"""Settings tabs are created lazily — only General is built at first open."""

from __future__ import annotations

from pathlib import Path


def test_settings_lazy_tabs_pattern():
    src = Path("skyadmin_pro/ui/views/settings/view.py").read_text(encoding="utf-8")
    assert "self._lazy_tabs" in src
    assert "_ensure_lazy_tab" in src
    assert 'self._ensure_lazy_tab("General")' in src
    # Must not eagerly build all four tabs in build().
    assert "_build_license_tab(self.tabs.tab" not in src
    assert "_build_business_tab(self.tabs.tab" not in src
    assert "_build_data_tab(self.tabs.tab" not in src
    assert "command=self._on_tab_changed" in src
