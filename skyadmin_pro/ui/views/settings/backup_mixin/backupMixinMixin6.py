from __future__ import annotations


class BackupMixinMixin6:
    def _backfill_drive_files(self) -> None:
        from skyadmin_pro.services.drive import backfill_local_files_to_drive, drive_connect_unlocked

        if not drive_connect_unlocked(self.app.db):
            self.feedback.error("Drive files are not enabled on this license.")
            return
        root = getattr(getattr(self.app, "paths", None), "root", None)
        result = backfill_local_files_to_drive(self.app.db, local_root=root)
        if not result.get("ok"):
            self.feedback.error(result.get("error") or "Drive backfill failed.")
            return
        self.feedback.success(
            f"Drive backfill: uploaded {result['uploaded']}, "
            f"skipped {result['skipped']}, errors {result.get('errors', 0)}."
        )
