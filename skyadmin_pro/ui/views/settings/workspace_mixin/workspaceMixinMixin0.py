from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

from skyadmin_pro.config import SETTING_WORKSPACE_CUSTOM, SETTING_WORKSPACE_ROOT
from skyadmin_pro.paths import WorkspacePaths
from skyadmin_pro.services.data_hygiene import run_data_hygiene
from skyadmin_pro.services.workflow import repair_client_workspaces


class WorkspaceMixinMixin0:
    def _browse_workspace(self) -> None:
        initial = self.workspace_var.get().strip() or str(Path.home())
        folder = filedialog.askdirectory(
            parent=self.winfo_toplevel(),
            title="Choose workspace folder",
            initialdir=initial if Path(initial).is_dir() else str(Path.home()),
        )
        if folder:
            self.workspace_var.set(str(Path(folder).resolve()))

    def _save_workspace(self) -> None:
        raw = self.workspace_var.get().strip()
        if not raw:
            self.feedback.error("Enter a workspace path.")
            return
        root = Path(raw).expanduser().resolve()
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.feedback.error(f"Cannot create the workspace folder: {exc}")
            return
        self.app.db.set_setting(SETTING_WORKSPACE_ROOT, str(root))
        # Explicit user choice — stop auto-normalizing to the exe folder.
        self.app.db.set_setting(SETTING_WORKSPACE_CUSTOM, "1")
        self.app.paths = WorkspacePaths(root)
        self.app.paths.ensure()
        self.on_show()
        self.feedback.success(f"Workspace changed to {root}")
        self.app.set_status(f"Workspace: {root}")

    def _repair_client_folders(self) -> None:
        names = self.app.db.list_client_names()
        if not names:
            self.feedback.error("No clients in the database.")
            return
        result = repair_client_workspaces(self.app.paths.clients, names)
        linked = int(result["linked"])
        created = int(result["created"])
        failed = int(result["failed"])
        if failed:
            self.feedback.error(
                f"Repaired {linked} linked, {created} created, {failed} failed. "
                f"Check: {', '.join(result['failed_names'][:3])}"
            )
            return
        self.feedback.success(f"Client folders OK — {linked} linked to existing folders, {created} newly created.")
        self.app.set_status(f"Client folders: {linked} linked, {created} created, {result['total']} total")

    def _run_data_hygiene(self) -> None:
        if not messagebox.askyesno(
            "Run data hygiene",
            "This will:\n"
            "• Refresh service pricing (flat-fee vs transaction tiers)\n"
            "• Import departments from contacts\n"
            "• Link/create client workspace folders\n"
            "• Roll forward stale annual expiry dates (31 Dec services)\n"
            "• Migrate any legacy IRD passwords to Office Hub\n"
            "• Infer accounting service types from documents (Tax IDs rollout)\n"
            "• Import client liaison contacts into Office Hub\n"
            "• Infer VO/CSH renewal dates from document expiry\n\n"
            "Continue?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            result = run_data_hygiene(self.app.db, self.app.paths.clients)
        except Exception as exc:
            self.feedback.error(str(exc))
            return
        self._load_directory_lists()
        self._refresh_pricing_services()
        self._refresh_pricing_matrix()
        failed = int(result["folders_failed"])
        msg = (
            f"Pricing refreshed · {result['departments_imported']} dept(s) imported · "
            f"{result['expiry_dates_rolled']} expiry date(s) rolled forward · "
            f"{result.get('service_types_inferred', 0)} service type(s) inferred · "
            f"{result.get('liaison_contacts_created', 0)} liaison contact(s) imported · "
            f"{result.get('vo_renewals_inferred', 0)} VO + "
            f"{result.get('csh_renewals_inferred', 0)} CSH renewal(s) inferred · "
            f"{result.get('ird_passwords_migrated', 0)} IRD password(s) migrated · "
            f"{result['folders_linked']} folder(s) linked · "
            f"{result['folders_created']} folder(s) created"
        )
        if failed:
            self.feedback.error(f"{msg} · {failed} folder(s) failed")
        else:
            self.feedback.success(msg)
        self.app.set_status("Data hygiene complete")

    def _open_clients(self) -> None:
        self._open_path(self.app.paths.clients)
