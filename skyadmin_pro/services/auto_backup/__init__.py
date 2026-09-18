"""Scheduled auto-backup — daily/weekly encrypted backup with notification."""

from __future__ import annotations

from ._const_0 import annotations, logger, logging  # noqa: F403
from ._const_1 import SETTING_AUTO_BACKUP_ENABLED, annotations  # noqa: F403
from ._const_2 import SETTING_AUTO_BACKUP_INTERVAL, annotations  # noqa: F403
from ._const_3 import SETTING_AUTO_BACKUP_LAST_RUN, annotations  # noqa: F403
from ._const_4 import AUTO_BACKUP_KEEP, annotations  # noqa: F403
from .autoBackupSchedulerMixin0 import AutoBackupSchedulerMixin0
from .funcs import auto_backups_dir, prune_old_backups, retention_help_text, run_auto_backup, should_run_backup


class AutoBackupScheduler(AutoBackupSchedulerMixin0):
    pass
