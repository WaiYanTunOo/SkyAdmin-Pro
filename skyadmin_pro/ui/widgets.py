"""Reusable CustomTkinter widgets for Document Hub and shared forms."""

from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import Any

import customtkinter as ctk

from skyadmin_pro.ui.dnd import enable_drop
from skyadmin_pro.ui.theme import (
    CARD_RADIUS,
    CARD_TITLE_SIZE,
    ENTRY_BORDER,
    ENTRY_FG,
    ENTRY_PLACEHOLDER,
    ENTRY_TEXT,
    FEEDBACK_ERROR,
    FEEDBACK_INFO,
    FEEDBACK_SUCCESS,
    FORM_FIELD_HEIGHT,
    FORM_LABEL_COLOR,
    FORM_LABEL_FONT_SIZE,
    FORM_LABEL_GAP,
    SURFACE_BG,
    TEXT_MUTED,
    TEXT_SUBTLE,
    TEXTBOX_BORDER,
    TEXTBOX_FG,
    TEXTBOX_TEXT,
    WRAP_CARD,
    card_style_kwargs,
    scrollable_style_kwargs,
    tabview_style_kwargs,
)
from skyadmin_pro.ui.treeview import ThemedTreeview

_INPUT_WIDGET_TYPES = (
    ctk.CTkEntry,
    ctk.CTkComboBox,
    ctk.CTkTextbox,
    ctk.CTkOptionMenu,
)


def entry_style_kwargs(**extra: Any) -> dict[str, Any]:
    """Shared CTkEntry styling."""
    return {
        "height": FORM_FIELD_HEIGHT,
        "fg_color": ENTRY_FG,
        "border_color": ENTRY_BORDER,
        "text_color": ENTRY_TEXT,
        "placeholder_text_color": ENTRY_PLACEHOLDER,
        "border_width": 1,
        **extra,
    }


def combo_style_kwargs(**extra: Any) -> dict[str, Any]:
    """CTkComboBox — no placeholder_text_color."""
    base = entry_style_kwargs()
    base.pop("placeholder_text_color", None)
    base.update(extra)
    return base


def option_menu_style_kwargs(**extra: Any) -> dict[str, Any]:
    """CTkOptionMenu — limited supported kwargs."""
    return {
        "height": FORM_FIELD_HEIGHT,
        "fg_color": ENTRY_FG,
        "text_color": ENTRY_TEXT,
        **extra,
    }


def textbox_style_kwargs(**extra: Any) -> dict[str, Any]:
    """Shared CTkTextbox styling."""
    return {
        "fg_color": TEXTBOX_FG,
        "border_color": TEXTBOX_BORDER,
        "text_color": TEXTBOX_TEXT,
        "border_width": 1,
        **extra,
    }


def themed_tabview(master, **kwargs: Any) -> ctk.CTkTabview:
    """Tabview with consistent surface colors in light and dark mode."""
    style = tabview_style_kwargs()
    style.update(kwargs)
    tabview = ctk.CTkTabview(master, **style)
    _style_tabview_tabs(tabview)
    return tabview


def themed_scrollable_frame(master, **kwargs: Any) -> ctk.CTkScrollableFrame:
    """Scrollable frame with readable background (not transparent/white)."""
    style = scrollable_style_kwargs()
    if kwargs.get("fg_color") == "transparent":
        kwargs.pop("fg_color")
    style.update(kwargs)
    return ctk.CTkScrollableFrame(master, **style)


def _style_tabview_tabs(tabview: ctk.CTkTabview) -> None:
    for name in getattr(tabview, "_name_list", []):
        try:
            tabview.tab(name).configure(fg_color=SURFACE_BG)
        except Exception:
            pass


def bind_wrap_label(label: ctk.CTkLabel, parent: ctk.Misc, *, pad: int = 32) -> None:
    """Keep label wraplength in sync with parent width."""

    def _resize(event=None) -> None:
        width = event.width if event is not None else parent.winfo_width()
        if width > 1:
            label.configure(wraplength=max(120, width - pad))

    parent.bind("<Configure>", _resize, add="+")
    parent.after(50, _resize)


def _apply_input_theme(widget: ctk.CTkBaseClass) -> None:
    if isinstance(widget, ctk.CTkTextbox):
        widget.configure(**textbox_style_kwargs())
    elif isinstance(widget, ctk.CTkComboBox):
        widget.configure(**combo_style_kwargs())
    elif isinstance(widget, ctk.CTkOptionMenu):
        widget.configure(**option_menu_style_kwargs())
    elif isinstance(widget, ctk.CTkEntry):
        widget.configure(**entry_style_kwargs())


_LAST_THEME_MODE: str | None = None


def apply_form_theme(root: ctk.Misc) -> None:
    """Re-apply input and table styling after appearance mode changes."""
    from skyadmin_pro.ui.canvas_scroll import CanvasScrollFrame

    if isinstance(root, ThemedTreeview):
        root.apply_theme()
    elif isinstance(root, ctk.CTkTabview):
        root.configure(**tabview_style_kwargs())
        _style_tabview_tabs(root)
    elif isinstance(root, ctk.CTkScrollableFrame):
        fg = root.cget("fg_color")
        if fg in ("transparent", "Transparent", None, ""):
            root.configure(**scrollable_style_kwargs())
    elif isinstance(root, CanvasScrollFrame):
        root.refresh_theme()
    elif isinstance(root, _INPUT_WIDGET_TYPES):
        _apply_input_theme(root)

    try:
        children = root.winfo_children()
    except Exception:
        return
    for child in children:
        apply_form_theme(child)


def should_apply_theme() -> bool:
    """Return True if the appearance mode changed since last call. Skips redundant full walks."""
    global _LAST_THEME_MODE
    current = ctk.get_appearance_mode()
    if current == _LAST_THEME_MODE:
        return False
    _LAST_THEME_MODE = current
    return True


class SectionCard(ctk.CTkFrame):
    """Titled form section with optional subtitle."""

    def __init__(
        self,
        master,
        *,
        title: str,
        subtitle: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=CARD_RADIUS, **card_style_kwargs(), **kwargs)
        self.grid_columnconfigure(0, weight=1)
        row = 0
        ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=16, pady=(14, 4 if subtitle else 8))
        row += 1
        if subtitle:
            sub = ctk.CTkLabel(
                self,
                text=subtitle,
                anchor="w",
                text_color=TEXT_MUTED,
                justify="left",
            )
            sub.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 8))
            bind_wrap_label(sub, self, pad=40)
            row += 1
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=row, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.body.grid_columnconfigure(0, weight=1)


class FormField(ctk.CTkFrame):
    """Label above a single input — consistent spacing and contrast."""

    def __init__(
        self,
        master,
        *,
        label: str,
        kind: str = "entry",
        textvariable: ctk.StringVar | None = None,
        values: list[str] | None = None,
        height: int | None = None,
        placeholder_text: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.kind = kind

        ctk.CTkLabel(
            self,
            text=label,
            anchor="w",
            font=ctk.CTkFont(size=FORM_LABEL_FONT_SIZE),
            text_color=FORM_LABEL_COLOR,
        ).grid(row=0, column=0, sticky="w")

        widget_kwargs: dict[str, Any] = {}
        if kind == "entry":
            widget_kwargs = entry_style_kwargs(placeholder_text=placeholder_text, **kwargs)
            if textvariable is not None:
                widget_kwargs["textvariable"] = textvariable
            self.widget: ctk.CTkBaseClass = ctk.CTkEntry(self, **widget_kwargs)
        elif kind == "combo":
            widget_kwargs = combo_style_kwargs(**kwargs)
            self.widget = ctk.CTkComboBox(self, values=values or [""], **widget_kwargs)
        elif kind == "option":
            widget_kwargs = option_menu_style_kwargs(**kwargs)
            self.widget = ctk.CTkOptionMenu(self, values=values or [""], **widget_kwargs)
        elif kind == "textbox":
            widget_kwargs = textbox_style_kwargs(height=height or 90, **kwargs)
            self.widget = ctk.CTkTextbox(self, **widget_kwargs)
        elif kind == "date":
            self.var = textvariable if textvariable is not None else ctk.StringVar()
            self.widget = DatePickerField(self, var=self.var)
        else:
            raise ValueError(f"Unknown FormField kind: {kind}")

        self.widget.grid(row=1, column=0, sticky="ew", pady=(FORM_LABEL_GAP, 0))

    def get(self) -> str:
        if self.kind == "date":
            return self.var.get().strip()
        if isinstance(self.widget, ctk.CTkTextbox):
            return self.widget.get("1.0", "end").strip()
        return str(self.widget.get()).strip()

    def set(self, value: str) -> None:
        if self.kind == "date":
            self.var.set(value)
            return
        if isinstance(self.widget, ctk.CTkTextbox):
            self.widget.delete("1.0", "end")
            if value:
                self.widget.insert("1.0", value)
            return
        self.widget.set(value)

    def clear(self) -> None:
        self.set("")

    def bind(self, sequence: str, func: Callable, add: str | bool | None = None) -> None:
        if add is None:
            self.widget.bind(sequence, func)
        else:
            self.widget.bind(sequence, func, add=add)


def labeled_entry(
    master,
    label: str,
    *,
    textvariable: ctk.StringVar | None = None,
    placeholder_text: str = "",
    **kwargs: Any,
) -> FormField:
    return FormField(
        master,
        label=label,
        kind="entry",
        textvariable=textvariable,
        placeholder_text=placeholder_text,
        **kwargs,
    )


def labeled_combo(master, label: str, *, values: list[str] | None = None, **kwargs: Any) -> FormField:
    return FormField(master, label=label, kind="combo", values=values, **kwargs)


def themed_entry(master, **kwargs: Any) -> ctk.CTkEntry:
    return ctk.CTkEntry(master, **entry_style_kwargs(**kwargs))


def themed_combo(master, **kwargs: Any) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(master, **combo_style_kwargs(**kwargs))


def themed_textbox(master, **kwargs: Any) -> ctk.CTkTextbox:
    return ctk.CTkTextbox(master, **textbox_style_kwargs(**kwargs))


MONTH_STATUS_OPEN = "open"
MONTH_STATUS_IN_PROGRESS = "in_progress"
MONTH_STATUS_CLOSED = "closed"


class LoadingIndicator(ctk.CTkFrame):
    """A simple loading spinner/indicator widget."""

    def __init__(self, master, text: str = "Loading...", **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._text = text
        self._visible = False

        self.grid_columnconfigure(0, weight=1)
        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=TEXT_MUTED,
        )
        self.label.grid(row=0, column=0, pady=20)

    def show(self, text: str | None = None) -> None:
        """Show the loading indicator."""
        if text:
            self.label.configure(text=text)
        self._visible = True
        self.grid()
        self.lift()

    def hide(self) -> None:
        """Hide the loading indicator."""
        self._visible = False
        self.grid_remove()

    @property
    def is_visible(self) -> bool:
        return self._visible


def bind_escape(top) -> None:
    """Let users close any dialog with the Escape key."""
    top.bind("<Escape>", lambda _event: top.destroy())


def make_modal(top) -> None:
    """Standard dialog setup: grab focus (best effort) + Escape to close."""

    def _grab() -> None:
        try:
            top.grab_set()
        except Exception:
            pass

    _grab()
    # If the window wasn't mapped yet, grab fails silently — retry shortly.
    try:
        if not top.grab_current():
            top.after(80, _grab)
    except Exception:
        pass
    bind_escape(top)


_STATUS_LABEL = {
    MONTH_STATUS_OPEN: "Open",
    MONTH_STATUS_IN_PROGRESS: "In progress",
    MONTH_STATUS_CLOSED: "Closed",
}
_STATUS_TAG = {
    MONTH_STATUS_OPEN: "",
    MONTH_STATUS_IN_PROGRESS: "wip",
    MONTH_STATUS_CLOSED: "done",
}
_STATUS_CYCLE = (
    MONTH_STATUS_OPEN,
    MONTH_STATUS_IN_PROGRESS,
    MONTH_STATUS_CLOSED,
    MONTH_STATUS_OPEN,
)


class MonthStatusPanel(ctk.CTkFrame):
    """Per-client monthly tax-close tracker: mark each client-month Open /
    In progress / Closed, with month navigation and a live summary."""

    def __init__(
        self,
        master,
        app,
        *,
        showheight: int = 8,
        title: str = "Client month closes",
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, **kwargs)
        self.app = app
        self._refresh_seq = 0
        today = date.today()
        self._year = today.year
        self._month = today.month
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=CARD_TITLE_SIZE, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.summary = ctk.CTkLabel(header, text="", text_color=TEXT_MUTED, anchor="e")
        self.summary.grid(row=0, column=2, sticky="e", padx=(12, 0))

        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=3, sticky="e", padx=(8, 0))
        self.month_label = ctk.CTkLabel(nav, text="", font=ctk.CTkFont(weight="bold"))
        self.month_label.pack(side="right")
        ctk.CTkButton(nav, text="\u25b6", width=34, command=lambda: self._shift(1)).pack(side="right", padx=(6, 8))
        ctk.CTkButton(nav, text="\u25c0", width=34, command=lambda: self._shift(-1)).pack(side="right")

        self.tree = ThemedTreeview(
            self,
            columns=(
                ("client", "Client", 240),
                ("status", "Status", 130),
                ("updated", "Updated", 150),
            ),
            on_double_click=self._advance,
        )
        self.tree.tree.configure(height=showheight)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 4))

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.status_menu = ctk.CTkSegmentedButton(controls, values=[_STATUS_LABEL[s] for s in _STATUS_CYCLE[:3]])
        self.status_menu.set(_STATUS_LABEL[MONTH_STATUS_OPEN])
        self.status_menu.pack(side="left")
        ctk.CTkButton(controls, text="Apply to selected", width=140, command=self._apply_selected).pack(
            side="left", padx=(10, 0)
        )
        ctk.CTkLabel(
            controls,
            text="Double-click a row to advance its status",
            text_color=TEXT_MUTED,
        ).pack(side="right")

    def _month_key(self) -> str:
        return f"{self._year:04d}-{self._month:02d}"

    def _shift(self, delta: int) -> None:
        total = self._year * 12 + (self._month - 1) + delta
        self._year, self._month = total // 12, total % 12 + 1
        self.refresh()

    def refresh(self) -> None:
        """Non-blocking month grid: snapshot off thread, Treeview on thread."""
        from skyadmin_pro.ui.async_ui import run_background

        month_key = self._month_key()
        try:
            self.month_label.configure(text=f"{calendar.month_name[self._month]} {self._year}")
        except Exception:
            pass
        self.tree.apply_theme()

        self._refresh_seq += 1
        seq = self._refresh_seq
        db = self.app.db

        def work():
            clients = db.list_monthly_tax_clients()
            client_ids = [int(c["id"]) for c in clients]
            return {
                "clients": clients,
                "summary": db.month_close_summary(month_key, client_ids=client_ids),
                "statuses": db.list_client_month_status(month_key),
            }

        def on_success(payload) -> None:
            if seq != self._refresh_seq or not self.winfo_exists():
                return
            summary = payload["summary"]
            try:
                self.summary.configure(
                    text=(f"{summary['closed']}/{summary['clients']} closed · {summary['in_progress']} in progress")
                )
            except Exception:
                pass
            rows, iids, tags = [], [], []
            for client in payload["clients"]:
                client_id = int(client["id"])
                record = payload["statuses"].get(client_id)
                status = record["status"] if record else MONTH_STATUS_OPEN
                updated = (record.get("updated_at") or "")[:16] if record else "—"
                rows.append((client.get("name") or "—", _STATUS_LABEL[status], updated))
                iids.append(str(client_id))
                tag = _STATUS_TAG[status]
                tags.append((tag,) if tag else ())
            self.tree.set_rows(rows, iids=iids, tags=tags)

        run_background(self, work=work, on_success=on_success)

    def _selected_client_id(self) -> int | None:
        iid = self.tree.selected_iid()
        return int(iid) if iid is not None else None

    def _apply_selected(self) -> None:
        client_id = self._selected_client_id()
        if client_id is None:
            self.app.set_status("Select a client row first.")
            return
        label = self.status_menu.get()
        status = next(key for key, value in _STATUS_LABEL.items() if value == label)
        self.app.db.set_client_month_status(client_id, self._month_key(), status)
        self.app.set_status(f"Month close set to '{label}' for this client ({self.month_label.cget('text')}).")
        self.refresh()

    def _advance(self, iid: str | None) -> None:
        if iid is None:
            return
        client_id = int(iid)
        statuses = self.app.db.list_client_month_status(self._month_key())
        record = statuses.get(client_id)
        current = record["status"] if record else MONTH_STATUS_OPEN
        next_status = _STATUS_CYCLE[_STATUS_CYCLE.index(current) + 1]
        self.app.db.set_client_month_status(client_id, self._month_key(), next_status)
        self.app.set_status(f"Status advanced to '{_STATUS_LABEL[next_status]}' for this client.")
        self.refresh()


def _step_month(view: date, delta: int) -> date:
    """Move a first-of-month date by delta months, wrapping year boundaries."""
    total = view.year * 12 + (view.month - 1) + delta
    return date(total // 12, total % 12 + 1, 1)


def calendar_popup_position(
    *,
    anchor_x: int,
    anchor_y: int,
    anchor_w: int,
    anchor_h: int,
    popup_w: int,
    popup_h: int,
    screen_w: int,
    screen_h: int,
    margin: int = 8,
) -> tuple[int, int]:
    """Place a calendar popup below the anchor field, flipping up near the screen bottom."""
    x = anchor_x
    if x + popup_w > screen_w - margin:
        x = max(margin, screen_w - popup_w - margin)
    y = anchor_y + anchor_h
    if y + popup_h > screen_h - margin:
        y = max(margin, anchor_y - popup_h)
    return x, y


class DatePickerField(ctk.CTkFrame):
    """Text entry plus a calendar popup; the StringVar always holds ISO YYYY-MM-DD."""

    def __init__(self, master, *, var: ctk.StringVar | None = None, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.var = var if var is not None else ctk.StringVar()
        self._calendar_top: ctk.CTkToplevel | None = None
        self._dismiss_bind_id: str | None = None
        self._escape_bind_id: str | None = None
        self._entry = ctk.CTkEntry(self, textvariable=self.var, placeholder_text="YYYY-MM-DD", **entry_style_kwargs())
        self._entry.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            self,
            text="Calendar",
            width=96,
            command=self._open_calendar,
        ).grid(row=0, column=1, padx=(8, 0))
        # Cleanup if parent destroyed while popup open
        self.bind("<Destroy>", self._on_destroy)
        # Validate manual entry on focus out
        self._entry.bind("<FocusOut>", lambda _e: self._validate_entry())

    def _on_destroy(self, event) -> None:
        if event.widget is self:
            self._close_calendar()

    def _validate_entry(self) -> None:
        value = self.var.get().strip()
        if not value:
            self._entry.configure(border_color=ENTRY_BORDER)
            return
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                datetime.strptime(value, fmt).date()
                self._entry.configure(border_color=ENTRY_BORDER)
                return
            except ValueError:
                continue
        self._entry.configure(border_color=FEEDBACK_ERROR)

    def _initial_date(self) -> date:
        value = self.var.get().strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return date.today()

    def _close_calendar(self) -> None:
        top = self._calendar_top
        root = self.winfo_toplevel()
        if self._dismiss_bind_id is not None:
            try:
                root.unbind("<Button-1>", self._dismiss_bind_id)
            except Exception:
                pass
            self._dismiss_bind_id = None
        if self._escape_bind_id is not None:
            try:
                root.unbind("<Escape>", self._escape_bind_id)
            except Exception:
                pass
            self._escape_bind_id = None
        if top is not None and top.winfo_exists():
            try:
                top.grab_release()
            except Exception:
                pass
            top.destroy()
        self._calendar_top = None

    def _bind_dismiss_on_click_outside(self, top: ctk.CTkToplevel) -> None:
        root = self.winfo_toplevel()
        # Close any other open DatePickerField calendar on the same root
        for child in root.winfo_children():
            try:
                if hasattr(child, "_calendar_top") and child._calendar_top is not None and child is not self:
                    child._close_calendar()
            except Exception:
                pass

        def _contains(widget, root_x: int, root_y: int) -> bool:
            try:
                if not widget.winfo_exists():
                    return False
                x = widget.winfo_rootx()
                y = widget.winfo_rooty()
                return x <= root_x <= x + widget.winfo_width() and y <= root_y <= y + widget.winfo_height()
            except Exception:
                return False

        def _on_click(event) -> None:
            if not top.winfo_exists():
                return
            if _contains(top, event.x_root, event.y_root) or _contains(self, event.x_root, event.y_root):
                return
            self._close_calendar()

        self._dismiss_bind_id = root.bind("<Button-1>", _on_click, add="+")
        # Also dismiss on Escape from root (unbound in _close_calendar to avoid buildup)
        if self._escape_bind_id is not None:
            try:
                root.unbind("<Escape>", self._escape_bind_id)
            except Exception:
                pass
        top.bind("<Escape>", lambda _e: self._close_calendar())
        self._escape_bind_id = root.bind(
            "<Escape>", lambda _e: self._close_calendar() if self._calendar_top else None, add="+"
        )

    def _place_calendar_popup(self, top: ctk.CTkToplevel, width: int, height: int) -> None:
        top.update_idletasks()
        # Use widget's screen for multi-monitor; fallback to top's screen
        try:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
        except Exception:
            screen_w = top.winfo_screenwidth()
            screen_h = top.winfo_screenheight()
        # Scale popup for DPI (CustomTkinter scaling)
        try:
            scaling = float(self.tk.call("tk", "scaling"))  # type: ignore[attr-defined]
            if scaling and scaling != 1.0:
                # Keep logical size but ensure placement accounts for scaled screen
                pass
        except Exception:
            pass
        x, y = calendar_popup_position(
            anchor_x=self.winfo_rootx(),
            anchor_y=self.winfo_rooty(),
            anchor_w=max(self.winfo_width(), 1),
            anchor_h=max(self.winfo_height(), 1),
            popup_w=width,
            popup_h=height,
            screen_w=screen_w,
            screen_h=screen_h,
        )
        top.geometry(f"{width}x{height}+{x}+{y}")

    def _open_calendar(self) -> None:
        self._close_calendar()
        today = date.today()
        view = self._initial_date().replace(day=1)

        root = self.winfo_toplevel()
        top = ctk.CTkToplevel(root)
        self._calendar_top = top
        top.title("Pick a date")
        top.resizable(False, False)
        top.transient(root)
        top.protocol("WM_DELETE_WINDOW", self._close_calendar)
        width, height = 360, 420

        body = ctk.CTkFrame(top, corner_radius=12)
        body.grid(row=0, column=0, padx=12, pady=12)
        body.grid_columnconfigure(0, weight=1)

        nav = ctk.CTkFrame(body, fg_color="transparent")
        nav.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        left_nav = ctk.CTkFrame(nav, fg_color="transparent")
        left_nav.pack(side="left")
        ctk.CTkButton(left_nav, text="\u25c0", width=28, command=lambda: set_year(view.year - 1)).pack(side="left")
        year_menu = ctk.CTkOptionMenu(
            left_nav,
            width=82,
            values=[str(year) for year in range(view.year - 10, view.year + 11)],
        )
        year_menu.pack(side="left", padx=4)
        ctk.CTkButton(left_nav, text="\u25b6", width=28, command=lambda: set_year(view.year + 1)).pack(side="left")

        month_label = ctk.CTkLabel(nav, text="", font=ctk.CTkFont(size=14, weight="bold"), anchor="center")
        month_label.pack(side="left", expand=True, fill="x", padx=6)

        right_nav = ctk.CTkFrame(nav, fg_color="transparent")
        right_nav.pack(side="right")
        ctk.CTkButton(right_nav, text="\u25c0", width=28, command=lambda: set_month(view.month - 1)).pack(side="left")
        month_menu = ctk.CTkOptionMenu(right_nav, width=96, values=calendar.month_name[1:])
        month_menu.pack(side="left", padx=4)
        ctk.CTkButton(right_nav, text="\u25b6", width=28, command=lambda: set_month(view.month + 1)).pack(side="left")

        grid_frame = ctk.CTkFrame(body, fg_color="transparent")
        grid_frame.grid(row=1, column=0, padx=6, pady=(0, 6))
        for col in range(7):
            grid_frame.grid_columnconfigure(col, weight=1)

        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 8))
        ctk.CTkButton(
            footer,
            text="Today",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._pick(top, today),
        ).pack(side="left")
        ctk.CTkButton(
            footer,
            text="Cancel",
            width=80,
            fg_color="transparent",
            border_width=1,
            command=self._close_calendar,
        ).pack(side="right")

        def draw() -> None:
            for child in grid_frame.winfo_children():
                child.destroy()
            month_label.configure(text=f"{calendar.month_name[view.month]} {view.year}")
            for index, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")):
                ctk.CTkLabel(
                    grid_frame,
                    text=name,
                    width=36,
                    text_color=TEXT_MUTED,
                ).grid(row=0, column=index, padx=1, pady=1)
            first_weekday, days_in_month = calendar.monthrange(view.year, view.month)
            for day_number in range(1, days_in_month + 1):
                chosen = date(view.year, view.month, day_number)
                is_today = chosen == today
                ctk.CTkButton(
                    grid_frame,
                    text=str(day_number),
                    width=36,
                    height=30,
                    fg_color=("#2563eb", "#3b82f6") if is_today else "transparent",
                    text_color=("white", "white") if is_today else ("gray10", "gray90"),
                    hover_color=("gray80", "gray25"),
                    command=lambda d=chosen: self._pick(top, d),
                ).grid(
                    row=(first_weekday + day_number - 1) // 7 + 1,
                    column=(first_weekday + day_number - 1) % 7,
                    padx=1,
                    pady=1,
                )

        def _sync_year_menu() -> None:
            values = tuple(str(year) for year in range(view.year - 10, view.year + 11))
            if set(year_menu.cget("values")) != set(values):
                year_menu.configure(values=values)
            year_menu.set(str(view.year))

        def _sync_month_menu() -> None:
            month_menu.set(calendar.month_name[view.month])

        def set_year(year: int) -> None:
            nonlocal view
            view = view.replace(year=year)
            _sync_year_menu()
            _sync_month_menu()
            draw()

        def set_month(month: int) -> None:
            nonlocal view
            view = _step_month(view, month - view.month)
            _sync_year_menu()
            _sync_month_menu()
            draw()

        year_menu.configure(command=lambda choice: set_year(int(choice)))
        month_menu.configure(command=lambda choice: set_month(calendar.month_name.index(choice)))
        _sync_year_menu()
        _sync_month_menu()
        draw()
        self._place_calendar_popup(top, width, height)
        self._bind_dismiss_on_click_outside(top)
        top.deiconify()
        top.lift()
        try:
            top.attributes("-topmost", True)
            top.after(200, lambda: top.attributes("-topmost", False) if top.winfo_exists() else None)
        except Exception:
            pass

        # Best-effort grab for modal dismissal
        def _try_grab() -> None:
            try:
                if top.winfo_exists():
                    top.grab_set()
            except Exception:
                pass

        top.after(80, _try_grab)
        try:
            top.focus_force()
        except Exception:
            pass
        bind_escape(top)

    def _pick(self, top: ctk.CTkToplevel, chosen: date) -> None:
        self.var.set(chosen.isoformat())
        self._close_calendar()


class FeedbackLabel(ctk.CTkLabel):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, text="", anchor="w", wraplength=WRAP_CARD, **kwargs)
        # Keep wrapping responsive — parents resize, so update with them.
        self.bind("<Configure>", lambda e: self.configure(wraplength=max(240, e.width - 8)))

    def success(self, message: str) -> None:
        self.configure(text=message, text_color=FEEDBACK_SUCCESS)

    def error(self, message: str) -> None:
        self.configure(text=message, text_color=FEEDBACK_ERROR)

    def info(self, message: str) -> None:
        self.configure(text=message, text_color=FEEDBACK_INFO)

    def clear(self) -> None:
        self.configure(text="")


class SelectableFileList(ctk.CTkFrame):
    """Single-select list of files in a folder, rebuilt only when contents change."""

    def __init__(
        self,
        master,
        *,
        on_select: Callable[[Path | None], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_select = on_select
        self._signature: tuple | None = None
        self._buttons: list[ctk.CTkButton] = []
        self.selected: Path | None = None
        self.files: list[Path] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._scroll = themed_scrollable_frame(self)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(
            self._scroll,
            text="No files in this folder.",
            text_color=TEXT_SUBTLE,
        )

    def set_files(self, files: list[Path], signature: tuple | None = None) -> None:
        if signature is not None and signature == self._signature:
            return
        previous = self.selected.name if self.selected else None
        self._signature = signature
        self.files = list(files)
        for button in self._buttons:
            button.destroy()
        self._buttons.clear()
        self._empty.grid_forget()

        if not files:
            self.selected = None
            self._empty.grid(row=0, column=0, padx=12, pady=16, sticky="w")
            if self._on_select:
                self._on_select(None)
            return

        restored: Path | None = None
        for index, path in enumerate(files):
            button = ctk.CTkButton(
                self._scroll,
                text=path.name,
                anchor="w",
                height=32,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda p=path: self.select(p),
            )
            button.grid(row=index, column=0, sticky="ew", padx=4, pady=2)
            self._buttons.append(button)
            if previous and path.name == previous:
                restored = path

        self.select(restored or files[0], notify=True)

    def select(self, path: Path | None, notify: bool = True) -> None:
        self.selected = path
        for button, file_path in zip(self._buttons, self.files, strict=True):
            if path is not None and file_path == path:
                button.configure(fg_color=("gray75", "gray30"))
            else:
                button.configure(fg_color="transparent")
        if notify and self._on_select:
            self._on_select(path)


class OrderedPathList(ctk.CTkFrame):
    """Multi-file list with remove / move up / move down for the PDF merger."""

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.paths: list[Path] = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._scroll = themed_scrollable_frame(self)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(1, weight=1)

    def add_paths(self, paths: list[Path]) -> None:
        existing = {item.resolve() for item in self.paths}
        for path in paths:
            if path.resolve() not in existing:
                self.paths.append(path)
                existing.add(path.resolve())
        self._redraw()

    def clear(self) -> None:
        self.paths.clear()
        self._redraw()

    def _move(self, index: int, delta: int) -> None:
        target = index + delta
        if 0 <= target < len(self.paths):
            self.paths[index], self.paths[target] = self.paths[target], self.paths[index]
            self._redraw()

    def _remove(self, index: int) -> None:
        if 0 <= index < len(self.paths):
            self.paths.pop(index)
            self._redraw()

    def _redraw(self) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()
        if not self.paths:
            ctk.CTkLabel(
                self._scroll,
                text="No PDFs added yet.",
                text_color=TEXT_SUBTLE,
            ).grid(row=0, column=0, columnspan=4, padx=12, pady=16, sticky="w")
            return
        for index, path in enumerate(self.paths):
            ctk.CTkLabel(
                self._scroll,
                text=f"{index + 1}.",
                width=28,
                anchor="e",
            ).grid(row=index, column=0, padx=(8, 4), pady=4)
            ctk.CTkLabel(self._scroll, text=path.name, anchor="w").grid(
                row=index, column=1, sticky="ew", padx=4, pady=4
            )
            ctk.CTkButton(self._scroll, text="Up", width=48, command=lambda i=index: self._move(i, -1)).grid(
                row=index, column=2, padx=2, pady=4
            )
            ctk.CTkButton(self._scroll, text="Down", width=56, command=lambda i=index: self._move(i, 1)).grid(
                row=index, column=3, padx=2, pady=4
            )
            ctk.CTkButton(
                self._scroll,
                text="Remove",
                width=72,
                fg_color="transparent",
                border_width=1,
                command=lambda i=index: self._remove(i),
            ).grid(row=index, column=4, padx=(2, 8), pady=4)


class DropZone(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        title: str,
        subtitle: str,
        on_files: Callable[[list[Path]], None],
        dnd_available: bool,
        **kwargs,
    ) -> None:
        super().__init__(master, corner_radius=12, border_width=2, **kwargs)
        self._on_files = on_files
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.grid(row=0, column=0, padx=24, pady=28)
        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack()
        ctk.CTkLabel(
            inner,
            text=subtitle,
            text_color=TEXT_MUTED,
            justify="center",
        ).pack(pady=(6, 0))
        # Make the whole zone clickable.
        self._bind_clicks(self)
        # Single drop handler — inner events bubble to the parent, so binding
        # only the outer frame avoids the double-fire on inner-label drops.
        enable_drop(self, self._on_files, dnd_available)

    def browse(self) -> None:
        self._on_click()

    def _bind_clicks(self, widget) -> None:
        widget.bind("<Button-1>", self._on_click)
        for child in widget.winfo_children():
            self._bind_clicks(child)

    def _on_click(self, _event=None) -> None:
        from tkinter import filedialog

        selections = filedialog.askopenfilenames(
            parent=self.winfo_toplevel(),
            title="Select images",
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not selections:
            return
        # filedialog may return a Tcl string list on some Tk builds.
        if isinstance(selections, str):
            selections = self.tk.splitlist(selections)
        files = [Path(item) for item in selections if Path(item).is_file()]
        if not files:
            self._on_files([])
            return
        self._on_files(files)
