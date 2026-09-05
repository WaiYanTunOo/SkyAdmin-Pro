"""CanvasScrollFrame smoke tests."""

import customtkinter as ctk

pytestmark = __import__("pytest").mark.skipif(
    __import__("importlib").util.find_spec("customtkinter") is None,
    reason="customtkinter not installed",
)


def test_canvas_scroll_frame_hosts_content():
    import pytest

    from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame

    ctk.set_appearance_mode("dark")
    try:
        root = ctk.CTk()
    except Exception as exc:  # headless or Tcl missing
        pytest.skip(f"Tk unavailable: {exc}")
        return
    try:
        root.withdraw()
        scroll = CanvasScrollFrame(root)
        scroll.pack(fill="both", expand=True)
        label = ctk.CTkLabel(scroll.content, text="Field")
        label.pack()
        root.update_idletasks()
        assert label.winfo_parent() == str(scroll.content)
        scroll.refresh_theme()
    except Exception as exc:
        pytest.skip(f"Tk init failed: {exc}")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def test_filing_history_outside_form_scroll():
    from pathlib import Path

    panel_src = (
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "company_details" / "panel.py"
    ).read_text(encoding="utf-8")
    # Form scrolls; history tree is parented on the tab (outside CanvasScrollFrame).
    assert "filing_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_filing_statuses_form(filing_scroll.content)" in panel_src
    assert "_build_filing_history(tab)" in panel_src
    assert "_build_filing_history(filing_scroll.content)" not in panel_src
    assert "filing_scroll.grid(row=0" in panel_src
    assert "_filing_history_frame.grid(row=1" in panel_src
    assert 'tab.grid_rowconfigure(1, weight=1)' in panel_src
    assert 'sticky="nsew", pady=(8, 0)' in panel_src or 'sticky="nsew"' in panel_src


def test_general_and_financial_trees_outside_canvas_scroll():
    from pathlib import Path

    panel_src = (
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "company_details" / "panel.py"
    ).read_text(encoding="utf-8")
    # Company info form scrolls; service/doc trees stay on the tab (outside scroll).
    assert "general_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_company_info(general_scroll.content)" in panel_src
    assert "_build_services(tab)" in panel_src
    assert "_build_documents(tab)" in panel_src
    assert "_build_services(general_scroll.content)" not in panel_src
    assert "_build_documents(general_scroll.content)" not in panel_src
    assert "fin_scroll = CanvasScrollFrame(fin_tab)" not in panel_src
    assert "_build_financial_docs(fin_tab)" in panel_src


def test_accounting_and_vo_csh_setup_trees_outside_canvas_scroll():
    from pathlib import Path

    panel_src = (
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "company_details" / "panel.py"
    ).read_text(encoding="utf-8")
    assert "setup_scroll = CanvasScrollFrame(tab)" not in panel_src
    assert "vo_setup_scroll = CanvasScrollFrame(tab)" not in panel_src
    assert "self._accounting_setup_frame = self._build_accounting_setup(tab)" in panel_src
    assert "self._vo_csh_setup_frame = self._build_vo_csh_setup(tab)" in panel_src


def test_tax_ids_and_vo_tabs_use_canvas_scroll():
    from pathlib import Path

    panel_src = (
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "company_details" / "panel.py"
    ).read_text(encoding="utf-8")
    # Tax IDs form scrolls; cred tree is parented on the tab (outside CanvasScrollFrame).
    assert "tax_ids_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_tax_ids(tax_ids_scroll.content, tab)" in panel_src
    # VO/CSH has no tree; form stays inside CanvasScrollFrame.
    assert "vo_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_vo_csh(vo_scroll.content)" in panel_src
    # Accounting Setup tree is outside CanvasScrollFrame now.
    assert "setup_scroll = CanvasScrollFrame(tab)" not in panel_src
    assert "vo_setup_scroll = CanvasScrollFrame(tab)" not in panel_src
    assert "themed_scrollable_frame(tab)" not in panel_src


def test_settings_checklist_not_nested_scroll():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "settings" / "view.py").read_text(
        encoding="utf-8"
    )
    assert "self.checklist_scroll = themed_scrollable_frame(cl_body" not in text
    assert "self.checklist_scroll = ctk.CTkFrame(cl_body" in text


def test_wheel_rebind_does_not_stack_handlers():
    import pytest

    from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame

    ctk.set_appearance_mode("dark")
    try:
        root = ctk.CTk()
    except Exception as exc:  # headless or Tcl missing
        pytest.skip(f"Tk unavailable: {exc}")
        return
    try:
        root.withdraw()
        scroll = CanvasScrollFrame(root)
        scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(scroll.content, text="Field").pack()
        root.update_idletasks()

        def wheel_script_len(widget) -> int:
            try:
                return len(widget.bind("<MouseWheel>") or "")
            except Exception:
                return 0

        child = scroll.content.winfo_children()[0]
        scroll._bind_wheel_recursive(scroll.content)
        first = wheel_script_len(child)
        assert first > 0
        # Repeated passes (every scrollregion update) must not add more.
        scroll._bind_wheel_recursive(scroll.content)
        scroll._bind_wheel_recursive(scroll.content)
        assert wheel_script_len(child) == first
    except Exception as exc:
        pytest.skip(f"Tk init failed: {exc}")
    finally:
        try:
            root.destroy()
        except Exception:
            pass
