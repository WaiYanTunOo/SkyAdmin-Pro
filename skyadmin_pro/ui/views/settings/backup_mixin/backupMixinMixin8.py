from __future__ import annotations


class BackupMixinMixin8:
    def _relink_and_backfill_drive_files(self) -> None:
        from skyadmin_pro.services.drive import drive_connect_unlocked, relink_and_backfill_to_drive

        if not drive_connect_unlocked(self.app.db):
            self.feedback.error("Drive files are not enabled on this license.")
            return
        root = getattr(getattr(self.app, "paths", None), "root", None)
        result = relink_and_backfill_to_drive(self.app.db, local_root=root)
        if not result.get("ok"):
            self.feedback.error(result.get("error") or "Relink / Drive upload failed.")
            return
        self.feedback.success(
            f"Relinked {result.get('relinked', 0)} "
            f"(ambiguous {result.get('ambiguous', 0)}), "
            f"uploaded {result.get('uploaded', 0)}, "
            f"skipped {result.get('skipped', 0)}, "
            f"errors {result.get('errors', 0)}."
        )
