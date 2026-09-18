"""SQLCipher live-database encryption (Phase 1).

The live ``skyadmin_pro.db`` is encrypted with SQLCipher (AES-256-CBC +
HMAC), keyed by a machine-bound PBKDF2 derivation. This module owns the
driver import, key derivation, plaintext detection, and the one-time
plaintext-to-cipher migration.

Conventions:
* Key format on the wire: ``PRAGMA key = "x'<64 hex chars>'"``.
* KDF iterations for connection open are lowered from the SQLCipher
  default (256k) to 64k: the key itself is 256-bit machine-bound entropy,
  so iteration count is defense-in-depth, and every pooled checkout pays
  the derivation cost.
* Tests set ``SKYADMIN_CIPHER_SALT`` (see ``tests/conftest.py``) so the
  suite never touches the real ``hardware.id``.
"""

from __future__ import annotations

from ._const_0 import annotations, logger, logging  # noqa: F403
from ._const_1 import CIPHER_KDF_ITERATIONS, annotations  # noqa: F403
from ._const_2 import CIPHER_PBKDF2_ITERATIONS, annotations  # noqa: F403
from ._const_3 import SQLITE_MAGIC, annotations  # noqa: F403
from ._const_4 import (  # noqa: F403
    HAS_CIPHER,
    Any,
    CipherConnection,
    CipherDatabaseError,
    CipherError,
    CipherIntegrityError,
    CipherOperationalError,
    CipherProgrammingError,
    CipherRow,
    annotations,
)
from ._const_5 import Any, DBConnection, annotations  # noqa: F403
from ._const_6 import DB_ERRORS, annotations, sqlite3  # noqa: F403
from ._const_7 import INTEGRITY_ERRORS, CipherIntegrityError, annotations, sqlite3  # noqa: F403
from ._const_8 import OPERATIONAL_ERRORS, CipherOperationalError, annotations, sqlite3  # noqa: F403
from .funcs_0 import (  # noqa: F403
    CIPHER_KDF_ITERATIONS,
    CIPHER_PBKDF2_ITERATIONS,
    HAS_CIPHER,
    SQLITE_MAGIC,
    Any,
    Path,
    _machine_salt,
    annotations,
    connect,
    db_state,
    derive_db_key_hex,
    driver,
    hashlib,
    logger,
    os,
    verify_cipher_db,
)
from .funcs_1 import (  # noqa: F403
    Path,
    _table_names,
    annotations,
    connect,
    db_state,
    derive_db_key_hex,
    logger,
    migrate_plaintext_to_cipher,
    os,
    sqlite3,
)
