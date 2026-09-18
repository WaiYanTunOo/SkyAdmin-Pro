from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackupArchiveInfo:
    has_database: bool
    database_bytes: int
    workspace_file_count: int
    workspace_bytes: int
    encrypted_bytes: int


@dataclass(frozen=True)
class RestoreSummary:
    database_bytes: int
    workspace_files_restored: int
    workspace_bytes: int
    paths_rewritten: int = 0
