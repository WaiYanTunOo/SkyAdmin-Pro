# SkyAdmin Pro — Procedures, Playbook & Engineering Invariants

> **Purpose**: Standard operating procedures, proven engineering invariants, anti-patterns to avoid, and exact verification commands to ensure zero regressions, eliminate repeat mistakes, and save tokens and compute cycles.

---

## 1. Core Architecture & Scope Boundaries

- **Desktop UI**: Python 3.12+ / CustomTkinter.
- **Database**: SQLite with SQLCipher (`skyadmin_pro/db/`).
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
