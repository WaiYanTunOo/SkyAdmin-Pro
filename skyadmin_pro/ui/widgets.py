"""Reusable CustomTkinter widgets for Document Hub."""

from __future__ import annotations

import calendar
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

import customtkinter as ctk

from skyadmin_pro.ui.dnd import enable_drop
from skyadmin_pro.ui.theme import (
    CARD_TITLE_SIZE,
    FEEDBACK_ERROR,
    FEEDBACK_INFO,
    FEEDBACK_SUCCESS,
    TEXT_MUTED,
    TEXT_SUBTLE,
    WRAP_CARD,
)
from skyadmin_pro.ui.treeview import ThemedTreeview

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

    def _grab():
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
        month_key = self._month_key()
        self.month_label.configure(text=f"{calendar.month_name[self._month]} {self._year}")
        clients = self.app.db.list_monthly_tax_clients()
        client_ids = [int(client["id"]) for client in clients]
        summary = self.app.db.month_close_summary(month_key, client_ids=client_ids)
        self.summary.configure(
            text=(f"{summary['closed']}/{summary['clients']} closed · {summary['in_progress']} in progress")
        )

        self.tree.apply_theme()
        statuses = self.app.db.list_client_month_status(month_key)
        rows, iids, tags = [], [], []
        for client in clients:
            client_id = int(client["id"])
            record = statuses.get(client_id)
            status = record["status"] if record else MONTH_STATUS_OPEN
            updated = (record.get("updated_at") or "")[:16] if record else "—"
            rows.append((client.get("name") or "—", _STATUS_LABEL[status], updated))
            iids.append(str(client_id))
            tag = _STATUS_TAG[status]
            tags.append((tag,) if tag else ())
        self.tree.set_rows(rows, iids=iids, tags=tags)

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


class DatePickerField(ctk.CTkFrame):
    """Text entry plus a calendar popup; the StringVar always holds ISO YYYY-MM-DD."""

    def __init__(self, master, *, var: ctk.StringVar | None = None, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.var = var if var is not None else ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.var, placeholder_text="YYYY-MM-DD").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            self,
            text="Calendar",
            width=96,
            command=self._open_calendar,
        ).grid(row=0, column=1, padx=(8, 0))

    def _initial_date(self) -> date:
        value = self.var.get().strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return date.today()

    def _open_calendar(self) -> None:
        today = date.today()
        view = self._initial_date().replace(day=1)

        top = ctk.CTkToplevel(self)
        top.title("Pick a date")
        top.resizable(False, False)
        top.attributes("-topmost", True)
        top.transient(self.winfo_toplevel())
        # Center over parent so it doesn't spawn off-screen in the frozen build.
        try:
            px, py = self.winfo_rootx(), self.winfo_rooty()
            pw, ph = self.winfo_width(), self.winfo_height()
            top.geometry(f"+{px + max(0, pw // 2 - 160)}+{py + max(0, ph // 2 - 160)}")
        except Exception:
            pass
        make_modal(top)

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
            command=top.destroy,
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

    def _pick(self, top: ctk.CTkToplevel, chosen: date) -> None:
        self.var.set(chosen.isoformat())
        top.destroy()


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
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=("gray92", "gray17"))
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
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=("gray92", "gray17"))
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
