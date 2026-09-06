"""Tk Canvas scrolling — smoother than CTkScrollableFrame for static forms."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from skyadmin_pro.ui.theme import SURFACE_BG


class CanvasScrollFrame(ctk.CTkFrame):
    """Vertical scroll container with a CTkFrame content host."""

    def __init__(self, master, **kwargs) -> None:
        fg = kwargs.pop("fg_color", "transparent")
        super().__init__(master, fg_color=fg, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        mode = ctk.get_appearance_mode()
        bg = SURFACE_BG[1 if mode == "Dark" else 0]
        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0, bg=bg)
        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._window_id = self._canvas.create_window((0, 0), window=self.content, anchor="nw")
        # Tk paths of widgets already wheel-bound; prevents stacking duplicate
        # handlers on every scrollregion update (paths are pruned when dead).
        self._wheel_bound: set[str] = set()
        self.content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._pending_scroll_update: str | None = None
        self._bind_mousewheel(self._canvas)
        self._bind_mousewheel(self.content)
        # Ensure wheel scroll works when hovering over any child (labels, frames)
        self._bind_wheel_recursive(self.content)

    def _on_content_configure(self, _event=None) -> None:
        # Debounce scrollregion recompute (Treeview incremental insert triggers many configures)
        if self._pending_scroll_update is not None:
            try:
                self.after_cancel(self._pending_scroll_update)
            except Exception:  # defensive: Tk teardown/callback
                pass
        self._pending_scroll_update = self.after(30, self._update_scrollregion)

    def _update_scrollregion(self) -> None:
        self._pending_scroll_update = None
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return
        try:
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        except Exception:  # defensive: Tk teardown/callback
            pass
        # Re-bind wheel for newly added children
        self._bind_wheel_recursive(self.content)

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._window_id, width=event.width)

    def _bind_wheel_recursive(self, widget) -> None:
        # Bind wheel to widget and all current descendants; called on content changes.
        # Iterative (no recursion-depth risk) with a bound-path set so repeated
        # passes don't stack duplicate handlers on the same widget.
        try:
            for dead in [p for p in self._wheel_bound]:
                try:
                    self.nametowidget(dead)
                except Exception:
                    self._wheel_bound.discard(dead)
            stack = list(widget.winfo_children())
        except Exception:
            return
        while stack:
            child = stack.pop()
            try:
                if "ThemedTreeview" in [c.__name__ for c in type(child).__mro__]:
                    continue
                try:
                    if child.winfo_class() == "Treeview":
                        continue
                except Exception:  # defensive: Tk teardown/callback
                    pass
                path = str(child)
                if path not in self._wheel_bound:
                    child.bind("<MouseWheel>", self._on_mousewheel, add="+")
                    child.bind("<Button-4>", self._on_mousewheel_linux, add="+")
                    child.bind("<Button-5>", self._on_mousewheel_linux, add="+")
                    self._wheel_bound.add(path)
                stack.extend(child.winfo_children())
            except Exception:  # defensive: Tk teardown/callback
                pass

    def _bind_mousewheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel_linux, add="+")
        widget.bind("<Button-5>", self._on_mousewheel_linux, add="+")

    def _on_mousewheel(self, event) -> None:
        # Let inner Treeview handle wheel if pointer is over a tree
        try:
            # Check if event widget is a treeview canvas — let it scroll itself
            w = event.widget
            # Walk up to see if we're inside a ThemedTreeview tree
            while w is not None:
                if w.winfo_class() == "Treeview":
                    return  # let tree handle
                try:
                    w = w.master  # type: ignore[attr-defined]
                except Exception:
                    break
        except Exception:  # defensive: Tk teardown/callback
            pass
        if event.delta:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

    def _on_mousewheel_linux(self, event) -> None:
        try:
            w = event.widget
            while w is not None:
                if w.winfo_class() == "Treeview":
                    return
                try:
                    w = w.master  # type: ignore[attr-defined]
                except Exception:
                    break
        except Exception:  # defensive: Tk teardown/callback
            pass
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        return "break"

    def destroy(self) -> None:
        if getattr(self, "_pending_scroll_update", None) is not None:
            try:
                self.after_cancel(self._pending_scroll_update)
            except Exception:  # defensive: Tk teardown/callback
                pass
            self._pending_scroll_update = None
        try:
            super().destroy()
        except Exception:  # defensive: Tk teardown/callback
            pass

    def winfo_children(self):
        children = list(super().winfo_children())
        if self.content not in children:
            children.append(self.content)
        return children

    def refresh_theme(self) -> None:
        mode = ctk.get_appearance_mode()
        self._canvas.configure(bg=SURFACE_BG[1 if mode == "Dark" else 0])
