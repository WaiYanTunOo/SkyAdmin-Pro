# UI Widgets — Feature Detail

## Purpose
Shared CustomTkinter components: DatePickerField, FormField, SectionCard, FeedbackLabel, ThemedTreeview, CanvasScrollFrame, theme tokens, high-DPI scaling.

## Code Files

| Layer | File | Key symbols |
|-------|------|-------------|
| Widgets | `skyadmin_pro/ui/widgets.py` | `DatePickerField`, `FormField`, `SectionCard`, `FeedbackLabel`, `MonthStatusPanel` |
| Treeview | `skyadmin_pro/ui/treeview.py` | `ThemedTreeview`, virtual scroll at 60 rows |
| Canvas scroll | `skyadmin_pro/ui/canvas_scroll.py` | `CanvasScrollFrame` |
| Theme | `skyadmin_pro/ui/theme.py` | All color/font constants, `CONTENT_PAD`, `CARD_RADIUS` |
| High-DPI | `skyadmin_pro/ui/display.py` | `apply_high_dpi_scaling()` |
| Debounce | `skyadmin_pro/ui/debounce.py` | 300ms shared debounce utility |
| DnD | `skyadmin_pro/ui/dnd.py` | File drag-and-drop support |
| Combobox | `skyadmin_pro/ui/combo_utils.py` | `fill_combo()` helper |
| Async UI | `skyadmin_pro/ui/async_ui.py` | Thread-safe UI updates |

## Architecture Decisions
- **DatePickerField**: transient `Toplevel` at screen coordinates (never clipped inside scrollers). Class-level open tracking. Grab without `after(80)`. No `-topmost` flicker.
- **ThemedTreeview**: virtual scroll at 60 rows; incremental update at 20 rows.
- **CanvasScrollFrame**: smoother than CTkScrollableFrame; treeview outside scroll frame (U1.0a landed).
- **Theme tokens**: single source of truth in `theme.py`; `apply_form_theme()` called on view switch.
- **High-DPI**: bootstrap in `main.py` + `display.py` (Phase 9C landed).

## Tests

| File | Covers |
|------|--------|
| `tests/test_date_picker.py` | Multi-instance dismiss, grab, transient |
| `tests/test_canvas_scroll.py` | Scroll behavior, wheel handling |
| `tests/test_treeview_empty_message.py` | Empty state display |
| `tests/test_treeview_incremental.py` | Incremental update at 20 rows |
| `tests/test_treeview_theme_cache.py` | Theme caching |
| `tests/test_form_widgets.py` | FormField, SectionCard |
| `tests/test_display_scaling.py` | High-DPI scaling |

## Known Fix Locations

| Issue | File:Line | Priority |
|-------|-----------|----------|
| Root-level `<Button-1>` and `<Escape>` binds conflict with multiple DatePicker instances | `widgets.py:635–638` | P0 |
| `_try_grab` after 80ms is fragile | `widgets.py:803–814` | ✅ Fixed |
| `-topmost` flicker (set then cleared after 200ms) | `widgets.py:798–799` | ✅ Fixed — transient instead |
| `_bind_wheel_recursive()` O(n) widget walk | `canvas_scroll.py:60–72` | P1 |
| Global `ttk.Style` mutation on every treeview | `treeview.py:77–195` | P2 |
| `apply_form_theme()` recursive walk on view switch | `widgets.py:142–165` | P1 |
| 100+ bare `except Exception: pass` across UI | `widgets.py`, `display.py`, `canvas_scroll.py`, `treeview.py`, `main_window.py` | P0 |
