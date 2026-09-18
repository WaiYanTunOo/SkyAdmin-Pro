"""File-level encryption — Sky Creation Innovations.

Machine-bound database encryption and universal-key encrypted backups.
Uses Fernet (AES-128-CBC + HMAC) from `cryptography`.
"""

from __future__ import annotations

from ._const_0 import annotations, logger, logging  # noqa: F403
from ._const_1 import MAGIC, annotations  # noqa: F403
from ._const_2 import WORKSPACE_PREFIX, annotations  # noqa: F403
from ._types import BackupArchiveInfo, RestoreSummary
from .funcs_0 import (  # noqa: F403
    Path,
    _copy_fallback,
    _looks_like_sqlite,
    _snapshot_db_for_backup,
    _verify_sqlite_payload,
    annotations,
    sqlite3,
)
from .funcs_1 import Path, _rewrite_db_paths, annotations  # noqa: F403
from .funcs_2 import (  # noqa: F403
    MAGIC,
    Path,
    _derive_backup_key,
    _derive_fernet_key,
    _derive_secret,
    _fernet_for_machine,
    _resolve_member_under,
    annotations,
    base64,
    format_byte_size,
    hashlib,
    is_encrypted,
)
from .funcs_3 import MAGIC, Path, annotations, decrypt_file, encrypt_file, is_encrypted, tempfile  # noqa: F403
from .funcs_4 import (  # noqa: F403
    MAGIC,
    WORKSPACE_PREFIX,
    BackupArchiveInfo,
    Path,
    _decrypt_backup_zip,
    _derive_backup_key,
    annotations,
    inspect_encrypted_backup,
    is_encrypted,
    tempfile,
    zipfile,
)
from .funcs_5 import (  # noqa: F403
    MAGIC,
    WORKSPACE_PREFIX,
    Path,
    _derive_backup_key,
    _snapshot_db_for_backup,
    annotations,
    create_encrypted_backup,
    tempfile,
    zipfile,
)
from .funcs_6 import (  # noqa: F403
    WORKSPACE_PREFIX,
    Path,
    RestoreSummary,
    _decrypt_backup_zip,
    _resolve_member_under,
    _rewrite_db_paths,
    _verify_sqlite_payload,
    annotations,
    remove_sqlite_sidecars,
    restore_encrypted_backup,
    zipfile,
)
