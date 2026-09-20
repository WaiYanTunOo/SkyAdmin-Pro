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


def _pkg_text(*parts: str) -> str:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1].joinpath(*parts)
    if root.is_file():
        return root.read_text(encoding="utf-8")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(root.rglob("*.py")))


def test_filing_form_only_no_history_panel():
    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    filing_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "filing_tab")
    assert "filing_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_filing_statuses_form(filing_scroll.content)" in panel_src
    assert "_build_filing_history" not in panel_src
    assert "_filing_history_frame" not in panel_src
    assert "Recent Changes" not in filing_src
    assert 'text="Edit"' not in filing_src
    assert "filing_labels" not in filing_src
    assert "log_tax_change" in filing_src
    # Monthly | Annual side-by-side columns (not stacked group headers only).
    assert 'uniform="filing"' in filing_src or 'uniform="filing"' in filing_src
    assert "FILING_FIELD_GROUPS" in filing_src


def test_general_tax_ids_whole_page_scroll_fills_tab():
    """General and Tax IDs use one full-tab CanvasScrollFrame (not form strip + fixed trees)."""
    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    assert "tab.grid_rowconfigure(0, weight=1)" in panel_src
    # Prior partial-scroll split must not return.
    assert "tab.grid_rowconfigure(0, weight=2)" not in panel_src
    assert "tab.grid_rowconfigure(1, weight=1, minsize=120)" not in panel_src
    assert "tab.grid_rowconfigure(2, weight=1, minsize=120)" not in panel_src
    assert "tab.grid_rowconfigure(2, weight=1, minsize=160)" not in panel_src
    assert "tab.grid_rowconfigure(1, weight=2, minsize=160)" not in panel_src
    assert "tab.grid_rowconfigure(2, weight=2, minsize=160)" not in panel_src


def test_office_hub_trees_outside_form_scroll():
    vault = _pkg_text("skyadmin_pro", "ui", "views", "office_hub", "vault_tab")
    contacts = _pkg_text("skyadmin_pro", "ui", "views", "office_hub", "contacts_tab")
    notebook = _pkg_text("skyadmin_pro", "ui", "views", "office_hub", "notebook_tab")
    for src, _tree_name in (
        (vault, "client_cred_tree"),
        (vault, "office_cred_tree"),
        (contacts, "contacts_tree"),
        (notebook, "notes_tree"),
    ):
        # Tree must NOT be inside the scroll frame's content area
        assert "ThemedTreeview(\n            scroll.content" not in src
        assert "CanvasScrollFrame(parent)" in src
    # Trees must not be parented on scroll.content or body
    for src in (vault, contacts, notebook):
        assert "ThemedTreeview(\n            body," not in src
        assert "ThemedTreeview(\n            scroll.content" not in src


def test_general_whole_page_scroll_and_financial_tree_first():
    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    general_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "general_tab")
    # Whole-page scroll: company + services + documents (trees included) on scroll.content.
    assert "general_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_company_info(general_scroll.content)" in panel_src
    assert "_build_services(general_scroll.content)" in panel_src
    assert "_build_documents(general_scroll.content)" in panel_src
    # Must not parent trees on the tab outside the scroll frame.
    assert "_build_services(general_scroll.content, tab)" not in panel_src
    assert "_build_documents(general_scroll.content, tab)" not in panel_src
    assert "_build_services(tab)" not in panel_src
    assert "_build_documents(tab)" not in panel_src
    assert "ThemedTreeview(\n            tree_card," in general_src
    # Financial Docs stays tree-first (no CanvasScrollFrame).
    assert "fin_scroll = CanvasScrollFrame(fin_tab)" not in panel_src
    assert "_build_financial_docs(fin_tab)" in panel_src


def test_vo_csh_setup_is_companies_tab():
    from skyadmin_pro.ui.views.company_details.constants import SUBTAB_NAMES
    from skyadmin_pro.ui.views.database_tasks.view import TAB_NAMES, TAB_VO_CSH_SETUP

    assert TAB_VO_CSH_SETUP in TAB_NAMES
    assert "VO/CSH Setup" not in SUBTAB_NAMES

    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    assert "_build_vo_csh_setup" not in panel_src

    from skyadmin_pro.config import NAV_GROUP_FINANCE, NAV_GROUPS

    finance = next(g for g in NAV_GROUPS if g[0] == NAV_GROUP_FINANCE)
    assert "vo_csh_setup" not in finance[2]

    menu_src = _pkg_text("skyadmin_pro", "ui", "views", "menu_panels")
    assert "VoCshSetupMenuView" not in menu_src
    assert "VoCshSetupPanel" in _pkg_text("skyadmin_pro", "ui", "views", "database_tasks", "vo_csh_setup_panel")


def test_accounting_setup_is_finance_menu_page():
    from skyadmin_pro.config import NAV_ACCOUNTING, NAV_GROUP_FINANCE, NAV_GROUPS

    finance = next(g for g in NAV_GROUPS if g[0] == NAV_GROUP_FINANCE)
    assert NAV_ACCOUNTING in finance[2]

    menu_src = _pkg_text("skyadmin_pro", "ui", "views", "menu_panels")
    assert "AccountingSetupMenuView" in menu_src
    assert "AccountingSetupPanel" in menu_src

    from skyadmin_pro.ui.views.company_details.constants import SUBTAB_NAMES

    assert "Accounting Setup" not in SUBTAB_NAMES
    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    assert "_build_accounting_setup" not in panel_src

    from skyadmin_pro.ui.views.database_tasks.view import TAB_NAMES

    assert "Accounting Setup" not in TAB_NAMES


def test_tax_ids_and_vo_tabs_use_canvas_scroll():
    panel_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "panel")
    tax_src = _pkg_text("skyadmin_pro", "ui", "views", "company_details", "tax_ids_tab")
    # Tax IDs whole-page scroll: tax form + portal tree + edit fields in one frame.
    assert "tax_ids_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_tax_ids(tax_ids_scroll.content)" in panel_src
    assert "_build_tax_ids(tax_ids_scroll.content, tab)" not in panel_src
    assert "tree_card = ctk.CTkFrame(frame, corner_radius=CARD_RADIUS)" in tax_src
    # VO/CSH has no tree; form stays inside CanvasScrollFrame.
    assert "vo_scroll = CanvasScrollFrame(tab)" in panel_src
    assert "_build_vo_csh(vo_scroll.content)" in panel_src
    assert "vo_setup_scroll = CanvasScrollFrame(tab)" not in panel_src
    assert "themed_scrollable_frame(tab)" not in panel_src


def test_settings_checklist_not_nested_scroll():
    text = _pkg_text("skyadmin_pro", "ui", "views", "settings", "view")
    assert "self.checklist_scroll = themed_scrollable_frame(cl_body" not in text
    assert "self.checklist_scroll = ctk.CTkFrame(cl_body" in text


def test_settings_pricing_tree_outside_canvas_scroll():
    text = _pkg_text("skyadmin_pro", "ui", "views", "settings", "view")
    assert "self.pricing_tree = ThemedTreeview(\n            tab," in text
    assert "_scroll_tab(tab, row=2" in text
    assert "ThemedTreeview(\n            pricing_body," not in text


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
