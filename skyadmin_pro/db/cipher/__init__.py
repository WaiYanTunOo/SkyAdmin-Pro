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

from ._const_1 import CIPHER_KDF_ITERATIONS
from ._const_2 import CIPHER_PBKDF2_ITERATIONS
from ._const_3 import SQLITE_MAGIC
from ._const_4 import (
    HAS_CIPHER,
    CipherConnection,
    CipherDatabaseError,
    CipherError,
    CipherIntegrityError,
    CipherOperationalError,
    CipherProgrammingError,
    CipherRow,
)
from ._const_5 import DBConnection
from ._const_6 import DB_ERRORS
from ._const_7 import INTEGRITY_ERRORS
from ._const_8 import OPERATIONAL_ERRORS
from .funcs_0 import (
    _machine_salt,
    connect,
    db_state,
    derive_db_key_hex,
    driver,
    verify_cipher_db,
)
from .funcs_1 import migrate_plaintext_to_cipher
