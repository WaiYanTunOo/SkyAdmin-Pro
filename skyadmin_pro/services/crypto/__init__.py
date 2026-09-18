"""File-level encryption — Sky Creation Innovations.

Machine-bound database encryption and universal-key encrypted backups.
Uses Fernet (AES-128-CBC + HMAC) from `cryptography`.
"""

from __future__ import annotations

from ._const_1 import MAGIC
from ._const_2 import WORKSPACE_PREFIX
from ._types import BackupArchiveInfo, RestoreSummary
from .funcs_0 import _copy_fallback, _looks_like_sqlite, _snapshot_db_for_backup, _verify_sqlite_payload
from .funcs_1 import _rewrite_db_paths
from .funcs_2 import (
    _derive_backup_key,
    _derive_fernet_key,
    _fernet_for_machine,
    _resolve_member_under,
    format_byte_size,
    is_encrypted,
)
from .funcs_3 import decrypt_file, encrypt_file
from .funcs_4 import _decrypt_backup_zip, inspect_encrypted_backup
from .funcs_5 import create_encrypted_backup
from .funcs_6 import restore_encrypted_backup

__all__ = [
    "MAGIC",
    "WORKSPACE_PREFIX",
    "BackupArchiveInfo",
    "RestoreSummary",
    "create_encrypted_backup",
    "decrypt_file",
    "encrypt_file",
    "format_byte_size",
    "inspect_encrypted_backup",
    "is_encrypted",
    "restore_encrypted_backup",
]
