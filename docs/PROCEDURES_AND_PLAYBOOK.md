# SkyAdmin Pro — Procedures, Playbook & Engineering Invariants

> **Purpose**: Standard operating procedures, proven engineering invariants, anti-patterns to avoid, and exact verification commands to ensure zero regressions, eliminate repeat mistakes, and save tokens and compute cycles.

---

## 1. Core Architecture & Scope Boundaries

- **Desktop UI**: Python 3.12+ / CustomTkinter.
- **Database**: SQLite (`skyadmin_pro/db/`) — DB file is not SQLCipher-encrypted at rest; sensitive columns use field-level encryption via `secret_fields` / vault helpers.
- **Edge Backend**: TypeScript Cloudflare Worker + D1 (`skyadmin-worker/`).
- **Packaging**: PyInstaller on Windows.
- **Scope Invariant**: **STRICTLY NO FRAMEWORK REWRITES** (no Kotlin/Swift mobile native, no Qt/Electron rewrite). All UI issues are CustomTkinter layout or event-dispatch challenges.

---

## 2. Company Details & Database/Tasks Invariants

### 2.1 Sub-tab Layout & Scroll Policy
| Sub-tab | Layout Strategy | Implementation Details |
|---|---|---|
| **General** | Card Overview (`CanvasScrollFrame`) | Company Info + Services + Documents stacked inside `CanvasScrollFrame`. `ThemedTreeview` delegates mousewheel upward when content fits or reaches boundary. |
| **Accounting** | Tree-First | Pure `ThemedTreeview` directly on tab. No `CanvasScrollFrame` to avoid nested scroll. |
| **Tax IDs** | Split-Pane | Form inside `CanvasScrollFrame`; Client credentials tree fixed outside the canvas in bottom pane. |
| **Filing** | Split-Pane | Filing status forms inside `CanvasScrollFrame`; Filing history tree fixed outside canvas with expandable height band. |
| **VO & CSH** | Form Scroll | Form inside `CanvasScrollFrame`. |
| **Financial Docs** | Tree-First | Pure `ThemedTreeview` directly on tab. No `CanvasScrollFrame`. |

### 2.2 Treeview Anti-Patterns & Safety Rules
1. **Empty State Placeholder (`__empty__`)**:
   - `ThemedTreeview.set_rows()` inserts a placeholder row with `iid = "__empty__"` when empty.
   - **Rule**: Never call `int(iid)` without validation.
   - **Protection**: `ThemedTreeview.selected_iid()` returns `None` if the placeholder is selected. `selected_iids()` filters out `"__empty__"`.
   - **Guards**: Always guard action buttons and handlers:
     ```python
     if not iid or iid == "__empty__" or not str(iid).isdigit():
         return
     ```
2. **Keyboard Activation `<Return>` / `<Space>`**:
   - In `ThemedTreeview._on_tree_activate()`:
     - **Wrong**: `self._on_double_click(event)` $\rightarrow$ passes `tkinter.Event`, causing `TypeError: int() argument must be a string...`.
     - **Correct**: `self._on_double_click(self.selected_iid())` if `iid is not None`.
3. **Mousewheel Trapping**:
   - In `ThemedTreeview`:
     - If the tree content fits completely without scroll (`yview() == (0.0, 1.0)`) or is at the boundary in the scroll direction, `_scroll_vertical_with_parent_fallback()` automatically delegates to `parent._canvas.yview_scroll(delta, "units")`.
     - Never unconditionally return `"break"` when the tree has nothing to scroll.

### 2.3 Form & State Management Rules
1. **Cancel Edit Controls**:
   - When editing an existing service or document (`_editing_service_id` or `_editing_doc_id` is set), the form must have an explicit **Cancel** button.
   - Clicking Cancel calls `_cancel_service_edit()` or `_cancel_document_edit()` to restore the form to `"New ... record"` mode and clear IDs.
2. **Automatic State Resets**:
   - Switching sub-tabs (`_on_subtab_changed`) or switching companies (`_on_company`) **must** call `_cancel_service_edit()` and `_cancel_document_edit()`. Stale IDs must never persist across view switches.
3. **Smart Ctrl+S Routing**:
   - When pressing `Ctrl+S` on the General tab:
     - If `_editing_service_id` is set $\rightarrow$ saves service.
     - If `_editing_doc_id` is set $\rightarrow$ saves document.
     - Otherwise $\rightarrow$ saves company info.
4. **Database Nullable Field Updates**:
   - When clearing a date or optional field, pass `clear=True` to `db.update_document(...)` or similar DB methods:
     ```python
     self.app.db.update_document(doc_id, expiry_date=expiry, clear=True)
     ```
     *(Without `clear=True`, SQL `COALESCE(?, expiry_date)` will silently retain the old value).*
5. **Numeric Formatting**:
   - `format_thousands(val)` must accept `int`, `float`, and `str`. Do not assume `val` has `.strip()`.

### 2.4 Dashboard & Filters Invariants
1. **Expired Item Filtering**:
   - The dashboard explicitly filters out already-expired regular client services and tasks (`days_until < 0`) from the **Next Actions** and **Expiry Alerts** priority trees so users are not cluttered with dead items.
   - **Exception**: Supplier services (e.g. Attori) are **excluded** from this rule. Expired supplier obligations must continue to display on the dashboard until they are explicitly marked as paid or renewed.
   - **Implementation**: Handled natively in Python inside `dashboard_snapshot` via `exclude_expired=True` on `list_expiring_documents()` and `list_tasks()`, combined with an explicit connection-pinned SQL query in `dashboard_counts()` to ensure counts accurately reflect the filtered state without breaking connection tracking.

### 2.5 CompanyDetailsPanel Mixin MRO
- **Definition**: `CompanyDetailsPanel` (in `skyadmin_pro/ui/views/company_details/panel/__init__.py`) composes 19 panel chunk mixins (`CompanyDetailsPanelMixin0`…`Mixin18`, each under 100 lines in `panel/chunk_*.py`) followed by the 5 sub-tab mixins (`GeneralTabMixin`, `TaxIdsTabMixin`, `FilingTabMixin`, `VoCshTabMixin`, `FinancialDocsTabMixin`) and then `ctk.CTkFrame`.
- **Resolution rule**: Python C3 MRO searches bases left→right. Base order in the class statement sets priority: **panel chunk mixins first (highest), then sub-tab mixins, then `CTkFrame`**. A method defined by an earlier base shadows the same method in later bases.
- **Panel-level vs sub-tab dispatch**:
  - Refresh dispatch (`refresh`, `refresh_active_subtab`, `_refresh_after_mutation`) lives on the **panel** chunk mixins (`panel/chunk_5.py`), NOT on sub-tab mixins — sub-tab mixins only implement their own `_refresh_<tab>_subtab` on panel mixins. Never move refresh dispatch into a sub-tab mixin.
  - Editing state (`_editing_service_id`, `_editing_doc_id`), Ctrl+S routing (`_on_shortcut_save` in `chunk_2.py`), sub-tab/company change resets, and cancel-edit live on panel chunk mixins so they always win over sub-tab scope.
- **Cancel-edit completeness**: `_cancel_service_edit()` (`chunk_10.py`) and `_cancel_document_edit()` (`chunk_11.py`) must clear the editing ID **and** reset every form widget to its "New record" default, including the type dropdowns (`service_type` → first service type; `doc_type` → `IMPORTANT_DOC_TYPES[0]`). A stale type dropdown is a stale dirty flag.

---

## 3. Fast Verification & Testing Playbook

### 3.1 Test Command Cheat Sheet

| Task | Command | Expected Duration | Notes |
|---|---|---|---|
| **General Tab Complete** | `python -m pytest tests/test_general_tab_complete.py -v` | ~1.8s | 22 tests covering forms, dates, cancel, shortcuts, and wheel |
| **Treeview Empty State** | `python -m pytest tests/test_treeview_empty_message.py -v` | ~0.8s | Placeholder selection & activate signature |
| **UI Smoke & Scroll** | `python -m pytest tests/test_ui_smoke.py tests/test_canvas_scroll.py -v` | ~2.5s | Layout & single-scroll validation |
| **Full Desktop Suite** | `python -m pytest tests/` | ~8 mins | 513 tests. Run as background task |
| **Worker Vitest Suite** | `cd skyadmin-worker; npm test; cd ..` | ~5.0s | 23 files, 192 tests |
| **Worker Typecheck** | `cd skyadmin-worker; npm run typecheck; cd ..` | ~3.0s | `tsc --noEmit` must pass with 0 errors |
| **Release Check Gate** | `python scripts/release_check.py --skip-installer` | ~3 mins | Final pre-ship gate |

### 3.2 Fixtures & Test Writing Caveats
- In tests for `CompanyDetailsPanel`: The pytest fixture name is **`fake_panel`** (NOT `mock_panel`).
- For Tkinter tests requiring a root window: Wrap in `try: root = ctk.CTk(); root.withdraw() ... finally: root.destroy()`. Guard with `except Exception as exc: pytest.skip(f"Tk not available: {exc}")`.

---

## 4. Subagent & Token Conservation Protocol

1. **Avoid Looping on `manage_task`**:
   - When a command is sent to background (e.g. `task-724`), **never** poll `manage_task(Action='status')` in a loop.
   - The environment delivers a high-priority `<SYSTEM_MESSAGE>` immediately upon task conclusion. Stop tool calling and wait.
2. **Targeted Research over Large Subagent Trees**:
   - For specific method lookups, use `grep_search` with `MatchPerLine: true`.
   - When delegating to subagents, assign `TypeName: "research"` for read-only audits.
3. **Sequence File Edits**:
   - Avoid editing the same file across multiple subagents concurrently.
   - Follow the established sequence: `company-details` and `ui-widgets` touch `widgets.py` sequentially.
4. **Git UTF-8 Cleanliness**:
   - `.gitignore` and all text files must be clean UTF-8 without BOM.

## Code Splitting Rule (Wave D7)
- **Strict 100-Line Limit:** ALL code files must be strictly under 100 lines. If a file (even a split mixin) exceeds 100 lines, it must be recursively subdivided into smaller modules (e.g. crud_reads.py, crud_writes.py) until every single file is wc -l < 100.
- **No Exceptions:** This applies to db/, ui/views/, services/, and skyadmin-worker/src/routes/.
