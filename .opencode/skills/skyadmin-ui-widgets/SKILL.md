---
name: skyadmin-ui-widgets
description: Use when fixing DatePickerField clipping, form fields, calendar popups, or any shared widget in widgets.py. Handles transient Toplevel popups and form widget consistency.
---

# SkyAdmin Pro — UI Widgets Skill

## Key Files

- `skyadmin_pro/ui/widgets.py` — Shared widgets including `DatePickerField`
- `skyadmin_pro/ui/views/database_tasks/` — Tab view with form widgets
- `skyadmin_pro/ui/views/company_details/` — Company Details sub-tabs with forms
- `skyadmin_pro/ui/views/settings/` — Settings forms
- `tests/test_date_picker.py` — DatePickerField tests
- `tests/test_form_widgets.py` — Form widget tests

## Known Issues

1. **DatePickerField clipping** — Date picker gets clipped inside scroll frames. Fix: use transient `Toplevel` popup that positions itself near the field but outside the scroll frame.
2. **Transient Toplevel** — Calendar popup should be a `Toplevel` with `transient()` and `grab_set()` for proper modal behavior.
3. **Flip-up near screen bottom** — When field is near bottom of screen, calendar should flip upward.
4. **Form widget consistency** — All form fields should follow the same styling and behavior patterns.

## Architecture

### DatePickerField

The `DatePickerField` is a compound widget that:
- Shows a button with the selected date
- On click, creates a `Toplevel` calendar popup
- The popup uses `transient()` to attach to the parent window
- Calendar grid allows month/year navigation
- Returns selected date via callback

### Scroll Frame Interaction

When a `DatePickerField` is placed inside a `CTkScrollableFrame`, the calendar popup must:
- Be created as a child of the root window (not the scroll frame)
- Use `winfo_rootx()`/`winfo_rooty()` to position relative to screen
- Handle screen-edge cases (flip up if near bottom, flip left if near right)

## Conventions

- All shared widgets go in `widgets.py`
- Use CustomTkinter styling from `theme.py`
- Test widget creation and interaction in `tests/`
- Follow existing pattern: widget class + callback mechanism
- Use `after()` for delayed operations to avoid UI blocking
