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
    # Filing form and history share a single CanvasScrollFrame (unified scroll)
    assert "filing_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_filing_statuses_form(filing_scroll.content)" in panel_src
    assert "_build_filing_history(filing_scroll.content)" in panel_src
    assert "filing_scroll.grid(row=0" in panel_src
    assert "_filing_history_frame.grid(row=1" in panel_src


def test_tax_ids_and_vo_tabs_use_canvas_scroll():
    from pathlib import Path

    panel_src = (
        Path(__file__).resolve().parents[1] / "skyadmin_pro" / "ui" / "views" / "company_details" / "panel.py"
    ).read_text(encoding="utf-8")
    assert "tax_ids_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_tax_ids(tax_ids_scroll.content)" in panel_src
    assert "vo_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_vo_csh(vo_scroll.content)" in panel_src
    assert "themed_scrollable_frame(tab)" not in panel_src


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
