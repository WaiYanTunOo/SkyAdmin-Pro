"""Main application window: sidebar navigation + swapping content frames."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

import customtkinter as ctk

from skyadmin_pro.config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    DEFAULT_WINDOW_GEOMETRY,
    MIN_WINDOW_SIZE,
    NAV_DASHBOARD,
    NAV_OFFICE_HUB,
    SETTING_SIDEBAR_COLLAPSED,
    SETTING_WINDOW_GEOMETRY,
)
from skyadmin_pro.ui.display import (
    form_sidebar_width,
    get_active_metrics,
    metrics_for_screen,
    preferred_geometry,
    set_active_metrics,
)
from skyadmin_pro.ui.dnd import dnd_base_class, init_dnd
from skyadmin_pro.ui.sidebar import SidebarWidget
from skyadmin_pro.ui.theme import (
    STATUS_BAR_HEIGHT,
    TEXT_FAINT,
    TEXT_MUTED,
)

if TYPE_CHECKING:
    from skyadmin_pro.database import Database
    from skyadmin_pro.paths import WorkspacePaths
    from skyadmin_pro.ui.views.base import BaseView

logger = logging.getLogger(__name__)


class MainWindow(dnd_base_class()):
    _VIEW_FACTORIES: dict[str, Callable[[MainWindow], BaseView]] = {}

    @classmethod
    def _register_view_factories(cls) -> None:
        if cls._VIEW_FACTORIES:
            return
        from skyadmin_pro.ui.views.dashboard import DashboardView
        from skyadmin_pro.ui.views.database_tasks import DatabaseTasksView
        from skyadmin_pro.ui.views.document_hub import DocumentHubView
        from skyadmin_pro.ui.views.menu_panels import (
            AccountingSetupMenuView,
            CourierMenuView,
            PipelineMenuView,
            SuppliersMenuView,
            TasksMenuView,
            TaxStatusMenuView,
        )
        from skyadmin_pro.ui.views.office_hub import OfficeHubView
        from skyadmin_pro.ui.views.settings import SettingsView
        from skyadmin_pro.ui.views.utilities import UtilitiesView

        cls._VIEW_FACTORIES = {
            "dashboard": lambda app: DashboardView(app.content, app=app),
            "document_hub": lambda app: DocumentHubView(app.content, app=app),
            "database_tasks": lambda app: DatabaseTasksView(app.content, app=app),
            "tasks": lambda app: TasksMenuView(app.content, app=app),
            "courier": lambda app: CourierMenuView(app.content, app=app),
            "tax_status": lambda app: TaxStatusMenuView(app.content, app=app),
            "accounting_setup": lambda app: AccountingSetupMenuView(app.content, app=app),
            "pipeline": lambda app: PipelineMenuView(app.content, app=app),
            "suppliers": lambda app: SuppliersMenuView(app.content, app=app),
            "office_hub": lambda app: OfficeHubView(app.content, app=app),
            "utilities": lambda app: UtilitiesView(app.content, app=app),
            "settings": lambda app: SettingsView(app.content, app=app),
        }

    def __init__(self, db: Database, paths: WorkspacePaths) -> None:
        super().__init__()
        self.db = db
        self.paths = paths
        self.dnd_available = init_dnd(self)
        self._register_view_factories()

        self.title(APP_NAME)
        self._set_window_icon()
        self._layout_after: str | None = None
        self._init_display_metrics()
        geometry = self.db.get_setting(SETTING_WINDOW_GEOMETRY, DEFAULT_WINDOW_GEOMETRY)
        geometry = self._pick_startup_geometry(geometry or DEFAULT_WINDOW_GEOMETRY)
        geometry = self._safe_geometry(geometry)
        self.geometry(geometry)
        m = get_active_metrics()
        self.minsize(m.min_width, m.min_height)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._views: dict[str, ctk.CTkFrame] = {}
        self._active_key: str | None = None
        self._sidebar_collapsed = self.db.get_setting(SETTING_SIDEBAR_COLLAPSED) == "1"

        self._build_sidebar()
        self._build_content()
        self._build_status_bar()
        self.show_view(NAV_DASHBOARD)
        self._bind_keyboard_shortcuts()
        self._start_auto_backup()
        self._start_auto_sync()
        self.bind("<Configure>", self._on_window_configure, add="+")
        self.bind("<FocusIn>", self._on_window_focus_in, add="+")
        self.bind("<Map>", self._on_window_map, add="+")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _bind_keyboard_shortcuts(self) -> None:
        """Global keyboard shortcuts — Ctrl+E export, Ctrl+F find, Ctrl+N new,
        Ctrl+S save-when-obvious, Ctrl+D theme.

        Ctrl+Z undoes the last client change (outside text inputs, where the
        keystroke stays with the field). Ctrl+S/F/N are bound globally on purpose
        (they are not needed for typing in entries).
        """
        self.bind("<Control-e>", lambda _e: self._shortcut_action("export"))
        self.bind("<Control-E>", lambda _e: self._shortcut_action("export"))
        self.bind("<Control-f>", lambda _e: self.open_global_search())
        self.bind("<Control-F>", lambda _e: self.open_global_search())
        self.bind("<Control-k>", lambda _e: self.open_global_search())
        self.bind("<Control-K>", lambda _e: self.open_global_search())
        self.bind("<Control-n>", lambda _e: self._shortcut_new())
        self.bind("<Control-N>", lambda _e: self._shortcut_new())
        self.bind("<Control-s>", lambda _e: self._shortcut_save())
        self.bind("<Control-S>", lambda _e: self._shortcut_save())
        self.bind("<Control-z>", lambda _e: self._shortcut_action("undo"))
        self.bind("<Control-Z>", lambda _e: self._shortcut_action("undo"))
        self.bind("<Control-d>", lambda _e: self._toggle_dark_light())
        self.bind("<Control-D>", lambda _e: self._toggle_dark_light())

    def _toggle_dark_light(self) -> None:
        """Toggle between Dark and Light mode (Ctrl+D, outside text inputs)."""
        if self._focus_in_text_input():
            return
        import customtkinter as _ctk

        from skyadmin_pro.config import SETTING_APPEARANCE_MODE

        current = _ctk.get_appearance_mode()
        new_mode = "light" if current == "Dark" else "dark"
        _ctk.set_appearance_mode(new_mode)
        self.db.set_setting(SETTING_APPEARANCE_MODE, new_mode)
        self.apply_app_theme()
        # Sync settings view if open
        settings = self._views.get("settings")
        if settings is not None and hasattr(settings, "appearance_menu"):
            settings.appearance_menu.set(new_mode.capitalize())

    def open_global_search(self) -> None:
        """Open the global search dialog (Ctrl+F)."""
        from skyadmin_pro.ui.views.global_search import GlobalSearchDialog

        GlobalSearchDialog(self)

    def _shortcut_new(self) -> None:
        """Ctrl+N — new client via active view, else Database & Tasks → Clients."""
        from skyadmin_pro.config import NAV_DATABASE_TASKS

        view = self._views.get(self._active_key) if self._active_key else None
        handler = getattr(view, "_on_shortcut_new", None) if view is not None else None
        if callable(handler):
            handler()
            return
        self.show_view(NAV_DATABASE_TASKS)
        tasks = self.get_view(NAV_DATABASE_TASKS)
        new_handler = getattr(tasks, "_on_shortcut_new", None) if tasks is not None else None
        if callable(new_handler):
            new_handler()

    def _shortcut_save(self) -> None:
        """Ctrl+S — call an obvious view save when present; else status no-op."""
        view = self._views.get(self._active_key) if self._active_key else None
        handler = getattr(view, "_on_shortcut_save", None) if view is not None else None
        if callable(handler):
            handled = handler()
            if handled is False:
                self.set_status("Nothing to save")
            return
        self.set_status("Nothing to save")

    def _focus_in_text_input(self) -> bool:
        """True when keyboard focus sits inside an editable text widget."""
        try:
            widget = self.focus_get()
        except tk.TclError:
            return False
        while widget is not None:
            try:
                cls = widget.winfo_class()
            except tk.TclError:
                return False
            if cls in ("Entry", "Text", "TCombobox", "CTkEntry", "CTkTextbox", "CTkComboBox"):
                return True
            try:
                widget = widget.master
            except (AttributeError, tk.TclError):
                return False
        return False

    def _shortcut_action(self, action: str) -> None:
        """Dispatch keyboard shortcut to the active view."""
        # Never hijack typing: export/new fire only when focus is outside inputs.
        # (Find + theme stay global — expected everywhere.)
        if self._focus_in_text_input():
            return
        if self._active_key is None:
            return
        view = self._views.get(self._active_key)
        if view is None:
            return
        handler = getattr(view, f"_on_shortcut_{action}", None)
        if callable(handler):
            handler()

    def _start_auto_backup(self) -> None:
        try:
            from skyadmin_pro.services.auto_backup import AutoBackupScheduler

            self._auto_backup = AutoBackupScheduler(self)
            self._auto_backup.start()
        except (OSError, RuntimeError) as exc:
            logger.warning("Auto-backup scheduler failed to start: %s", exc)

    def _start_auto_sync(self) -> None:
        try:
            from skyadmin_pro.services.data_sync import AutoSyncScheduler

            self._auto_sync = AutoSyncScheduler(self)
            self._auto_sync.start()
        except (OSError, RuntimeError) as exc:
            logger.warning("Auto-sync scheduler failed to start: %s", exc)

    def _on_window_focus_in(self, event) -> None:
        if event.widget is not self:
            return
        scheduler = getattr(self, "_auto_sync", None)
        on_focus = getattr(scheduler, "on_window_focus", None)
        if callable(on_focus):
            try:
                on_focus()
            except Exception:
                logger.debug("Auto-sync focus pull failed", exc_info=True)

    def _on_window_map(self, event) -> None:
        if event.widget is not self:
            return
        scheduler = getattr(self, "_auto_sync", None)
        on_focus = getattr(scheduler, "on_window_focus", None)
        if callable(on_focus):
            try:
                on_focus()
            except Exception:
                logger.debug("Auto-sync map pull failed", exc_info=True)

    def _build_sidebar(self) -> None:
        """Build the outer sidebar frame and hand nav-button management to SidebarWidget."""
        m = get_active_metrics()
        width = m.sidebar_collapsed if self._sidebar_collapsed else m.sidebar_width
        self.sidebar = ctk.CTkFrame(self, width=width, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(2, weight=1)

        from skyadmin_pro.ui.theme import SIDEBAR_HOVER_BG, SIDEBAR_PADX

        top_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        top_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(12, 4))
        top_row.grid_columnconfigure(0, weight=1)
        self.sidebar_toggle_btn = ctk.CTkButton(
            top_row,
            text="»" if self._sidebar_collapsed else "«",
            width=36,
            height=32,
            corner_radius=8,
            fg_color="transparent",
            hover_color=SIDEBAR_HOVER_BG,
            command=self._toggle_sidebar,
        )
        self.sidebar_toggle_btn.grid(row=0, column=0, sticky="e")

        self.brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.brand.grid(row=1, column=0, sticky="ew", padx=SIDEBAR_PADX, pady=(0, 16))
        ctk.CTkLabel(
            self.brand,
            text=APP_NAME,
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(fill="x")
        self.tagline_label = ctk.CTkLabel(
            self.brand,
            text=self.db.get_setting("app_tagline") or APP_TAGLINE,
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.tagline_label.pack(fill="x", pady=(2, 0))

        self.nav_host = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.nav_host.grid(row=2, column=0, sticky="nsew")
        self.nav_host.grid_columnconfigure(0, weight=1)

        self.sidebar_widget = SidebarWidget(
            self.nav_host,
            self.db,
            self.show_view,
            collapsed=self._sidebar_collapsed,
        )

        self.version_label = ctk.CTkLabel(
            self.sidebar,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_FAINT,
        )
        self.version_label.grid(row=3, column=0, padx=SIDEBAR_PADX, pady=(0, 2), sticky="sw")
        self.refresh_sidebar_status()
        self.copyright_label = ctk.CTkLabel(
            self.sidebar,
            text="© Sky Creation Innovations\nAll rights reserved",
            font=ctk.CTkFont(size=10),
            text_color=TEXT_FAINT,
            justify="left",
            anchor="w",
        )
        self.copyright_label.grid(row=4, column=0, padx=SIDEBAR_PADX, pady=(0, 18), sticky="sw")
        self._apply_sidebar_layout()

    def _toggle_sidebar(self) -> None:
        self._sidebar_collapsed = not self._sidebar_collapsed
        self.db.set_setting(SETTING_SIDEBAR_COLLAPSED, "1" if self._sidebar_collapsed else "0")
        self._apply_sidebar_layout()

    def _init_display_metrics(self) -> None:
        try:
            sw = int(self.winfo_screenwidth())
            sh = int(self.winfo_screenheight())
        except (tk.TclError, ValueError):
            sw, sh = 1920, 1080
        set_active_metrics(metrics_for_screen(sw, sh))

    def _pick_startup_geometry(self, geometry: str) -> str:
        """On large screens, replace the stock 1280x800 default with a fitted size."""
        try:
            sw = int(self.winfo_screenwidth())
            sh = int(self.winfo_screenheight())
        except (tk.TclError, ValueError):
            return geometry
        raw = str(geometry or "").strip()
        if raw == DEFAULT_WINDOW_GEOMETRY and max(sw, sh) >= 2560:
            return preferred_geometry(sw, sh)
        return geometry

    def _on_window_configure(self, event=None) -> None:
        if event is not None and event.widget is not self:
            return
        if self._layout_after is not None:
            try:
                self.after_cancel(self._layout_after)
            except (tk.TclError, ValueError):
                pass
        self._layout_after = self.after(120, self._apply_responsive_layout)

    def _apply_responsive_layout(self) -> None:
        self._layout_after = None
        try:
            if not self.winfo_exists():
                return
            sw = int(self.winfo_screenwidth())
            sh = int(self.winfo_screenheight())
            ww = int(self.winfo_width())
        except (tk.TclError, ValueError):
            return
        set_active_metrics(metrics_for_screen(sw, sh))
        m = get_active_metrics()
        try:
            self.minsize(m.min_width, m.min_height)
        except tk.TclError:
            pass
        self._apply_sidebar_layout()
        content_w = max(0, ww - (m.sidebar_collapsed if self._sidebar_collapsed else m.sidebar_width))
        form_w = form_sidebar_width(content_w, m)
        for view in self._views.values():
            apply = getattr(view, "_apply_responsive_layout", None)
            if callable(apply):
                try:
                    apply(form_sidebar_min=form_w, metrics=m)
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")
            panel = getattr(view, "panel", None)
            apply_p = getattr(panel, "_apply_responsive_layout", None) if panel is not None else None
            if callable(apply_p):
                try:
                    apply_p(form_sidebar_min=form_w, metrics=m)
                except Exception as e:
                    import logging

                    logging.error(f"UI Error: {e}")

    def _apply_sidebar_layout(self) -> None:
        collapsed = self._sidebar_collapsed
        m = get_active_metrics()
        width = m.sidebar_collapsed if collapsed else m.sidebar_width
        self.sidebar.configure(width=width)
        self.sidebar_toggle_btn.configure(text="»" if collapsed else "«")
        if collapsed:
            self.brand.grid_remove()
            self.version_label.grid_remove()
            self.copyright_label.grid_remove()
        else:
            self.brand.grid()
            self.version_label.grid()
            self.copyright_label.grid()
        self.sidebar_widget.apply_layout(collapsed)

    def _get_window_scaling(self) -> float:
        """Pixels-per-point reported by Tk (diagnostic use only)."""
        try:
            return float(self.tk.call("tk", "scaling"))
        except (tk.TclError, ValueError):
            return 1.0

    def _safe_geometry(self, geometry: str) -> str:
        """Clamp a saved geometry string so the window always lands on-screen.

        Restored databases carry the previous machine's window_geometry
        (e.g. ``1280x800+3000+100`` from a second monitor). Applying it blind
        opens the window off-screen — the app looks like it never started.
        Parse WxH+X+Y, clamp the size to the current screen, and re-center
        when the saved position is not visible.
        """
        import re

        fallback = DEFAULT_WINDOW_GEOMETRY
        try:
            match = re.match(r"^(\d+)x(\d+)([+-]\d+)?([+-]\d+)?$", str(geometry or "").strip())
            if not match:
                return fallback
            width, height = int(match.group(1)), int(match.group(2))
            try:
                screen_w = int(self.winfo_screenwidth())
                screen_h = int(self.winfo_screenheight())
            except (tk.TclError, ValueError):
                return f"{width}x{height}"
            width = max(MIN_WINDOW_SIZE[0], min(width, screen_w))
            height = max(MIN_WINDOW_SIZE[1], min(height, screen_h))
            if match.group(3) is None or match.group(4) is None:
                return f"{width}x{height}"
            x, y = int(match.group(3)), int(match.group(4))
            visible = (-width + 50 < x < screen_w - 50) and (-height + 50 < y < screen_h - 50)
            if visible:
                return f"{width}x{height}{x:+d}{y:+d}"
            cx = max(0, (screen_w - width) // 2)
            cy = max(0, (screen_h - height) // 2)
            return f"{width}x{height}+{cx}+{cy}"
        except (ValueError, TypeError):
            return fallback

    def _build_content(self) -> None:
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    def _ensure_view(self, key: str) -> ctk.CTkFrame | None:
        if key in self._views:
            return self._views[key]
        factory = self._VIEW_FACTORIES.get(key)
        if factory is None:
            return None
        view = factory(self)
        view.grid(row=0, column=0, sticky="nsew")
        self._views[key] = view
        # Apply theme immediately so newly created views don't render with
        # default colours before the first appearance-mode toggle.
        from skyadmin_pro.ui.widgets import apply_form_theme

        apply_form_theme(view)
        return view

    def get_view(self, key: str) -> ctk.CTkFrame | None:
        """Public accessor for views — replaces private _views access from other modules."""
        return self._views.get(key)

    def _build_status_bar(self) -> None:
        # Scale height with DPI to avoid clipping at 150% (32*1.35=43)
        try:
            scale = float(self.tk.call("tk", "scaling"))
        except (tk.TclError, ValueError):
            scale = 1.0
        scaled_h = int(STATUS_BAR_HEIGHT * max(1.0, min(1.35, scale)))
        self.status_bar = ctk.CTkFrame(self, height=scaled_h, corner_radius=0)
        self.status_bar.grid(row=1, column=1, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)
        self.status_bar.grid_rowconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text=f"Workspace: {self.paths.root}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=16, pady=6)
        from skyadmin_pro.ui.widgets import bind_wrap_label

        bind_wrap_label(self.status_label, self.status_bar, pad=180)

        db_ok = "Database ready" if self.db.ping() else "Database error"
        ctk.CTkLabel(
            self.status_bar,
            text=db_ok,
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=16, pady=6)

    def show_view(self, key: str) -> None:
        view = self._ensure_view(key)
        if view is None:
            return

        if self._active_key and self._active_key != key:
            on_hide = getattr(self._views[self._active_key], "on_hide", None)
            if callable(on_hide):
                on_hide()

        view.tkraise()
        self._active_key = key
        self._highlight_nav(key)
        self.sidebar_widget.ensure_group_expanded(key)

        on_show = getattr(view, "on_show", None)
        if callable(on_show):
            on_show()
        from skyadmin_pro.ui.widgets import should_apply_theme

        if should_apply_theme():
            self.apply_app_theme(view)

    def apply_app_theme(self, root: ctk.Misc | None = None) -> None:
        """Re-apply form input and table styling after appearance changes."""
        from skyadmin_pro.ui.widgets import apply_form_theme, should_apply_theme

        if root is not None:
            apply_form_theme(root)
            return
        if not should_apply_theme():
            return  # skip full walk if mode unchanged
        apply_form_theme(self)
        for view in self._views.values():
            apply_form_theme(view)

    def open_office_hub_client_credentials(
        self,
        client_name: str,
        *,
        credential_type: str | None = None,
        credential_id: int | None = None,
    ) -> None:
        """Navigate to Office Hub → Clients Login Data for the given company."""
        view = self._ensure_view(NAV_OFFICE_HUB)
        if view is not None:
            view._pending_client_credentials = (
                (client_name or "").strip(),
                credential_type,
                credential_id,
            )
        self.show_view(NAV_OFFICE_HUB)

    def open_office_hub_client_rd(self, client_name: str) -> None:
        """Backward-compatible alias for RD-only navigation."""
        self.open_office_hub_client_credentials(client_name, credential_type="RD")

    def open_accounting_setup(self) -> None:
        """Navigate to Finance → Accounting Setup rollout queue."""
        from skyadmin_pro.config import NAV_ACCOUNTING

        self._ensure_view(NAV_ACCOUNTING)
        self.show_view(NAV_ACCOUNTING)

    def open_office_hub_setup(self) -> None:
        """Navigate to Office Hub → Setup migration queue."""
        view = self._ensure_view(NAV_OFFICE_HUB)
        if view is not None and hasattr(view, "open_setup"):
            view.open_setup()
        self.show_view(NAV_OFFICE_HUB)

    def open_vo_csh_setup(self) -> None:
        """Navigate to Companies → VO/CSH Setup rollout queue."""
        from skyadmin_pro.config import NAV_DATABASE_TASKS

        view = self._ensure_view(NAV_DATABASE_TASKS)
        if view is not None and hasattr(view, "open_vo_csh_setup"):
            view.open_vo_csh_setup()
        self.show_view(NAV_DATABASE_TASKS)

    def _highlight_nav(self, active_key: str) -> None:
        self.sidebar_widget.highlight(active_key)

    def refresh_sidebar_status(self) -> None:
        """Update sidebar version line (license expiry when active)."""
        from skyadmin_pro.services.license import (
            available_update,
            license_expiry_text,
            verify_license,
        )

        update = available_update()
        if update:
            ver = update.get("version", "?")
            self.version_label.configure(text=f"v{APP_VERSION}  ·  Update: v{ver}")
            return

        ok, _msg = verify_license()
        if ok:
            expiry = license_expiry_text()
            if expiry.startswith("no expiry"):
                self.version_label.configure(text=f"v{APP_VERSION}  ·  Licensed")
            else:
                self.version_label.configure(text=f"v{APP_VERSION}  ·  {expiry}")
        else:
            self.version_label.configure(text=f"v{APP_VERSION}")

    def refresh_tagline(self, text: str | None = None) -> None:
        from skyadmin_pro.config import APP_TAGLINE

        self.tagline_label.configure(text=text or self.db.get_setting("app_tagline") or APP_TAGLINE)

    def set_status(self, message: str) -> None:
        self.status_label.configure(text=message)

    def invalidate_dashboard(self) -> None:
        """Mark the dashboard cache stale after data changes in other views."""
        view = self._views.get("dashboard")
        if view is not None and hasattr(view, "mark_stale"):
            view.mark_stale()

    def _set_window_icon(self) -> None:
        """Set application icon for window titlebar, taskbar, and Alt-Tab."""
        import sys
        from pathlib import Path

        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SkyCreation.SkyAdminPro.App.0.3")
            except (AttributeError, OSError):
                pass

        base_dir = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent.parent.parent
        )
        ico_path = base_dir / "icon.ico"
        png_path = base_dir / "icon.png"

        try:
            if sys.platform == "win32" and ico_path.is_file():
                self.iconbitmap(str(ico_path))
            elif png_path.is_file():
                from PIL import Image, ImageTk

                img = Image.open(png_path)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, self._icon_photo)
        except (tk.TclError, OSError):
            pass

    def _on_close(self) -> None:
        # Give the active view a chance to cancel polling / after handles so
        # callbacks don't fire on a destroyed widget.
        if self._active_key and self._active_key in self._views:
            on_hide = getattr(self._views[self._active_key], "on_hide", None)
            if callable(on_hide):
                try:
                    on_hide()
                except Exception as exc:
                    logger.debug("Error in view on_hide: %s", exc)
        # Stop the auto-backup timer chain (process exit would reap it anyway).
        scheduler = getattr(self, "_auto_backup", None)
        stop = getattr(scheduler, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception as exc:
                logger.warning("Error stopping auto backup: %s", exc)
        auto_sync = getattr(self, "_auto_sync", None)
        stop_sync = getattr(auto_sync, "stop", None)
        if callable(stop_sync):
            try:
                stop_sync()
            except Exception as exc:
                logger.warning("Error stopping auto sync: %s", exc)
        for view in self._views.values():
            teardown = getattr(view, "on_hide", None)
            if callable(teardown):
                try:
                    teardown()
                except Exception as exc:
                    logger.debug("Error during view teardown: %s", exc)
        self.db.set_setting(SETTING_WINDOW_GEOMETRY, self.geometry())
        self.destroy()
